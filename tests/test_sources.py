from app.services.sources import make_hook, parse_itunes_item, parse_kp_detail, parse_kp_list_item


def test_parse_kp_list_item():
    d = parse_kp_list_item({
        "kinopoiskId": 435, "nameRu": "Зелёная миля", "nameEn": None, "nameOriginal": "The Green Mile",
        "ratingKinopoisk": 9.1, "ratingImdb": 8.6, "year": "1999", "type": "FILM",
        "genres": [{"genre": "драма"}, {"genre": "криминал"}, {"genre": "фэнтези"}],
        "posterUrl": "https://kp.example/p.jpg"})
    assert d.source_id == "435" and d.year == 1999 and d.genres == ["Драма", "Криминал", "Мистика"]
    assert d.original_title == "The Green Mile" and d.kp_rating == 9.1


def test_kp_list_item_without_poster_or_genres_is_skipped():
    assert parse_kp_list_item({"kinopoiskId": 1, "nameRu": "X", "genres": [{"genre": "документальный"}], "posterUrl": "u"}) is None
    assert parse_kp_list_item({"kinopoiskId": 1, "nameRu": "X", "genres": [{"genre": "драма"}]}) is None


def test_parse_kp_detail():
    r = parse_kp_detail({"description": "Первое предложение. Второе.", "filmLength": 189,
                         "ratingAgeLimits": "age16", "ratingKinopoiskVoteCount": 1000,
                         "webUrl": "https://www.kinopoisk.ru/film/435/"})
    assert r["age"] == "16+" and r["duration_min"] == 189 and r["short_hook"] == "Первое предложение."


def test_parse_itunes_item():
    d = parse_itunes_item({"kind": "feature-movie", "trackId": 7, "trackName": "Начало",
                           "releaseDate": "2010-07-16T07:00:00Z", "primaryGenreName": "Боевик и приключения",
                           "longDescription": "Профессиональный вор крадёт секреты из подсознания во время сна. " * 2,
                           "artworkUrl100": "https://a/100x100bb.jpg", "trackTimeMillis": 8880000,
                           "trackViewUrl": "https://tv.apple.com/x"})
    assert d.year == 2010 and d.genres == ["Экшен", "Приключения"] and d.duration_min == 148
    assert d.poster_url.endswith("600x900bb.jpg")
    assert parse_itunes_item({"kind": "song"}) is None


def test_make_hook_truncates():
    assert len(make_hook("слово " * 100)) <= 175
