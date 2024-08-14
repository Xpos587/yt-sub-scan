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


async def create_tables(conn):
    logger.info("Создание таблиц, если они не существуют")
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS video_data (
            video_id TEXT PRIMARY KEY,
            title TEXT,
            description TEXT,
            views INT,
            likes INT,
            comments INT,
            duration INT,
            publish_date TIMESTAMP,
            channel_id TEXT,
            channel_title TEXT,
            last_updated TIMESTAMP,
            search_query TEXT,
            position INT
        )
    """
    )
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS subtitle_data (
            video_id TEXT PRIMARY KEY REFERENCES video_data(video_id),
            subtitle_json JSONB,
            is_auto_generated BOOLEAN
        )
    """
    )
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS api_keys (
            api_key TEXT PRIMARY KEY,
            daily_usage INT DEFAULT 0,
            is_banned BOOLEAN DEFAULT FALSE,
            quota_exceeded BOOLEAN DEFAULT FALSE,
            last_used DATE DEFAULT CURRENT_DATE
        )
    """
    )
