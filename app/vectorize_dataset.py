"""
Векторизация датасета часов с использованием DINOv2 или CLIP

Модель выбирается через config.EMBEDDING_MODEL ("dinov2" или "clip")

ВАЖНО: Этот скрипт использует обработанные через YOLO11-seg фото из data/images/{brand}_dialonly/
Перед запуском убедитесь, что вы выполнили:
    python preprocess_database_dialonly.py
"""
import os
import re
import pandas as pd
import numpy as np
from tqdm import tqdm
from pathlib import Path
import sys

# Добавляем корневую папку в path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.embedding import DINOv2Embedder
from app.clip_embedding import CLIPEmbedder
from app.vector_db import VectorDatabase
from config import *


def extract_base_model(article: str, brand: str) -> str:
    """
    Извлекает базовую модель из артикула (только для Nika)
    
    Args:
        article: Артикул часов
        brand: Бренд (nika/platinor)
        
    Returns:
        Базовая модель или полный артикул
    """
    if brand != "nika":
        return article
    
    # Убираем числовой суффикс (длина браслета) в конце
    # Например: 1064-0-9-83H-150 -> 1064-0-9-83H
    parts = article.rsplit('-', 1)
    if len(parts) == 2 and parts[1].isdigit():
        return parts[0]
    
    return article


def load_dataset(csv_path: str, images_dir: str, brand: str, use_preprocessed: bool = True) -> pd.DataFrame:
    """
    Загрузка датасета из CSV
    
    Args:
        csv_path: Путь к CSV файлу
        images_dir: Папка с изображениями
        brand: Название бренда (nika/platinor)
        use_preprocessed: Использовать обработанные YOLO фото
        
    Returns:
        DataFrame с метаданными
    """
    print(f"\nЗагрузка датасета: {brand}")
    
    df = pd.read_csv(csv_path)
    
    # Добавляем бренд
    df['brand'] = brand
    
    # Извлекаем базовую модель для группировки (только Nika)
    df['base_model'] = df['article'].apply(lambda x: extract_base_model(x, brand))
    
    # Если используем обработанные фото
    if use_preprocessed:
        # Используем путь из config.py
        preprocessed_dir = images_dir
        
        def get_preprocessed_path(original_path):
            """Получить путь к обработанному фото"""
            filename = os.path.basename(original_path)
            # Сохраняем оригинальное расширение (jpg/JPG)
            return os.path.join(preprocessed_dir, filename)
        
        df['preprocessed_path'] = df['image_local_path'].apply(get_preprocessed_path)
        df['image_exists'] = df['preprocessed_path'].apply(os.path.exists)
        
        # Используем обработанный путь для векторизации
        df['vectorize_path'] = df['preprocessed_path']
        
        # Определяем тип изображений по пути
        if "_dialonly" in preprocessed_dir:
            print(f"✓ Используются циферблаты (YOLO11-seg) из {preprocessed_dir}")
        elif "_yolo" in preprocessed_dir:
            print(f"✓ Используются полные часы (YOLO11-seg) из {preprocessed_dir}")
        else:
            print(f"✓ Используются оригинальные фото из {preprocessed_dir}")
    else:
        # Используем оригинальные фото
        df['image_exists'] = df['image_local_path'].apply(os.path.exists)
        df['vectorize_path'] = df['image_local_path']
        print(f"✓ Используются оригинальные фото из {images_dir}")
    
    missing = df[~df['image_exists']].shape[0]
    if missing > 0:
        print(f"⚠️  Не найдено {missing} изображений")
        df = df[df['image_exists']]
    
    print(f"✓ Загружено {len(df)} записей ({brand})")
    
    return df


def vectorize_dataset(
    embedder: DINOv2Embedder,
    df: pd.DataFrame,
    batch_size: int = 1
) -> tuple:
    """
    Векторизация всех изображений из датасета
    
    Args:
        embedder: DINOv2 модель
        df: DataFrame с путями к изображениям
        batch_size: Размер батча (для CPU лучше 1)
        
    Returns:
        (embeddings, metadata) - векторы и метаданные
    """
    embeddings = []
    metadata = []
    
    print(f"\nВекторизация {len(df)} изображений...")
    print(f"Batch size: {batch_size}")
    print(f"Устройство: {embedder.device}")
    
    # Обрабатываем по батчам
    for i in tqdm(range(0, len(df), batch_size), desc="Векторизация"):
        batch_df = df.iloc[i:i+batch_size]
        
        try:
            if batch_size == 1:
                # Single image
                row = batch_df.iloc[0]
                embedding = embedder.embed_single(row['vectorize_path'])
                embeddings.append(embedding)
            else:
                # Batch
                batch_images = batch_df['vectorize_path'].tolist()
                batch_embeddings = embedder.embed_batch(batch_images)
                embeddings.extend(batch_embeddings)
            
            # Сохраняем метаданные
            for _, row in batch_df.iterrows():
                metadata.append({
                    'article': row['article'],
                    'model_name': row['model_name'],
                    'metal_type': row['metal_type'],
                    'metal_weight_grams': row['metal_weight_grams'],
                    'brand': row['brand'],
                    'base_model': row['base_model'],
                    'image_local_path': row['image_local_path'],
                    'product_url': row['product_url']
                })
                
        except Exception as e:
            print(f"\n⚠️  Ошибка при обработке батча {i}: {e}")
            continue
    
    embeddings_array = np.vstack(embeddings)
    
    print(f"\n✓ Векторизация завершена")
    print(f"  Размерность: {embeddings_array.shape}")
    
    return embeddings_array, metadata


def main():
    """Основная функция векторизации датасета"""
    
    print("="*60)
    print("ВЕКТОРИЗАЦИЯ ДАТАСЕТА ЧАСОВ")
    print("="*60)
    print(f"Модель эмбеддингов: {EMBEDDING_MODEL.upper()}")
    print(f"Режим препроцессинга: {PREPROCESS_MODE}")
    print("="*60)
    
    # 1. Инициализация модели эмбеддингов
    print(f"\n[1/5] Инициализация {EMBEDDING_MODEL.upper()}...")
    
    if EMBEDDING_MODEL == "clip":
        embedder = CLIPEmbedder(
            model_name=CLIP_MODEL,
            device=CLIP_DEVICE
        )
        batch_size = CLIP_BATCH_SIZE
    elif EMBEDDING_MODEL == "dinov2":
        embedder = DINOv2Embedder(
            model_name=DINOV2_MODEL,
            device=DINOV2_DEVICE
        )
        batch_size = DINOV2_BATCH_SIZE
    else:
        raise ValueError(f"Неизвестная модель: {EMBEDDING_MODEL}. Используйте 'dinov2' или 'clip'")
    
    # 2. Загрузка датасетов
    print("\n[2/5] Загрузка датасетов...")
    
    nika_df = load_dataset(
        DATASET_PATHS["nika"]["csv"],
        DATASET_PATHS["nika"]["images"],
        "nika"
    )
    
    platinor_df = load_dataset(
        DATASET_PATHS["platinor"]["csv"],
        DATASET_PATHS["platinor"]["images"],
        "platinor"
    )
    
    # Объединяем
    full_df = pd.concat([nika_df, platinor_df], ignore_index=True)
    print(f"\n✓ Всего изображений: {len(full_df)}")
    
    # 3. Векторизация
    print("\n[3/5] Векторизация изображений...")
    print(f"Batch size: {batch_size}")
    embeddings, metadata = vectorize_dataset(
        embedder,
        full_df,
        batch_size=batch_size
    )
    
    # 4. Создание FAISS индекса
    print("\n[4/5] Создание FAISS индекса...")
    db = VectorDatabase(
        dimension=embedder.get_embedding_dim(),
        metric=FAISS_METRIC
    )
    
    db.add_vectors(embeddings, metadata)
    
    # 5. Сохранение
    print("\n[5/5] Сохранение результатов...")
    
    os.makedirs("vectors", exist_ok=True)
    
    # Сохраняем индекс и метаданные
    db.save(
        FAISS_INDEX_PATH,
        FAISS_METADATA_PATH
    )
    
    # Сохраняем сырые эмбеддинги (опционально)
    embeddings_path = "vectors/watch_embeddings.npy"
    np.save(embeddings_path, embeddings)
    print(f"✓ Эмбеддинги сохранены: {embeddings_path}")
    
    # Статистика
    print("\n" + "="*60)
    print("СТАТИСТИКА")
    print("="*60)
    stats = db.get_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    # Статистика по брендам
    brands = full_df['brand'].value_counts()
    print(f"\nПо брендам:")
    for brand, count in brands.items():
        print(f"  {brand}: {count}")
    
    # Статистика по вариантам (Nika)
    nika_variants = full_df[full_df['brand'] == 'nika'].groupby('base_model').size()
    variants_with_multiple = nika_variants[nika_variants > 1]
    print(f"\nNika модели с вариантами: {len(variants_with_multiple)}")
    print(f"Всего вариантов: {variants_with_multiple.sum()}")
    
    print("\n" + "="*60)
    print("✓ ВЕКТОРИЗАЦИЯ ЗАВЕРШЕНА!")
    print("="*60)


if __name__ == "__main__":
    main()

