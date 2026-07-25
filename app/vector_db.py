import numpy as np
import faiss
import pickle
from typing import List, Dict, Tuple
import os


class VectorDatabase:
    """
    FAISS векторная база данных для поиска похожих изображений
    """
    
    def __init__(self, dimension: int = 1024, metric: str = "cosine"):
        """
        Инициализация векторной БД
        
        Args:
            dimension: Размерность векторов (1024 для DINOv2-large)
            metric: 'cosine' или 'l2'
        """
        self.dimension = dimension
        self.metric = metric
        self.index = None
        self.metadata = []
        
        if metric == "cosine":
            # IndexFlatIP для cosine similarity (после нормализации)
            self.index = faiss.IndexFlatIP(dimension)
        elif metric == "l2":
            # IndexFlatL2 для L2 distance
            self.index = faiss.IndexFlatL2(dimension)
        else:
            raise ValueError(f"Неизвестная метрика: {metric}")
        
        print(f"✓ FAISS индекс создан: {metric}, dim={dimension}")
    
    def add_vectors(self, vectors: np.ndarray, metadata: List[Dict]):
        """
        Добавление векторов в базу
        
        Args:
            vectors: numpy array [N, dimension]
            metadata: Список словарей с метаданными для каждого вектора
        """
        if len(vectors) != len(metadata):
            raise ValueError("Количество векторов и метаданных не совпадает")
        
        # Нормализация для cosine similarity
        if self.metric == "cosine":
            faiss.normalize_L2(vectors)
        
        self.index.add(vectors.astype(np.float32))
        self.metadata.extend(metadata)
    
    def search(self, query_vector: np.ndarray, k: int = 10) -> Tuple[List[float], List[Dict]]:
        """
        Поиск top-K похожих векторов
        
        Args:
            query_vector: Вектор запроса [dimension]
            k: Количество результатов
            
        Returns:
            (scores, metadata) - списки оценок и метаданных
        """
        if self.index.ntotal == 0:
            raise ValueError("База данных пуста")
        
        query = query_vector.reshape(1, -1).astype(np.float32)
        
        # Нормализация для cosine similarity
        if self.metric == "cosine":
            faiss.normalize_L2(query)
        
        distances, indices = self.index.search(query, k)
        
        scores = distances[0].tolist()
        results_metadata = [self.metadata[idx] for idx in indices[0] if idx < len(self.metadata)]
        
        return scores, results_metadata
    
    def save(self, index_path: str, metadata_path: str):
        """
        Сохранение индекса и метаданных
        
        Args:
            index_path: Путь для сохранения FAISS индекса
            metadata_path: Путь для сохранения метаданных (pickle)
        """
        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
        
        faiss.write_index(self.index, index_path)
        
        with open(metadata_path, 'wb') as f:
            pickle.dump(self.metadata, f)
        
        print(f"✓ Индекс сохранен: {index_path}")
        print(f"✓ Метаданные сохранены: {metadata_path}")
    
    def load(self, index_path: str, metadata_path: str):
        """
        Загрузка индекса и метаданных
        
        Args:
            index_path: Путь к FAISS индексу
            metadata_path: Путь к метаданным (pickle)
        """
        if not os.path.exists(index_path):
            raise FileNotFoundError(f"Индекс не найден: {index_path}")
        if not os.path.exists(metadata_path):
            raise FileNotFoundError(f"Метаданные не найдены: {metadata_path}")
        
        self.index = faiss.read_index(index_path)
        
        with open(metadata_path, 'rb') as f:
            self.metadata = pickle.load(f)
        
        print(f"✓ Индекс загружен: {self.index.ntotal} векторов")
        print(f"✓ Метаданные загружены: {len(self.metadata)} записей")
    
    def get_stats(self) -> Dict:
        """Статистика базы данных"""
        return {
            "total_vectors": self.index.ntotal,
            "dimension": self.dimension,
            "metric": self.metric,
            "metadata_count": len(self.metadata)
        }


if __name__ == "__main__":
    # Тест
    print("Тест VectorDatabase\n")
    
    db = VectorDatabase(dimension=1024, metric="cosine")
    
    # Тестовые данные
    test_vectors = np.random.randn(10, 1024).astype(np.float32)
    test_metadata = [{"id": i, "name": f"item_{i}"} for i in range(10)]
    
    db.add_vectors(test_vectors, test_metadata)
    
    # Поиск
    query = np.random.randn(1024).astype(np.float32)
    scores, results = db.search(query, k=3)
    
    print("\nРезультаты поиска:")
    for score, meta in zip(scores, results):
        print(f"  Score: {score:.4f}, ID: {meta['id']}, Name: {meta['name']}")
    
    print(f"\nСтатистика: {db.get_stats()}")

