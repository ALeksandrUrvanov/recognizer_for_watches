"""
Тестирование Yandex Search API
"""
import config
from app.yandex_search import YandexImageSearch
from pathlib import Path


def test_simple_search():
    """Простой тест поиска по изображению"""
    
    # Проверка настроек
    if not config.YANDEX_IAM_TOKEN:
        print("YANDEX_IAM_TOKEN не задан в .env")
        return
    
    if not config.YANDEX_FOLDER_ID:
        print("YANDEX_FOLDER_ID не задан в .env")
        return
    
    # Проверка тестового изображения
    test_image = r"C:\Users\USER\Downloads\200200.306.jpg"
    if not Path(test_image).exists():
        print(f"Тестовое изображение не найдено: {test_image}")
        return
    
    print("=" * 70)
    print("ТЕСТ YANDEX SEARCH API")
    print("=" * 70)
    print(f"Изображение: {test_image}")
    print(f"Folder ID: {config.YANDEX_FOLDER_ID}")
    print(f"API URL: {config.YANDEX_SEARCH_API_URL}")
    print("=" * 70 + "\n")
    
    # Инициализация API
    yandex_api = YandexImageSearch(
        config.YANDEX_IAM_TOKEN,
        config.YANDEX_FOLDER_ID,
        config.YANDEX_SEARCH_API_URL
    )
    
    # Тест 1: Поиск без ограничения по сайту
    print("Тест 1: Поиск без ограничения по сайту...")
    results = yandex_api.search_by_image(test_image, target_site=None, max_results=5)
    
    if results:
        print(f"✓ Найдено {len(results)} результатов\n")
        for idx, item in enumerate(results, 1):
            print(f"{idx}. {item['title'][:60]}...")
            print(f"   URL: {item['url']}")
            print(f"   Изображение: {item['image_url'][:80]}...")
            print()
    else:
        print("Ничего не найдено\n")
    
    # Тест 2: Поиск на nikawatches.ru
    print("Тест 2: Поиск на nikawatches.ru...")
    results_nika = yandex_api.search_by_image(test_image, target_site="nikawatches.ru", max_results=3)
    
    if results_nika:
        print(f"✓ Найдено {len(results_nika)} результатов\n")
        for idx, item in enumerate(results_nika, 1):
            print(f"{idx}. {item['title'][:60]}...")
            print(f"   URL: {item['url']}")
            print()
    else:
        print("Ничего не найдено на nikawatches.ru\n")
    
    # Тест 3: Поиск на platinor.ru
    print("Тест 3: Поиск на platinor.ru...")
    results_platinor = yandex_api.search_by_image(test_image, target_site="platinor.ru", max_results=3)
    
    if results_platinor:
        print(f"✓ Найдено {len(results_platinor)} результатов\n")
        for idx, item in enumerate(results_platinor, 1):
            print(f"{idx}. {item['title'][:60]}...")
            print(f"   URL: {item['url']}")
            print()
    else:
        print("Ничего не найдено на platinor.ru\n")
    
    print("=" * 70)
    print("ТЕСТ ЗАВЕРШЕН")
    print("=" * 70)


if __name__ == "__main__":
    test_simple_search()

