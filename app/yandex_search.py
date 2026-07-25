"""
Модуль для работы с Yandex Search API (поиск по изображению)
"""
import base64
import requests
from typing import List, Dict, Optional
from pathlib import Path


class YandexImageSearch:
    """Поиск похожих изображений через Yandex Search API"""
    
    def __init__(self, iam_token: str, folder_id: str, api_url: str):
        self.iam_token = iam_token
        self.folder_id = folder_id
        self.api_url = api_url
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {iam_token}",
            "Content-Type": "application/json"
        })
    
    def _encode_image_to_base64(self, image_path: str) -> str:
        """Кодирует изображение в Base64"""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    
    def search_by_image(
        self,
        image_path: str,
        target_site: str = None,
        max_results: int = 10,
        page: int = 0
    ) -> List[Dict]:
        """
        Ищет похожие изображения на указанном сайте
        
        Args:
            image_path: путь к изображению для поиска
            target_site: доменное имя сайта (например, "nika-time.ru"), опционально
            max_results: максимум результатов
            page: номер страницы (для пагинации)
        
        Returns:
            Список словарей с результатами:
            [
                {
                    "url": "https://...",
                    "title": "...",
                    "image_url": "https://...",
                    "snippet": "..."
                },
                ...
            ]
        """
        image_base64 = self._encode_image_to_base64(image_path)
        
        payload = {
            "folderId": self.folder_id,
            "data": image_base64,
            "page": page
        }
        
        if target_site:
            payload["site"] = target_site
        
        try:
            response = self.session.post(self.api_url, json=payload)
            response.raise_for_status()
            
            data = response.json()
            
            results = []
            
            # Парсим ответ (Yandex возвращает ключ "images")
            if "images" in data:
                for item in data["images"][:max_results]:
                    results.append({
                        "url": item.get("pageUrl", ""),
                        "title": item.get("pageTitle", ""),
                        "image_url": item.get("url", ""),
                        "snippet": item.get("passage", ""),
                        "host": item.get("host", "")
                    })
            
            return results
        
        except requests.exceptions.RequestException as e:
            print(f"❌ Ошибка при запросе к Yandex API: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   Код ответа: {e.response.status_code}")
                print(f"   Тело ответа: {e.response.text[:500]}")
            return []
    
    def search_on_multiple_sites(
        self,
        image_path: str,
        sites: List[str],
        max_results_per_site: int = 5
    ) -> Dict[str, List[Dict]]:
        """
        Ищет на нескольких сайтах
        
        Args:
            image_path: путь к изображению
            sites: список доменов
            max_results_per_site: максимум результатов с каждого сайта
        
        Returns:
            {
                "nika-time.ru": [...],
                "platinor.ru": [...]
            }
        """
        results = {}
        
        for site in sites:
            print(f"   → Поиск на {site}...")
            site_results = self.search_by_image(
                image_path,
                site,
                max_results=max_results_per_site
            )
            results[site] = site_results
            print(f"   ✓ Найдено {len(site_results)} изображений")
        
        return results
    
    def download_image(self, url: str, save_path: str, min_size_kb: int = 10) -> dict:
        """
        Скачивает изображение по URL с проверкой качества
        
        Args:
            url: URL изображения
            save_path: путь для сохранения
            min_size_kb: минимальный размер файла в KB
        
        Returns:
            dict: {"success": bool, "width": int, "height": int, "size_kb": int}
        """
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Проверка размера файла
            size_kb = len(response.content) / 1024
            if size_kb < min_size_kb:
                return {
                    "success": False,
                    "error": f"Файл слишком маленький ({size_kb:.1f}KB < {min_size_kb}KB)"
                }
            
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(save_path, "wb") as f:
                f.write(response.content)
            
            # Проверка разрешения изображения
            try:
                from PIL import Image
                img = Image.open(save_path)
                width, height = img.size
                
                # Минимальное разрешение для качественного фото
                if width < 200 or height < 200:
                    Path(save_path).unlink()  # Удаляем некачественное изображение
                    return {
                        "success": False,
                        "error": f"Разрешение слишком низкое ({width}x{height})"
                    }
                
                return {
                    "success": True,
                    "width": width,
                    "height": height,
                    "size_kb": size_kb
                }
            
            except Exception as img_error:
                Path(save_path).unlink()  # Удаляем битый файл
                return {
                    "success": False,
                    "error": f"Не удалось прочитать изображение: {img_error}"
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


def test_api_connection(iam_token: str, folder_id: str) -> bool:
    """
    Проверяет подключение к Yandex Search API
    
    Returns:
        True если подключение успешно
    """
    api_url = "https://searchapi.api.cloud.yandex.net/v2/image/search_by_image"
    
    headers = {
        "Authorization": f"Bearer {iam_token}",
        "Content-Type": "application/json"
    }
    
    # Простой тестовый запрос с URL изображения
    payload = {
        "folderId": folder_id,
        "url": "https://yandex.ru/images/search?text=watch&img_url=https://avatars.mds.yandex.net/get-images-cbir/1545078/test.jpg",
        "page": 0
    }
    
    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            print("✓ Подключение к Yandex Search API успешно!")
            return True
        elif response.status_code == 401:
            print("❌ Ошибка авторизации! Проверьте IAM-токен")
            print(f"   Ответ: {response.text[:300]}")
            return False
        elif response.status_code == 403:
            print("❌ Доступ запрещен! Проверьте права сервисного аккаунта")
            print(f"   Ответ: {response.text[:300]}")
            return False
        elif response.status_code == 400:
            print("⚠️  Запрос сформирован неверно, но подключение работает!")
            print(f"   Код: {response.status_code}")
            print(f"   Ответ: {response.text[:300]}")
            return True
        else:
            print(f"❌ Неожиданный статус: {response.status_code}")
            print(f"   Ответ: {response.text[:500]}")
            return False
    
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return False

