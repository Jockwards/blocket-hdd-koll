#!/bin/bash
# Quick deployment script

# Ensure we are in the script's directory
cd "$(dirname "$0")"

# Add /usr/bin to PATH just in case
export PATH=$PATH:/usr/bin:/usr/local/bin

echo "🔍 Running scraper..."
python3 scraper.py

echo ""
echo "📊 Results:"
python3 -c "import json; d=json.load(open('data/deals.json')); l=json.load(open('data/listings.json')); print(f'  - {len(l)} drives found'); print(f'  - {len(d)} deals (≤150 SEK/TB)')"

echo ""
echo "🚀 Deploying to Surge..."
npx surge . jockeblocket.surge.sh

echo ""
echo "✅ Done! Visit: https://jockeblocket.surge.sh"
