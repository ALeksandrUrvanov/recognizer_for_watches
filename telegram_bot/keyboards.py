from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню бота"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❓ Инструкция", callback_data="help")]
    ])


def get_selection_keyboard(session_id: str) -> InlineKeyboardMarkup:
    """Клавиатура выбора результата (1-5 или 0)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1️⃣", callback_data=f"select_{session_id}_1"),
            InlineKeyboardButton(text="2️⃣", callback_data=f"select_{session_id}_2"),
            InlineKeyboardButton(text="3️⃣", callback_data=f"select_{session_id}_3"),
            InlineKeyboardButton(text="4️⃣", callback_data=f"select_{session_id}_4"),
            InlineKeyboardButton(text="5️⃣", callback_data=f"select_{session_id}_5"),
        ],
        [
            InlineKeyboardButton(text="❌ Нет совпадений", callback_data=f"select_{session_id}_0")
        ]
    ])

