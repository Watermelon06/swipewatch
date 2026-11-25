import asyncio
import os
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import MetaData, Table, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import create_async_engine

# Чтобы импортировался app.models при запуске из корня проекта
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.models import Base  # noqa: E402


def to_asyncpg_url(raw_url: str) -> str:
    url = raw_url.strip()
    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://") :]
    elif url.startswith("postgres://"):
        url = "postgresql+asyncpg://" + url[len("postgres://") :]

    parts = urlsplit(url)
    filtered_q = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if k.lower() not in {"sslmode", "channel_binding", "ssl"}
    ]
    new_query = urlencode(filtered_q)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))


async def migrate_movies() -> None:
    neon_raw = os.environ["NEON_DATABASE_URL"]
    amvera_raw = os.environ["AMVERA_DATABASE_URL"]

    src_engine = create_async_engine(to_asyncpg_url(neon_raw), connect_args={"ssl": "require"})
    # Для внешнего домена Amvera (*.amvera.tech) требуется SSL; если подключаешься по внутреннему cnpg-*-rw, ssl можно убрать
    dst_ssl = "require" if ".amvera.tech" in amvera_raw else False
    dst_engine = create_async_engine(
        to_asyncpg_url(amvera_raw),
        connect_args={"ssl": dst_ssl} if dst_ssl else {},
    )

    src_meta = MetaData()
    async with src_engine.begin() as conn:
        await conn.run_sync(lambda c: src_meta.reflect(bind=c, only=["movies"]))

    async with dst_engine.begin() as conn:
        # Создаст все таблицы из app/models.py, если их ещё нет в базе
        await conn.run_sync(Base.metadata.create_all)

    dst_meta = MetaData()
    async with dst_engine.begin() as conn:
        await conn.run_sync(lambda c: dst_meta.reflect(bind=c, only=["movies"]))

    src_table: Table = src_meta.tables["movies"]
    dst_table: Table = dst_meta.tables["movies"]

    async with src_engine.connect() as conn:
        rows = (await conn.execute(select(src_table))).mappings().all()

    print(f"Прочитано фильмов из Neon: {len(rows)}")
    if not rows:
        await src_engine.dispose()
        await dst_engine.dispose()
        return

    pk_cols = [col.name for col in dst_table.primary_key.columns] or ["id"]
    non_pk_cols = [col.name for col in dst_table.columns if col.name not in pk_cols]

    batch_size = 500
    inserted_total = 0

    async with dst_engine.begin() as conn:
        for i in range(0, len(rows), batch_size):
            batch = [dict(r) for r in rows[i : i + batch_size]]
            stmt = insert(dst_table).values(batch)
            if non_pk_cols:
                stmt = stmt.on_conflict_do_update(
                    index_elements=pk_cols,
                    set_={col: getattr(stmt.excluded, col) for col in non_pk_cols},
                )
            else:
                stmt = stmt.on_conflict_do_nothing(index_elements=pk_cols)
            await conn.execute(stmt)
            inserted_total += len(batch)
            print(f"Перенесено батчем: {inserted_total}/{len(rows)}")

    await src_engine.dispose()
    await dst_engine.dispose()
    print("Готово! Таблица movies перенесена.")


if __name__ == "__main__":
    asyncio.run(migrate_movies())