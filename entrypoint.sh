#!/bin/bash

echo "Запуск Watch Recognition..."

# Проверяем наличие векторной базы
if [ ! -d "/app/vectors" ] || [ -z "$(ls -A /app/vectors)" ]; then
    echo "Ошибка: Векторная база не найдена в /app/vectors"
    exit 1
fi

echo "✓ Векторная база найдена"

# Проверяем наличие конфигурации
if [ ! -f "/app/config.py" ]; then
    echo "Ошибка: Файл конфигурации не найден"
    exit 1
fi

echo "✓ Конфигурация найдена"

# Создаем папку для логов
mkdir -p /app/logs/queries

# Запускаем API сервер в фоне
echo "✓ Запуск API сервера на порту 8084..."
python3.10 api_server.py &
API_PID=$!

# Ждем 3 секунды для инициализации API
sleep 3

# Запускаем Telegram бота
echo "✓ Запуск Telegram бота..."
python3.10 telegram_bot/bot.py &
BOT_PID=$!

# Функция для graceful shutdown
shutdown() {
    echo "Получен сигнал завершения..."
    kill $API_PID 2>/dev/null
    kill $BOT_PID 2>/dev/null
    wait $API_PID 2>/dev/null
    wait $BOT_PID 2>/dev/null
    echo "Завершение работы"
    exit 0
}

# Обрабатываем сигналы завершения
trap shutdown SIGTERM SIGINT

# Ждем завершения процессов
wait
