import os

from dotenv import load_dotenv

load_dotenv()

# Настройки базы данных
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")

# Настройки YouTube API
YOUTUBE_API_SERVICE_NAME = os.getenv("YOUTUBE_API_SERVICE_NAME")
YOUTUBE_API_VERSION = os.getenv("YOUTUBE_API_VERSION")

PROXY = os.getenv("PROXY")

MIN_VIEWS = int(os.getenv("MIN_VIEWS", 600))

# Поисковые запросы
SEARCH_QUERIES = [
    "новости",
    "технологии",
    "наука",
    "спорт",
    "музыка",
    "кино",
    "игры",
    "образование",
    "путешествия",
    "кулинария",
    "мода",
    "здоровье",
    "бизнес",
    "искусство",
    "история",
    "природа",
    "автомобили",
    "юмор",
    "программирование",
    "ютуб",
    "анонимность",
    "впн",
    "замедление",
]

# Путь к директории логов
LOG_DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
