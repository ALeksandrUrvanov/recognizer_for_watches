import asyncio
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InputMediaPhoto, FSInputFile

from config import TELEGRAM_SESSION_TIMEOUT_MINUTES
from telegram_bot.states import RecognitionStates
from telegram_bot.keyboards import get_main_menu_keyboard, get_selection_keyboard
from telegram_bot.api_client import WatchRecognitionClient
from telegram_bot.logger import (
    ensure_log_structure,
    save_query_photo,
    log_recognition_request,
    update_recognition_response
)

router = Router()

timeout_tasks = {}


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    await state.clear()
    
    await message.answer(
        "Здравствуйте! 👋\n\n"
        "Я бот для распознавания часов компании <b>Ломбард</b>.\n\n"
        "Отправьте мне фото часов, постараюсь найти их для вас!",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(RecognitionStates.waiting_photo)


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    await message.answer(
        "📖 <b>ИНСТРУКЦИЯ ПО РАБОТЕ С БОТОМ</b>\n\n"
        "1️⃣ Сделайте фото циферблата часов\n"
        "2️⃣ Отправьте <b>ОДНО</b> фото в этот чат\n"
        "3️⃣ Дождитесь результатов\n"
        "4️⃣ Выберите номер подходящего варианта (1-5) или \"Нет совпадений\" (0)\n\n"
        "💡 <b>СОВЕТЫ:</b>\n"
        "• Избегайте бликов и размытости\n\n"
        "Для начала работы: /start",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "help")
async def callback_help(callback: CallbackQuery):
    """Обработчик кнопки 'Инструкция'"""
    await callback.message.answer(
        "📖 <b>ИНСТРУКЦИЯ ПО РАБОТЕ С БОТОМ</b>\n\n"
        "1️⃣ Сделайте фото циферблата часов\n"
        "2️⃣ Отправьте <b>ОДНО</b> фото в этот чат\n"
        "3️⃣ Дождитесь результатов\n"
        "4️⃣ Выберите номер подходящего варианта (1-5) или \"Нет совпадений\" (0)\n\n"
        "💡 <b>СОВЕТЫ:</b>\n"
        "• Избегайте бликов и размытости",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(RecognitionStates.waiting_photo, F.photo)
async def handle_photo(message: Message, state: FSMContext, bot: Bot):
    """Обработчик получения фото от товароведа"""
    
    await ensure_log_structure()
    
    status_msg = await message.answer("📸 Принято! Обрабатываю...")
    
    photo = message.photo[-1]
    photo_file = await bot.get_file(photo.file_id)
    photo_bytes = await bot.download_file(photo_file.file_path)
    photo_data = photo_bytes.read()
    
    # Создаем единый timestamp для имени файла и CSV
    request_time = datetime.now()
    # Формат: query_27102025_160908_136550.jpg (дата_время_микросекунды)
    session_id = request_time.strftime("%d%m%Y_%H%M%S_%f")
    query_filename = f"query_{session_id}.jpg"
    
    await save_query_photo(photo_data, query_filename)
    
    client = WatchRecognitionClient()
    result = await client.recognize_watch(photo_data)
    
    if not result or not result.get('success'):
        await status_msg.edit_text(
            "❌ Ошибка при распознавании. Попробуйте еще раз или обратитесь к администратору.\n\n"
            "Если есть другие часы - присылайте фото!"
        )
        await state.set_state(RecognitionStates.waiting_photo)
        return
    
    processing_time = result.get('processing_time', 0)
    results = result.get('results', [])
    
    if len(results) == 0:
        await status_msg.edit_text(
            "❌ Не удалось найти похожие часы. Попробуйте другое фото.\n\n"
            "Если есть другие часы - присылайте фото!"
        )
        await state.set_state(RecognitionStates.waiting_photo)
        return
    
    await log_recognition_request(
        user_id=message.from_user.id,
        query_photo=query_filename,
        processing_time=processing_time,
        timestamp=request_time
    )
    
    media_group = []
    for i, watch in enumerate(results, 1):
        similarity = watch['similarity_score'] * 100
        brand = watch['brand'].upper()
        article = watch['article']
        model_name = watch['model_name']
        metal_type = watch['metal_type']
        metal_weight = watch['metal_weight_grams']
        product_url = watch['product_url']
        image_path = watch.get('image_local_path', '')
        
        weight_str = f"{metal_weight}г" if metal_weight != 'N/A' else metal_weight
        
        caption = (
            f"{i}️⃣ [{similarity:.1f}%] {brand} {article}\n"
            f"{model_name}\n"
            f"Металл: {metal_type}\n"
            f"Вес: {weight_str}\n"
            f"🔗 {product_url}"
        )
        
        if image_path and image_path != 'N/A' and os.path.exists(image_path):
            media_group.append(
                InputMediaPhoto(
                    media=FSInputFile(image_path),
                    caption=caption
                )
            )
        else:
            print(f"Warning: Image not found: {image_path}")
    
    if len(media_group) == 0:
        await status_msg.edit_text(
            "❌ Ошибка загрузки изображений. Попробуйте еще раз.\n\n"
            "Если есть другие часы - присылайте фото!"
        )
        await state.set_state(RecognitionStates.waiting_photo)
        return
    
    try:
        await bot.send_media_group(
            chat_id=message.chat.id,
            media=media_group
        )
        
        selection_msg = await message.answer(
            "🔍 Нашли часы среди результатов?",
            reply_markup=get_selection_keyboard(session_id)
        )
        
        await status_msg.delete()
        
        await state.update_data(
            session_id=session_id,
            query_filename=query_filename,
            selection_message_id=selection_msg.message_id
        )
        await state.set_state(RecognitionStates.waiting_selection)
        
        timeout_task = asyncio.create_task(
            handle_selection_timeout(message, state, bot, session_id)
        )
        timeout_tasks[session_id] = timeout_task
        
    except Exception as e:
        print(f"Error sending media group: {e}")
        await status_msg.edit_text(
            "❌ Ошибка отправки результатов. Попробуйте еще раз.\n\n"
            "Если есть другие часы - присылайте фото!"
        )
        await state.set_state(RecognitionStates.waiting_photo)


async def handle_selection_timeout(message: Message, state: FSMContext, bot: Bot, session_id: str):
    """Обработчик таймаута ожидания выбора"""
    await asyncio.sleep(TELEGRAM_SESSION_TIMEOUT_MINUTES * 60)
    
    current_state = await state.get_state()
    if current_state != RecognitionStates.waiting_selection.state:
        return
    
    data = await state.get_data()
    if data.get('session_id') != session_id:
        return
    
    query_filename = data.get('query_filename')
    selection_message_id = data.get('selection_message_id')
    
    if query_filename:
        await update_recognition_response(
            user_id=message.from_user.id,
            query_photo=query_filename,
            selected_option='timeout'
        )
    
    if selection_message_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=selection_message_id,
                text="⏱ Время ожидания ответа истекло.\n\nЕсли есть другие часы - присылайте фото!"
            )
        except Exception:
            pass
    
    await state.set_state(RecognitionStates.waiting_photo)
    
    if session_id in timeout_tasks:
        del timeout_tasks[session_id]


@router.callback_query(F.data.startswith("select_"))
async def handle_selection(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора результата"""
    
    # Формат: select_{session_id}_{option}
    # session_id содержит подчеркивания, поэтому берем последнюю часть как option
    parts = callback.data.split('_')
    if len(parts) < 3:
        await callback.answer("Ошибка выбора")
        return
    
    selected_option = parts[-1]  # Последняя часть - это опция (0-5)
    session_id = '_'.join(parts[1:-1])  # Все между "select" и опцией - это session_id
    
    data = await state.get_data()
    if data.get('session_id') != session_id:
        await callback.answer("Эта сессия завершена")
        return
    
    if session_id in timeout_tasks:
        timeout_task = timeout_tasks[session_id]
        if not timeout_task.done():
            timeout_task.cancel()
        del timeout_tasks[session_id]
    
    query_filename = data.get('query_filename')
    
    if query_filename:
        await update_recognition_response(
            user_id=callback.from_user.id,
            query_photo=query_filename,
            selected_option=selected_option
        )
    
    if selected_option == '0':
        response_text = "✅ Спасибо! Отмечено: нет совпадений.\n\nЕсли есть ещё часы - присылайте фото!"
    else:
        response_text = f"✅ Спасибо! Вы выбрали вариант {selected_option}.\n\nЕсли есть ещё часы - присылайте фото!"
    
    await callback.message.edit_text(text=response_text)
    await callback.answer()
    
    await state.set_state(RecognitionStates.waiting_photo)


@router.message(F.photo)
async def handle_photo_fallback(message: Message):
    """Обработчик фото вне состояния waiting_photo"""
    await message.answer(
        "Пожалуйста, начните с команды /start"
    )


@router.message()
async def handle_other(message: Message):
    """Обработчик всех остальных сообщений"""
    await message.answer(
        "Пожалуйста, отправьте фото часов или воспользуйтесь /start"
    )

