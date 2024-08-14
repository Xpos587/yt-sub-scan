import asyncio
from pathlib import Path

import asyncpg

from scripts.config import (
    POSTGRES_DB,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
    POSTGRES_USER,
)
from scripts.logger import logger


async def init_db():
    logger.info("Инициализация подключения к базе данных")
    return await asyncpg.connect(
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        database=POSTGRES_DB,
        host=POSTGRES_HOST,
    )


async def import_api_keys(file_path: str):
    conn = await init_db()
    try:
        async with conn.transaction():
            with open(file_path, "r") as file:
                api_keys = file.read().strip().split("\n")
                for api_key in api_keys:
                    api_key = api_key.strip()
                    if api_key:
                        # Проверка на уникальность
                        exists = await conn.fetchval(
                            "SELECT COUNT(*) FROM api_keys WHERE api_key = $1",
                            api_key,
                        )
                        if exists == 0:
                            await conn.execute(
                                "INSERT INTO api_keys (api_key) VALUES ($1)",
                                api_key,
                            )
                            logger.info(
                                f"API ключ {api_key} успешно добавлен в БД."
                            )
                        else:
                            logger.warning(
                                f"API ключ {api_key} уже существует в БД."
                            )
    finally:
        await conn.close()


def main():
    file_path = Path(__file__).parent.parent / "api_keys.txt"
    asyncio.run(import_api_keys(str(file_path)))


if __name__ == "__main__":
    main()
