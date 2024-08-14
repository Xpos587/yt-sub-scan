import asyncio
import random

import cachetools
from googleapiclient.discovery import HttpError, build

from scripts.config import (
    SEARCH_QUERIES,
    YOUTUBE_API_SERVICE_NAME,
    YOUTUBE_API_VERSION,
)
from scripts.logger import logger

video_cache = cachetools.TTLCache(
    maxsize=100000, ttl=86400
)  # Кэш на 100,000 видео с временем жизни 24 часа


async def get_valid_api_key(conn):
    while True:
        api_key = await conn.fetchrow(
            """
            SELECT api_key FROM api_keys
            WHERE NOT is_banned AND NOT quota_exceeded AND (last_used != CURRENT_DATE OR daily_usage < 10000)
            ORDER BY daily_usage ASC
            LIMIT 1
        """
        )

        if api_key:
            return api_key["api_key"]

        logger.warning("Нет доступных API ключей. Ожидание 1 час.")
        await asyncio.sleep(3600)


async def update_api_key_usage(conn, api_key):
    await conn.execute(
        """
        UPDATE api_keys
        SET daily_usage = CASE
            WHEN last_used = CURRENT_DATE THEN daily_usage + 1
            ELSE 1
        END,
        last_used = CURRENT_DATE
        WHERE api_key = $1
    """,
        api_key,
    )


async def mark_api_key_as_banned(conn, api_key):
    await conn.execute(
        "UPDATE api_keys SET is_banned = TRUE WHERE api_key = $1", api_key
    )


async def mark_api_key_quota_exceeded(conn, api_key):
    await conn.execute(
        "UPDATE api_keys SET quota_exceeded = TRUE WHERE api_key = $1", api_key
    )


async def fetch_videos(conn, published_after, page_token=None):
    api_key = await get_valid_api_key(conn)
    youtube = build(
        YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=api_key
    )

    logger.info(f"Запрос видео, опубликованных после {published_after}")
    search_query = random.choice(SEARCH_QUERIES)
    logger.info(f"Выбран поисковый запрос: {search_query}")

    try:
        request = youtube.search().list(
            part="id,snippet",
            safeSearch="none",
            maxResults=50,
            regionCode="RU",
            relevanceLanguage="ru",
            type="video",
            order="relevance",
            q=search_query,
            publishedAfter=published_after.isoformat() + "Z",
            videoDuration="medium",
            videoCaption="closedCaption",
            pageToken=page_token,
        )
        response = await asyncio.to_thread(request.execute)
        await update_api_key_usage(conn, api_key)
        return response, search_query
    except HttpError as e:
        if "quotaExceeded" in str(e):
            await mark_api_key_quota_exceeded(conn, api_key)
            logger.warning(
                f"Квота превышена для ключа {api_key}. Попытка использовать другой ключ."
            )
            return await fetch_videos(conn, published_after, page_token)
        elif e.resp.status in [400, 403]:
            await mark_api_key_as_banned(conn, api_key)
            logger.warning(
                f"Ключ {api_key} забанен. Попытка использовать другой ключ."
            )
            return await fetch_videos(conn, published_after, page_token)
        else:
            raise


async def get_video_details(conn, video_ids):
    api_key = await get_valid_api_key(conn)
    youtube = build(
        YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=api_key
    )

    logger.info(f"Получение деталей для видео: {video_ids}")
    uncached_ids = [vid for vid in video_ids if vid not in video_cache]

    if uncached_ids:
        try:
            request = youtube.videos().list(
                part="snippet,statistics,contentDetails",
                id=",".join(uncached_ids),
            )
            response = await asyncio.to_thread(request.execute)
            await update_api_key_usage(conn, api_key)
            for item in response["items"]:
                video_cache[item["id"]] = item
        except HttpError as e:
            if "quotaExceeded" in str(e):
                await mark_api_key_quota_exceeded(conn, api_key)
                logger.warning(
                    f"Квота превышена для ключа {api_key}. Попытка использовать другой ключ."
                )
                return await get_video_details(conn, video_ids)
            elif e.resp.status in [400, 403]:
                await mark_api_key_as_banned(conn, api_key)
                logger.warning(
                    f"Ключ {api_key} забанен. Попытка использовать другой ключ."
                )
                return await get_video_details(conn, video_ids)
            else:
                raise

    return {
        "items": [video_cache[vid] for vid in video_ids if vid in video_cache]
    }
