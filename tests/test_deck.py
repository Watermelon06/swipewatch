import random

from app.services import deck
from app.services.catalog import CatalogItem
from app.services.genres import ALL_GENRES, dedupe_key, normalize_genres


def catalog(n=60, seed=3):
    r = random.Random(seed)
    return [CatalogItem(i, tuple(r.sample(ALL_GENRES, r.randint(1, 3))), round(r.uniform(6, 9), 1), "kp")
            for i in range(n)]


def test_weights_match_client_rules():
    w = deck.session_weights(["Драма"], [("right", None, ["Драма", "Триллер"]), ("left", None, ["Комедия"]),
                                          ("up", 5, ["Драма"]), ("up", 1, ["Хоррор"])])
    assert w == {"Драма": 2 + 2 + 3, "Триллер": 2, "Комедия": -1, "Хоррор": -2}


def test_no_duplicates_and_respects_exclusions():
    c = catalog()
    batch = deck.build_batch(c, n=20, weights={}, excluded={0, 1, 2}, tiers={}, rng=random.Random(1))
    ids = [x.id for x in batch]
    assert len(ids) == len(set(ids)) == 20
    assert not {0, 1, 2} & set(ids)


def test_different_seeds_give_different_decks():
    c = catalog(200)
    decks = {tuple(x.id for x in deck.build_batch(c, n=8, weights={}, excluded=set(), tiers={},
                                                   rng=random.Random(s))) for s in range(10)}
    assert len(decks) > 5


def test_taste_is_followed_but_not_exclusively():
    c = catalog(300)
    w = {"Хоррор": 6}
    hits = 0
    for s in range(30):
        b = deck.build_batch(c, n=10, weights=w, excluded=set(), tiers={}, rng=random.Random(s))
        hits += sum("Хоррор" in x.genres for x in b)
    share = hits / 300
    base = sum("Хоррор" in x.genres for x in c) / len(c)
    assert share > base + 0.1 and share < 0.95


def test_fresh_before_soft_tiers():
    c = catalog(30)
    tiers = {i: deck.TIER_SOFT for i in range(0, 15)}
    b = deck.build_batch(c, n=10, weights={}, excluded=set(), tiers=tiers, rng=random.Random(1))
    assert all(x.id >= 15 for x in b)
    b = deck.build_batch(c, n=25, weights={}, excluded=set(), tiers=tiers, rng=random.Random(1))
    assert len({x.id for x in b}) == 25      # когда свежих не хватает, добираем из мягких


def test_diversity_max_run():
    items = [CatalogItem(i, ("Драма",), 7, "kp") for i in range(6)] + [CatalogItem(10 + i, ("Комедия",), 7, "kp") for i in range(3)]
    out = deck.enforce_diversity(items, [], max_run=3)
    run = best = 0
    prev = None
    for x in out[:9]:
        run = run + 1 if x.genres[0] == prev else 1
        prev = x.genres[0]
        best = max(best, run)
    assert best <= 3


def test_genre_normalization_and_dedupe():
    assert normalize_genres(["боевик", "драма"]) == ["Экшен", "Драма"]
    assert normalize_genres(["Action & Adventure"]) == ["Экшен", "Приключения"]
    assert normalize_genres(["мелодрама"]) == ["Драма"]   # осознанно: мелодрама ~ драма
    assert normalize_genres(["документальный", "мультфильм"]) == []
    assert dedupe_key("Остров проклятых!", 2010) == dedupe_key("остров  проклятых", 2010)
