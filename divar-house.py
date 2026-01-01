
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes, CallbackQueryHandler
import requests
from bs4 import BeautifulSoup
import logging
import json

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# States for conversation
ASK_TYPE, ASK_PROPERTY_TYPE, ASK_REGION, ASK_DISTRICTS, ASK_DEPOSIT, ASK_RENT, ASK_BALCONY, ASK_PARKING, ASK_WAREHOUSE, ASK_ROOMS, ASK_SIZE = range(11)

# Your Telegram bot token and user ID
TELEGRAM_TOKEN = '8199181120:AAFSAZd7IceqKA64dNWTgXdWGHgm83oxldU'

# Base URL for Divar searches
BASE_URL = "https://divar.ir/s/tehran/"

# Dictionary to store chat data (including deposit and rent values)
chat_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_keyboard = [["خرید", "اجاره"]]
    await update.message.reply_text(
        "سلام! لطفاً یکی را انتخاب کنید:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return ASK_TYPE

async def ask_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    text = update.message.text.strip().lower()
    if text == "برگشت":
        # در اولین مرحله امکان برگشت نیست
        await update.message.reply_text("در اولین مرحله هستید و امکان بازگشت وجود ندارد.")
        return ASK_TYPE
    if text in ["اجاره", "rent"]:
        chat_data[chat_id] = {'type': 'rent'}
        reply_keyboard = [["مسکونی", "تجاری/اداری"], ["برگشت"]]
        await update.message.reply_text(
            "نوع ملک را انتخاب کنید:",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return ASK_PROPERTY_TYPE
    elif text in ["خرید", "buy"]:
        chat_data[chat_id] = {'type': 'buy'}
        reply_keyboard = [["مسکونی", "تجاری/اداری"], ["برگشت"]]
        await update.message.reply_text(
            "نوع ملک را انتخاب کنید:",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return ASK_PROPERTY_TYPE

async def ask_property_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    text = update.message.text.strip().lower()
    if text == "برگشت":
        reply_keyboard = [["خرید", "اجاره"]]
        await update.message.reply_text(
            "به مرحله قبل بازگشتید. لطفاً یکی را انتخاب کنید:",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return ASK_TYPE
    if text in ["مسکونی", "residential"]:
        chat_data[chat_id]['property_type'] = 'residential'
    elif text in ["تجاری/اداری", "تجاری", "اداری", "commercial", "office"]:
        chat_data[chat_id]['property_type'] = 'commercial'
    else:
        reply_keyboard = [["مسکونی", "تجاری/اداری"], ["برگشت"]]
        await update.message.reply_text(
            "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return ASK_PROPERTY_TYPE
    reply_keyboard = [["۱", "۲", "۳"], ["۵", "۶"], ["برگشت"]]
    await update.message.reply_text(
        "کدام منطقه تهران را انتخاب می‌کنید؟",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return ASK_REGION

async def ask_region(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    region = update.message.text.strip()
    if region == "برگشت":
        reply_keyboard = [["مسکونی", "تجاری/اداری"], ["برگشت"]]
        await update.message.reply_text(
            "به مرحله قبل بازگشتید. نوع ملک را انتخاب کنید:",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return ASK_PROPERTY_TYPE
    if region not in ["۱", "2", "۲", "3", "۳", "5", "۵", "6", "۶"]:
        reply_keyboard = [["۱", "۲", "۳"], ["۵", "۶"], ["برگشت"]]
        await update.message.reply_text(
            "لطفاً فقط یکی از مناطق ۱، ۲، ۳، ۵ یا ۶ را انتخاب کنید.",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return ASK_REGION
    # Normalize region to English digits for later use
    region_map = {"۱": "1", "۲": "2", "۳": "3", "۵": "5", "۶": "6", "1": "1", "2": "2", "3": "3", "5": "5", "6": "6"}
    chat_data[chat_id]['region'] = region_map.get(region, region)
    chat_data[chat_id]['selected_districts'] = []
    
    # Load zones.json and show districts
    try:
        with open('zones.json', 'r', encoding='utf-8') as f:
            zones_data = json.load(f)
        zone_key = f"zone{chat_data[chat_id]['region']}"
        districts = zones_data[0].get(zone_key, [])
        
        if not districts:
            await update.message.reply_text("محله‌ای برای این منطقه یافت نشد.")
            return ASK_REGION
        
        # Create inline keyboard with districts
        keyboard = []
        for i in range(0, len(districts), 2):
            row = []
            for j in range(2):
                if i + j < len(districts):
                    district = districts[i + j]
                    row.append(InlineKeyboardButton(
                        district['name'], 
                        callback_data=f"district_{district['id']}"
                    ))
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("✅ تایید انتخاب", callback_data="confirm_districts")])
        keyboard.append([InlineKeyboardButton("🔙 برگشت", callback_data="back_from_districts")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "لطفاً محله‌های مورد نظر خود را انتخاب کنید:\n(می‌توانید چند محله انتخاب کنید)",
            reply_markup=reply_markup
        )
        return ASK_DISTRICTS
    except Exception as e:
        logging.error(f"Error loading zones.json: {e}")
        await update.message.reply_text("خطا در بارگذاری اطلاعات محله‌ها.")
        return ASK_REGION

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    # Remove all jobs for this chat
    jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    for job in jobs:
        job.schedule_removal()
    await update.message.reply_text("اعلان‌های جستجوی آپارتمان متوقف شد.")


async def newprocess(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    # Remove all jobs for this chat
    jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    for job in jobs:
        job.schedule_removal()
    # Clear previous deposit/rent
    chat_data.pop(chat_id, None)
    reply_keyboard = [["خرید", "اجاره"]]
    await update.message.reply_text(
        "فرآیند جدید آغاز شد. لطفاً یکی را انتخاب کنید:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return ASK_TYPE

async def handle_district_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    chat_id = query.message.chat_id
    data = query.data
    
    if data == "back_from_districts":
        reply_keyboard = [["۱", "۲", "۳"], ["۵", "۶"], ["برگشت"]]
        await query.message.reply_text(
            "به مرحله قبل بازگشتید. کدام منطقه تهران را انتخاب می‌کنید؟",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        await query.message.delete()
        return ASK_REGION
    
    if data == "confirm_districts":
        if not chat_data[chat_id].get('selected_districts'):
            await query.answer("لطفاً حداقل یک محله انتخاب کنید!", show_alert=True)
            return ASK_DISTRICTS
        
        await query.message.delete()
        if chat_data[chat_id]['type'] == 'rent':
            reply_keyboard = [["برگشت"]]
            await context.bot.send_message(
                chat_id=chat_id,
                text="لطفاً مبلغ ودیعه مورد نظر خود را وارد کنید (به میلیون تومان، مثلاً ۴۰۰ برای ۴۰۰,۰۰۰,۰۰۰)",
                reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
            )
            return ASK_DEPOSIT
        reply_keyboard = [["برگشت"]]
        await context.bot.send_message(
            chat_id=chat_id,
            text="لطفاً قیمت مورد نظر خود را وارد کنید (به میلیون تومان، مثلاً ۵۰۰۰ برای ۵,۰۰۰,۰۰۰,۰۰۰)",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return ASK_DEPOSIT
    
    if data.startswith("district_"):
        district_id = data.split("_")[1]
        selected = chat_data[chat_id].get('selected_districts', [])
        
        # Toggle selection
        if district_id in selected:
            selected.remove(district_id)
        else:
            selected.append(district_id)
        
        chat_data[chat_id]['selected_districts'] = selected
        
        # Reload zones to update button text
        try:
            with open('zones.json', 'r', encoding='utf-8') as f:
                zones_data = json.load(f)
            zone_key = f"zone{chat_data[chat_id]['region']}"
            districts = zones_data[0].get(zone_key, [])
            
            # Create updated keyboard
            keyboard = []
            for i in range(0, len(districts), 2):
                row = []
                for j in range(2):
                    if i + j < len(districts):
                        district = districts[i + j]
                        is_selected = str(district['id']) in selected
                        button_text = f"✓ {district['name']}" if is_selected else district['name']
                        row.append(InlineKeyboardButton(
                            button_text,
                            callback_data=f"district_{district['id']}"
                        ))
                keyboard.append(row)
            
            keyboard.append([InlineKeyboardButton("✅ تایید انتخاب", callback_data="confirm_districts")])
            keyboard.append([InlineKeyboardButton("🔙 برگشت", callback_data="back_from_districts")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"لطفاً محله‌های مورد نظر خود را انتخاب کنید:\n(می‌توانید چند محله انتخاب کنید)\n\nانتخاب شده: {len(selected)} محله",
                reply_markup=reply_markup
            )
        except Exception as e:
            logging.error(f"Error updating district selection: {e}")
        
        return ASK_DISTRICTS

async def ask_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    deposit = update.message.text
    chat_id = update.message.chat_id
    if deposit == "برگشت":
        reply_keyboard = [["۱", "۲", "۳"], ["۵", "۶"], ["برگشت"]]
        await update.message.reply_text(
            "به مرحله قبل بازگشتید. کدام منطقه تهران را انتخاب می‌کنید؟",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return ASK_REGION
    try:
        deposit_value = int(deposit)
    except ValueError:
        reply_keyboard = [["برگشت"]]
        await update.message.reply_text("مبلغ ودیعه نامعتبر است. لطفاً یک عدد صحیح وارد کنید.",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True))
        return ASK_DEPOSIT

    # Store the deposit/price in chat_data
    chat_data[chat_id]['deposit'] = deposit_value

    # If type is rent, ask for rent, else go to next step
    if chat_data[chat_id].get('type') == 'rent':
        reply_keyboard = [["برگشت"]]
        await update.message.reply_text("عالی! حالا مبلغ اجاره مورد نظر خود را وارد کنید (به میلیون تومان، مثلاً ۳۰ برای ۳۰,۰۰۰,۰۰۰)",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True))
        return ASK_RENT
    else:
        reply_keyboard = [["بله", "خیر", "بیخیال"], ["برگشت"]]
        await update.message.reply_text(
            "آیا بالکن می‌خواهید؟",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return ASK_BALCONY

async def ask_rent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rent = update.message.text
    chat_id = update.message.chat_id
    if rent == "برگشت":
        reply_keyboard = [["برگشت"]]
        await update.message.reply_text(
            "به مرحله قبل بازگشتید. لطفاً مبلغ ودیعه مورد نظر خود را وارد کنید (به میلیون تومان، مثلاً ۴۰۰ برای ۴۰۰,۰۰۰,۰۰۰)",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return ASK_DEPOSIT
    try:
        rent_value = int(rent)
    except ValueError:
        reply_keyboard = [["برگشت"]]
        await update.message.reply_text("مبلغ اجاره نامعتبر است. لطفاً یک عدد صحیح وارد کنید.",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True))
        return ASK_RENT

    # Store the rent in chat_data
    chat_data[chat_id]['rent'] = rent_value

    # Ask for balcony with buttons
    reply_keyboard = [["بله", "خیر", "بیخیال"], ["برگشت"]]
    await update.message.reply_text(
        "آیا بالکن می‌خواهید؟",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return ASK_BALCONY

async def ask_balcony(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    text = update.message.text.strip().lower()
    if text == "برگشت":
        if chat_data[chat_id].get('type') == 'rent':
            reply_keyboard = [["برگشت"]]
            await update.message.reply_text(
                "به مرحله قبل بازگشتید. لطفاً مبلغ اجاره مورد نظر خود را وارد کنید (به میلیون تومان، مثلاً ۳۰ برای ۳۰,۰۰۰,۰۰۰)",
                reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
            )
            return ASK_RENT
        else:
            reply_keyboard = [["برگشت"]]
            await update.message.reply_text(
                "به مرحله قبل بازگشتید. لطفاً مبلغ ودیعه/قیمت مورد نظر خود را وارد کنید.",
                reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
            )
            return ASK_DEPOSIT
    if text in ["بیخیال", "skip", "رد", "نه", "خیر", "no", ""]:
        chat_data[chat_id]['balcony'] = False
    else:
        chat_data[chat_id]['balcony'] = True
    reply_keyboard = [["بله", "خیر", "بیخیال"], ["برگشت"]]
    await update.message.reply_text(
        "آیا پارکینگ می‌خواهید؟",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return ASK_PARKING

async def ask_parking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    text = update.message.text.strip().lower()
    if text == "برگشت":
        reply_keyboard = [["بله", "خیر", "بیخیال"], ["برگشت"]]
        await update.message.reply_text(
            "به مرحله قبل بازگشتید. آیا بالکن می‌خواهید؟",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return ASK_BALCONY
    if text in ["بیخیال", "skip", "رد", "نه", "خیر", "no", ""]:
        chat_data[chat_id]['parking'] = False
    else:
        chat_data[chat_id]['parking'] = True
    reply_keyboard = [["بله", "خیر", "بیخیال"], ["برگشت"]]
    await update.message.reply_text(
        "آیا انباری می‌خواهید؟",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return ASK_WAREHOUSE

async def ask_warehouse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    text = update.message.text.strip().lower()
    if text == "برگشت":
        reply_keyboard = [["بله", "خیر", "بیخیال"], ["برگشت"]]
        await update.message.reply_text(
            "به مرحله قبل بازگشتید. آیا پارکینگ می‌خواهید؟",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return ASK_PARKING
    if text in ["بیخیال", "skip", "رد", "نه", "خیر", "no", ""]:
        chat_data[chat_id]['warehouse'] = False
    else:
        chat_data[chat_id]['warehouse'] = True
    reply_keyboard = [["یک", "دو", "سه"], ["چهار", "چهار و بیشتر", "بدون اتاق"], ["بیخیال"], ["برگشت"]]
    await update.message.reply_text(
        "چند اتاق می‌خواهید؟",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return ASK_ROOMS

async def ask_rooms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    rooms = update.message.text.strip()
    if rooms == "برگشت":
        reply_keyboard = [["یک", "دو", "سه"], ["چهار", "چهار و بیشتر", "بدون اتاق"], ["بیخیال"], ["برگشت"]]
        await update.message.reply_text(
            "به مرحله قبل بازگشتید. آیا انباری می‌خواهید؟",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return ASK_WAREHOUSE
    if rooms in ["skip", "", "رد", "بیخیال"]:
        chat_data[chat_id]['rooms'] = None  # skip means do not include
    else:
        chat_data[chat_id]['rooms'] = rooms
    reply_keyboard = [["بیخیال"], ["برگشت"]]
    await update.message.reply_text(
        "لطفاً بازه متراژ را وارد کنید (مثلاً ۳۰-۱۰۰ یا بیخیال)",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return ASK_SIZE

async def ask_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    size = update.message.text.strip()
    if size == "برگشت":
        reply_keyboard = [["بیخیال"], ["برگشت"]]
        await update.message.reply_text(
            "به مرحله قبل بازگشتید. چند اتاق می‌خواهید؟",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return ASK_ROOMS
    if size in ["skip", "", "رد", "بیخیال"]:
        chat_data[chat_id]['size'] = None  # skip means do not include
    else:
        # Validate size format (should be like "30-100" or a single number)
        import re
        # Check if format is correct: two numbers separated by dash (e.g., "30-100" or "۳۰-۱۰۰")
        if '-' in size:
            parts = size.split('-')
            if len(parts) == 2:
                try:
                    # Try to convert to integers (works with both English and Persian numbers after conversion)
                    min_size = int(parts[0].replace('۰', '0').replace('۱', '1').replace('۲', '2').replace('۳', '3').replace('۴', '4').replace('۵', '5').replace('۶', '6').replace('۷', '7').replace('۸', '8').replace('۹', '9'))
                    max_size = int(parts[1].replace('۰', '0').replace('۱', '1').replace('۲', '2').replace('۳', '3').replace('۴', '4').replace('۵', '5').replace('۶', '6').replace('۷', '7').replace('۸', '8').replace('۹', '9'))
                    if min_size <= 0 or max_size <= 0 or min_size >= max_size:
                        reply_keyboard = [["بیخیال"], ["برگشت"]]
                        await update.message.reply_text(
                            "❌ فرمت متراژ نامعتبر است!\n\nلطفاً بازه متراژ را به صورت صحیح وارد کنید.\nمثال: ۳۰-۱۰۰ یا 30-100\n\n(عدد اول باید کوچکتر از عدد دوم باشد)",
                            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
                        )
                        return ASK_SIZE
                except ValueError:
                    reply_keyboard = [["بیخیال"], ["برگشت"]]
                    await update.message.reply_text(
                        "❌ فرمت متراژ نامعتبر است!\n\nلطفاً بازه متراژ را به صورت صحیح وارد کنید.\nمثال: ۳۰-۱۰۰ یا 30-100",
                        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
                    )
                    return ASK_SIZE
            else:
                reply_keyboard = [["بیخیال"], ["برگشت"]]
                await update.message.reply_text(
                    "❌ فرمت متراژ نامعتبر است!\n\nلطفاً بازه متراژ را به صورت صحیح وارد کنید.\nمثال: ۳۰-۱۰۰ یا 30-100",
                    reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
                )
                return ASK_SIZE
        chat_data[chat_id]['size'] = size

    await update.message.reply_text("در حال جستجوی آپارتمان‌ها... هر ۳۰ دقیقه موارد جدید را بررسی می‌کنم.")

    # Fetch and send all current items immediately
    await fetch_and_send_items(chat_id, context, send_all=True)

    # Schedule the job to check for new items based on user-provided options
    jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    for job in jobs:
        job.schedule_removal()
    context.job_queue.run_repeating(
        check_new_items,
        interval=30 * 60,  # 30 minutes
        first=30 * 60,
        data=chat_id,
        name=str(chat_id)
    )

    return ConversationHandler.END

async def check_new_items(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.data
    await fetch_and_send_items(chat_id, context, send_all=False)

async def fetch_and_send_items(chat_id, context, send_all=False):
    if chat_id not in chat_data:
        return

    deposit = chat_data[chat_id].get('deposit')
    rent = chat_data[chat_id].get('rent')
    search_type = chat_data[chat_id].get('type', 'rent')
    property_type = chat_data[chat_id].get('property_type', 'residential')
    region = chat_data[chat_id].get('region')
    balcony = chat_data[chat_id].get('balcony', None)
    parking = chat_data[chat_id].get('parking', None)
    warehouse = chat_data[chat_id].get('warehouse', None)
    rooms = chat_data[chat_id].get('rooms', None)
    size = chat_data[chat_id].get('size', None)
    selected_districts = chat_data[chat_id].get('selected_districts', [])
    import urllib.parse
    
    # Build URL based on selected districts
    if selected_districts:
        # Load zones.json to get slug for first district
        try:
            with open('zones.json', 'r', encoding='utf-8') as f:
                zones_data = json.load(f)
            zone_key = f"zone{region}"
            districts = zones_data[0].get(zone_key, [])
            
            # Get slug from first selected district
            first_district_id = selected_districts[0]
            base_slug = None
            for district in districts:
                if str(district['id']) == first_district_id:
                    base_slug = district.get('slug') or district.get('second_slug')
                    break
            
            if not base_slug:
                base_slug = "tehran"
            
            # Create districts parameter
            districts_param = "%2C".join(selected_districts)
            url = f"{base_slug}?districts={districts_param}"
        except Exception as e:
            logging.error(f"Error building URL from selected districts: {e}")
            return
    else:
        logging.error("No districts selected")
        return
    
    if url:
        # Add price/rent filters if available
        params = []
        # تعیین نوع ملک در URL
        if search_type == 'buy':
            if property_type == 'residential':
                url = BASE_URL + "buy-residential/" + url
            else:
                url = BASE_URL + "buy-commercial-property/" + url
        else:
            if property_type == 'residential':
                url = BASE_URL + "rent-residential/" + url
            else:
                url = BASE_URL + "rent-commercial-property/" + url
        if search_type == 'buy' and deposit:
            params.append(f"price=-{deposit * 1000000}")
        elif search_type == 'rent' and deposit:
            params.append(f"credit=-{deposit * 1000000}")
        if search_type == 'rent' and rent:
            params.append(f"rent=-{rent * 1000000}")
        if params:
            url += ('&' if '?' in url else '?') + '&'.join(params)
        url += "&has-photo=true"
    if rooms:
        rooms_encoded = urllib.parse.quote(rooms)
        url += f"&rooms={rooms_encoded}"
    if size:
        # Convert Persian digits to English
        size_english = size.replace('۰', '0').replace('۱', '1').replace('۲', '2').replace('۳', '3').replace('۴', '4').replace('۵', '5').replace('۶', '6').replace('۷', '7').replace('۸', '8').replace('۹', '9')
        url += f"&size={size_english}"
    if balcony:
        url += "&balcony=true"
    if parking:
        url += "&parking=true"
    if warehouse:
        url += "&warehouse=true"
    logging.info("Checking URL: %s", url)
    import random
    from lxml import html
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0"
    ]
    headers = {
        "User-Agent": random.choice(user_agents),
        "Accept-Language": "fa,en-US;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Connection": "keep-alive",
        "Referer": "https://divar.ir/",
        "DNT": "1"
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching URL: {e}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Check if page shows "no results found" message
    no_results_messages = [
        "نتیجهٔ دقیقی پیدا نشد",
        "نتیجه دقیقی پیدا نشد",
        "نتیجه‌ای یافت نشد",
        "آگهی یافت نشد"
    ]
    page_text = soup.get_text()
    has_no_results = any(msg in page_text for msg in no_results_messages)
    
    if has_no_results:
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ متاسفانه هیچ نتیجه‌ای با فیلترهای انتخابی شما یافت نشد.\n\nلطفاً فیلترهای خود را تغییر دهید و دوباره امتحان کنید."
        )
        # Offer to start over
        reply_keyboard = [["/newprocess"]]
        await context.bot.send_message(
            chat_id=chat_id,
            text="برای شروع جستجوی جدید دستور /newprocess را ارسال کنید.",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return
    
    scripts = soup.find_all("script", type="application/ld+json")
    logging.info("Found %d script tags with type application/ld+json", len(scripts))
    if not scripts:
        logging.warning("No ld+json scripts found")
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ خطا در دریافت نتایج. لطفاً دوباره تلاش کنید."
        )
        return

    try:
        items = json.loads(scripts[-1].string)
    except Exception as e:
        logging.error(f"Error parsing JSON: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ خطا در پردازش نتایج. لطفاً دوباره تلاش کنید."
        )
        return

    # Check if there are any results and if items is a list of dictionaries
    if not items or len(items) == 0:
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ متاسفانه هیچ نتیجه‌ای با فیلترهای انتخابی شما یافت نشد.\n\nلطفاً فیلترهای خود را تغییر دهید و دوباره امتحان کنید."
        )
        # Offer to start over
        reply_keyboard = [["/newprocess"]]
        await context.bot.send_message(
            chat_id=chat_id,
            text="برای شروع جستجوی جدید دستور /newprocess را ارسال کنید.",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return
    
    # Check if items contains dictionaries with 'url' key (valid results)
    # If first item is a string or doesn't have 'url', it means no valid results
    if not isinstance(items, list) or (len(items) > 0 and not isinstance(items[0], dict)):
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ متاسفانه هیچ نتیجه‌ای با فیلترهای انتخابی شما یافت نشد.\n\nلطفاً فیلترهای خود را تغییر دهید و دوباره امتحان کنید."
        )
        # Offer to start over
        reply_keyboard = [["/newprocess"]]
        await context.bot.send_message(
            chat_id=chat_id,
            text="برای شروع جستجوی جدید دستور /newprocess را ارسال کنید.",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return
    
    # Filter out any non-dict items
    items = [item for item in items if isinstance(item, dict) and item.get("url")]
    
    if len(items) == 0:
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ متاسفانه هیچ نتیجه‌ای با فیلترهای انتخابی شما یافت نشد.\n\nلطفاً فیلترهای خود را تغییر دهید و دوباره امتحان کنید."
        )
        # Offer to start over
        reply_keyboard = [["/newprocess"]]
        await context.bot.send_message(
            chat_id=chat_id,
            text="برای شروع جستجوی جدید دستور /newprocess را ارسال کنید.",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return

    # Send initial message
    if send_all:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🔍 در حال بررسی نتایج...\n\n🔗 لینک جستجو:\n{url}"
        )

    seen_items = chat_data[chat_id].get('seen_items', set())
    new_seen = set(seen_items)
    logging.info("seen_items: %s", seen_items)
    
    # Track valid items and new items
    valid_items = []
    new_items_count = 0
    
    for item in items:
        href = item.get("url")
        is_new = href not in seen_items
        
        # Initialize item validation
        item_matches = True
        title = item.get("name", "")
        image = item.get("image", "")
        year_built = "N/A"
        
        if send_all or is_new:
            if search_type == 'buy':
                total_price = item.get("price", "N/A")
                price_per_meter = item.get("price_per_meter", "N/A")
                
                # Validate price matches user's deposit (max price) filter
                if deposit:
                    try:
                        import re
                        # Extract numeric value from price string
                        price_str = str(total_price).replace(",", "").replace("تومان", "").strip()
                        price_numeric = re.sub(r'[^\d]', '', price_str)
                        if price_numeric:
                            item_price = int(price_numeric)
                            max_price = deposit * 1000000
                            if item_price > max_price:
                                item_matches = False
                                logging.info(f"Filtering out item: price {item_price} > max {max_price}")
                                continue  # Skip this item
                    except Exception as e:
                        logging.error(f"Error parsing price: {e}")
                
                for attempt in range(3):
                    try:
                        headers_detail = headers.copy()
                        headers_detail["User-Agent"] = random.choice(user_agents)
                        detail_response = requests.get(href, headers=headers_detail)
                        detail_response.raise_for_status()
                        detail_soup = BeautifulSoup(detail_response.text, 'html.parser')
                        # Try to find price and price per meter
                        price_tag = detail_soup.find(string=lambda s: s and ("قیمت کل" in s))
                        price_meter_tag = detail_soup.find(string=lambda s: s and ("قیمت هر متر" in s))
                        # سال ساخت از جدول
                        year_built = "N/A"
                        table = detail_soup.find("table", class_="kt-group-row")
                        if table:
                            rows = table.find_all("tr")
                            if len(rows) > 1:
                                cells = rows[1].find_all("td")
                                if len(cells) > 1:
                                    year_built = cells[1].text.strip()
                        # اگر جدول نبود یا مقدار نبود، روش قبلی
                        if year_built == "N/A":
                            year_tag = detail_soup.find(string=lambda s: s and ("ساخت" in s))
                            if year_tag:
                                year_built_div = year_tag.find_next("div")
                                year_built = year_built_div.text.strip() if year_built_div and year_built_div.text else "N/A"
                        if price_tag:
                            total_price = price_tag.find_next("div").text.strip()
                        if price_meter_tag:
                            price_per_meter = price_meter_tag.find_next("div").text.strip()
                        break
                    except Exception as e:
                        logging.error(f"Attempt {attempt+1}: Error fetching buy details for {href}: {e}")
                        if attempt == 2:
                            total_price = total_price or "N/A"
                            price_per_meter = price_per_meter or "N/A"
                            year_built = year_built or "N/A"
                user_response = "\n".join([
                    f"عنوان: {title}",
                    f"قیمت کل: {total_price}",
                    f"قیمت هر متر: {price_per_meter}",
                    f"سال ساخت: {year_built}",
                    f"لینک: {href}"
                ])
            else:
                deposit_text = ""
                rent_text = ""
                for attempt in range(3):
                    try:
                        headers_detail = headers.copy()
                        headers_detail["User-Agent"] = random.choice(user_agents)
                        detail_response = requests.get(href, headers=headers_detail)
                        detail_response.raise_for_status()
                        detail_soup = BeautifulSoup(detail_response.text, 'html.parser')
                        deposit_tag = detail_soup.find("div", string=lambda s: s and ("ودیعه" in s or "رهن" in s))
                        rent_tag = detail_soup.find("div", string=lambda s: s and ("اجاره" in s))
                        # سال ساخت از جدول
                        year_built = "N/A"
                        table = detail_soup.find("table", class_="kt-group-row")
                        if table:
                            rows = table.find_all("tr")
                            if len(rows) > 1:
                                cells = rows[1].find_all("td")
                                if len(cells) > 1:
                                    year_built = cells[1].text.strip()
                        if year_built == "N/A":
                            year_tag = detail_soup.find(string=lambda s: s and ("ساخت" in s))
                            if year_tag:
                                year_built_div = year_tag.find_next("div")
                                year_built = year_built_div.text.strip() if year_built_div and year_built_div.text else "N/A"
                        logging.info(f"Deposit tag: {deposit_tag}, Rent tag: {rent_tag}, Year tag: {year_built}")
                        if deposit_tag:
                            next_div = deposit_tag.find_next("div")
                            deposit_text = next_div.text.strip() if next_div and next_div.text else ""
                        else:
                            try:
                                root = html.fromstring(detail_response.text)
                                nodes = root.xpath('/html/body/div[1]/div[1]/div/main/article/div/div[1]/section[1]/div[5]/div[2]/div[2]/p')
                                deposit_text = nodes[0].text_content().strip()
                            except Exception:
                                deposit_text = rent_tag.text.strip() if rent_tag and rent_tag.text else ""
                        if rent_tag:
                            next_div = rent_tag.find_next("div")
                            rent_text = next_div.text.strip() if next_div and next_div.text else ""
                        else:
                            try:
                                root = html.fromstring(detail_response.text)
                                nodes = root.xpath('/html/body/div[1]/div[1]/div/main/article/div/div[1]/section[1]/div[5]/div[3]/div[1]/p')
                                deposit_text = nodes[0].text_content().strip()
                            except Exception:
                                deposit_text = rent_tag.text.strip() if rent_tag and rent_tag.text else ""
                        break  # Success, exit retry loop
                    except Exception as e:
                        logging.error(f"Attempt {attempt+1}: Error fetching details for {href}: {e}")
                        if attempt == 2:
                            deposit_text = "N/A"
                            rent_text = "N/A"
                            year_built = year_built or "N/A"
                
                # Validate deposit and rent match user's filters
                if deposit or rent:
                    try:
                        import re
                        if deposit and deposit_text and deposit_text != "N/A":
                            deposit_numeric = re.sub(r'[^\d]', '', str(deposit_text))
                            if deposit_numeric:
                                item_deposit = int(deposit_numeric)
                                max_deposit = deposit * 1000000
                                if item_deposit > max_deposit:
                                    item_matches = False
                                    logging.info(f"Filtering out item: deposit {item_deposit} > max {max_deposit}")
                                    continue  # Skip this item
                        
                        if rent and rent_text and rent_text != "N/A" and item_matches:
                            rent_numeric = re.sub(r'[^\d]', '', str(rent_text))
                            if rent_numeric:
                                item_rent = int(rent_numeric)
                                max_rent = rent * 1000000
                                if item_rent > max_rent:
                                    item_matches = False
                                    logging.info(f"Filtering out item: rent {item_rent} > max {max_rent}")
                                    continue  # Skip this item
                    except Exception as e:
                        logging.error(f"Error parsing deposit/rent: {e}")
                
                user_response = "\n".join([
                    f"عنوان: {title}",
                    f"ودیعه: {deposit_text}",
                    f"اجاره: {rent_text}",
                    f"سال ساخت: {year_built}",
                    f"لینک: {href}"
                ])
            
            # Only send if item matches all criteria
            if item_matches:
                valid_items.append(item)
                new_seen.add(href)
                if is_new:
                    new_items_count += 1
                await context.bot.send_photo(chat_id=chat_id, photo=image, caption=user_response)
    
    # Send summary after processing all items
    if send_all:
        if len(valid_items) == 0:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ متاسفانه هیچ نتیجه‌ای با فیلترهای انتخابی شما یافت نشد.\n\nدیوار {len(items)} نتیجه بازگشت داد، اما هیچ‌کدام با معیارهای قیمتی شما مطابقت نداشتند.\n\nلطفاً فیلترهای خود را تغییر دهید و دوباره امتحان کنید."
            )
            # Offer to start over
            reply_keyboard = [["/newprocess"]]
            await context.bot.send_message(
                chat_id=chat_id,
                text="برای شروع جستجوی جدید دستور /newprocess را ارسال کنید.",
                reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"✅ تعداد نتایج مطابق با فیلترهای شما: {len(valid_items)} مورد"
            )
    elif not send_all:
        if new_items_count > 0:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🆕 {new_items_count} مورد جدید یافت شد!"
            )
        else:
            logging.info(f"No new matching items found for chat {chat_id}")
    
    chat_data[chat_id]['seen_items'] = new_seen

def main():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()


    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start), CommandHandler("newprocess", newprocess)],
        states={
            ASK_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_type)],
            ASK_PROPERTY_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_property_type)],
            ASK_REGION: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_region)],
            ASK_DISTRICTS: [CallbackQueryHandler(handle_district_selection)],
            ASK_DEPOSIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_deposit)],
            ASK_RENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_rent)],
            ASK_BALCONY: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_balcony)],
            ASK_PARKING: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_parking)],
            ASK_WAREHOUSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_warehouse)],
            ASK_ROOMS: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_rooms)],
            ASK_SIZE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_size)],
        },
        fallbacks=[]
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("stop", stop))

    application.run_polling()

if __name__ == '__main__':
    main()
