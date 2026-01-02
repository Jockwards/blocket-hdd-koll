#!/usr/bin/env python3
import os
import json
import time
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai
from blocket_api import BlocketAPI, SubCategory

load_dotenv()

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=GEMINI_API_KEY)

api = BlocketAPI()
PRICE_PER_TB_THRESHOLD_HDD = 150  # For HDDs
PRICE_PER_TB_THRESHOLD_SSD = 600  # For SSDs
DATA_DIR = "data"
MAX_PAGES_PER_TERM = 3  # Reduced to 3 pages (~150 listings) for faster processing
MIN_CAPACITY_TB = 1.0  # Ignore drives under 1TB

os.makedirs(DATA_DIR, exist_ok=True)

def search_blocket(query, max_pages=5):
    """Search Blocket for listings using blocket-api package with pagination"""
    all_docs = []
    
    try:
        # Use Datorer subcategory to narrow down to computers & storage
        results = api.search(query, sub_category=SubCategory.DATORER, page=1)
        if results and 'docs' in results:
            all_docs.extend(results['docs'])
            
            # Check if there are more pages
            paging = results.get('metadata', {}).get('paging', {})
            last_page = paging.get('last', 1)
            match_count = results.get('metadata', {}).get('result_size', {}).get('match_count', 0)
            
            print(f"  Found {match_count} total results across {last_page} pages")
            print(f"  Fetching up to {max_pages} pages...")
            
            # Fetch additional pages
            for page in range(2, min(max_pages + 1, last_page + 1)):
                print(f"  Fetching page {page}...")
                results = api.search(query, sub_category=SubCategory.DATORER, page=page)
                if results and 'docs' in results:
                    all_docs.extend(results['docs'])
                time.sleep(0.3)  # Faster rate limiting
        
        return all_docs
    except Exception as e:
        print(f"Error fetching from Blocket API: {e}")
        return []

def parse_listing_with_gemini(listing):
    """Use Gemini to extract storage capacity and verify it's a hard drive"""
    model = genai.GenerativeModel('gemini-2.5-flash-lite')  # Using lite model for speed
    
    title = listing.get('heading', '')
    body = listing.get('body', '')[:500]
    price = listing.get('price', {}).get('amount', 0) if 'price' in listing else 0
    
    prompt = f"""Analyze this Swedish Blocket listing and extract information:
Title: {title}
Description: {body}
Price: {price} SEK

Tasks:
1. Is this actually a hard drive (HDD/SSD) for sale? (not a computer/laptop that happens to mention storage)
2. What is the storage capacity in TB? Convert GB to TB if needed.
3. Extract the exact price in SEK
4. Is this an SSD (solid state) or HDD (mechanical)? 
   - SSD indicators: "SSD", "NVMe", "M.2", "M2", "Solid State", "Flash", "Samsung 980", "Samsung 970", "Samsung 870", "Kingston Fury", "Crucial P3"
   - HDD indicators: "HDD", "mekanisk", "mechanisk", "7200 RPM", "5400 RPM", "WD Red", "WD Blue", "IronWolf", "Exos", "Barracuda"
   - If title/description mentions "SSD" it's definitely an SSD
   - Traditional "extern hårddisk" or "hårddisk" without SSD mentioned is usually HDD

Respond ONLY with JSON:
{{
  "is_hard_drive": true/false,
  "capacity_tb": number or null,
  "price_sek": number or null,
  "is_ssd": true/false,
  "confidence": "high/medium/low"
}}"""
    
    try:
        response = model.generate_content(prompt)
        text = response.text.strip().replace('```json', '').replace('```', '').strip()
        parsed = json.loads(text)
        return parsed
    except Exception as e:
        print(f"Error parsing with Gemini: {e}")
        return {
            "is_hard_drive": False,
            "capacity_tb": None,
            "price_sek": None,
            "is_ssd": False,
            "confidence": "low"
        }

def calculate_price_per_tb(price_sek, capacity_tb):
    """Calculate price per TB"""
    if capacity_tb and capacity_tb > 0:
        return round(price_sek / capacity_tb, 2)
    return None

def scrape_and_process():
    """Main scraping function"""
    print("🔍 Searching Blocket for hard drives...")
    
    search_terms = ["hårddisk"]  # Just one term since we're getting many pages
    all_listings = []
    seen_ids = set()
    
    for term in search_terms:
        print(f"\nSearching for: {term}")
        results = search_blocket(term, max_pages=MAX_PAGES_PER_TERM)
        
        if results:
            for ad in results:
                ad_id = ad.get('id')
                if ad_id and ad_id not in seen_ids:
                    # Check if shipping is available (kan skickas)
                    flags = ad.get('flags', [])
                    if 'shipping_exists' in flags or 'fiks_ferdig' in str(ad.get('labels', [])):
                        all_listings.append(ad)
                        seen_ids.add(ad_id)
                    else:
                        print(f"  ⊘ Skipping {ad.get('heading', 'Unknown')[:50]} - no shipping")
    
    print(f"\n📦 Found {len(all_listings)} unique listings with shipping to process")
    
    processed_listings = []
    deals = []
    
    # Load existing processed IDs to avoid re-processing
    processed_ids = set()
    try:
        with open(f"{DATA_DIR}/listings.json", 'r', encoding='utf-8') as f:
            existing = json.load(f)
            processed_ids = {str(item['id']) for item in existing}
            processed_listings = existing.copy()
            print(f"📋 Loaded {len(processed_ids)} previously processed listings")
    except FileNotFoundError:
        pass
    
    # Load existing deals to preserve them
    try:
        with open(f"{DATA_DIR}/deals.json", 'r', encoding='utf-8') as f:
            existing_deals = json.load(f)
            deals = existing_deals.copy()
            print(f"💎 Loaded {len(deals)} existing deals")
    except FileNotFoundError:
        pass
    
    new_deals_count = 0
    
    for i, listing in enumerate(all_listings, 1):
        ad_id = str(listing.get('id'))
        title = listing.get('heading', 'Unknown')
        
        # Skip if already processed
        if ad_id in processed_ids:
            print(f"[{i}/{len(all_listings)}] ⏭️  Skipping (already processed): {title[:60]}")
            continue
            
        print(f"[{i}/{len(all_listings)}] Processing: {title}")
        
        parsed = parse_listing_with_gemini(listing)
        
        if not parsed['is_hard_drive']:
            print(f"  ❌ Not a hard drive")
            continue
        
        if parsed['capacity_tb'] and parsed['price_sek']:
            # Ignore drives under 1TB
            if parsed['capacity_tb'] < MIN_CAPACITY_TB:
                print(f"  ⊘ Too small ({parsed['capacity_tb']}TB < {MIN_CAPACITY_TB}TB)")
                continue
            
            price_per_tb = calculate_price_per_tb(parsed['price_sek'], parsed['capacity_tb'])
            is_ssd = parsed.get('is_ssd', False)
            drive_type = "SSD" if is_ssd else "HDD"
            threshold = PRICE_PER_TB_THRESHOLD_SSD if is_ssd else PRICE_PER_TB_THRESHOLD_HDD
            
            print(f"  ✓ {parsed['capacity_tb']}TB {drive_type} @ {price_per_tb} SEK/TB")
            
            ad_id = listing.get('id')
            url = f"https://www.blocket.se/recommerce/forsale/item/{ad_id}"
            location = listing.get('location', '')
            date_pub = datetime.fromtimestamp(listing.get('timestamp', 0) / 1000).isoformat() if listing.get('timestamp') else datetime.now().isoformat()
            
            processed_item = {
                "id": ad_id,
                "title": title,
                "price_sek": parsed['price_sek'],
                "capacity_tb": parsed['capacity_tb'],
                "price_per_tb": price_per_tb,
                "is_ssd": is_ssd,
                "drive_type": drive_type,
                "url": url,
                "location": location,
                "date": date_pub,
                "confidence": parsed['confidence']
            }
            
            processed_listings.append(processed_item)
            processed_ids.add(ad_id)
            
            # Check if this is a deal
            if price_per_tb and price_per_tb <= threshold:
                # Check if not already in deals
                existing_deal_ids = {str(d['id']) for d in deals}
                if ad_id not in existing_deal_ids:
                    deals.append(processed_item)
                    new_deals_count += 1
                    print(f"  🔥 NEW DEAL!")
                else:
                    print(f"  🔥 DEAL (already saved)")
        
        # Rate limiting to avoid API throttling
        time.sleep(0.5)
    
    # Save all data
    with open(f"{DATA_DIR}/listings.json", 'w', encoding='utf-8') as f:
        json.dump(processed_listings, f, ensure_ascii=False, indent=2)
    
    with open(f"{DATA_DIR}/deals.json", 'w', encoding='utf-8') as f:
        json.dump(deals, f, ensure_ascii=False, indent=2)
    
    update_stats(processed_listings)
    
    print(f"✅ Processed {len([l for l in processed_listings if str(l['id']) not in processed_ids or str(l['id']) in [str(listing.get('id')) for listing in all_listings]])} new hard drives")
    print(f"💰 Found {len(deals)} total deals ({new_deals_count} new)")
    print(f"   HDD (≤{PRICE_PER_TB_THRESHOLD_HDD} SEK/TB): {len([d for d in deals if not d.get('is_ssd', False)])}")
    print(f"   SSD (≤{PRICE_PER_TB_THRESHOLD_SSD} SEK/TB): {len([d for d in deals if d.get('is_ssd', False)])}")

def update_stats(listings):
    """Update statistics file with historical data"""
    stats_file = f"{DATA_DIR}/stats.json"
    
    try:
        with open(stats_file, 'r', encoding='utf-8') as f:
            stats = json.load(f)
    except FileNotFoundError:
        stats = {"history": []}
    
    hdd_listings = [l for l in listings if not l.get('is_ssd', False) and l.get('price_per_tb')]
    ssd_listings = [l for l in listings if l.get('is_ssd', False) and l.get('price_per_tb')]
    
    avg_price_hdd = sum(l['price_per_tb'] for l in hdd_listings) / len(hdd_listings) if hdd_listings else 0
    avg_price_ssd = sum(l['price_per_tb'] for l in ssd_listings) / len(ssd_listings) if ssd_listings else 0
    
    if listings:
        avg_price_per_tb = sum(l['price_per_tb'] for l in listings if l['price_per_tb']) / len([l for l in listings if l['price_per_tb']])
    else:
        avg_price_per_tb = 0
    
    stats['history'].append({
        "date": datetime.now().isoformat(),
        "avg_price_per_tb": round(avg_price_per_tb, 2),
        "avg_price_hdd": round(avg_price_hdd, 2),
        "avg_price_ssd": round(avg_price_ssd, 2),
        "total_listings": len(listings)
    })
    
    stats['history'] = stats['history'][-30:]
    
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    scrape_and_process()
