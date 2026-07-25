import aiohttp
import os
import sys
from typing import Optional, Dict, Any

# Добавляем корневую папку проекта в PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import API_HOST, API_PORT


class WatchRecognitionClient:
    """Клиент для взаимодействия с FastAPI сервером распознавания часов"""
    
    def __init__(self, host: str = API_HOST, port: int = API_PORT):
        self.base_url = f"http://{host}:{port}"
    
    async def recognize_watch(self, image_bytes: bytes) -> Optional[Dict[str, Any]]:
        """
        Отправляет фото на распознавание
        """
        try:
            async with aiohttp.ClientSession() as session:
                data = aiohttp.FormData()
                data.add_field('file', image_bytes, filename='watch.jpg', content_type='image/jpeg')
                
                async with session.post(
                    f"{self.base_url}/upload-and-recognize",
                    data=data,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        print(f"API Error: {response.status} - {error_text}")
                        return None
                        
        except aiohttp.ClientError as e:
            print(f"Network error: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None

