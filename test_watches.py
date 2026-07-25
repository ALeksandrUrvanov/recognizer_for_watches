import requests
import os

#  Указать путь к фото часов:
INPUT_FILE = r"C:\Users\USER\Downloads\1807.2.9.34H.6.jpg"

if not os.path.exists(INPUT_FILE):
    print(f"Файл не найден: {INPUT_FILE}")
    exit()

print(f"Отправка фото на сервер...")

try:
    with open(INPUT_FILE, "rb") as f:
        files = {"file": (os.path.basename(INPUT_FILE), f, "image/jpeg")}
        response = requests.post("http://localhost:8084/upload-and-recognize-formatted", files=files, timeout=60)
    
    if response.status_code == 200:
        result = response.json()
        print(result['formatted_result'])
    else:
        print(f"Ошибка: {response.status_code}")
        
except Exception as e:
    print(f"Ошибка: {e}")