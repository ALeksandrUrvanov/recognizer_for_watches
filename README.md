# Watch Recognizer

Telegram-бот + FastAPI: поиск похожих моделей часов по фото (CLIP + FAISS, top-5).

## Stack

- Python, FastAPI, Uvicorn, aiogram 3
- PyTorch, transformers CLIP (`laion/CLIP-ViT-bigG-14-laion2B-39B-b160k`, 1280d)
- faiss-cpu, OpenCV, Pillow, pandas, NumPy
- Docker (`entrypoint.sh`: API `:8084` + bot)

## Pipeline

1. Фото в Telegram → HTTP `localhost:8084`.
2. CLIP-эмбеддинг → FAISS cosine top-5.
3. Пользователь выбирает вариант → лог в CSV.

## Run

```bash
pip install -r requirements.txt
# нужны vectors/*.faiss|pkl и data/ с изображениями (не в репо)
export TELEGRAM_BOT_TOKEN=...
uvicorn api_server:app --host 0.0.0.0 --port 8084
python -m telegram_bot.bot
```

## Config

| Variable | Required | Notes |
|----------|----------|-------|
| `TELEGRAM_BOT_TOKEN` | yes | |
| `YANDEX_IAM_TOKEN` / `YANDEX_FOLDER_ID` | no | только вспомогательные скрипты |

Пути индекса: `vectors/watch_index_clip.faiss`, `vectors/watch_metadata_clip.pkl`.

## Notes

- Датасет, FAISS-индекс и кэш CLIP в репозиторий не входят.
- Пересборка индекса: `app/vectorize_dataset.py`.
