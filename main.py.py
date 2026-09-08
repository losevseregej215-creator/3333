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

# Функции для работы с БД
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
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Ошибка создания магазина: {e}")
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

# Обработчики
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    # Регистрируем пользователя
    register_user(user_id, user.username, user.first_name)
    
    # Проверяем наличие магазина
    shop = get_user_shop(user_id)
    has_shop = shop is not None
    
    # Создаем клавиатуру
    reply_markup = get_main_keyboard(has_shop)
    
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\n"
        "Добро пожаловать в ShopBot!\n"
        "Выберите действие:",
        reply_markup=reply_markup
    )

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    logger.info(f"Пользователь {user_id} нажал: {text}")
    
    if text == "➕ Создать магазин":
        # Проверяем, есть ли уже магазин
        if get_user_shop(user_id):
            await update.message.reply_text("У вас уже есть магазин!")
            return
        
        # Начинаем создание
        context.user_data['creating_shop'] = True
        await update.message.reply_text("Введите название магазина:")
        return NAME
    
    elif text == "🏪 Мой магазин":
        shop = get_user_shop(user_id)
        if not shop:
            await update.message.reply_text("У вас нет магазина.")
            return
        
        shop_id, owner_id, name, about, photo_id, agreement, created_date = shop
        
        # Создаем inline кнопки
        keyboard = [
            [InlineKeyboardButton("📁 Добавить категорию", callback_data=f"add_cat_{shop_id}")],
            [InlineKeyboardButton("➕ Добавить товар", callback_data=f"add_prod_{shop_id}")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🏪 {name}\n\n📝 {about}\n\nУправление магазином:",
            reply_markup=reply_markup
        )
        return
    
    elif text == "🛍 Купить":
        shops = get_all_shops()
        if not shops:
            await update.message.reply_text("Пока нет магазинов.")
            return
        
        # Создаем клавиатуру с магазинами
        keyboard = []
        for shop in shops:
            shop_id, name, about, photo_id = shop
            keyboard.append([KeyboardButton(f"📦 {name}")])
        keyboard.append([KeyboardButton("🔙 Назад")])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text("Выберите магазин:", reply_markup=reply_markup)
        return
    
    elif text.startswith("📦 "):
        # Выбор магазина для покупки
        shop_name = text.replace("📦 ", "")
        shop = get_user_shop(user_id)  # Временно, нужно искать по имени
        
        # Ищем магазин по имени
        shops = get_all_shops()
        for s in shops:
            if s[1] == shop_name:
                shop_id = s[0]
                categories = get_shop_categories(shop_id)
                if not categories:
                    await update.message.reply_text("В этом магазине нет категорий.")
                    return
                
                # Показываем категории
                keyboard = []
                for cat in categories:
                    cat_id, cat_name = cat
                    keyboard.append([InlineKeyboardButton(cat_name, callback_data=f"view_cat_{cat_id}")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text("Выберите категорию:", reply_markup=reply_markup)
                return
        
        await update.message.reply_text("Магазин не найден.")
        return
    
    elif text == "🔙 Назад":
        shop = get_user_shop(user_id)
        reply_markup = get_main_keyboard(shop is not None)
        await update.message.reply_text("Главное меню:", reply_markup=reply_markup)
        return

# Создание магазина
async def create_shop_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['shop_name'] = update.message.text
    await update.message.reply_text("Расскажите о магазине:")
    return ABOUT

async def create_shop_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['shop_about'] = update.message.text
    await update.message.reply_text("Отправьте фото (или напишите 'пропустить'):")
    return PHOTO

async def create_shop_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        photo_id = update.message.photo[-1].file_id
        context.user_data['shop_photo'] = photo_id
    else:
        context.user_data['shop_photo'] = None
    
    await update.message.reply_text("Введите соглашение о продаже:")
    return AGREEMENT

async def create_shop_agreement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    agreement = update.message.text
    
    # Сохраняем магазин
    success = create_shop(
        user_id,
        context.user_data.get('shop_name', ''),
        context.user_data.get('shop_about', ''),
        context.user_data.get('shop_photo'),
        agreement
    )
    
    if success:
        # Обновляем клавиатуру
        reply_markup = get_main_keyboard(True)
        await update.message.reply_text(
            "✅ Магазин создан!",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text("❌ Ошибка создания магазина.")
    
    # Очищаем данные
    context.user_data.clear()
    return ConversationHandler.END

async def skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['shop_photo'] = None
    await update.message.reply_text("Введите соглашение о продаже:")
    return AGREEMENT

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Действие отменено.")
    context.user_data.clear()
    return ConversationHandler.END

# Обработка inline кнопок
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    
    logger.info(f"Callback: {data} от {user_id}")
    
    if data.startswith("add_cat_"):
        await query.edit_message_text("Введите название категории:")
        return
    
    elif data.startswith("add_prod_"):
        shop_id = int(data.split("_")[2])
        categories = get_shop_categories(shop_id)
        if not categories:
            await query.edit_message_text("Сначала создайте категорию!")
            return
        
        keyboard = []
        for cat in categories:
            cat_id, cat_name = cat
            keyboard.append([InlineKeyboardButton(cat_name, callback_data=f"sel_cat_{cat_id}")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Выберите категорию:", reply_markup=reply_markup)
        return
    
    elif data.startswith("view_cat_"):
        category_id = int(data.split("_")[2])
        products = get_category_products(category_id)
        if not products:
            await query.edit_message_text("В этой категории нет товаров.")
            return
        
        text = "Товары:\n\n"
        for prod in products:
            prod_id, name, price, photo, desc = prod
            text += f"📦 {name}\n💰 {price}₽\n{desc if desc else ''}\n\n"
        
        await query.edit_message_text(text)
        return

# Основная функция
def main():
    # Инициализируем БД
    init_db()
    
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    
    # ConversationHandler для создания магазина
    conv_handler = ConversationHandler(
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
    application.add_handler(conv_handler)
    
    # Обработчик кнопок
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons))
    
    # Обработчик callback
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Запускаем бота
    logger.info("Бот запущен!")
    application.run_polling()

if __name__ == '__main__':
    main()