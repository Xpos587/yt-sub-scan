import asyncio
from datetime import datetime, timedelta

from scripts.database import create_tables, init_db
from scripts.logger import logger
from scripts.video_processor import process_videos
from scripts.youtube_api import fetch_videos


async def main():
    conn = await init_db()
    await create_tables(conn)

    two_years_ago = datetime.now() - timedelta(days=730)
    next_page_token = None

    while True:
        try:
            videos_response, search_query = await fetch_videos(
                conn, two_years_ago, next_page_token
            )
            logger.info(
                f"Получено {len(videos_response['items'])} видео для запроса '{search_query}'"
            )

            if not videos_response["items"]:
                logger.info("Новых видео не найдено. Ожидание 1 секунда.")
                await asyncio.sleep(1)
                continue

            await process_videos(conn, videos_response["items"], search_query)

            if "nextPageToken" in videos_response:
                next_page_token = videos_response["nextPageToken"]
            else:
                next_page_token = None
                last_video_date = datetime.strptime(
                    videos_response["items"][-1]["snippet"]["publishedAt"],
                    "%Y-%m-%dT%H:%M:%SZ",
                )
                two_years_ago = max(two_years_ago, last_video_date)
                logger.info(
                    f"Обновлена дата последнего обработанного видео: {two_years_ago}"
                )

            if "quotaExceeded" in str(videos_response):
                logger.warning("Квота API превышена. Ожидание 24 часа.")
                await asyncio.sleep(86400)

        except Exception as e:
            logger.error(f"Произошла ошибка: {e}")
            await asyncio.sleep(60)

    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
