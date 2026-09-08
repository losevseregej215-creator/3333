import logging
import sqlite3
import os
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, List, Tuple, Optional

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, 
    ReplyKeyboardMarkup, KeyboardButton, InputMediaPhoto
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, ConversationHandler, filters
)
from telegram.constants import ParseMode
from telegram.error import TimedOut, NetworkError

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен бота
BOT_TOKEN = "8829785655:AAHv-44OuFHSUV0BFI38kyROyng5PdEVEe0"

# Состояния для ConversationHandler
(NAME, ABOUT, PHOTO, AGREEMENT, 
 ADD_CATEGORY, DELETE_CATEGORY, 
 ADD_PRODUCT_NAME, ADD_PRODUCT_PRICE, ADD_PRODUCT_PHOTO, ADD_PRODUCT_DESC,
 ADD_PAYMENT_DETAILS, 
 PURCHASE_ADDRESS, PURCHASE_PAYMENT,
 ORDER_CONFIRMATION, SELECT_CATEGORY_FOR_PRODUCT) = range(15)

# Инициализация базы данных
def init_db():
    try:
        conn = sqlite3.connect('shop_bot.db')
        c = conn.cursor()
        
        # Таблица пользователей
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (user_id INTEGER PRIMARY KEY, 
                      username TEXT, 
                      first_name TEXT,
                      last_name TEXT,
                      register_date TIMESTAMP)''')
        
        # Таблица магазинов
        c.execute('''CREATE TABLE IF NOT EXISTS shops
                     (shop_id INTEGER PRIMARY KEY AUTOINCREMENT,
                      owner_id INTEGER,
                      name TEXT UNIQUE,
                      about TEXT,
                      photo_id TEXT,
                      agreement TEXT,
                      created_date TIMESTAMP,
                      FOREIGN KEY (owner_id) REFERENCES users(user_id))''')
        
        # Таблица категорий
        c.execute('''CREATE TABLE IF NOT EXISTS categories
                     (category_id INTEGER PRIMARY KEY AUTOINCREMENT,
                      shop_id INTEGER,
                      name TEXT,
                      FOREIGN KEY (shop_id) REFERENCES shops(shop_id))''')
        
        # Таблица товаров
        c.execute('''CREATE TABLE IF NOT EXISTS products
                     (product_id INTEGER PRIMARY KEY AUTOINCREMENT,
                      category_id INTEGER,
                      name TEXT,
                      price REAL,
                      photo_id TEXT,
                      description TEXT,
                      FOREIGN KEY (category_id) REFERENCES categories(category_id))''')
        
        # Таблица реквизитов
        c.execute('''CREATE TABLE IF NOT EXISTS payment_details
                     (detail_id INTEGER PRIMARY KEY AUTOINCREMENT,
                      shop_id INTEGER,
                      detail_type TEXT,
                      detail_value TEXT,
                      FOREIGN KEY (shop_id) REFERENCES shops(shop_id))''')
        
        # Таблица заказов
        c.execute('''CREATE TABLE IF NOT EXISTS orders
                     (order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                      shop_id INTEGER,
                      buyer_id INTEGER,
                      product_id INTEGER,
                      product_name TEXT,
                      product_price REAL,
                      address TEXT,
                      payment_method TEXT,
                      status TEXT,
                      order_date TIMESTAMP,
                      completed_date TIMESTAMP,
                      FOREIGN KEY (shop_id) REFERENCES shops(shop_id),
                      FOREIGN KEY (buyer_id) REFERENCES users(user_id),
                      FOREIGN KEY (product_id) REFERENCES products(product_id))''')
        
        # Таблица завершенных заказов
        c.execute('''CREATE TABLE IF NOT EXISTS completed_orders
                     (order_id INTEGER PRIMARY KEY,
                      shop_id INTEGER,
                      buyer_id INTEGER,
                      product_name TEXT,
                      product_price REAL,
                      order_date TIMESTAMP,
                      completed_date TIMESTAMP,
                      FOREIGN KEY (shop_id) REFERENCES shops(shop_id),
                      FOREIGN KEY (buyer_id) REFERENCES users(user_id))''')
        
        # Таблица для уведомлений
        c.execute('''CREATE TABLE IF NOT EXISTS purchase_notifications
                     (notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
                      order_id INTEGER,
                      buyer_id INTEGER,
                      seller_id INTEGER,
                      product_name TEXT,
                      notification_time TIMESTAMP,
                      sent BOOLEAN DEFAULT 0)''')
        
        conn.commit()
        conn.close()
        logger.info("База данных инициализирована успешно")
    except Exception as e:
        logger.error(f"Ошибка инициализации БД: {e}")

# Вспомогательные функции для работы с БД
def is_user_registered(user_id):
    try:
        conn = sqlite3.connect('shop_bot.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        result = c.fetchone()
        conn.close()
        return result is not None
    except Exception as e:
        logger.error(f"Ошибка проверки регистрации: {e}")
        return False

def register_user(user_id, username, first_name, last_name):
    try:
        conn = sqlite3.connect('shop_bot.db')
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, register_date) VALUES (?, ?, ?, ?, ?)",
                  (user_id, username or "", first_name or "", last_name or "", datetime.now()))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка регистрации: {e}")
        return False

def get_user_shop(user_id):
    try:
        conn = sqlite3.connect('shop_bot.db')
        c = conn.cursor()
        c.execute("SELECT * FROM shops WHERE owner_id=?", (user_id,))
        shop = c.fetchone()
        conn.close()
        return shop
    except Exception as e:
        logger.error(f"Ошибка получения магазина: {e}")
        return None

def get_shop_categories(shop_id):
    try:
        conn = sqlite3.connect('shop_bot.db')
        c = conn.cursor()
        c.execute("SELECT category_id, name FROM categories WHERE shop_id=? ORDER BY name", (shop_id,))
        categories = c.fetchall()
        conn.close()
        return categories
    except Exception as e:
        logger.error(f"Ошибка получения категорий: {e}")
        return []

def get_category_products(category_id):
    try:
        conn = sqlite3.connect('shop_bot.db')
        c = conn.cursor()
        c.execute("SELECT product_id, name, price, photo_id, description FROM products WHERE category_id=?", (category_id,))
        products = c.fetchall()
        conn.close()
        return products
    except Exception as e:
        logger.error(f"Ошибка получения товаров: {e}")
        return []

def get_all_shops():
    try:
        conn = sqlite3.connect('shop_bot.db')
        c = conn.cursor()
        c.execute("SELECT shop_id, name, about, photo_id FROM shops")
        shops = c.fetchall()
        conn.close()
        return shops
    except Exception as e:
        logger.error(f"Ошибка получения магазинов: {e}")
        return []

def get_product(product_id):
    try:
        conn = sqlite3.connect('shop_bot.db')
        c = conn.cursor()
        c.execute("SELECT * FROM products WHERE product_id=?", (product_id,))
        product = c.fetchone()
        conn.close()
        return product
    except Exception as e:
        logger.error(f"Ошибка получения товара: {e}")
        return None

def get_payment_details(shop_id):
    try:
        conn = sqlite3.connect('shop_bot.db')
        c = conn.cursor()
        c.execute("SELECT * FROM payment_details WHERE shop_id=?", (shop_id,))
        details = c.fetchall()
        conn.close()
        return details
    except Exception as e:
        logger.error(f"Ошибка получения реквизитов: {e}")
        return []

def get_order(order_id):
    try:
        conn = sqlite3.connect('shop_bot.db')
        c = conn.cursor()
        c.execute("SELECT * FROM orders WHERE order_id=?", (order_id,))
        order = c.fetchone()
        conn.close()
        return order
    except Exception as e:
        logger.error(f"Ошибка получения заказа: {e}")
        return None

def get_shop_orders(shop_id, status=None):
    try:
        conn = sqlite3.connect('shop_bot.db')
        c = conn.cursor()
        if status:
            c.execute("SELECT * FROM orders WHERE shop_id=? AND status=? ORDER BY order_date DESC", (shop_id, status))
        else:
            c.execute("SELECT * FROM orders WHERE shop_id=? ORDER BY order_date DESC", (shop_id,))
        orders = c.fetchall()
        conn.close()
        return orders
    except Exception as e:
        logger.error(f"Ошибка получения заказов: {e}")
        return []

def get_user_orders(user_id, status=None):
    try:
        conn = sqlite3.connect('shop_bot.db')
        c = conn.cursor()
        if status:
            c.execute("SELECT * FROM orders WHERE buyer_id=? AND status=? ORDER BY order_date DESC", (user_id, status))
        else:
            c.execute("SELECT * FROM orders WHERE buyer_id=? ORDER BY order_date DESC", (user_id,))
        orders = c.fetchall()
        conn.close()
        return orders
    except Exception as e:
        logger.error(f"Ошибка получения заказов пользователя: {e}")
        return []

def get_shop_by_name(name):
    try:
        conn = sqlite3.connect('shop_bot.db')
        c = conn.cursor()
        c.execute("SELECT * FROM shops WHERE name=?", (name,))
        shop = c.fetchone()
        conn.close()
        return shop
    except Exception as e:
        logger.error(f"Ошибка получения магазина по имени: {e}")
        return None

def get_shop_by_id(shop_id):
    try:
        conn = sqlite3.connect('shop_bot.db')
        c = conn.cursor()
        c.execute("SELECT * FROM shops WHERE shop_id=?", (shop_id,))
        shop = c.fetchone()
        conn.close()
        return shop
    except Exception as e:
        logger.error(f"Ошибка получения магазина по ID: {e}")
        return None

def get_category_by_id(category_id):
    try:
        conn = sqlite3.connect('shop_bot.db')
        c = conn.cursor()
        c.execute("SELECT * FROM categories WHERE category_id=?", (category_id,))
        category = c.fetchone()
        conn.close()
        return category
    except Exception as e:
        logger.error(f"Ошибка получения категории: {e}")
        return None

def add_category(shop_id, name):
    try:
        conn = sqlite3.connect('shop_bot.db')
        c = conn.cursor()
        c.execute("INSERT INTO categories (shop_id, name) VALUES (?, ?)", (shop_id, name))
        conn.commit()
        category_id = c.lastrowid
        conn.close()
        return category_id
    except Exception as e:
        logger.error(f"Ошибка добавления категории: {e}")
        return None

def delete_category(category_id):
    try:
        conn = sqlite3.connect('shop_bot.db')
        c = conn.cursor()
        c.execute("DELETE FROM products WHERE category_id=?", (category_id,))
        c.execute("DELETE FROM categories WHERE category_id=?", (category_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка удаления категории: {e}")
        return False

def add_product(category_id, name, price, photo_id, description):
    try:
        conn = sqlite3.connect('shop_bot.db')
        c = conn.cursor()
        c.execute("INSERT INTO products (category_id, name, price, photo_id, description) VALUES (?, ?, ?, ?, ?)",
                  (category_id, name, price, photo_id, description))
        conn.commit()
        product_id = c.lastrowid
        conn.close()
        return product_id
    except Exception as e:
        logger.error(f"Ошибка добавления товара: {e}")
        return None

def delete_product(product_id):
    try:
        conn = sqlite3.connect('shop_bot.db')
        c = conn.cursor()
        c.execute("DELETE FROM products WHERE product_id=?", (product_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка удаления товара: {e}")
        return False

def add_payment_details(shop_id, details):
    try:
        conn = sqlite3.connect('shop_bot.db')
        c = conn.cursor()
        c.execute("INSERT INTO payment_details (shop_id, detail_type, detail_value) VALUES (?, ?, ?)",
                  (shop_id, "Общие", details))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка добавления реквизитов: {e}")
        return False

def create_order(shop_id, buyer_id, product_id, product_name, product_price, address, payment_method):
    try:
        conn = sqlite3.connect('shop_bot.db')
        c = conn.cursor()
        c.execute("""INSERT INTO orders (shop_id, buyer_id, product_id, product_name, product_price, 
                     address, payment_method, status, order_date)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                  (shop_id, buyer_id, product_id, product_name, product_price, 
                   address, payment_method, 'active', datetime.now()))
        order_id = c.lastrowid
        conn.commit()
        conn.close()
        return order_id
    except Exception as e:
        logger.error(f"Ошибка создания заказа: {e}")
        return None

def complete_order(order_id):
    try:
        conn = sqlite3.connect('shop_bot.db')
        c = conn.cursor()
        
        c.execute("SELECT * FROM orders WHERE order_id=?", (order_id,))
        order = c.fetchone()
        
        if order:
            c.execute("""INSERT INTO completed_orders (order_id, shop_id, buyer_id, product_name, product_price, order_date, completed_date)
                         VALUES (?, ?, ?, ?, ?, ?, ?)""",
                      (order[0], order[1], order[2], order[5], order[6], order[9], datetime.now()))
            
            c.execute("DELETE FROM products WHERE product_id=?", (order[3],))
            c.execute("DELETE FROM orders WHERE order_id=?", (order_id,))
            
            conn.commit()
            conn.close()
            return True
        
        conn.close()
        return False
    except Exception as e:
        logger.error(f"Ошибка завершения заказа: {e}")
        return False

def cancel_order(order_id):
    try:
        conn = sqlite3.connect('shop_bot.db')
        c = conn.cursor()
        c.execute("DELETE FROM orders WHERE order_id=?", (order_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка отмены заказа: {e}")
        return False

def get_shop_products(shop_id):
    try:
        conn = sqlite3.connect('shop_bot.db')
        c = conn.cursor()
        c.execute("""SELECT p.product_id, p.name, p.price, p.photo_id, p.description, c.name 
                     FROM products p 
                     JOIN categories c ON p.category_id = c.category_id 
                     WHERE c.shop_id = ?""", (shop_id,))
        products = c.fetchall()
        conn.close()
        return products
    except Exception as e:
        logger.error(f"Ошибка получения товаров магазина: {e}")
        return []

# Создание клавиатуры в зависимости от статуса пользователя
async def get_main_keyboard(user_id):
    shop = get_user_shop(user_id)
    
    if shop:
        keyboard = [
            [KeyboardButton("🛍 Купить")],
            [KeyboardButton("🏪 Мой магазин")],
            [KeyboardButton("📦 Мои покупки")],
            [KeyboardButton("📋 Покупки (продавец)")]
        ]
    else:
        keyboard = [
            [KeyboardButton("🛍 Купить")],
            [KeyboardButton("➕ Создать магазин")]
        ]
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Основные обработчики
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    register_user(user.id, user.username, user.first_name, user.last_name)
    
    reply_markup = await get_main_keyboard(user.id)
    
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\n"
        "Добро пожаловать в ShopBot!\n"
        "Здесь вы можете создавать магазины и покупать товары.",
        reply_markup=reply_markup
    )

async def handle_main_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    logger.info(f"Кнопка: {text} от {user_id}")
    
    if text == "➕ Создать магазин":
        if get_user_shop(user_id):
            await update.message.reply_text("У вас уже есть магазин!")
            return
        
        context.user_data['creating_shop'] = True
        await update.message.reply_text("🏪 Введите название магазина:")
        return NAME
    
    elif text == "🏪 Мой магазин":
        shop = get_user_shop(user_id)
        if not shop:
            await update.message.reply_text("У вас нет магазина.")
            return
        
        await show_my_shop(update, context, shop)
        return
    
    elif text == "🛍 Купить":
        shops = get_all_shops()
        if not shops:
            await update.message.reply_text("😕 Пока нет магазинов.")
            return
        
        # Создаем клавиатуру с магазинами
        keyboard = []
        for shop in shops:
            shop_id, name, about, photo_id = shop
            keyboard.append([KeyboardButton(f"🏪 {name}")])
        keyboard.append([KeyboardButton("🔙 Назад")])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text("Выберите магазин:", reply_markup=reply_markup)
        return
    
    elif text.startswith("🏪 ") and text != "🏪 Мой магазин":
        # Выбор магазина для покупки
        shop_name = text.replace("🏪 ", "")
        shop = get_shop_by_name(shop_name)
        
        if not shop:
            await update.message.reply_text("Магазин не найден")
            return
        
        shop_id, owner_id, name, about, photo_id, agreement, created_date = shop
        context.user_data['current_shop_id'] = shop_id
        
        # Показываем магазин с фото и категориями
        await show_shop_for_buying(update, context, shop)
        return
    
    elif text == "📦 Мои покупки":
        await show_my_purchases(update, context)
        return
    
    elif text == "📋 Покупки (продавец)":
        await show_seller_purchases(update, context)
        return
    
    elif text == "🔙 Назад":
        reply_markup = await get_main_keyboard(user_id)
        await update.message.reply_text("Главное меню:", reply_markup=reply_markup)
        return

async def show_my_shop(update: Update, context: ContextTypes.DEFAULT_TYPE, shop):
    shop_id, owner_id, name, about, photo_id, agreement, created_date = shop
    
    # Создаем inline клавиатуру для управления
    keyboard = [
        [InlineKeyboardButton("📁 Создать категорию", callback_data=f"add_category_{shop_id}")],
    ]
    
    # Добавляем существующие категории как кнопки
    categories = get_shop_categories(shop_id)
    for cat_id, cat_name in categories:
        keyboard.append([InlineKeyboardButton(f"📂 {cat_name}", callback_data=f"manage_category_{cat_id}")])
    
    keyboard.append([InlineKeyboardButton("💳 Добавить реквизиты", callback_data=f"add_payment_{shop_id}")])
    keyboard.append([InlineKeyboardButton("🗑 Удалить магазин", callback_data=f"delete_shop_{shop_id}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    caption = f"🏪 {name}\n\n📝 {about}\n\n📋 Управление магазином:"
    
    if photo_id:
        await update.message.reply_photo(
            photo=photo_id,
            caption=caption,
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(caption, reply_markup=reply_markup)

async def show_shop_for_buying(update: Update, context: ContextTypes.DEFAULT_TYPE, shop):
    shop_id, owner_id, name, about, photo_id, agreement, created_date = shop
    
    categories = get_shop_categories(shop_id)
    
    # Создаем клавиатуру с категориями
    keyboard = []
    for cat_id, cat_name in categories:
        keyboard.append([KeyboardButton(f"📂 {cat_name}")])
    
    if not keyboard:
        await update.message.reply_text("В этом магазине пока нет категорий.")
        return
    
    keyboard.append([KeyboardButton("🔙 Назад")])
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    caption = f"🏪 {name}\n\n📝 {about}\n\nВыберите категорию:"
    
    if photo_id:
        await update.message.reply_photo(
            photo=photo_id,
            caption=caption,
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(caption, reply_markup=reply_markup)

async def show_category_products(update: Update, context: ContextTypes.DEFAULT_TYPE, category_id, category_name):
    products = get_category_products(category_id)
    
    if not products:
        await update.message.reply_text(f"В категории '{category_name}' пока нет товаров.")
        return
    
    # Создаем клавиатуру с товарами
    keyboard = []
    for prod_id, name, price, photo, desc in products:
        keyboard.append([KeyboardButton(f"📦 {name} - {price}₽")])
    
    keyboard.append([KeyboardButton("🔙 Назад")])
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"📂 {category_name}\n\nВыберите товар:",
        reply_markup=reply_markup
    )

async def show_product_details(update: Update, context: ContextTypes.DEFAULT_TYPE, product_id):
    product = get_product(product_id)
    if not product:
        await update.message.reply_text("Товар не найден")
        return
    
    prod_id, cat_id, name, price, photo, desc = product
    
    context.user_data['current_product'] = prod_id
    
    text = f"📦 {name}\n💰 {price}₽\n\n📝 {desc if desc else 'Описание отсутствует'}"
    
    keyboard = [[InlineKeyboardButton("🛒 Оформить заказ", callback_data=f"order_product_{prod_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if photo:
        await update.message.reply_photo(photo=photo, caption=text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)

async def show_my_purchases(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    orders = get_user_orders(user_id, 'active')
    
    if not orders:
        await update.message.reply_text("У вас нет активных покупок.")
        return
    
    for order in orders:
        order_id, shop_id, buyer_id, product_id, product_name, product_price, address, payment_method, status, order_date, completed_date = order
        
        text = f"📦 {product_name}\n💰 {product_price}₽\n📍 {address}\n💳 {payment_method}\n📅 {order_date}"
        keyboard = [[InlineKeyboardButton("💬 Связаться с продавцом", callback_data=f"contact_seller_{order_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup)

async def show_seller_purchases(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    shop = get_user_shop(user_id)
    
    if not shop:
        await update.message.reply_text("У вас нет магазина.")
        return
    
    shop_id = shop[0]
    orders = get_shop_orders(shop_id, 'active')
    
    if not orders:
        await update.message.reply_text("Нет активных покупок.")
        return
    
    for order in orders:
        order_id, shop_id_o, buyer_id, product_id, product_name, product_price, address, payment_method, status, order_date, completed_date = order
        
        conn = sqlite3.connect('shop_bot.db')
        c = conn.cursor()
        c.execute("SELECT first_name FROM users WHERE user_id=?", (buyer_id,))
        buyer = c.fetchone()
        conn.close()
        
        buyer_name = buyer[0] if buyer else "Пользователь"
        
        text = f"👤 {buyer_name}\n📦 {product_name}\n💰 {product_price}₽\n📍 {address}\n💳 {payment_method}"
        keyboard = [
            [InlineKeyboardButton("💬 Ответить", callback_data=f"reply_to_buyer_{order_id}")],
            [InlineKeyboardButton("✅ Завершить", callback_data=f"complete_order_{order_id}")],
            [InlineKeyboardButton("❌ Отменить", callback_data=f"cancel_order_{order_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup)

# Создание магазина
async def create_shop_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    shop_name = update.message.text
    
    if get_shop_by_name(shop_name):
        await update.message.reply_text("❌ Это имя уже занято. Выберите другое:")
        return NAME
    
    context.user_data['shop_name'] = shop_name
    await update.message.reply_text("📝 Расскажите о магазине:")
    return ABOUT

async def create_shop_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['shop_about'] = update.message.text
    await update.message.reply_text("📷 Отправьте фото магазина (или напишите 'пропустить'):")
    return PHOTO

async def create_shop_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        photo_id = update.message.photo[-1].file_id
        context.user_data['shop_photo'] = photo_id
    else:
        context.user_data['shop_photo'] = None
    
    await update.message.reply_text("📝 Введите соглашение о продаже:")
    return AGREEMENT

async def create_shop_agreement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    agreement = update.message.text
    
    success = create_shop(
        user_id,
        context.user_data.get('shop_name', ''),
        context.user_data.get('shop_about', ''),
        context.user_data.get('shop_photo'),
        agreement
    )
    
    if success:
        reply_markup = await get_main_keyboard(user_id)
        await update.message.reply_text(
            f"✅ Магазин '{context.user_data.get('shop_name', '')}' создан!",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text("❌ Ошибка создания магазина.")
    
    context.user_data.clear()
    return ConversationHandler.END

async def skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['shop_photo'] = None
    await update.message.reply_text("📝 Введите соглашение о продаже:")
    return AGREEMENT

# Обработчики inline кнопок
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    
    logger.info(f"Callback: {data} от {user_id}")
    
    # Создание категории
    if data.startswith("add_category_"):
        shop_id = int(data.split("_")[2])
        context.user_data['temp_shop_id'] = shop_id
        await query.edit_message_text("Введите название категории:")
        return ADD_CATEGORY
    
    # Управление категорией
    elif data.startswith("manage_category_"):
        category_id = int(data.split("_")[2])
        category = get_category_by_id(category_id)
        if not category:
            await query.edit_message_text("Категория не найдена")
            return
        
        cat_id, shop_id, cat_name = category
        
        keyboard = [
            [InlineKeyboardButton("➕ Добавить товар", callback_data=f"add_product_{cat_id}")],
            [InlineKeyboardButton("🗑 Удалить категорию", callback_data=f"delete_category_{cat_id}")],
            [InlineKeyboardButton("🔙 Назад", callback_data=f"back_to_shop_{shop_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Показываем товары в категории
        products = get_category_products(category_id)
        text = f"📂 {cat_name}\n\n"
        if products:
            text += "Товары в категории:\n"
            for prod_id, name, price, photo, desc in products:
                text += f"• {name} - {price}₽\n"
        else:
            text += "В категории пока нет товаров."
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        return
    
    # Добавление товара
    elif data.startswith("add_product_"):
        category_id = int(data.split("_")[2])
        context.user_data['temp_category_id'] = category_id
        await query.edit_message_text("Введите название товара:")
        return ADD_PRODUCT_NAME
    
    # Удаление категории
    elif data.startswith("delete_category_"):
        category_id = int(data.split("_")[2])
        category = get_category_by_id(category_id)
        if category:
            cat_id, shop_id, cat_name = category
            keyboard = [
                [InlineKeyboardButton("✅ Да, удалить", callback_data=f"confirm_del_cat_{category_id}")],
                [InlineKeyboardButton("❌ Отмена", callback_data=f"back_to_shop_{shop_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"⚠️ Удалить категорию '{cat_name}' и все товары в ней?",
                reply_markup=reply_markup
            )
        return
    
    # Подтверждение удаления категории
    elif data.startswith("confirm_del_cat_"):
        category_id = int(data.split("_")[3])
        category = get_category_by_id(category_id)
        if category:
            shop_id = category[1]
            if delete_category(category_id):
                await query.edit_message_text("✅ Категория удалена!")
                # Возвращаемся в магазин
                shop = get_user_shop(user_id)
                if shop:
                    await show_my_shop(update, context, shop)
            else:
                await query.edit_message_text("❌ Ошибка удаления")
        return
    
    # Возврат в магазин
    elif data.startswith("back_to_shop_"):
        shop_id = int(data.split("_")[2])
        shop = get_shop_by_id(shop_id)
        if shop:
            await show_my_shop(update, context, shop)
        return
    
    # Просмотр товара
    elif data.startswith("view_product_"):
        product_id = int(data.split("_")[2])
        await show_product_details(update, context, product_id)
        return
    
    # Оформление заказа
    elif data.startswith("order_product_"):
        product_id = int(data.split("_")[2])
        product = get_product(product_id)
        if not product:
            await query.edit_message_text("Товар не найден")
            return
        
        context.user_data['current_product'] = product_id
        await query.edit_message_text("📍 Введите адрес доставки:")
        return PURCHASE_ADDRESS
    
    # Добавление реквизитов
    elif data.startswith("add_payment_"):
        shop_id = int(data.split("_")[2])
        context.user_data['temp_shop_id'] = shop_id
        await query.edit_message_text(
            "💳 Введите реквизиты для оплаты:\n\n"
            "Например:\n"
            "Карта: 1234 5678 9012 3456"
        )
        return ADD_PAYMENT_DETAILS
    
    # Удаление магазина
    elif data.startswith("delete_shop_"):
        shop_id = int(data.split("_")[2])
        keyboard = [
            [InlineKeyboardButton("✅ Да, удалить", callback_data=f"confirm_del_shop_{shop_id}")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel_delete")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "⚠️ Удалить магазин? Все данные будут потеряны!",
            reply_markup=reply_markup
        )
        return
    
    # Подтверждение удаления магазина
    elif data.startswith("confirm_del_shop_"):
        shop_id = int(data.split("_")[3])
        conn = sqlite3.connect('shop_bot.db')
        c = conn.cursor()
        c.execute("DELETE FROM orders WHERE shop_id=?", (shop_id,))
        c.execute("DELETE FROM payment_details WHERE shop_id=?", (shop_id,))
        c.execute("DELETE FROM products WHERE category_id IN (SELECT category_id FROM categories WHERE shop_id=?)", (shop_id,))
        c.execute("DELETE FROM categories WHERE shop_id=?", (shop_id,))
        c.execute("DELETE FROM shops WHERE shop_id=?", (shop_id,))
        conn.commit()
        conn.close()
        
        reply_markup = await get_main_keyboard(user_id)
        await query.edit_message_text("🗑 Магазин удален!", reply_markup=reply_markup)
        return
    
    elif data == "cancel_delete":
        shop = get_user_shop(user_id)
        if shop:
            await show_my_shop(update, context, shop)
        return
    
    # Связь с продавцом
    elif data.startswith("contact_seller_"):
        order_id = int(data.split("_")[2])
        order = get_order(order_id)
        if not order:
            await query.edit_message_text("Заказ не найден")
            return
        
        shop = get_shop_by_id(order[1])
        if not shop:
            await query.edit_message_text("Магазин не найден")
            return
        
        context.user_data['current_order_id'] = order_id
        context.user_data['current_seller_id'] = shop[1]
        
        await query.edit_message_text("💬 Напишите сообщение продавцу:")
        return ORDER_CONFIRMATION
    
    # Ответ покупателю
    elif data.startswith("reply_to_buyer_"):
        order_id = int(data.split("_")[2])
        order = get_order(order_id)
        if not order:
            await query.edit_message_text("Заказ не найден")
            return
        
        context.user_data['current_order_id'] = order_id
        context.user_data['current_buyer_id'] = order[2]
        
        await query.edit_message_text("💬 Напишите сообщение покупателю:")
        return ORDER_CONFIRMATION
    
    # Завершение заказа
    elif data.startswith("complete_order_"):
        order_id = int(data.split("_")[2])
        order = get_order(order_id)
        if not order:
            await query.edit_message_text("Заказ не найден")
            return
        
        if complete_order(order_id):
            shop = get_shop_by_id(order[1])
            if shop:
                agreement = shop[5] if shop[5] else "Спасибо за покупку!"
                try:
                    await context.bot.send_message(
                        chat_id=order[2],
                        text=f"✅ Заказ завершен!\n\n{agreement}\n\n{order[5]} - {order[6]}₽"
                    )
                except:
                    pass
            
            await query.edit_message_text("✅ Заказ завершен! Товар удален.")
        else:
            await query.edit_message_text("❌ Ошибка")
        return
    
    # Отмена заказа
    elif data.startswith("cancel_order_"):
        order_id = int(data.split("_")[2])
        order = get_order(order_id)
        if not order:
            await query.edit_message_text("Заказ не найден")
            return
        
        if cancel_order(order_id):
            try:
                await context.bot.send_message(
                    chat_id=order[2],
                    text=f"❌ Заказ отменен!\n\n{order[5]} - {order[6]}₽"
                )
            except:
                pass
            
            await query.edit_message_text("❌ Заказ отменен!")
        else:
            await query.edit_message_text("❌ Ошибка")
        return

# Добавление категории
async def add_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    category_name = update.message.text
    shop_id = context.user_data.get('temp_shop_id')
    
    if not shop_id:
        await update.message.reply_text("Ошибка. Попробуйте заново.")
        return ConversationHandler.END
    
    category_id = add_category(shop_id, category_name)
    
    if category_id:
        # Показываем обновленный магазин
        shop = get_user_shop(update.effective_user.id)
        if shop:
            await show_my_shop(update, context, shop)
    else:
        await update.message.reply_text("❌ Ошибка создания категории.")
    
    context.user_data.pop('temp_shop_id', None)
    return ConversationHandler.END

# Добавление товара
async def add_product_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['product_name'] = update.message.text
    await update.message.reply_text("💰 Введите цену товара (в рублях):")
    return ADD_PRODUCT_PRICE

async def add_product_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = float(update.message.text.replace(',', '.'))
        context.user_data['product_price'] = price
        await update.message.reply_text("📷 Отправьте фото товара (или напишите 'пропустить'):")
        return ADD_PRODUCT_PHOTO
    except ValueError:
        await update.message.reply_text("❌ Введите корректную цену:")
        return ADD_PRODUCT_PRICE

async def add_product_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        photo_id = update.message.photo[-1].file_id
        context.user_data['product_photo'] = photo_id
    else:
        context.user_data['product_photo'] = None
    
    await update.message.reply_text("📝 Введите описание товара:")
    return ADD_PRODUCT_DESC

async def add_product_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    description = update.message.text
    category_id = context.user_data.get('temp_category_id')
    
    if not category_id:
        await update.message.reply_text("Ошибка. Попробуйте заново.")
        return ConversationHandler.END
    
    product_id = add_product(
        category_id,
        context.user_data.get('product_name', ''),
        context.user_data.get('product_price', 0),
        context.user_data.get('product_photo'),
        description
    )
    
    if product_id:
        await update.message.reply_text("✅ Товар добавлен!")
        
        # Показываем обновленную категорию
        category = get_category_by_id(category_id)
        if category:
            shop_id = category[1]
            shop = get_shop_by_id(shop_id)
            if shop:
                await show_my_shop(update, context, shop)
    else:
        await update.message.reply_text("❌ Ошибка добавления товара.")
    
    for key in ['temp_category_id', 'product_name', 'product_price', 'product_photo']:
        context.user_data.pop(key, None)
    
    return ConversationHandler.END

async def skip_product_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['product_photo'] = None
    await update.message.reply_text("📝 Введите описание товара:")
    return ADD_PRODUCT_DESC

# Добавление реквизитов
async def add_payment_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    details = update.message.text
    shop_id = context.user_data.get('temp_shop_id')
    
    if not shop_id:
        await update.message.reply_text("Ошибка. Попробуйте заново.")
        return ConversationHandler.END
    
    if add_payment_details(shop_id, details):
        await update.message.reply_text("✅ Реквизиты добавлены!")
        
        shop = get_user_shop(update.effective_user.id)
        if shop:
            await show_my_shop(update, context, shop)
    else:
        await update.message.reply_text("❌ Ошибка добавления реквизитов.")
    
    context.user_data.pop('temp_shop_id', None)
    return ConversationHandler.END

# Оформление заказа
async def order_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    address = update.message.text
    context.user_data['order_address'] = address
    
    keyboard = [
        [InlineKeyboardButton("💳 Перевод", callback_data="payment_transfer")],
        [InlineKeyboardButton("💵 Наличные", callback_data="payment_cash")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "💳 Выберите способ оплаты:",
        reply_markup=reply_markup
    )
    return PURCHASE_PAYMENT

async def order_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    payment_method = "Перевод" if query.data == "payment_transfer" else "Наличные"
    
    product_id = context.user_data.get('current_product')
    if not product_id:
        await query.edit_message_text("Ошибка. Попробуйте заново.")
        return ConversationHandler.END
    
    product = get_product(product_id)
    if not product:
        await query.edit_message_text("Товар недоступен.")
        return ConversationHandler.END
    
    conn = sqlite3.connect('shop_bot.db')
    c = conn.cursor()
    c.execute("SELECT shop_id FROM categories WHERE category_id=?", (product[1],))
    result = c.fetchone()
    conn.close()
    
    if not result:
        await query.edit_message_text("Ошибка. Магазин не найден.")
        return ConversationHandler.END
    
    shop_id = result[0]
    buyer_id = update.effective_user.id
    
    order_id = create_order(
        shop_id,
        buyer_id,
        product_id,
        product[2],
        product[3],
        context.user_data.get('order_address', ''),
        payment_method
    )
    
    if not order_id:
        await query.edit_message_text("❌ Ошибка создания заказа.")
        return ConversationHandler.END
    
    # Уведомление продавцу
    shop = get_shop_by_id(shop_id)
    if shop:
        try:
            await context.bot.send_message(
                chat_id=shop[1],
                text=f"🛒 НОВАЯ ПОКУПКА!\n\n"
                     f"Товар: {product[2]}\n"
                     f"Цена: {product[3]}₽\n"
                     f"Адрес: {context.user_data.get('order_address', '')}\n"
                     f"Оплата: {payment_method}"
            )
        except:
            pass
    
    # Ответ покупателю
    if payment_method == "Перевод":
        payment_details = get_payment_details(shop_id)
        details_text = "Реквизиты для оплаты:\n\n"
        for detail in payment_details:
            details_text += f"• {detail[2]}\n"
        
        await query.edit_message_text(
            f"✅ Заказ оформлен!\n\n"
            f"Товар: {product[2]}\n"
            f"Цена: {product[3]}₽\n"
            f"Адрес: {context.user_data.get('order_address', '')}\n\n"
            f"{details_text}\n\n"
            f"📢 Продавец свяжется с вами."
        )
    else:
        await query.edit_message_text(
            f"✅ Заказ оформлен!\n\n"
            f"Товар: {product[2]}\n"
            f"Цена: {product[3]}₽\n"
            f"Адрес: {context.user_data.get('order_address', '')}\n"
            f"Оплата: Наличными\n\n"
            f"📢 Продавец свяжется с вами."
        )
    
    context.user_data.pop('current_product', None)
    context.user_data.pop('order_address', None)
    
    return ConversationHandler.END

# Общение продавец-покупатель
async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    order_id = context.user_data.get('current_order_id')
    
    if not order_id:
        await update.message.reply_text("Ошибка. Попробуйте заново.")
        return
    
    order = get_order(order_id)
    if not order:
        await update.message.reply_text("Заказ не найден")
        return
    
    shop = get_shop_by_id(order[1])
    if not shop:
        await update.message.reply_text("Магазин не найден")
        return
    
    if user_id == order[2]:  # Покупатель
        await context.bot.send_message(
            chat_id=shop[1],
            text=f"💬 Сообщение от покупателя:\n\n{text}"
        )
        await update.message.reply_text("✅ Сообщение отправлено продавцу!")
    elif user_id == shop[1]:  # Продавец
        await context.bot.send_message(
            chat_id=order[2],
            text=f"💬 Сообщение от продавца:\n\n{text}"
        )
        await update.message.reply_text("✅ Сообщение отправлено покупателю!")
    
    context.user_data.pop('current_order_id', None)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Действие отменено.")
    context.user_data.clear()
    return ConversationHandler.END

# Основная функция
def main():
    init_db()
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Основные обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_buttons))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Создание магазина
    shop_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^➕ Создать магазин$"), handle_main_buttons)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_shop_name)],
            ABOUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_shop_about)],
            PHOTO: [
                MessageHandler(filters.PHOTO, create_shop_photo),
                MessageHandler(filters.Regex("^пропустить$"), skip_photo)
            ],
            AGREEMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_shop_agreement)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    application.add_handler(shop_conv)
    
    # Добавление категории
    category_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_callback, pattern="^add_category_")],
        states={
            ADD_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_category)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    application.add_handler(category_conv)
    
    # Добавление товара
    product_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_callback, pattern="^add_product_")],
        states={
            ADD_PRODUCT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_name)],
            ADD_PRODUCT_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_price)],
            ADD_PRODUCT_PHOTO: [
                MessageHandler(filters.PHOTO, add_product_photo),
                MessageHandler(filters.Regex("^пропустить$"), skip_product_photo)
            ],
            ADD_PRODUCT_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_description)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    application.add_handler(product_conv)
    
    # Добавление реквизитов
    payment_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_callback, pattern="^add_payment_")],
        states={
            ADD_PAYMENT_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_payment_details)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    application.add_handler(payment_conv)
    
    # Оформление заказа
    order_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_callback, pattern="^order_product_")],
        states={
            PURCHASE_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, order_address)],
            PURCHASE_PAYMENT: [CallbackQueryHandler(order_payment, pattern="^payment_")],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    application.add_handler(order_conv)
    
    # Общение
    message_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handle_callback, pattern="^contact_seller_"),
            CallbackQueryHandler(handle_callback, pattern="^reply_to_buyer_")
        ],
        states={
            ORDER_CONFIRMATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_message)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    application.add_handler(message_conv)
    
    logger.info("Бот запущен!")
    application.run_polling()

if __name__ == '__main__':
    main()
