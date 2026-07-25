import asyncio
import csv
import os
import sys
from datetime import datetime
from typing import Optional

# Добавляем корневую папку проекта в PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import LOG_CSV_PATH, LOG_DIR, SAVE_QUERY_PHOTOS


csv_lock = asyncio.Lock()


async def ensure_log_structure():
    """Создает папку для логов и CSV файл если не существуют"""
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    
    if not os.path.exists(LOG_CSV_PATH):
        async with csv_lock:
            with open(LOG_CSV_PATH, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp',
                    'user_id',
                    'query_photo',
                    'selected_option',
                    'processing_time',
                    'response_time'
                ])


async def save_query_photo(photo_bytes: bytes, filename: str) -> str:
    """
    Сохраняет запросное фото от товароведа
    """
    if not SAVE_QUERY_PHOTOS:
        return filename
    
    filepath = os.path.join(LOG_DIR, filename)
    
    with open(filepath, 'wb') as f:
        f.write(photo_bytes)
    
    return filepath


async def log_recognition_request(
    user_id: int,
    query_photo: str,
    processing_time: float,
    timestamp: Optional[datetime] = None
) -> None:
    """
    Создает запись о новом запросе на распознавание
    """
    if timestamp is None:
        timestamp = datetime.now()
    
    async with csv_lock:
        with open(LOG_CSV_PATH, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                timestamp.strftime("%d.%m.%Y %H:%M:%S"),
                user_id,
                query_photo,
                'pending',
                f"{processing_time:.2f}",
                ''
            ])


async def update_recognition_response(
    user_id: int,
    query_photo: str,
    selected_option: str
) -> None:
    """
    Обновляет запись после выбора товароведа
    """
    async with csv_lock:
        with open(LOG_CSV_PATH, 'r', encoding='utf-8') as f:
            rows = list(csv.reader(f))
        
        for i in range(len(rows) - 1, 0, -1):
            if len(rows[i]) >= 3 and rows[i][1] == str(user_id) and rows[i][2] == query_photo:
                request_time = datetime.strptime(rows[i][0], "%d.%m.%Y %H:%M:%S")
                response_time = (datetime.now() - request_time).total_seconds()
                rows[i][3] = str(selected_option)
                rows[i][5] = f"{response_time:.1f}"
                break
        
        with open(LOG_CSV_PATH, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(rows)


async def get_session_data(user_id: int, query_photo: str) -> Optional[dict]:
    """
    Получает данные сессии из CSV
    """
    async with csv_lock:
        if not os.path.exists(LOG_CSV_PATH):
            return None
        
        with open(LOG_CSV_PATH, 'r', encoding='utf-8') as f:
            rows = list(csv.reader(f))
        
        for i in range(len(rows) - 1, 0, -1):
            if len(rows[i]) >= 3 and rows[i][1] == str(user_id) and rows[i][2] == query_photo:
                return {
                    'timestamp': rows[i][0],
                    'user_id': rows[i][1],
                    'query_photo': rows[i][2],
                    'selected_option': rows[i][3],
                    'processing_time': rows[i][4],
                    'response_time': rows[i][5] if len(rows[i]) > 5 else ''
                }
        
        return None

