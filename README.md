# divar-house-rental-bot

## What is it?

This project is a Telegram bot for searching and monitoring house rentals (and purchases) in Tehran using Divar.ir. The bot interacts with users in Persian, collects their preferences (region, price, rent, rooms, etc.), and periodically checks Divar for new listings matching their criteria, sending results (with images and details) directly to the user on Telegram.

**Main features:**

- Interactive Telegram bot (in Persian)
- Supports both rent and buy flows
- Filters by region, price, rent, rooms, balcony, parking, warehouse, and size
- Periodically checks for new listings and notifies users
- Sends listing details and images

## How to develop

1. **Clone the repository:**
   ```bash
   git clone <repo-url>
   cd divar-house-rental-bot
   ```
2. **Install dependencies (recommended: use a virtual environment):**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. **Edit the bot token:**

   - Open `divar-house.py` and set your own Telegram bot token in the `TELEGRAM_TOKEN` variable.

4. **(Optional) Adjust code for your needs:**
   - You can modify regions, filters, or add new features in `divar-house.py`.

## How to run

### Run locally

1. Make sure dependencies are installed (see above).
2. Run the bot:
   ```bash
   python divar-house.py
   ```

### Run with Docker

1. Build the Docker image:
   ```bash
   docker build -t divar-bot .
   ```
2. Run the container:
   ```bash
   docker run --rm divar-bot
   ```

### Run with Docker Compose

1. Start the service:
   ```bash
   docker-compose up --build
   ```

## Notes

- The bot is designed for Persian-speaking users and Tehran regions.
- You must set your own Telegram bot token for production use.
- The bot scrapes Divar.ir, so be mindful of their terms of service.

---

Feel free to contribute or open issues!
