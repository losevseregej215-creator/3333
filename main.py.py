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
NAME, ABOUT, PHOTO, AGREEMENT, ADD_CATEGORY, ADD_PRODUCT_NAME, ADD_PRODUCT_PRICE, ADD_PRODUCT_PHOTO, ADD_PRODUCT_DESC = range(9)

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

def add_category(shop_id, name):
    try:
        conn = sqlite3.connect('shop_bot.db')
        c = conn.cursor()
        c.execute("INSERT INTO categories (shop_id, name) VALUES (?, ?)", (shop_id, name))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return False

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

def add_product(category_id, name, price, photo_id, description):
    try:
        conn = sqlite3.connect('shop_bot.db')
        c = conn.cursor()
        c.execute("INSERT INTO products (category_id, name, price, photo_id, description) VALUES (?, ?, ?, ?, ?)",
                  (category_id, name, price, photo_id, description))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return False

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

def delete_shop(shop_id):
    try:
        conn = sqlite3.connect('shop_bot.db')
        c = conn.cursor()
        c.execute("DELETE FROM products WHERE category_id IN (SELECT category_id FROM categories WHERE shop_id=?)", (shop_id,))
        c.execute("DELETE FROM categories WHERE shop_id=?", (shop_id,))
        c.execute("DELETE FROM shops WHERE shop_id=?", (shop_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return False

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
    reply_markup = get_main_keyboard(shop is not None)
    
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\nВыберите действие:",
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
        
        await update.message.reply_text("🏪 Введите название магазина:")
        return NAME
    
    elif text == "🏪 Мой магазин":
        shop = get_user_shop(user_id)
        if not shop:
            await update.message.reply_text("У вас нет магазина. Создайте его!")
            return
        
        await show_my_shop(update, context, shop)
        return
    
    elif text == "🛍 Купить":
        shops = get_all_shops()
        if not shops:
            await update.message.reply_text("😕 Пока нет магазинов.")
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
        
        await show_shop_profile(update, context, shop)
        return
    
    elif text.startswith("📂 "):
        # Выбор категории для просмотра товаров
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
        # Просмотр товара
        product_info = text.replace("📦 ", "")
        product_name = product_info.split(" - ")[0]
        
        shop_id = context.user_data.get('current_shop_id')
        if not shop_id:
            await update.message.reply_text("Ошибка.")
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
        text = f"📦 {name}\n💰 {price}₽\n\n📝 {desc if desc else 'Описание отсутствует'}"
        
        if photo:
            await update.message.reply_photo(photo=photo, caption=text)
        else:
            await update.message.reply_text(text)
        return
    
    elif text == "🔙 Назад":
        shop = get_user_shop(user_id)
        reply_markup = get_main_keyboard(shop is not None)
        await update.message.reply_text("Главное меню:", reply_markup=reply_markup)
        return

# Показать профиль магазина для покупателя
async def show_shop_profile(update: Update, context: ContextTypes.DEFAULT_TYPE, shop):
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

# Показать мой магазин (для владельца)
async def show_my_shop(update: Update, context: ContextTypes.DEFAULT_TYPE, shop):
    shop_id, owner_id, name, about, photo_id, agreement, created_date = shop
    
    keyboard = [
        [InlineKeyboardButton("📁 Создать категорию", callback_data=f"add_category_{shop_id}")],
    ]
    
    categories = get_shop_categories(shop_id)
    for cat_id, cat_name in categories:
        keyboard.append([InlineKeyboardButton(f"📂 {cat_name}", callback_data=f"manage_category_{cat_id}")])
    
    keyboard.append([InlineKeyboardButton("🗑 Удалить магазин", callback_data=f"delete_shop_{shop_id}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    caption = f"🏪 {name}\n\n📝 {about}\n\n📋 Управление магазином:"
    
    if photo_id:
        await update.message.reply_photo(photo=photo_id, caption=caption, reply_markup=reply_markup)
    else:
        await update.message.reply_text(caption, reply_markup=reply_markup)

# СОЗДАНИЕ МАГАЗИНА
async def create_shop_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    shop_name = update.message.text
    
    logger.info(f"ПОЛУЧЕНО НАЗВАНИЕ: '{shop_name}' от {user_id}")
    
    if get_shop_by_name(shop_name):
        await update.message.reply_text("❌ Это имя уже занято. Выберите другое:")
        return NAME
    
    context.user_data['shop_name'] = shop_name
    await update.message.reply_text("📝 Расскажите о магазине:")
    return ABOUT

async def create_shop_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['shop_about'] = update.message.text
    await update.message.reply_text("📷 Отправьте фото (или напишите 'пропустить'):")
    return PHOTO

async def create_shop_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        context.user_data['shop_photo'] = update.message.photo[-1].file_id
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
    
    logger.info(f"СОЗДАЕМ МАГАЗИН: '{shop_name}' для {user_id}")
    
    shop_id = create_shop(user_id, shop_name, shop_about, shop_photo, agreement)
    
    if shop_id:
        reply_markup = get_main_keyboard(True)
        await update.message.reply_text(
            f"✅ Магазин '{shop_name}' успешно создан!",
            reply_markup=reply_markup
        )
        logger.info(f"МАГАЗИН СОЗДАН! ID: {shop_id}")
    else:
        await update.message.reply_text("❌ Ошибка создания магазина.")
    
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
        products = get_category_products(category_id)
        
        keyboard = [
            [InlineKeyboardButton("➕ Добавить товар", callback_data=f"add_product_{category_id}")],
            [InlineKeyboardButton("🔙 Назад в магазин", callback_data="back_to_shop")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = "📂 Товары в категории:\n\n"
        if products:
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
    
    elif data == "back_to_shop":
        shop = get_user_shop(user_id)
        if shop:
            await show_my_shop(update, context, shop)
        return
    
    elif data.startswith("delete_shop_"):
        shop_id = int(data.split("_")[2])
        keyboard = [
            [InlineKeyboardButton("✅ Да, удалить", callback_data=f"confirm_delete_shop_{shop_id}")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel_delete")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("⚠️ Удалить магазин? Все данные будут потеряны!", reply_markup=reply_markup)
        return
    
    elif data.startswith("confirm_delete_shop_"):
        shop_id = int(data.split("_")[3])
        if delete_shop(shop_id):
            reply_markup = get_main_keyboard(False)
            await query.edit_message_text("🗑 Магазин удален!", reply_markup=reply_markup)
        else:
            await query.edit_message_text("❌ Ошибка удаления")
        return
    
    elif data == "cancel_delete":
        shop = get_user_shop(user_id)
        if shop:
            await show_my_shop(update, context, shop)
        return

# Добавление категории
async def add_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    category_name = update.message.text
    shop_id = context.user_data.get('temp_shop_id')
    
    if not shop_id:
        await update.message.reply_text("Ошибка. Попробуйте заново.")
        return ConversationHandler.END
    
    if add_category(shop_id, category_name):
        await update.message.reply_text(f"✅ Категория '{category_name}' создана!")
        
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
    await update.message.reply_text("💰 Введите цену товара:")
    return ADD_PRODUCT_PRICE

async def add_product_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = float(update.message.text.replace(',', '.'))
        context.user_data['product_price'] = price
        await update.message.reply_text("📷 Отправьте фото (или 'пропустить'):")
        return ADD_PRODUCT_PHOTO
    except ValueError:
        await update.message.reply_text("❌ Введите число:")
        return ADD_PRODUCT_PRICE

async def add_product_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        context.user_data['product_photo'] = update.message.photo[-1].file_id
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
    
    if add_product(
        category_id,
        context.user_data.get('product_name', ''),
        context.user_data.get('product_price', 0),
        context.user_data.get('product_photo'),
        description
    ):
        await update.message.reply_text("✅ Товар добавлен!")
    else:
        await update.message.reply_text("❌ Ошибка добавления товара.")
    
    # Возвращаемся в магазин
    shop = get_user_shop(update.effective_user.id)
    if shop:
        await show_my_shop(update, context, shop)
    
    for key in ['temp_category_id', 'product_name', 'product_price', 'product_photo']:
        context.user_data.pop(key, None)
    
    return ConversationHandler.END

async def skip_product_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['product_photo'] = None
    await update.message.reply_text("📝 Введите описание товара:")
    return ADD_PRODUCT_DESC

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено.")
    context.user_data.clear()
    return ConversationHandler.END

# Главная функция
def main():
    init_db()
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Старт
    application.add_handler(CommandHandler("start", start))
    
    # СОЗДАНИЕ МАГАЗИНА
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
    
    # ОСТАЛЬНЫЕ КНОПКИ
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons))
    
    # INLINE КНОПКИ
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # ДОБАВЛЕНИЕ КАТЕГОРИИ
    category_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_callback, pattern="^add_category_")],
        states={
            ADD_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_category)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    application.add_handler(category_conv)
    
    # ДОБАВЛЕНИЕ ТОВАРА
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
    
    logger.info("Бот запущен!")
    application.run_polling()

if __name__ == '__main__':
    main()
