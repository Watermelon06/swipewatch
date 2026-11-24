"""Подтянуть фильмы из Кинопоиска и iTunes/Apple TV в БД.

  python -m scripts.sync_catalog                  # KP + iTunes, лимит 450 запросов к KP
  python -m scripts.sync_catalog --budget 300     # меньше запросов
  python -m scripts.sync_catalog --no-itunes      # только Кинопоиск

Бесплатный тариф kinopoiskapiunofficial.tech — ~500 запросов в сутки (проверь свой тариф),
поэтому запускай раз в сутки: каталог накапливается (на каждом запуске дозагружаются описания)."""
import argparse
import asyncio

from app.config import get_settings
from app.db import SessionLocal, engine
from app.models import Base
from app.services.sync import run_sync


async def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--budget", type=int, default=450, help="максимум запросов к Кинопоиску за запуск")
    p.add_argument("--no-itunes", action="store_true")
    args = p.parse_args()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    report = await run_sync(SessionLocal, get_settings().kp_api_key, args.budget, not args.no_itunes)
    print(f"KP запросов: {report.kp_requests} | новых: {report.added} | обновлено: {report.updated} | "
          f"описаний подгружено: {report.enriched} | iTunes новых: {report.itunes_added}")
    for e in report.errors[:10]:
        print("  !", e)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
