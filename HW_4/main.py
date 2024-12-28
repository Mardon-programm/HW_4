import sqlite3
from dotenv import load_dotenv
import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command


load_dotenv()


logging.basicConfig(level=logging.INFO)


API_TOKEN = os.getenv('TOKEN')
DATABASE = 'orders.db'


bot = Bot(token=API_TOKEN)
dp = Dispatcher()


def create_db():
    with sqlite3.connect(DATABASE) as db:
        cursor = db.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                user_name TEXT NOT NULL,
                address TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'Заказ принят!'
            )
        """)
        db.commit()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    inline_keyboard  = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton("Еда", callback_data='food'),
        InlineKeyboardButton("Запчасти", callback_data='parts'),
        InlineKeyboardButton("Мебель", callback_data='furniture')
    ]
    inline_keyboard .add(*buttons)
    await message.answer("Добро пожаловать! Выберите категорию заказа:", reply_markup=inline_keyboard )


@dp.callback_query(lambda c: c.data in ['food', 'parts', 'furniture'])
async def category_choice(callback_query: types.CallbackQuery):
    category = callback_query.data
    await callback_query.answer()

    await bot.send_message(callback_query.from_user.id, f"Вы выбрали категорию: {category}. Пожалуйста, введите ваше имя.")

    dp.current_state(user=callback_query.from_user.id).update_data(category=category)


@dp.message(lambda message: not message.text.isdigit())
async def collect_user_data(message: types.Message):
    state = dp.current_state(user=message.from_user.id)
    user_data = await state.get_data()

    if 'category' not in user_data:
        await message.answer("Ошибка!!! Сначала выберите категорию с помощью кнопок.")
        return

    category = user_data['category']

    
    if 'name' not in user_data:
        await state.update_data(name=message.text)
        await message.answer("Введите адрес доставки:")
    
    elif 'address' not in user_data:
        await state.update_data(address=message.text)
        await message.answer("Введите описание заказа:")
    
    elif 'description' not in user_data:
        await state.update_data(description=message.text)

        
        with sqlite3.connect(DATABASE) as db:
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO orders (category, user_name, address, description)
                VALUES (?, ?, ?, ?)
            """, (category, user_data['name'], user_data['address'], user_data['description']))
            db.commit()

        order_id = cursor.lastrowid
        await message.answer(f"Ваш заказ подтвержден!!! Номер заказа: {order_id}! \nТеперь вы можете отслеживать его статус!")
        await state.clear()  


@dp.message(lambda message: message.text.isdigit())
async def check_order_status(message: types.Message):
    order_id = int(message.text)

    with sqlite3.connect(DATABASE) as db:
        cursor = db.cursor()
        cursor.execute("SELECT status FROM orders WHERE order_id = ?", (order_id,))
        result = cursor.fetchone()

    if result:
        status = result[0]
        await message.answer(f"Статус вашего заказа {order_id}: {status}.")
    else:
        await message.answer(f"Заказ с номером {order_id} не найден!")

async def main():
    create_db()  
    await dp.start_polling(bot) 

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
