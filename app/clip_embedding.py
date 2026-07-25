"""
CLIP эмбеддинги для изображений часов

Используется модель OpenAI CLIP (ViT-L/14-336) для получения векторных представлений
"""
import torch
import numpy as np
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
from typing import List, Union


class CLIPEmbedder:
    """
    Класс для получения CLIP эмбеддингов из изображений
    """
    
    def __init__(
        self,
        model_name: str = "openai/clip-vit-large-patch14-336",
        device: str = "cpu",
        cache_dir: str = None
    ):
        """
        Args:
            model_name: Название модели CLIP на HuggingFace
            device: Устройство для вычислений ("cpu" или "cuda")
            cache_dir: Директория для кэширования модели
        """
        self.device = device
        self.model_name = model_name
        self.cache_dir = cache_dir
        
        print(f"Загрузка {model_name} на {device}...")
        self.model = CLIPModel.from_pretrained(model_name, cache_dir=cache_dir).to(device)
        self.processor = CLIPProcessor.from_pretrained(model_name, cache_dir=cache_dir, use_fast=False)
        self.model.eval()
        
        # Определяем размерность эмбеддингов
        with torch.no_grad():
            dummy_img = Image.new('RGB', (224, 224), color='white')
            inputs = self.processor(images=dummy_img, return_tensors="pt").to(device)
            outputs = self.model.get_image_features(**inputs)
            self.embedding_dim = outputs.shape[1]
    
    def get_embedding_dim(self) -> int:
        """Возвращает размерность эмбеддингов"""
        return self.embedding_dim
    
    @torch.no_grad()
    def embed_single(self, image_path: str) -> np.ndarray:
        """
        Получить эмбеддинг одного изображения
        
        Args:
            image_path: Путь к изображению
        
        Returns:
            numpy array размерности [embedding_dim]
        """
        image = Image.open(image_path).convert('RGB')
        
        # Препроцессинг
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)
        
        # Получаем эмбеддинги
        image_features = self.model.get_image_features(**inputs)
        
        # Нормализуем (CLIP эмбеддинги обычно нормализуются)
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        
        # Конвертируем в numpy
        embedding = image_features.cpu().numpy()[0]
        
        return embedding
    
    @torch.no_grad()
    def embed_batch(self, image_paths: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Получить эмбеддинги батча изображений
        
        Args:
            image_paths: Список путей к изображениям
            batch_size: Размер батча
        
        Returns:
            numpy array размерности [len(image_paths), embedding_dim]
        """
        embeddings = []
        
        for i in range(0, len(image_paths), batch_size):
            batch_paths = image_paths[i:i + batch_size]
            
            # Загружаем изображения
            images = [Image.open(p).convert('RGB') for p in batch_paths]
            
            # Препроцессинг батча
            inputs = self.processor(images=images, return_tensors="pt").to(self.device)
            
            # Получаем эмбеддинги
            image_features = self.model.get_image_features(**inputs)
            
            # Нормализуем
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            
            # Конвертируем в numpy
            batch_embeddings = image_features.cpu().numpy()
            embeddings.append(batch_embeddings)
        
        return np.vstack(embeddings)
    
    def __repr__(self):
        return f"CLIPEmbedder(model={self.model_name}, dim={self.embedding_dim}, device={self.device})"

