# Blocket HDD Koll

Find the best hard drive bargains on Blocket.se automatically!

## Features

- 🔍 Scrapes Blocket for hard drive listings
- 🤖 Uses Google Gemini AI to parse listings and extract capacity/price
- 💰 Identifies bargains (≤150 SEK/TB)
- 📊 Tracks price trends over time
- 📱 Responsive single-page app
- 🚀 Hosted on Surge.sh (static)

## Setup

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt --break-system-packages
   ```

2. **Configure API key:**
   - API key is already configured in `.env`
   - **Never commit `.env` to git!**

3. **Run the scraper:**
   ```bash
   python3 scraper.py
   ```

## Deploy to Surge.sh

1. **Install Surge (if not already installed):**
   ```bash
   npm install surge
   ```

2. **Deploy:**
   ```bash
   npx surge . jockeblocket.surge.sh
   ```
   
   - First time: You'll need to create a Surge account (free)
   - Enter your email and create a password
   - Site will be live at https://jockeblocket.surge.sh

3. **Update data:**
   - Run `python3 scraper.py` to refresh data
   - Run `npx surge . jockeblocket.surge.sh` to redeploy

## File Structure

- `scraper.py` - Python scraper using Blocket API + Gemini
- `index.html` - Main single-page app
- `style.css` - Styling
- `app.js` - Frontend JavaScript
- `data/` - JSON data files (listings, deals, stats)
- `.env` - **SECRET** API keys (never commit!)

## How It Works

1. Scraper searches Blocket for hard drive keywords
2. Gemini AI parses each listing to extract:
   - Storage capacity (TB)
   - Price (SEK)
   - Whether it's actually a hard drive
3. Calculates SEK/TB and identifies bargains
4. Saves data to JSON files
5. Static frontend loads and displays data
6. Deploy updated JSON to Surge.sh

## Threshold

Default: **150 SEK/TB** = bargain 🔥

Change in `scraper.py`: `PRICE_PER_TB_THRESHOLD = 150`

## Security

- API keys stored in `.env` (gitignored)
- Never hardcode secrets in source files
- `.env.example` provided for reference

## Update Schedule

Run `python3 scraper.py` regularly (daily/weekly) to refresh data, then redeploy to Surge.

## Configuration

Edit in `scraper.py`:
- `PRICE_PER_TB_THRESHOLD_HDD = 150` - Deal threshold for HDDs
- `PRICE_PER_TB_THRESHOLD_SSD = 600` - Deal threshold for SSDs
- `MIN_CAPACITY_TB = 1.0` - Minimum drive size to consider
- `MAX_PAGES_PER_TERM = 3` - Listings pages to fetch

## Current Data

Last run found:
- **39 hard drives** ≥1TB with shipping available
- **4 HDD deals** found (≤150 SEK/TB)
- **0 SSD deals** found (≤600 SEK/TB)

Best deal: 4TB WD My Cloud @ 133.75 SEK/TB 🏆

## Example Commands

```bash
# Run scraper
python3 scraper.py

# View deals
cat data/deals.json | python3 -m json.tool

# Test frontend locally
python3 -m http.server 8000
# Then visit http://localhost:8000

# Deploy to Surge
npx surge . jockeblocket.surge.sh
```
