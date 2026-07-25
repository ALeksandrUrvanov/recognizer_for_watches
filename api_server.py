import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import tempfile
from datetime import datetime
from typing import List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
import uvicorn

from app.clip_embedding import CLIPEmbedder
from app.vector_db import VectorDatabase
from config import *

# Глобальные переменные для модели и базы
embedder = None
vector_db = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    # Startup
    await initialize_models()
    yield
    # Shutdown (если нужно что-то очистить)
    pass


app = FastAPI(title="Watch Recognition API", version="1.0.0", lifespan=lifespan)


class WatchResult(BaseModel):
    brand: str
    article: str
    model_name: str
    metal_type: str
    metal_weight_grams: str
    product_url: str
    similarity_score: float
    image_local_path: str


class RecognitionResponse(BaseModel):
    success: bool
    message: str
    results: List[WatchResult] = []
    processing_time: float


async def initialize_models():
    """Инициализация моделей при запуске"""
    global embedder, vector_db
    
    embedder = CLIPEmbedder(
        model_name=CLIP_MODEL,
        device=CLIP_DEVICE,
        cache_dir=CLIP_CACHE_DIR
    )
    print("CLIP модель загружена")
    
    print("\nЗагрузка векторной базы FAISS...")
    vector_db = VectorDatabase(
        dimension=embedder.get_embedding_dim(),
        metric=FAISS_METRIC
    )
    vector_db.load(FAISS_INDEX_PATH, FAISS_METADATA_PATH)
    print("Векторная база загружена")


def format_recognition_results(results: List[WatchResult], processing_time: float) -> str:
    """Форматирует результаты распознавания для вывода"""
    formatted = f"\n{'='*70}\n"
    formatted += f"TOP-5 РЕЗУЛЬТАТОВ:\n"
    formatted += f"{'='*70}\n\n"
    
    for i, watch in enumerate(results, 1):
        similarity = watch.similarity_score * 100
        brand = watch.brand.upper()
        article = watch.article
        model_name = watch.model_name
        metal_type = watch.metal_type
        metal_weight = watch.metal_weight_grams
        url = watch.product_url
        
        weight_str = f"{metal_weight}г" if metal_weight != 'N/A' else metal_weight
        
        formatted += f"{i}. [{similarity:.2f}%] {brand} {article}\n"
        formatted += f"   Название: {model_name}\n"
        formatted += f"   Металл: {metal_type}\n"
        formatted += f"   Вес: {weight_str}\n"
        formatted += f"   URL: {url}\n"
        formatted += f"\n"
    
    formatted += f"{'='*70}\n"
    formatted += f"Время: {processing_time:.1f} сек\n"
    formatted += f"{'='*70}\n"
    
    return formatted


async def recognize_watch(image_data: bytes) -> RecognitionResponse:
    """Распознавание часов на изображении"""
    start_time = datetime.now()
    
    try:
        # Сохраняем временный файл (кроссплатформенно)
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.jpg', delete=False) as f:
            f.write(image_data)
            temp_path = f.name
        
        # Векторизация
        query_embedding = embedder.embed_single(temp_path)
        
        # Поиск в FAISS
        scores, results = vector_db.search(query_embedding, k=5)
        
        # Формирование результатов
        watch_results = []
        for score, metadata in zip(scores, results):
            # Поддерживаем оба ключа для обратной совместимости
            image_path = metadata.get('image_local_path') or metadata.get('image_path', 'N/A')
            
            watch_results.append(WatchResult(
                brand=metadata['brand'],
                article=metadata['article'],
                model_name=metadata.get('model_name', 'N/A'),
                metal_type=metadata.get('metal_type', 'N/A'),
                metal_weight_grams=str(metadata.get('metal_weight_grams', 'N/A')),
                product_url=metadata.get('product_url', 'N/A'),
                similarity_score=float(score),
                image_local_path=image_path
            ))
        
        # Удаляем временный файл
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return RecognitionResponse(
            success=True,
            message=f"Найдено {len(watch_results)} результатов",
            results=watch_results,
            processing_time=processing_time
        )
        
    except Exception as e:
        processing_time = (datetime.now() - start_time).total_seconds()
        raise HTTPException(
            status_code=500, 
            detail=f"Ошибка распознавания: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


async def _process_upload(file: UploadFile):
    """Общая логика обработки загруженного файла"""
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Файл не является изображением")
    
    image_data = await file.read()
    return await recognize_watch(image_data)


@app.post("/upload-and-recognize")
async def upload_and_recognize(file: UploadFile = File(...)):
    """Загрузка файла и распознавание часов (JSON ответ)"""
    try:
        return await _process_upload(file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обработки файла: {str(e)}")


@app.post("/upload-and-recognize-formatted")
async def upload_and_recognize_formatted(file: UploadFile = File(...)):
    """Загрузка файла и распознавание часов (форматированный текст)"""
    try:
        result = await _process_upload(file)
        
        if not result.success:
            return {"formatted_result": f"Ошибка: {result.message}"}
        
        formatted_text = format_recognition_results(result.results, result.processing_time)
        return {"formatted_result": formatted_text}
        
    except Exception as e:
        return {"formatted_result": f"Ошибка: {str(e)}"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8084)
