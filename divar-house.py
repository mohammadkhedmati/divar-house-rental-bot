import logging
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, JobQueue

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Your Telegram bot token and user ID
TELEGRAM_TOKEN = ''

# URL to scrape
URL = "https://divar.ir/s/tehran/rent-apartment/shahrak-jandarmeri?rent=-30000000&has-photo=true&credit=-400000000&building-age=-10&districts=139"

# Dictionary to store chat IDs and their seen items sets
chat_data = {}


async def check_new_items(context: ContextTypes.DEFAULT_TYPE):
    global chat_data

    chat_id = context.job.data  # Access chat ID from data

    if chat_id not in chat_data:
        chat_data[chat_id] = set()  # Initialize seen items for this chat

    seen_items = chat_data[chat_id]  # Get seen items for this chat

    logging.info("Checking for new items for chat %d...", chat_id)

    try:
        response = requests.get(URL)
        response.raise_for_status()  # Raise an exception for HTTP errors
    except requests.exceptions.RequestException as e:
        logging.error("Error fetching URL: %s", e)
        return

    soup = BeautifulSoup(response.text, 'html.parser')

    # Find the relevant container (adjust selectors based on Divar's HTML structure)
    container = soup.find('div', class_='post-list__items-container-e44b2')
    if container:
        items = container.find_all('div', class_='post-list__widget-col-c1444')

        if not items:
            logging.warning("No items found in the container.")

        for item in items:
            link = item.find('a', href=True)
            if link:
                # item link
                href = link['href']
                href = 'divar.ir' + href

                info = link.find('div', class_='kt-post-card__info')
                title = info.find('h2', class_='kt-post-card__title')
                prices = info.find_all('div', class_='kt-post-card__description')
                deposit = prices[0]
                rent = prices[0]
                print(title.text.stirp())
                user_response = f"""
                title : {title.text.stirp()}
                deposit : {deposit} 
                rent : {rent}
                link : {href}
                """
                if href not in seen_items:
                    await context.bot.send_message(chat_id=chat_id, text=user_response)
                    seen_items.add(href)
                    logging.info(f"New link found and sent to chat {chat_id}: {href}")
                else:
                    logging.info(f"Link already seen for chat {chat_id}: {href}")
    else:
        logging.warning("No relevant container found.")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot started! I will check for new items every 15 minutes.")

    # Add user's chat ID and initialize seen items set
    chat_id = update.message.chat.id
    chat_data[chat_id] = set()

    # Schedule the job to run every 15 minutes and pass the chat ID as data
    context.job_queue.run_repeating(
        check_new_items,
        interval=10,  # Interval in seconds (15 minutes)
        first=0,
        data=chat_id
    )

    logging.info(f"Job scheduled for chat {chat_id} to check for new items every 15 minutes.")


def main():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Command handler to start the bot
    application.add_handler(CommandHandler("start", start))

    # Add error handler for unexpected exceptions
    def handle_error(update: Update, context: ContextTypes.DEFAULT_TYPE, exception: Exception):
        logging.error(f"An error occurred: {exception}")
    application.add_error_handler(handle_error)  # Register using add_error_handler

    # Start the bot
    application.run_polling()


if __name__ == '__main__':
    main()