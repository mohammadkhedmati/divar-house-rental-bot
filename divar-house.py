from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes
import requests
from bs4 import BeautifulSoup
import logging

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# States for conversation
ASK_DEPOSIT, ASK_RENT = range(2)

# Your Telegram bot token and user ID
TELEGRAM_TOKEN = ''

# Base URL for Divar searches
BASE_URL = "https://divar.ir/s/tehran/rent-apartment/"

# Dictionary to store chat data (including deposit and rent values)
chat_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Let's start by entering your desired deposit amount (in millions). e.g: 400,000,000 = 400")
    return ASK_DEPOSIT

async def ask_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    deposit = update.message.text
    chat_id = update.message.chat_id

    try:
        deposit_value = int(deposit)
    except ValueError:
        await update.message.reply_text("Invalid deposit amount. Please enter a valid number.")
        return ASK_DEPOSIT

    # Store the deposit in chat_data
    chat_data[chat_id] = {'deposit': deposit_value}

    # Ask for rent after deposit is provided
    await update.message.reply_text("Great! Now, enter your desired rent amount (in millions). e.g: 30,000,000 = 30")
    return ASK_RENT

async def ask_rent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rent = update.message.text
    chat_id = update.message.chat_id

    try:
        rent_value = int(rent)
    except ValueError:
        await update.message.reply_text("Invalid rent amount. Please enter a valid number.")
        return ASK_RENT

    # Store the rent in chat_data
    chat_data[chat_id]['rent'] = rent_value

    await update.message.reply_text("Searching for apartments... ,I will check for new items every 15 minutes.")

    # Schedule the job to check for new items based on user-provided deposit and rent
    context.job_queue.run_repeating(
        check_new_items,
        interval=10,  # Interval in seconds (15 minutes)
        first=0,
        data=chat_id
    )
    
    return ConversationHandler.END

async def check_new_items(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.data
    if chat_id not in chat_data:
        return

    deposit = chat_data[chat_id].get('deposit')
    rent = chat_data[chat_id].get('rent')

    # Build URL based on deposit and rent values
    url = BASE_URL + f"?rent=-{rent * 1000000}&has-photo=true&credit=-{deposit * 1000000}&building-age=-10&districts=139%2C138"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching URL: {e}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    container = soup.find('div', class_='post-list__items-container-e44b2')

    if container:
        items = container.find_all('div', class_='post-list__widget-col-c1444')

        if not items:
            logging.warning("No items found in the container.")
        
        seen_items = chat_data.get(chat_id, {}).get('seen_items', set())

        for item in items:
            link = item.find('a', href=True)
            if link:
                href = 'divar.ir' + link['href']
                if href not in seen_items:
                    seen_items.add(href)
                    chat_data[chat_id]['seen_items'] = seen_items

                    # Extract the title, price, and image information from the HTML
                    info = link.find('div', class_='kt-post-card__info')
                    title = info.find('h2', class_='kt-post-card__title').text.strip()
                    prices = info.find_all('div', class_='kt-post-card__description')
                    deposit = prices[0].text.strip()
                    rent = prices[1].text.strip()
                    image = link.find('img', src=True)['data-src']

                    user_response = "\n".join([
                        f"title: {title}",
                        f"deposit: {deposit}",
                        f"rent: {rent}",
                        f"link: {href}"
                    ])

                    # Send message to user with the apartment details
                    await context.bot.send_photo(chat_id=chat_id, photo=image, caption=user_response)

    else:
        logging.warning("No relevant container found on the webpage.")

def main():
    # Create the application instance
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Create a ConversationHandler with states for asking deposit and rent
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_DEPOSIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_deposit)],
            ASK_RENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_rent)],
        },
        fallbacks=[]  # Optional: You can add a fallback state if needed
    )

    # Add the conversation handler to the application
    application.add_handler(conv_handler)

    # Run the bot
    application.run_polling()

if __name__ == '__main__':
    main()
