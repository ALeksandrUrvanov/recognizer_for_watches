import os
from dotenv import load_dotenv

load_dotenv()

# API настройки
API_PORT = 8084
API_HOST = "localhost"

# Yandex Search API настройки (для тестирования)
YANDEX_IAM_TOKEN = os.getenv("YANDEX_IAM_TOKEN")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
YANDEX_SEARCH_API_URL = "https://searchapi.api.cloud.yandex.net/v2/image/search_by_image"
YANDEX_TARGET_SITES = [
    "nikawatches.ru",  # Официальный сайт NIKA
    "platinor.ru"      # Официальный сайт Platinor
]

# CLIP настройки 
CLIP_MODEL = "laion/CLIP-ViT-bigG-14-laion2B-39B-b160k"  # 1280d
CLIP_DEVICE = "cpu"
CLIP_CACHE_DIR = "models/clip_cache"

# FAISS настройки
FAISS_INDEX_PATH = "vectors/watch_index_clip.faiss"
FAISS_METADATA_PATH = "vectors/watch_metadata_clip.pkl"
FAISS_METRIC = "cosine"

# Telegram Bot настройки
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_SESSION_TIMEOUT_MINUTES = 5

# Логирование запросов
LOG_DIR = "logs/queries"
LOG_CSV_PATH = "logs/recognition_log.csv"
SAVE_QUERY_PHOTOS = True