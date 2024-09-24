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

# To keep track of the items already seen
seen_items = set()


async def check_new_items(context: ContextTypes.DEFAULT_TYPE):
    global seen_items
    chat_id = context.job.data  # Access chat ID from data

    logging.info("Checking for new items...")

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
                href = link['href']
                href = 'divar.ir' + href
                if href not in seen_items:
                    await context.bot.send_message(chat_id=chat_id, text=href)
                    seen_items.add(href)
                    logging.info(f"New link found and sent: {href}")
                else:
                    logging.info(f"Link already seen: {href}")
    else:
        logging.warning("No relevant container found.")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot started! I will check for new items every 15 minutes.")

    # Schedule the job to run every 15 minutes and pass the chat ID as data
    context.job_queue.run_repeating(
        check_new_items,
        interval=900,  # Interval in seconds (15 minutes)
        first=0,
        data=update.message.chat.id
    )

    logging.info("Job scheduled to check for new items every 15 minutes.")


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
