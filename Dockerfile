FROM ubuntu:22.04

# Слой 1: Системные зависимости
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-dev \
    python3.10-distutils \
    python3-pip \
    build-essential \
    curl \
    git \
    wget \
    gnupg2 \
    software-properties-common \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && ln -sf /usr/bin/python3.10 /usr/bin/python \
    && ln -sf /usr/bin/python3.10 /usr/bin/python3 \
    && python3.10 -m pip install --upgrade pip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*

# Слой 2: Настройка окружения
WORKDIR /app

ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DOCKER_ENV=true \
    KMP_DUPLICATE_LIB_OK=TRUE

# Слой 3: Python зависимости
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    python3.10 -m pip install --no-cache-dir --timeout=300 --retries=10 \
        --index-url https://pypi.org/simple/ \
        packaging setuptools wheel && \
    python3.10 -m pip install --no-cache-dir --timeout=300 --retries=10 \
        --index-url https://pypi.org/simple/ \
        -r requirements.txt && \
    apt-get update && apt-get remove -y build-essential python3.10-dev && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf /tmp/* && \
    rm -rf /var/tmp/* && \
    find /usr/local -name '*.pyc' -delete && \
    find /usr/local -name '__pycache__' -delete

# Слой 4: Проверка установки
RUN python3.10 -c "import torch; print('✓ PyTorch установлен:', torch.__version__)" && \
    python3.10 -c "import transformers; print('✓ Transformers установлен:', transformers.__version__)" && \
    python3.10 -c "import faiss; print('✓ FAISS установлен:', faiss.__version__)" && \
    python3.10 -c "import fastapi; print('✓ FastAPI установлен:', fastapi.__version__)" && \
    python3.10 -c "import uvicorn; print('✓ Uvicorn установлен:', uvicorn.__version__)" && \
    python3.10 -c "import aiogram; print('✓ Aiogram установлен:', aiogram.__version__)" && \
    python3.10 -c "import aiohttp; print('✓ Aiohttp установлен:', aiohttp.__version__)"

# Слой 5: Код и векторы
COPY app/clip_embedding.py ./app/
COPY app/vector_db.py ./app/
COPY telegram_bot/ ./telegram_bot/
COPY config.py .
COPY api_server.py .
COPY admin_stats.py .
COPY vectors/ ./vectors/
COPY entrypoint.sh /entrypoint.sh

# Создаем __init__.py для пакета app
RUN touch ./app/__init__.py

# Слой 6: Настройка прав
RUN chmod +x /entrypoint.sh

EXPOSE 8084

ENTRYPOINT ["/entrypoint.sh"]
