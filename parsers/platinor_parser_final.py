"""
Финальный парсер для Platinor
Парсит все коллекции и модели, сохраняет в CSV и скачивает фото
"""

import time
import json
import csv
import os
import re
import requests
import html
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from tqdm import tqdm


def setup_driver():
    """Настройка Chrome WebDriver"""
    chrome_options = Options()
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36')
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
    except Exception:
        from webdriver_manager.chrome import ChromeDriverManager
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
    })
    
    return driver


def extract_json_ld(soup):
    """Извлекает структурированные данные JSON-LD"""
    scripts = soup.find_all('script', type='application/ld+json')
    for script in scripts:
        try:
            data = json.loads(script.string)
            if data.get('@type') == 'Product':
                return data
        except:
            continue
    return None


def parse_model_page(driver, url):
    """Парсинг страницы модели"""
    try:
        driver.get(url)
        time.sleep(2)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Извлекаем данные из JSON-LD
        json_ld_data = extract_json_ld(soup)
        
        result = {
            'article': '',
            'model_name': '',
            'product_url': url,
            'image_url': '',
            'metal_type': '',
            'metal_weight_grams': ''
        }
        
        if json_ld_data:
            # Артикул: заменяем ВСЕ спецсимволы на тире
            article_raw = json_ld_data.get('sku', json_ld_data.get('productID', ''))
            # Заменяем все не буквенно-цифровые символы (кроме тире) на тире
            # Только латинские буквы, цифры и тире
            result['article'] = re.sub(r'[^a-zA-Z0-9-]', '-', article_raw)
            
            # Название: расшифровываем HTML entities и убираем кавычки
            name_raw = json_ld_data.get('name', '')
            # Сначала расшифровываем HTML entities через BeautifulSoup
            name_soup = BeautifulSoup(name_raw, 'html.parser')
            name_unescaped = name_soup.get_text()
            # Убираем все виды кавычек
            name_clean = name_unescaped.replace('«', '').replace('»', '').replace('"', '').replace("'", '').replace('&laquo;', '').replace('&raquo;', '')
            result['model_name'] = name_clean.strip()
            
            # Извлекаем первое изображение
            images = json_ld_data.get('image', [])
            if images and len(images) > 0:
                result['image_url'] = images[0]
        
        # Если JSON-LD не дал результатов, пробуем другие методы
        if not result['model_name']:
            h1 = soup.find('h1')
            if h1:
                result['model_name'] = h1.get_text(strip=True)
        
        # Поиск металла
        metal_keywords = ['золото', 'серебро', 'платина', 'палладий']
        metal_patterns = [
            r'((?:Желтое|Розовое|Белое|Красное)?\s*(?:золото|серебро|платина|палладий)\s*\d+[°]?)',
            r'(\d+\s*проба)',
        ]
        
        page_text = soup.get_text()
        for pattern in metal_patterns:
            matches = re.findall(pattern, page_text, re.IGNORECASE)
            if matches:
                result['metal_type'] = matches[0].strip()
                break
        
        # Поиск веса (ищем "Средний вес, г" + число)
        weight_pattern = r'Средний вес[,\s]*г[:\s]*(\d+[.,]?\d*)'
        weight_match = re.search(weight_pattern, page_text, re.IGNORECASE)
        if weight_match:
            result['metal_weight_grams'] = weight_match.group(1).replace(',', '.')
        else:
            # Если не нашли "Средний вес", пробуем другие варианты
            weight_pattern2 = r'(?:Вес|Масса)[:\s]*(\d+[.,]?\d*)\s*(?:г|гр|грамм)'
            weight_match2 = re.search(weight_pattern2, page_text, re.IGNORECASE)
            if weight_match2:
                result['metal_weight_grams'] = weight_match2.group(1).replace(',', '.')
        
        return result
        
    except Exception as e:
        print(f"\nОшибка парсинга {url}: {e}")
        return None


def download_image(url, save_path):
    """Скачивание изображения в максимальном качестве"""
    try:
        # Формируем полный URL если нужно
        if not url.startswith('http'):
            url = f"https://www.platinor.ru{url}"
        
        # Получаем оригинал: убираем /resized/ и размеры из имени
        original_url = url.replace('/resized/', '/')
        original_url = re.sub(r'_\d+x\d+', '', original_url)
        
        # Пробуем скачать оригинал
        try:
            response = requests.get(original_url, timeout=10)
            response.raise_for_status()
            
            with open(save_path, 'wb') as f:
                f.write(response.content)
            return True
        except:
            # Если оригинал не найден, пробуем исходный URL
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            with open(save_path, 'wb') as f:
                f.write(response.content)
            return True
            
    except Exception as e:
        print(f"\nОшибка загрузки изображения {url}: {e}")
        return False


def get_models_from_collection(driver, collection_url):
    """Получить все модели из коллекции (с учетом пагинации)"""
    
    # Извлекаем ключевое слово коллекции из URL
    # Берем последнюю часть URL и оставляем только базовое название (до первого _)
    collection_key_full = collection_url.rstrip('/').split('/')[-1]
    # Убираем суффиксы _gold, _silver и т.д.
    collection_key = collection_key_full.replace('_gold', '').replace('_silver', '').replace('_woman', '').replace('_man', '')
    # Если остались цифры или другие суффиксы (например _458), берем только до первого _
    if '_' in collection_key:
        collection_key = collection_key.split('_')[0]
    
    # Словарь для проблемных транслитераций (collection_url_key -> model_url_key)
    transliteration_map = {
        # Автоматически собранные
        'alisia': 'alisiya',
        'alisija': 'alisiya',
        'amelia': 'ameliya',
        'arkadia': 'arkadiya',
        'batterfly': 'batterflyaj',
        'dzhulia': 'dzhuliya',
        'konstancia': 'konstantsiya',
        'marianna-2': 'marianna',
        'marianna-3': 'marianna',
        'olivia': 'oliviya',
        'severnoe-sijanie': 'severnoe',
        'stefany': 'stefani',
        'valeria': 'valeriya',
        'vanessa-1': 'vanessa',
        'venetsiya-2': 'venetsiya',
        # Вручную проверенные
        'angelina': 'anzhelina',
        'anabel': 'annabel',
        'djein': 'dzhejn',
        'jennifer': 'dzhennifer',
        'djina': 'dzhina',
        'jasmin': 'zhasmin',
        'kate': 'kejt',
        'kler-1': 'kler',
        'lubava': 'lyubava',
        'mery': 'meri',
        'suzen': 'syuzen',
        'elisabeth': 'elizabet',
        # Категория Чайка
        'victoria': 'viktoriya',
        'svetlana': 'chajka',
        'chayka': 'chajka',
        # Категория Женские серебряные часы
        'djennifer-silver': 'dzhennifer',
        'laima': 'lajma',
        'randewu': 'randevu',
        'severnoe-siyanie': 'severnoe',
        'silver-alexandra': 'aleksandra',
        'silver-amanda': 'amanda',
        'silver-amelia': 'ameliya',
        'silver-batterfly': 'batterflyaj',
        'silver-chayka': 'chajka',
        'silver-debora': 'debora',
        'silver-elen': 'elen',
        'silver-elizabet': 'elizabet',
        'silver-gretta': 'gretta',
        'silver-horizont': 'syuzen',
        'silver-ilona': 'ilona',
        'silver-inga': 'inga',
        'silver-jane': 'dzhejn',
        'silver-janet': 'zhanet',
        'silver-jasmin': 'zhasmin',
        'silver-julia': 'dzhuliya',
        'silver-kamila': 'kamilla',
        'silver-konstancia': 'konstantsiya',
        'silver-lubava': 'lyubava',
        'silver-madlen': 'madlen',
        'silver-margo': 'margo',
        'silver-mari': 'meri',
        'silver-marlen': 'marlen',
        'silver-milana': 'milana',
        'silver-mishel': 'mishel',
        'silver-nezhnost': 'nezhnost',
        'silver-nikol': 'nikol',
        'silver-nikoletta': 'nikoletta',
        'silver-olivia': 'oliviya',
        'silver-paula': 'paula',
        'silver-rio': 'rio',
        'silver-ritm': 'ritm',
        'silver-ritm2': 'ritm',
        'silver-silvia': 'silviya',
        'silver-sofi': 'sofi',
        'silver-unona': 'yunona',
        'silver-valeria': 'valeriya',
        'silver-venera': 'venera',
        'silver-vesna': 'vesna',
        'silver-vesta': 'vesta',
        'silver-zlata': 'zlata',
        'siver-natali': 'natali',
        'snejana': 'snezhana',
        # Категория Мужские золотые часы
        '419': 'skeleton',
        '477': 'boston',
        '478': 'pushkin',
        '485': 'myunkhen',
        '501': 'sirius',
        '502': 'odissej',
        '503': 'saturn',
        '504': 'yupiter',
        '506': 'vityaz',
        '507': 'voskhod',
        '508': 'mankhetten',
        '519': 'altaj',
        '520': 'enisej',
        '522': 'vostok',
        '525': 'diplomat',
        '530': 'start',
        '533': 'iridium',
        '535': 'neptun',
        '539': 'fregat',
        '548': 'forum',
        '555': 'shturman',
        '564': 'merkurij',
        '577': 'konsul',
        '578': 'monarkh',
        'admiral2': 'admiral',
        'alex': 'aleks',
        'baykal': 'bajkal',
        'bris': 'briz',
        'gorisont': 'gorizont',
        'ocean': 'okean',
        'poseydon': 'posejdon',
        'topas': 'topaz',
        'vihr': 'vikhr',
        # Категория Мужские серебряные часы
        '525': 'diplomat',
        'atlantida': 'platinor',
        'atlantida-1': 'platinor',
        'amur-1': 'amur',
        'marshal-1': 'marshal',
        'monako-1': 'monako',
        'venetsiya-1': 'venetsiya',
        'silver-atlant': 'atlant',
        'silver-baltica': 'baltika',
        'silver-bris': 'briz',
        'silver-dnepr': 'dnepr',
        'silver-horizon': 'gorizont',
        'silver-mercury': 'merkurij',
        'silver-salvatore': 'salvador',
        'silver-salvatore-3': 'salvador',
        'silver-sharm': 'platinor',
        'silver-sirius': 'sirius',
        'silver-419': 'skeleton',
        'silver-477': 'boston',
        'silver-485': 'myunkhen',
        'silver-504': 'yupiter',
        'silver-508': 'mankhetten',
        'silver-519': 'altaj',
        'silver-548': 'forum',
        'silver-karmannye': 'karmannye',
    }
    
    # Создаем список вариантов ключа для поиска
    search_keys = [collection_key]
    if collection_key in transliteration_map:
        search_keys.append(transliteration_map[collection_key])
    
    models = []
    seen_urls = set()
    pages_to_visit = [collection_url]
    visited_pages = set()
    
    # Обходим все страницы с пагинацией
    while pages_to_visit:
        current_url = pages_to_visit.pop(0)
        
        if current_url in visited_pages:
            continue
        
        visited_pages.add(current_url)
        
        driver.get(current_url)
        time.sleep(2)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        all_links = soup.find_all('a', href=True)
        
        # Ищем модели на текущей странице
        for link in all_links:
            href = link.get('href', '')
            
            # Фильтруем ссылки:
            # 1. Должны содержать -detail
            # 2. Должны содержать ЛЮБОЙ вариант ключа коллекции в URL
            # 3. НЕ должны быть служебными ссылками (notify, vm-search и т.д.)
            if '-detail' in href:
                # Проверяем все варианты ключа (оригинал + альтернативная транслитерация)
                key_found = any(key in href.lower() for key in search_keys)
                
                if key_found:
                    # Исключаем служебные URL (уведомления, поиск и т.д.)
                    if '/notify' in href or '/vm-search/' in href:
                        continue
                    
                    if href.startswith('/'):
                        full_url = f"https://www.platinor.ru{href}"
                    else:
                        full_url = href
                    
                    if full_url not in seen_urls:
                        seen_urls.add(full_url)
                        models.append(full_url)
        
        # Ищем ссылки на следующие страницы (пагинация)
        for link in all_links:
            href = link.get('href', '')
            # Ссылки пагинации содержат '/results,' и относятся к текущей коллекции
            if '/results,' in href and collection_key_full in href:
                if href.startswith('/'):
                    next_page_url = f"https://www.platinor.ru{href}"
                else:
                    next_page_url = href
                
                if next_page_url not in visited_pages and next_page_url not in pages_to_visit:
                    pages_to_visit.append(next_page_url)
    
    return models


def save_results_to_csv(csv_file, all_results):
    """Сохранение результатов в CSV с добавлением к существующим записям"""
    # Читаем существующие записи
    existing_articles = set()
    existing_rows = []
    
    if os.path.exists(csv_file):
        with open(csv_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_articles.add(row['article'])
                existing_rows.append(row)
    
    # Добавляем только новые записи (избегаем дубликатов)
    new_rows = []
    for result in all_results:
        if result['article'] not in existing_articles:
            new_rows.append(result)
            existing_articles.add(result['article'])
    
    # Объединяем старые и новые записи
    all_rows = existing_rows + new_rows
    
    # Записываем все обратно
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['article', 'model_name', 'product_url', 'image_local_path', 'metal_type', 'metal_weight_grams'])
        writer.writeheader()
        writer.writerows(all_rows)
    
    return len(new_rows), len(all_rows)


def parse_all_collections(test_mode=False, test_limit=5, single_collection=None, single_category=None):
    """Основная функция парсинга всех коллекций"""
    
    # Загружаем список коллекций
    with open('parsers/platinor_collections.json', 'r', encoding='utf-8') as f:
        collections_data = json.load(f)
    
    # Файл для отслеживания прогресса
    progress_file = 'parsers/platinor_progress.json'
    
    # Загружаем прогресс если есть
    if os.path.exists(progress_file):
        with open(progress_file, 'r', encoding='utf-8') as f:
            progress = json.load(f)
    else:
        progress = {'completed_models': [], 'failed_models': []}
    
    # Подготавливаем CSV
    csv_file = 'data/platinor_watches.csv'
    images_dir = 'data/images/platinor'
    os.makedirs(images_dir, exist_ok=True)
    
    driver = setup_driver()
    
    all_results = []
    total_models = 0
    
    try:
        print(f"\n{'='*80}")
        print("ПАРСИНГ PLATINOR")
        print(f"Режим: {'ТЕСТОВЫЙ' if test_mode else 'ПОЛНЫЙ'}")
        if single_category:
            print(f"Фильтр категории: {single_category}")
        print(f"{'='*80}\n")
        
        for category in collections_data['categories']:
            category_name = category['name']
            category_type = category['type']
            
            # Если указана конкретная категория - парсим только её
            if single_category:
                # Используем частичное совпадение из-за проблем с кодировкой в PowerShell
                # Сравниваем в lowercase и проверяем вхождение ключевых слов
                match_found = False
                
                # Точное совпадение (если кодировка ОК)
                if category_name == single_category:
                    match_found = True
                # Частичное совпадение по ключевым словам
                elif single_category.lower() in category_name.lower() or category_name.lower() in single_category.lower():
                    match_found = True
                
                if not match_found:
                    continue
            
            print(f"\nКатегория: {category_name}")
            print(f"Коллекций: {len(category['collections'])}")
            
            for collection in category['collections']:
                collection_name = collection['name']
                collection_url = collection['url']
                
                # Если указана конкретная коллекция - парсим только её
                if single_collection and collection_name != single_collection:
                    continue
                
                print(f"\n  Коллекция: {collection_name}")
                
                # Получаем модели из коллекции
                if category_type == 'direct_models':
                    # Модели напрямую на странице
                    models = get_models_from_collection(driver, collection_url)
                else:
                    # Модели внутри коллекции
                    models = get_models_from_collection(driver, collection_url)
                
                print(f"  Найдено моделей: {len(models)}")
                
                # В тестовом режиме берем только первые N моделей
                if test_mode and len(models) > test_limit:
                    models = models[:test_limit]
                    print(f"  Тестовый режим: парсим только {test_limit} моделей")
                
                # Парсим каждую модель
                for model_url in tqdm(models, desc=f"  Парсинг {collection_name}"):
                    # Пропускаем если уже обработана
                    if model_url in progress['completed_models']:
                        continue
                    
                    model_data = parse_model_page(driver, model_url)
                    
                    if model_data and model_data['article']:
                        # Формируем имя файла изображения (артикул уже с тире)
                        image_filename = f"{model_data['article']}.jpg"
                        image_local_path = f"data/images/platinor/{image_filename}"
                        
                        # Скачиваем изображение
                        if model_data['image_url']:
                            download_image(model_data['image_url'], image_local_path)
                        
                        # Добавляем в результаты
                        model_result = {
                            'article': model_data['article'],
                            'model_name': model_data['model_name'],
                            'product_url': model_data['product_url'],
                            'image_local_path': image_local_path,
                            'metal_type': model_data['metal_type'],
                            'metal_weight_grams': model_data['metal_weight_grams']
                        }
                        all_results.append(model_result)
                        
                        total_models += 1
                        
                        # Отмечаем как завершенную
                        progress['completed_models'].append(model_url)
                        
                        # Сохраняем в CSV после каждой модели
                        save_results_to_csv(csv_file, [model_result])
                    else:
                        # Отмечаем как неудачную
                        progress['failed_models'].append(model_url)
                    
                    # Сохраняем прогресс после каждой модели
                    with open(progress_file, 'w', encoding='utf-8') as f:
                        json.dump(progress, f, ensure_ascii=False, indent=2)
                    
                    # Задержка между запросами
                    time.sleep(1.5)
                
                # Задержка между коллекциями
                time.sleep(2)
                
                # В тестовом режиме парсим только первую коллекцию
                if test_mode:
                    break
                
                # Если парсим одну коллекцию - выходим после неё
                if single_collection:
                    break
            
            # В тестовом режиме парсим только первую категорию
            if test_mode:
                break
            
            # Если парсим одну коллекцию - выходим
            if single_collection:
                break
            
            # Если парсим одну категорию - выходим после неё
            if single_category:
                break
        
        # Финальное сохранение результатов в CSV
        print(f"\n{'='*80}")
        print(f"Парсинг завершен!")
        print(f"Всего новых моделей: {total_models}")
        print(f"Финальное сохранение в {csv_file}...")
        
        if all_results:
            new_count, total_count = save_results_to_csv(csv_file, all_results)
            print(f"Готово! Добавлено новых записей: {new_count}")
            print(f"Всего записей в файле: {total_count}")
        else:
            print("Нет новых записей для сохранения.")
        
        print(f"{'='*80}\n")
        
    except Exception as e:
        print(f"\nКритическая ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        driver.quit()


if __name__ == "__main__":
    import sys
    
    # Проверяем аргументы командной строки
    test_mode = '--test' in sys.argv or '-t' in sys.argv
    
    # Проверяем указана ли конкретная коллекция
    single_collection = None
    single_category = None
    
    for arg in sys.argv:
        if arg.startswith('--collection='):
            single_collection = arg.split('=', 1)[1]
        elif arg.startswith('--category='):
            single_category = arg.split('=', 1)[1]
    
    if test_mode:
        print("\n🧪 ТЕСТОВЫЙ РЕЖИМ")
        print("Будет обработана только первая коллекция (первые 3 модели)")
        print("Запуск через 2 секунды...\n")
        time.sleep(2)
        parse_all_collections(test_mode=True, test_limit=3)
    elif single_collection:
        print(f"\n📦 ПАРСИНГ ОДНОЙ КОЛЛЕКЦИИ")
        print(f"Коллекция: {single_collection}")
        print("Запуск через 2 секунды...\n")
        time.sleep(2)
        parse_all_collections(test_mode=False, single_collection=single_collection)
    elif single_category:
        print(f"\n[ПАРСИНГ ОДНОЙ КАТЕГОРИИ]")
        print(f"Категория: {single_category}")
        print("Запуск через 2 секунды...\n")
        time.sleep(2)
        parse_all_collections(test_mode=False, single_category=single_category)
    else:
        print("\n⚠️  ПОЛНЫЙ РЕЖИМ ПАРСИНГА")
        print("Будут обработаны ВСЕ категории, коллекции и модели!")
        print("Это займет несколько часов.\n")
        response = input("Продолжить? (y/n): ")
        if response.lower() != 'y':
            print("Отмена.")
            exit()
        parse_all_collections(test_mode=False)

