import asyncio
import re

import aiohttp
import orjson
from cachetools import TTLCache
from lxml import etree

from scripts.config import PROXY
from scripts.logger import logger

SUBTITLE_REGEX = re.compile(
    r'<text start="([\d.]+)" dur="([\d.]+)".*?>(.*?)</text>', re.DOTALL
)
JSON_REGEX = re.compile(r"ytInitialPlayerResponse\s*=\s*({.+?});", re.DOTALL)

subtitle_cache = TTLCache(maxsize=1000, ttl=3600)


async def create_session():
    return aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(
            ssl=False,
            limit=100,
            resolver=aiohttp.resolver.AsyncResolver(
                nameservers=["8.8.8.8", "8.8.4.4"]
            ),
        ),
        trust_env=True,
        timeout=aiohttp.ClientTimeout(
            total=10, connect=5, sock_connect=5, sock_read=5
        ),
    )


async def fetch(session, url):
    try:
        async with session.get(url, proxy=PROXY) as response:
            return await response.text()
    except Exception as e:
        logger.error(f"Ошибка при запросе {url}: {str(e)}")
        return None


async def extract_json_and_subtitle_url(html_content):
    start = html_content.find("ytInitialPlayerResponse = ") + 26
    end = html_content.find("};", start) + 1
    if start > 25 and end > 0:
        try:
            json_data = orjson.loads(html_content[start:end])
            captions = (
                json_data.get("captions", {})
                .get("playerCaptionsTracklistRenderer", {})
                .get("captionTracks", [])
            )
            for caption in captions:
                if caption.get("languageCode") == "ru":
                    return caption.get("baseUrl")
        except orjson.JSONDecodeError as e:
            logger.error(f"Ошибка при парсинге JSON: {str(e)}")
    return None


async def parse_subtitles(xml_content):
    if not xml_content:
        return []
    root = etree.fromstring(xml_content.encode("utf-8"))
    return [
        {
            "start": float(text.get("start")),
            "duration": float(text.get("dur")),
            "text": text.text.strip()
            .replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">"),
        }
        for text in root.findall(".//text")
    ]


async def get_russian_subtitles(video_id):
    try:
        async with await create_session() as session:
            url = f"https://www.youtube.com/watch?v={video_id}"
            html_content = await fetch(session, url)
            if not html_content:
                return None, False

            subtitle_url = await extract_json_and_subtitle_url(html_content)
            if not subtitle_url:
                return None, False

            xml_content, is_auto_generated = await asyncio.gather(
                fetch(session, subtitle_url),
                asyncio.to_thread(lambda: "kind=asr" in subtitle_url),
            )

            subtitles = await parse_subtitles(xml_content)
            return subtitles, is_auto_generated

    except Exception as e:
        logger.error(
            f"Неожиданная ошибка при обработке видео {video_id}: {str(e)}"
        )

    return None, False
