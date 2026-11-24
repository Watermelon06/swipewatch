"""Сборка колоды: вкус (веса жанров) + взвешенный рандом + антиповторы + немного исследования.

Чистые функции без обращения к БД -> легко тестировать."""
import math
import random
from collections.abc import Iterable, Sequence
from datetime import datetime, timedelta, timezone

from .catalog import CatalogItem

RATING_DELTA = {1: -2, 2: -1, 3: 1, 4: 2, 5: 3}   # как в клиенте
TIER_FRESH, TIER_SOFT, TIER_LIKED = 0, 1, 2          # порядок "свежести": сначала новые, потом остальное


def session_weights(initial_genres: Iterable[str],
                    swipes: Iterable[tuple[str, int | None, Sequence[str]]]) -> dict[str, float]:
    """Веса жанров сессии. Считаются из неотменённых свайпов -> undo не расходится с клиентом."""
    w: dict[str, float] = {}
    for g in initial_genres:
        w[g] = w.get(g, 0) + 2
    for action, rating, genres in swipes:
        if action == "right":
            delta = 2
        elif action == "left":
            delta = -1
        else:
            delta = RATING_DELTA.get(rating or 3, 1)
        for g in genres:
            w[g] = w.get(g, 0) + delta
    return w


def affinity(genres: Sequence[str], weights: dict[str, float]) -> float:
    # нормируем на sqrt(числа жанров), чтобы фильмы с 4 жанрами не выигрывали всегда
    if not genres:
        return 0.0
    return sum(weights.get(g, 0) for g in genres) / math.sqrt(len(genres))


def quality(item: CatalogItem) -> float:
    r = item.rating if item.rating is not None else 6.5
    return 0.6 + r / 10.0


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def compute_tiers(states: dict[int, tuple[str, datetime]], last_session_ids: set[int],
                  now: datetime, skip_cooldown_days: int) -> tuple[dict[int, int], set[int]]:
    """Возвращает (tier по id, множество жёстко исключённых = просмотренные)."""
    tiers: dict[int, int] = {}
    hard: set[int] = set()
    for mid, (state, updated) in states.items():
        if state == "watched":
            hard.add(mid)
        elif state == "liked":
            tiers[mid] = TIER_LIKED
        elif state == "skipped" and _aware(updated) > now - timedelta(days=skip_cooldown_days):
            tiers[mid] = TIER_SOFT
    for mid in last_session_ids:          # выдавали в прошлой сессии -> чтобы старт не повторялся
        tiers.setdefault(mid, TIER_SOFT)
    return tiers, hard


def weighted_sample(items: Sequence[CatalogItem], weights: Sequence[float], k: int,
                    rng: random.Random) -> list[CatalogItem]:
    """Efraimidis–Spirakis: ключ = log(u)/w, берём k наибольших. Лучшие чаще, но порядок каждый раз разный."""
    if k <= 0 or not items:
        return []
    keyed = []
    for it, w in zip(items, weights):
        w = max(w, 1e-9)
        keyed.append((math.log(1.0 - rng.random()) / w, it.id, it))
    keyed.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [it for _, _, it in keyed[:k]]


def _primary(item: CatalogItem) -> str:
    return item.genres[0] if item.genres else ""


def enforce_diversity(items: list[CatalogItem], history_primary: Sequence[str], max_run: int = 3) -> list[CatalogItem]:
    """Не больше max_run подряд карточек с одним основным жанром."""
    result: list[CatalogItem] = []
    remaining = list(items)
    hist = list(history_primary)
    while remaining:
        pick = None
        for c in remaining:
            tail = hist[-max_run:]
            if len(tail) == max_run and all(x == _primary(c) for x in tail):
                continue
            pick = c
            break
        pick = pick or remaining[0]
        remaining.remove(pick)
        result.append(pick)
        hist.append(_primary(pick))
    return result


def _interleave(main: list[CatalogItem], explore: list[CatalogItem]) -> list[CatalogItem]:
    out = list(main)
    for i, e in enumerate(explore):
        out.insert(min(len(out), 3 + 4 * i), e)   # "неожиданные" на 4-й, 8-й, 12-й позиции
    return out


def build_batch(catalog: Sequence[CatalogItem], *, n: int, weights: dict[str, float],
                excluded: set[int], tiers: dict[int, int], rng: random.Random,
                surprise: bool = False, explore_ratio: float = 0.2, temperature: float = 3.0,
                history_primary: Sequence[str] = ()) -> list[CatalogItem]:
    pool = [c for c in catalog if c.id not in excluded]
    if surprise:
        good = [c for c in pool if (c.rating or 0) >= 7.0]
        if len(good) >= n * 3:
            pool = good
        temperature = 1e6   # почти равномерно

    def w_of(c: CatalogItem) -> float:
        a = max(-6.0, min(6.0, affinity(c.genres, weights) / temperature))
        return math.exp(a) * quality(c)

    chosen: list[CatalogItem] = []
    for tier in (TIER_FRESH, TIER_SOFT, TIER_LIKED):
        need = n - len(chosen)
        if need <= 0:
            break
        cands = [c for c in pool if tiers.get(c.id, TIER_FRESH) == tier]
        if not cands:
            continue
        take = min(need, len(cands))
        if tier == TIER_FRESH and not surprise and take >= 4:
            n_exp = round(take * explore_ratio)
            main = weighted_sample(cands, [w_of(c) for c in cands], take - n_exp, rng)
            taken = {c.id for c in main}
            rest = [c for c in cands if c.id not in taken]
            exp_pool = [c for c in rest if affinity(c.genres, weights) <= 0] or rest
            exp = weighted_sample(exp_pool, [quality(c) for c in exp_pool], n_exp, rng)
            chosen += _interleave(main, exp)
        else:
            chosen += weighted_sample(cands, [w_of(c) for c in cands], take, rng)
    return enforce_diversity(chosen, history_primary)
