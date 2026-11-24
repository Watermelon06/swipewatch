"""Нормализация жанров под 10 жанров приложения (те же, что в клиенте)."""
import re

ALL_GENRES = ['Триллер', 'Детектив', 'Драма', 'Фантастика', 'Приключения',
              'Криминал', 'Экшен', 'Комедия', 'Мистика', 'Хоррор']

# подстрока (lowercase) -> жанр приложения. Работает и для русских, и для английских названий.
_KEYWORDS = [
    ("триллер", "Триллер"), ("thriller", "Триллер"), ("suspense", "Триллер"),
    ("детектив", "Детектив"), ("mystery", "Детектив"),
    ("драм", "Драма"), ("drama", "Драма"),
    ("фантаст", "Фантастика"), ("sci-fi", "Фантастика"), ("science fiction", "Фантастика"),
    ("приключ", "Приключения"), ("adventure", "Приключения"),
    ("криминал", "Криминал"), ("crime", "Криминал"), ("нуар", "Криминал"), ("noir", "Криминал"),
    ("боевик", "Экшен"), ("action", "Экшен"),
    ("комед", "Комедия"), ("comedy", "Комедия"),
    ("мистик", "Мистика"), ("фэнтези", "Мистика"), ("fantasy", "Мистика"),
    ("ужас", "Хоррор"), ("horror", "Хоррор"),
]


def normalize_genres(raw: list[str]) -> list[str]:
    out: list[str] = []
    for item in raw:
        low = (item or "").lower()
        # порядок жанров внутри одной строки — как в тексте ("Боевик и приключения" -> Экшен, Приключения)
        hits = sorted((low.find(key), genre) for key, genre in _KEYWORDS if key in low)
        for _, genre in hits:
            if genre not in out:
                out.append(genre)
    return out


def dedupe_key(title: str, year: int | None) -> str:
    norm = re.sub(r"[\W_]+", "", (title or "").lower())
    return f"{norm}|{year or 0}"
