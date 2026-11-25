"""Сборка колоды: вкус (веса жанров) + взвешенный рандом + антиповторы + немного исследования.

Чистые функции без обращения к БД -> легко тестировать."""
import math
import random
from collections.abc import Iterable, Sequence
from datetime import datetime, timedelta, timezone

from .catalog import CatalogItem

RATING_DELTA = {1: -2, 2: -1, 3: 1, 4: 2, 5: 3}   # как в клиенте
TIER_FRESH, TIER_SOFT, TIER_LIKED = 0, 1, 2          # порядок "свежести": сначала новые, потом остальное


def signal_bonus(opened_details: bool, dwell_ms: int) -> float:
    """Слабый положительный сигнал: открыл «Подробнее» (+0.5), думал над карточкой >= 5 c (+0.25)."""
    return (0.5 if opened_details else 0.0) + (0.25 if dwell_ms >= 5000 else 0.0)


def session_weights(initial_genres: Iterable[str], swipes: Iterable[tuple]) -> dict[str, float]:
    """Веса жанров сессии. Считаются из неотменённых свайпов -> undo не расходится с клиентом.
    Элемент swipes: (action, rating, genres) или (action, rating, genres, bonus).
    bonus (см. signal_bonus) прибавляется только к right/up: отказ после чтения остаётся отказом."""
    w: dict[str, float] = {}
    for g in initial_genres:
        w[g] = w.get(g, 0) + 2
    for item in swipes:
        action, rating, genres = item[0], item[1], item[2]
        bonus = item[3] if len(item) > 3 else 0.0
        if action == "right":
            delta = 2 + bonus
        elif action == "left":
            delta = -1
        else:
            delta = RATING_DELTA.get(rating or 3, 1) + bonus
        for g in genres:
            w[g] = w.get(g, 0) + delta
    return w


def affinity(genres: Sequence[str], weights: dict[str, float]) -> float:
    # нормируем на sqrt(числа жанров), чтобы фильмы с 4 жанрами не выигрывали всегда
    if not genres:
        return 0.0
    return sum(weights.get(g, 0) for g in genres) / math.sqrt(len(genres))


def quality_of(rating: float | None) -> float:
    r = rating if rating is not None else 6.5
    return 0.6 + r / 10.0


def quality(item: CatalogItem) -> float:
    return quality_of(item.rating)


def rank_score(genres: Sequence[str], rating: float | None, weights: dict[str, float]) -> float:
    """Ранг для итоговой рекомендации: выученный вкус + рейтинг."""
    return affinity(genres, weights) + 2 * quality_of(rating)


def match_percent(genres: Sequence[str], rating: float | None, weights: dict[str, float]) -> int:
    """Читаемый «процент совпадения» 35..99 (не вероятность, а нормированный ранг)."""
    r = rating if rating is not None else 6.5
    return max(35, min(98, round(50 + 40 * math.tanh(affinity(genres, weights) / 8) + 3 * (r - 6.5))))


def match_reasons(genres: Sequence[str], rating: float | None, weights: dict[str, float],
                  initial_genres: Sequence[str], liked: Sequence[tuple[str, Sequence[str]]],
                  self_id: int | None = None, liked_ids: Sequence[int] = ()) -> list[str]:
    """До двух коротких причин на русском. liked = [(название, жанры)] сохранённых фильмов."""
    out: list[str] = []
    chosen = [g for g in genres if g in initial_genres]
    if chosen:
        out.append("Жанр, который вы выбрали: " + ", ".join(chosen[:2]))
    else:
        pos = [g for g in genres if weights.get(g, 0) > 0]
        if pos:
            out.append("Вам близко: " + ", ".join(pos[:2]))
    similar = [t for (t, g), lid in zip(liked, liked_ids or [None] * len(liked))
               if lid != self_id and set(g) & set(genres)][:2]
    if similar:
        out.append("Похож на " + " и ".join(f"«{t}»" for t in similar))
    if rating is not None and rating >= 7.5:
        out.append(f"Высокий рейтинг {rating:.1f}")
    return out[:2]


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


def _age_value(value) -> int | None:
    try:
        return int(str(value).replace("+", "").strip())
    except (TypeError, ValueError):
        return None          # неизвестный возраст не отсеиваем


def _pool(catalog: Sequence[CatalogItem], *, n: int, excluded: set[int], filters: dict,
          strict_genres: Sequence[str], surprise: bool) -> list[CatalogItem]:
    """Кандидаты после фильтров. Пустые поля (длительность/рейтинг/возраст = None) фильтры НЕ отсеивают."""
    pool = [c for c in catalog if c.id not in excluded]
    content_type = filters.get("content_type", "all")
    if content_type == "films":
        pool = [c for c in pool if c.type.lower() not in {"сериал", "series", "tv series"}]
    elif content_type == "series":
        pool = [c for c in pool if c.type.lower() in {"сериал", "series", "tv series"}]
    year_from, year_to = filters.get("year_from"), filters.get("year_to")
    if year_from:
        pool = [c for c in pool if c.year is not None and c.year >= int(year_from)]
    if year_to:
        pool = [c for c in pool if c.year is not None and c.year <= int(year_to)]
    max_duration = filters.get("max_duration")
    if max_duration:
        pool = [c for c in pool if c.duration_min is None or c.duration_min <= int(max_duration)]
    min_rating = filters.get("min_rating")
    if min_rating:
        pool = [c for c in pool if c.rating is None or c.rating >= float(min_rating)]
    max_age = filters.get("max_age")
    if max_age:
        pool = [c for c in pool if _age_value(c.age) is None or _age_value(c.age) <= int(max_age)]
    if strict_genres and not surprise:          # выбранные жанры = жёсткий фильтр
        wanted = set(strict_genres)
        pool = [c for c in pool if wanted & set(c.genres)]
    if surprise:
        good = [c for c in pool if (c.rating or 0) >= 7.0]
        if len(good) >= n * 3:
            pool = good
    return pool


def _allowed_tiers(strict_genres: Sequence[str], surprise: bool) -> tuple[int, ...]:
    # По жанрам не повторяем ничего (скипнутые, лайкнутые, прошлая сессия) — лучше закончить раньше.
    return (TIER_FRESH,) if strict_genres and not surprise else (TIER_FRESH, TIER_SOFT, TIER_LIKED)


def count_available(catalog: Sequence[CatalogItem], *, n: int, excluded: set[int], tiers: dict[int, int],
                    surprise: bool = False, filters: dict | None = None,
                    strict_genres: Sequence[str] = ()) -> int:
    """Сколько карточек ещё можно показать (с учётом фильтров, жанров и правил антиповторов)."""
    pool = _pool(catalog, n=n, excluded=excluded, filters=filters or {},
                 strict_genres=strict_genres, surprise=surprise)
    allowed = _allowed_tiers(strict_genres, surprise)
    return sum(1 for c in pool if tiers.get(c.id, TIER_FRESH) in allowed)


def build_batch(catalog: Sequence[CatalogItem], *, n: int, weights: dict[str, float],
                excluded: set[int], tiers: dict[int, int], rng: random.Random,
                surprise: bool = False, explore_ratio: float = 0.2, temperature: float = 3.0,
                history_primary: Sequence[str] = (), filters: dict | None = None,
                strict_genres: Sequence[str] = ()) -> list[CatalogItem]:
    pool = _pool(catalog, n=n, excluded=excluded, filters=filters or {},
                 strict_genres=strict_genres, surprise=surprise)
    strict = bool(strict_genres) and not surprise
    if strict:
        explore_ratio = 0.0                      # никаких «исследовательских» карточек вне жанра
    if surprise:
        temperature = 1e6   # почти равномерно

    def w_of(c: CatalogItem) -> float:
        a = max(-6.0, min(6.0, affinity(c.genres, weights) / temperature))
        return math.exp(a) * quality(c)

    chosen: list[CatalogItem] = []
    for tier in _allowed_tiers(strict_genres, surprise):
        need = n - len(chosen)
        if need <= 0:
            break
        cands = [c for c in pool if tiers.get(c.id, TIER_FRESH) == tier]
        if not cands:
            continue
        take = min(need, len(cands))
        if tier == TIER_FRESH and not surprise and explore_ratio > 0 and take >= 4:
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


def recommend_pool(catalog: Sequence[CatalogItem], *, n: int, excluded: set[int], tiers: dict[int, int],
                   weights: dict[str, float], surprise: bool = False, filters: dict | None = None,
                   strict_genres: Sequence[str] = ()) -> list[CatalogItem]:
    """Непоказанные/нереагированные кандидаты для итога, лучшие по рангу первыми. Только «свежие»."""
    pool = _pool(catalog, n=n, excluded=excluded, filters=filters or {},
                 strict_genres=strict_genres, surprise=surprise)
    fresh = [c for c in pool if tiers.get(c.id, TIER_FRESH) == TIER_FRESH]
    return sorted(fresh, key=lambda c: (-rank_score(c.genres, c.rating, weights), c.id))
