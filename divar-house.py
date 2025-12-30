from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes
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
ASK_DEPOSIT, ASK_RENT = range(2)

# Your Telegram bot token and user ID
TELEGRAM_TOKEN = '8199181120:AAFSAZd7IceqKA64dNWTgXdWGHgm83oxldU'

# Base URL for Divar searches
BASE_URL = "https://divar.ir/s/tehran/rent-apartment/"

# Dictionary to store chat data (including deposit and rent values)
chat_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Let's start by entering your desired deposit amount (in millions). e.g: 400,000,000 = 400")
    return ASK_DEPOSIT


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    # Remove all jobs for this chat
    jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    for job in jobs:
        job.schedule_removal()
    await update.message.reply_text("Stopped apartment search notifications.")


async def newprocess(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    # Remove all jobs for this chat
    jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    for job in jobs:
        job.schedule_removal()
    # Clear previous deposit/rent
    chat_data.pop(chat_id, None)
    await update.message.reply_text("Starting new process. Please enter your desired deposit amount (in millions). e.g: 400,000,000 = 400")
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

    # Retrieve deposit value from chat_data
    deposit = chat_data[chat_id]['deposit']

    await update.message.reply_text("Searching for apartments... I will check for new items every 15 minutes.")

    # Fetch and send all current items immediately
    await fetch_and_send_items(chat_id, context, send_all=True)

    # Schedule the job to check for new items based on user-provided deposit and rent
    # Remove any previous jobs for this chat
    jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    for job in jobs:
        job.schedule_removal()
    # Schedule new job with chat_id as name
    context.job_queue.run_repeating(
        check_new_items,
        interval=60,  # 1 minute
        first=60,
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
    url = BASE_URL + f"shahrak-jandarmeri?rent=-{rent * 1000000}&has-photo=true&credit=-{deposit * 1000000}&building-age=-10&districts=139%2C138"
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
    scripts = soup.find_all("script", type="application/ld+json")
    logging.info("Found %d script tags with type application/ld+json", len(scripts))
    if not scripts:
        logging.warning("No ld+json scripts found")
        return

    try:
        items = json.loads(scripts[-1].string)
    except Exception as e:
        logging.error(f"Error parsing JSON: {e}")
        return

    seen_items = chat_data[chat_id].get('seen_items', set())
    new_seen = set(seen_items)
    logging.info("seen_items: %s", seen_items)
    for item in items:
        href = item.get("url")
        is_new = href not in seen_items
        if send_all or is_new:
            new_seen.add(href)
            title = item.get("name", "")
            image = item.get("image", "")

            # Fetch details from the item's page with up to 3 retries
            deposit_text = ""
            rent_text = ""
            for attempt in range(3):
                try:
                    headers_detail = headers.copy()
                    headers_detail["User-Agent"] = random.choice(user_agents)
                    detail_response = requests.get(href, headers=headers_detail)
                    detail_response.raise_for_status()
                    detail_soup = BeautifulSoup(detail_response.text, 'html.parser')
                    # Try to find deposit and rent in the detail page
                    deposit_tag = detail_soup.find("div", string=lambda s: s and ("ودیعه" in s or "رهن" in s))
                    rent_tag = detail_soup.find("div", string=lambda s: s and ("اجاره" in s))
                    logging.info(f"Deposit tag: {deposit_tag}, Rent tag: {rent_tag}")
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

            user_response = "\n".join([
                f"title: {title}",
                f"deposit: {deposit_text}",
                f"rent: {rent_text}",
                f"link: {href}"
            ])
            await context.bot.send_photo(chat_id=chat_id, photo=image, caption=user_response)
    chat_data[chat_id]['seen_items'] = new_seen

def main():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start), CommandHandler("newprocess", newprocess)],
        states={
            ASK_DEPOSIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_deposit)],
            ASK_RENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_rent)],
        },
        fallbacks=[]
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("stop", stop))

    application.run_polling()

if __name__ == '__main__':
    main()
