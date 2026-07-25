import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

from datetime import datetime
from app.clip_embedding import CLIPEmbedder
from app.vector_db import VectorDatabase
from config import *


def test_recognition(image_path: str):
    """Прямой поиск часов в базе"""
    print(f"\n{'='*70}")
    print(f"ТЕСТ РАСПОЗНАВАНИЯ ЧАСОВ")
    print(f"{'='*70}")
    print(f"Файл: {os.path.basename(image_path)}")
    print(f"Модель: {CLIP_MODEL}")
    print(f"{'='*70}\n")
    
    start_time = datetime.now()
    
    # Шаг 1: Векторизация
    print(f"[1/2] Векторизация с CLIP...")
    step1_start = datetime.now()
    
    embedder = CLIPEmbedder(
        model_name=CLIP_MODEL,
        device=CLIP_DEVICE
    )
    
    query_embedding = embedder.embed_single(image_path)
    step1_time = (datetime.now() - step1_start).total_seconds()
    print(f"   Вектор [{len(query_embedding)}d] за {step1_time:.1f}с\n")
    
    # Шаг 2: Поиск в FAISS
    print(f"[2/2] Поиск в FAISS (топ-5)...")
    step2_start = datetime.now()
    
    vector_db = VectorDatabase(
        dimension=embedder.get_embedding_dim(),
        metric=FAISS_METRIC
    )
    vector_db.load(FAISS_INDEX_PATH, FAISS_METADATA_PATH)
    scores, results = vector_db.search(query_embedding, k=5)
    step2_time = (datetime.now() - step2_start).total_seconds()
    print(f"   Найдено {len(results)} кандидатов за {step2_time:.3f}с\n")
    
    # Вывод результатов
    print(f"{'='*70}")
    print(f"TOP-5 РЕЗУЛЬТАТОВ:")
    print(f"{'='*70}\n")
    
    for i, (score, metadata) in enumerate(zip(scores, results), 1):
        similarity = score * 100
        
        brand = metadata['brand'].upper()
        article = metadata['article']
        model_name = metadata.get('model_name', 'N/A')
        metal_type = metadata.get('metal_type', 'N/A')
        metal_weight = metadata.get('metal_weight_grams', 'N/A')
        url = metadata.get('product_url', 'N/A')
        
        weight_str = f"{metal_weight}г" if metal_weight != 'N/A' else metal_weight
        
        print(f"{i}. [{similarity:.2f}%] {brand} {article}")
        print(f"   Название: {model_name}")
        print(f"   Металл: {metal_type}")
        print(f"   Вес: {weight_str}")
        print(f"   URL: {url}")
        print()  # Пустая строка для читаемости
    
    total_time = (datetime.now() - start_time).total_seconds()
    
    print(f"{'='*70}")
    print(f"Время: {total_time:.1f} сек")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    # Путь к тестовому изображению
    TEST_IMAGE = r"C:\Users\USER\Downloads\200200.306.jpg"
    
    if not os.path.exists(TEST_IMAGE):
        print(f"\nОШИБКА: Файл не найден: {TEST_IMAGE}")
        print("Измените TEST_IMAGE в конце скрипта")
    else:
        test_recognition(TEST_IMAGE)
