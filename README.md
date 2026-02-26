# Price Tracker CA 🇨🇦

Daily price monitoring for Retail Stores in Canada.

## Setup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Configure products in `config/products.json`.
3. (Optional) Set `DISCORD_WEBHOOK` environment variable for alerts.

## Execution
Run manually:
```bash
python main.py
```

## Compliance & Limits
- **Frequency**: 1 run per day.
- **Delay**: 2 seconds between requests.
- **User-Agent**: Honest identification.
- **No Bypass**: No CAPTCHA or anti-bot bypass implemented.

## Architecture
- `/scrapers`: Extraction logic (BeautifulSoup).
- `/storage`: SQLite persistence.
- `/alerts`: Discord/Slack notifications.
- `/config`: JSON product list.
