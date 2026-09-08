import logging
import sqlite3
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters, ConversationHandler

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен бота
BOT_TOKEN = "8829785655:AAHv-44OuFHSUV0BFI38kyROyng5PdEVEe0"

# Состояния
NAME, ABOUT, PHOTO, AGREEMENT = range(4)

# Инициализация БД
def init_db():
    try:
        conn = sqlite3.connect('shop_bot.db')
        c = conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, register_date TIMESTAMP)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS shops
                     (shop_id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER, name TEXT UNIQUE, 
                      about TEXT, photo_id TEXT, agreement TEXT, created_date TIMESTAMP)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS categories
                     (category_id INTEGER PRIMARY KEY AUTOINCREMENT, shop_id INTEGER, name TEXT)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS products
                     (product_id INTEGER PRIMARY KEY AUTOINCREMENT, category_id INTEGER, 
                      name TEXT, price REAL, photo_id TEXT, description TEXT)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS payment_details
                     (detail_id INTEGER PRIMARY KEY AUTOINCREMENT, shop_id INTEGER, detail_value TEXT)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS orders
                     (order_id INTEGER PRIMARY KEY AUTOINCREMENT, shop_id INTEGER, buyer_id INTEGER,
                      product_id INTEGER, product_name TEXT, product_price REAL, address TEXT,
                      payment_method TEXT, status TEXT, order_date TIMESTAMP)''')
        
        conn.commit()
        conn.close()
        logger.info("База данных создана")
        return True
    except Exception as e:
        logger.error(f"Ошибка БД: {e}")
        return False

# Функции БД
def register_user(user_id, username, first_name):
    try:
        conn = sqlite3.connect('shop_bot.db')
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (user_id, username, first_name, register_date) VALUES (?, ?, ?, ?)",
                  (user_id, username or "", first_name or "", datetime.now()))
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
        logger.error(f"Ошибка: {e}")
        return None

def create_shop(user_id, name, about, photo_id, agreement):
    try:
        conn = sqlite3.connect('shop_bot.db')
        c = conn.cursor()
        c.execute("INSERT INTO shops (owner_id, name, about, photo_id, agreement, created_date) VALUES (?, ?, ?, ?, ?, ?)",
                  (user_id, name, about, photo_id, agreement, datetime.now()))
        conn.commit()
        shop_id = c.lastrowid
        conn.close()
        logger.info(f"Магазин создан: {name} (ID: {shop_id})")
        return shop_id
    except Exception as e:
        logger.error(f"Ошибка создания магазина: {e}")
        return None

def get_all_shops():
    try:
        conn = sqlite3.connect('shop_bot.db')
        c = conn.cursor()
        c.execute("SELECT shop_id, name, about, photo_id FROM shops")
        shops = c.fetchall()
        conn.close()
        return shops
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return []

def get_shop_categories(shop_id):
    try:
        conn = sqlite3.connect('shop_bot.db')
        c = conn.cursor()
        c.execute("SELECT category_id, name FROM categories WHERE shop_id=?", (shop_id,))
        categories = c.fetchall()
        conn.close()
        return categories
    except Exception as e:
        logger.error(f"Ошибка: {e}")
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
        logger.error(f"Ошибка: {e}")
        return []

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
        logger.error(f"Ошибка: {e}")
        return None

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
        logger.error(f"Ошибка: {e}")
        return None

def get_shop_by_name(name):
    try:
        conn = sqlite3.connect('shop_bot.db')
        c = conn.cursor()
        c.execute("SELECT * FROM shops WHERE name=?", (name,))
        shop = c.fetchone()
        conn.close()
        return shop
    except Exception as e:
        logger.error(f"Ошибка: {e}")
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
        logger.error(f"Ошибка: {e}")
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
        logger.error(f"Ошибка: {e}")
        return None

# Клавиатуры
def get_main_keyboard(has_shop):
    if has_shop:
        keyboard = [
            [KeyboardButton("🛍 Купить")],
            [KeyboardButton("🏪 Мой магазин")],
        ]
    else:
        keyboard = [
            [KeyboardButton("🛍 Купить")],
            [KeyboardButton("➕ Создать магазин")],
        ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Старт
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    register_user(user_id, user.username, user.first_name)
    
    shop = get_user_shop(user_id)
    has_shop = shop is not None
    
    reply_markup = get_main_keyboard(has_shop)
    
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\n"
        "Добро пожаловать в ShopBot!\n"
        "Выберите действие:",
        reply_markup=reply_markup
    )

# Обработка кнопок
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        
        shop_id, owner_id, name, about, photo_id, agreement, created_date = shop
        
        keyboard = [
            [InlineKeyboardButton("📁 Создать категорию", callback_data=f"add_category_{shop_id}")],
        ]
        
        categories = get_shop_categories(shop_id)
        for cat_id, cat_name in categories:
            keyboard.append([InlineKeyboardButton(f"📂 {cat_name}", callback_data=f"manage_category_{cat_id}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        caption = f"🏪 {name}\n\n📝 {about}"
        
        if photo_id:
            await update.message.reply_photo(photo=photo_id, caption=caption, reply_markup=reply_markup)
        else:
            await update.message.reply_text(caption, reply_markup=reply_markup)
        return
    
    elif text == "🛍 Купить":
        shops = get_all_shops()
        if not shops:
            await update.message.reply_text("Пока нет магазинов.")
            return
        
        keyboard = []
        for shop in shops:
            shop_id, name, about, photo_id = shop
            keyboard.append([KeyboardButton(f"🏪 {name}")])
        keyboard.append([KeyboardButton("🔙 Назад")])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text("Выберите магазин:", reply_markup=reply_markup)
        return
    
    elif text.startswith("🏪 ") and text != "🏪 Мой магазин":
        shop_name = text.replace("🏪 ", "")
        shop = get_shop_by_name(shop_name)
        
        if not shop:
            await update.message.reply_text("Магазин не найден")
            return
        
        shop_id, owner_id, name, about, photo_id, agreement, created_date = shop
        context.user_data['current_shop_id'] = shop_id
        
        categories = get_shop_categories(shop_id)
        
        keyboard = []
        for cat_id, cat_name in categories:
            keyboard.append([KeyboardButton(f"📂 {cat_name}")])
        
        if not keyboard:
            await update.message.reply_text("В этом магазине пока нет категорий.")
            return
        
        keyboard.append([KeyboardButton("🔙 Назад")])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        caption = f"🏪 {name}\n\n📝 {about}"
        
        if photo_id:
            await update.message.reply_photo(photo=photo_id, caption=caption, reply_markup=reply_markup)
        else:
            await update.message.reply_text(caption, reply_markup=reply_markup)
        return
    
    elif text.startswith("📂 "):
        category_name = text.replace("📂 ", "")
        shop_id = context.user_data.get('current_shop_id')
        
        if not shop_id:
            await update.message.reply_text("Ошибка. Выберите магазин сначала.")
            return
        
        categories = get_shop_categories(shop_id)
        category_id = None
        for cat_id, cat_name in categories:
            if cat_name == category_name:
                category_id = cat_id
                break
        
        if not category_id:
            await update.message.reply_text("Категория не найдена")
            return
        
        products = get_category_products(category_id)
        
        if not products:
            await update.message.reply_text(f"В категории '{category_name}' пока нет товаров.")
            return
        
        keyboard = []
        for prod_id, name, price, photo, desc in products:
            keyboard.append([KeyboardButton(f"📦 {name} - {price}₽")])
        
        keyboard.append([KeyboardButton("🔙 Назад")])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            f"📂 {category_name}\n\nВыберите товар:",
            reply_markup=reply_markup
        )
        return
    
    elif text.startswith("📦 "):
        product_info = text.replace("📦 ", "")
        product_name = product_info.split(" - ")[0]
        
        shop_id = context.user_data.get('current_shop_id')
        if not shop_id:
            await update.message.reply_text("Ошибка. Выберите магазин сначала.")
            return
        
        categories = get_shop_categories(shop_id)
        found_product = None
        for cat_id, cat_name in categories:
            products = get_category_products(cat_id)
            for prod in products:
                if prod[1] == product_name:
                    found_product = prod
                    break
            if found_product:
                break
        
        if not found_product:
            await update.message.reply_text("Товар не найден")
            return
        
        prod_id, name, price, photo, desc = found_product
        context.user_data['current_product'] = prod_id
        
        text = f"📦 {name}\n💰 {price}₽\n\n📝 {desc if desc else 'Описание отсутствует'}"
        
        keyboard = [[InlineKeyboardButton("🛒 Оформить заказ", callback_data=f"order_product_{prod_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if photo:
            await update.message.reply_photo(photo=photo, caption=text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)
        return
    
    elif text == "🔙 Назад":
        shop = get_user_shop(user_id)
        reply_markup = get_main_keyboard(shop is not None)
        await update.message.reply_text("Главное меню:", reply_markup=reply_markup)
        return

# Создание магазина
async def create_shop_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    shop_name = update.message.text
    
    logger.info(f"Получено название: {shop_name} от {user_id}")
    
    # Проверяем, не занято ли имя
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
    
    shop_name = context.user_data.get('shop_name', '')
    shop_about = context.user_data.get('shop_about', '')
    shop_photo = context.user_data.get('shop_photo')
    
    logger.info(f"Создаем магазин: {shop_name} для {user_id}")
    
    # СОЗДАЕМ МАГАЗИН
    shop_id = create_shop(user_id, shop_name, shop_about, shop_photo, agreement)
    
    if shop_id:
        reply_markup = get_main_keyboard(True)
        await update.message.reply_text(
            f"✅ Магазин '{shop_name}' успешно создан!",
            reply_markup=reply_markup
        )
        logger.info(f"Магазин создан! ID: {shop_id}")
    else:
        await update.message.reply_text("❌ Ошибка создания магазина. Попробуйте позже.")
        logger.error(f"Не удалось создать магазин для {user_id}")
    
    context.user_data.clear()
    return ConversationHandler.END

async def skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['shop_photo'] = None
    await update.message.reply_text("📝 Введите соглашение о продаже:")
    return AGREEMENT

# Обработка inline кнопок
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    
    logger.info(f"Callback: {data}")
    
    if data.startswith("add_category_"):
        shop_id = int(data.split("_")[2])
        context.user_data['temp_shop_id'] = shop_id
        await query.edit_message_text("Введите название категории:")
        return ADD_CATEGORY
    
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
        
        products = get_category_products(category_id)
        text = f"📂 {cat_name}\n\n"
        if products:
            text += "Товары:\n"
            for prod_id, name, price, photo, desc in products:
                text += f"• {name} - {price}₽\n"
        else:
            text += "Нет товаров."
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        return
    
    elif data.startswith("add_product_"):
        category_id = int(data.split("_")[2])
        context.user_data['temp_category_id'] = category_id
        await query.edit_message_text("Введите название товара:")
        return ADD_PRODUCT_NAME
    
    elif data.startswith("delete_category_"):
        category_id = int(data.split("_")[2])
        category = get_category_by_id(category_id)
        if category:
            cat_id, shop_id, cat_name = category
            keyboard = [
                [InlineKeyboardButton("✅ Да", callback_data=f"confirm_del_cat_{category_id}")],
                [InlineKeyboardButton("❌ Нет", callback_data=f"back_to_shop_{shop_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(f"Удалить категорию '{cat_name}'?", reply_markup=reply_markup)
        return
    
    elif data.startswith("confirm_del_cat_"):
        category_id = int(data.split("_")[3])
        category = get_category_by_id(category_id)
        if category:
            shop_id = category[1]
            conn = sqlite3.connect('shop_bot.db')
            c = conn.cursor()
            c.execute("DELETE FROM products WHERE category_id=?", (category_id,))
            c.execute("DELETE FROM categories WHERE category_id=?", (category_id,))
            conn.commit()
            conn.close()
            await query.edit_message_text("✅ Категория удалена!")
            shop = get_user_shop(user_id)
            if shop:
                await show_shop(update, context, shop)
        return
    
    elif data.startswith("back_to_shop_"):
        shop_id = int(data.split("_")[2])
        shop = get_shop_by_id(shop_id)
        if shop:
            await show_shop(update, context, shop)
        return
    
    elif data.startswith("order_product_"):
        product_id = int(data.split("_")[2])
        product = get_product(product_id)
        if not product:
            await query.edit_message_text("Товар не найден")
            return
        
        context.user_data['current_product'] = product_id
        await query.edit_message_text("📍 Введите адрес доставки:")
        return PURCHASE_ADDRESS
    
    elif data.startswith("delete_shop_"):
        shop_id = int(data.split("_")[2])
        keyboard = [
            [InlineKeyboardButton("✅ Да", callback_data=f"confirm_del_shop_{shop_id}")],
            [InlineKeyboardButton("❌ Нет", callback_data="cancel_delete")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("⚠️ Удалить магазин?", reply_markup=reply_markup)
        return
    
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
        
        reply_markup = get_main_keyboard(False)
        await query.edit_message_text("🗑 Магазин удален!", reply_markup=reply_markup)
        return
    
    elif data == "cancel_delete":
        shop = get_user_shop(user_id)
        if shop:
            await show_shop(update, context, shop)
        return

async def show_shop(update, context, shop):
    shop_id, owner_id, name, about, photo_id, agreement, created_date = shop
    
    keyboard = [
        [InlineKeyboardButton("📁 Создать категорию", callback_data=f"add_category_{shop_id}")],
    ]
    
    categories = get_shop_categories(shop_id)
    for cat_id, cat_name in categories:
        keyboard.append([InlineKeyboardButton(f"📂 {cat_name}", callback_data=f"manage_category_{cat_id}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    caption = f"🏪 {name}\n\n📝 {about}"
    
    if photo_id:
        await update.message.reply_photo(photo=photo_id, caption=caption, reply_markup=reply_markup)
    else:
        await update.message.reply_text(caption, reply_markup=reply_markup)

# Добавление категории
async def add_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    category_name = update.message.text
    shop_id = context.user_data.get('temp_shop_id')
    
    if not shop_id:
        await update.message.reply_text("Ошибка.")
        return ConversationHandler.END
    
    add_category(shop_id, category_name)
    
    shop = get_user_shop(update.effective_user.id)
    if shop:
        await show_shop(update, context, shop)
    
    context.user_data.pop('temp_shop_id', None)
    return ConversationHandler.END

# Добавление товара
async def add_product_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['product_name'] = update.message.text
    await update.message.reply_text("💰 Введите цену:")
    return ADD_PRODUCT_PRICE

async def add_product_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = float(update.message.text.replace(',', '.'))
        context.user_data['product_price'] = price
        await update.message.reply_text("📷 Отправьте фото (или 'пропустить'):")
        return ADD_PRODUCT_PHOTO
    except:
        await update.message.reply_text("❌ Введите число:")
        return ADD_PRODUCT_PRICE

async def add_product_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        context.user_data['product_photo'] = update.message.photo[-1].file_id
    else:
        context.user_data['product_photo'] = None
    
    await update.message.reply_text("📝 Введите описание:")
    return ADD_PRODUCT_DESC

async def add_product_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    description = update.message.text
    category_id = context.user_data.get('temp_category_id')
    
    if not category_id:
        await update.message.reply_text("Ошибка.")
        return ConversationHandler.END
    
    add_product(
        category_id,
        context.user_data.get('product_name', ''),
        context.user_data.get('product_price', 0),
        context.user_data.get('product_photo'),
        description
    )
    
    await update.message.reply_text("✅ Товар добавлен!")
    
    category = get_category_by_id(category_id)
    if category:
        shop = get_shop_by_id(category[1])
        if shop:
            await show_shop(update, context, shop)
    
    for key in ['temp_category_id', 'product_name', 'product_price', 'product_photo']:
        context.user_data.pop(key, None)
    
    return ConversationHandler.END

async def skip_product_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['product_photo'] = None
    await update.message.reply_text("📝 Введите описание:")
    return ADD_PRODUCT_DESC

# Оформление заказа
async def order_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    address = update.message.text
    context.user_data['order_address'] = address
    
    keyboard = [
        [InlineKeyboardButton("💳 Перевод", callback_data="payment_transfer")],
        [InlineKeyboardButton("💵 Наличные", callback_data="payment_cash")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("Выберите оплату:", reply_markup=reply_markup)
    return PURCHASE_PAYMENT

async def order_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    payment_method = "Перевод" if query.data == "payment_transfer" else "Наличные"
    
    product_id = context.user_data.get('current_product')
    if not product_id:
        await query.edit_message_text("Ошибка.")
        return ConversationHandler.END
    
    product = get_product(product_id)
    if not product:
        await query.edit_message_text("Товар не найден.")
        return ConversationHandler.END
    
    # Создаем заказ
    conn = sqlite3.connect('shop_bot.db')
    c = conn.cursor()
    c.execute("SELECT shop_id FROM categories WHERE category_id=?", (product[1],))
    result = c.fetchone()
    conn.close()
    
    if not result:
        await query.edit_message_text("Ошибка.")
        return ConversationHandler.END
    
    shop_id = result[0]
    buyer_id = update.effective_user.id
    
    conn = sqlite3.connect('shop_bot.db')
    c = conn.cursor()
    c.execute("""INSERT INTO orders (shop_id, buyer_id, product_id, product_name, product_price, 
                 address, payment_method, status, order_date)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
              (shop_id, buyer_id, product_id, product[2], product[3],
               context.user_data.get('order_address', ''), payment_method, 'active', datetime.now()))
    conn.commit()
    conn.close()
    
    await query.edit_message_text(
        f"✅ Заказ оформлен!\n\n"
        f"Товар: {product[2]}\n"
        f"Цена: {product[3]}₽\n"
        f"Адрес: {context.user_data.get('order_address', '')}\n"
        f"Оплата: {payment_method}\n\n"
        f"Продавец свяжется с вами."
    )
    
    context.user_data.pop('current_product', None)
    context.user_data.pop('order_address', None)
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено.")
    context.user_data.clear()
    return ConversationHandler.END

# Главная функция
def main():
    # Инициализируем БД
    if not init_db():
        logger.error("Не удалось инициализировать БД")
        return
    
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Старт
    application.add_handler(CommandHandler("start", start))
    
    # Создание магазина
    shop_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^➕ Создать магазин$"), handle_buttons)],
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
    
    # Остальные обработчики
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Добавление категории
    category_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_callback, pattern="^add_category_")],
        states={ADD_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_category)]},
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
    
    # Запускаем
    logger.info("Бот запущен!")
    application.run_polling()

if __name__ == '__main__':
    main()
