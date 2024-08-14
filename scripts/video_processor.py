import json
from datetime import datetime

import asyncpg

from scripts.config import MIN_VIEWS
from scripts.logger import logger
from scripts.subtitles import get_russian_subtitles
from scripts.youtube_api import get_video_details


def parse_duration(duration):
    hours = 0
    minutes = 0
    seconds = 0

    if "H" in duration:
        hours = int(duration.split("H")[0].replace("PT", ""))
        duration = duration.split("H")[1]
    if "M" in duration:
        minutes = int(duration.split("M")[0].replace("PT", ""))
        duration = duration.split("M")[1]
    if "S" in duration:
        seconds = int(duration.split("S")[0].replace("PT", ""))

    return hours * 3600 + minutes * 60 + seconds


async def process_videos(conn, videos, search_query):
    video_ids = [video["id"]["videoId"] for video in videos]
    video_details = await get_video_details(conn, video_ids)

    for index, item in enumerate(video_details["items"]):
        video_id = item["id"]
        snippet = item["snippet"]
        statistics = item["statistics"]

        views = int(statistics.get("viewCount", 0))
        likes = int(statistics.get("likeCount", 0))
        comments = int(statistics.get("commentCount", 0))
        duration = parse_duration(item["contentDetails"]["duration"])

        if views < MIN_VIEWS:
            logger.info(
                f"Видео {video_id} не соответствует критериям по просмотрам: {views}"
            )
            continue

        publish_date = datetime.strptime(
            snippet["publishedAt"], "%Y-%m-%dT%H:%M:%SZ"
        )

        existing_video = await conn.fetchrow(
            "SELECT * FROM video_data WHERE video_id = $1", video_id
        )
        if existing_video:
            logger.info(f"Видео {video_id} уже существует в базе данных")
            continue

        subtitles, is_auto_generated = await get_russian_subtitles(video_id)
        if not subtitles:
            logger.info(f"Для видео {video_id} не найдены русские субтитры")
            continue

        if isinstance(subtitles, list):
            subtitles_json = json.dumps(subtitles)
        else:
            logger.warning(
                f"Неожиданный формат субтитров для видео {video_id}: {type(subtitles)}"
            )
            continue

        try:
            async with conn.transaction():
                await conn.execute(
                    """
                    INSERT INTO video_data (
                        video_id, title, description, views, likes, comments,
                        duration, publish_date, channel_id, channel_title, last_updated,
                        search_query, position
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                """,
                    video_id,
                    snippet["title"],
                    snippet["description"],
                    views,
                    likes,
                    comments,
                    duration,
                    publish_date,
                    snippet["channelId"],
                    snippet["channelTitle"],
                    datetime.now(),
                    search_query,
                    index + 1,
                )

                await conn.execute(
                    """
                    INSERT INTO subtitle_data (video_id, subtitle_json, is_auto_generated)
                    VALUES ($1, $2, $3)
                """,
                    video_id,
                    subtitles_json,
                    is_auto_generated,
                )

            logger.info(f"Данные для видео {video_id} успешно сохранены")

        except asyncpg.exceptions.UniqueViolationError:
            logger.info(f"Данные для видео {video_id} уже существуют в базе")
        except Exception as e:
            logger.error(
                f"Ошибка при сохранении данных для видео {video_id}: {str(e)}"
            )
