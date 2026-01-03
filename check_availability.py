#!/usr/bin/env python3
import json
import time
import requests
import os
import sys

DATA_DIR = "data"
LISTINGS_FILE = f"{DATA_DIR}/listings.json"
DEALS_FILE = f"{DATA_DIR}/deals.json"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def check_url(url):
    """
    Check if a URL is accessible (returns 200 OK).
    Returns True if accessible, False otherwise.
    """
    try:
        # Use HEAD request first to be fast
        response = requests.head(url, headers=HEADERS, timeout=10, allow_redirects=True)
        
        # If 405 Method Not Allowed, try GET (some servers block HEAD)
        if response.status_code == 405:
            response = requests.get(url, headers=HEADERS, timeout=10, stream=True)
            response.close()
            
        return response.status_code == 200
    except requests.RequestException as e:
        print(f"  Error checking {url}: {e}")
        return False

def clean_file(filename):
    if not os.path.exists(filename):
        print(f"{filename} does not exist.")
        return

    print(f"Processing {filename}...")
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            items = json.load(f)
    except json.JSONDecodeError:
        print(f"Error decoding {filename}")
        return

    initial_count = len(items)
    print(f"Checking {initial_count} items...")
    
    active_items = []
    removed_count = 0
    
    # Create a set of active IDs to avoid duplicates if any
    active_ids = set()
    
    for i, item in enumerate(items):
        url = item.get('url')
        item_id = item.get('id')
        title = item.get('title', 'Unknown')
        
        if not url:
            continue
            
        # Skip if we already have this ID (deduplication)
        if item_id in active_ids:
            continue
            
        sys.stdout.write(f"\r[{i+1}/{initial_count}] Checking: {title[:40]}...")
        sys.stdout.flush()
        
        if check_url(url):
            active_items.append(item)
            active_ids.add(item_id)
            # print(f" ✅")
        else:
            removed_count += 1
            print(f"\n❌ REMOVED: {title} ({url})")
        
        # Rate limiting
        time.sleep(0.2)

    print(f"\nFinished {filename}. Removed {removed_count} items. Remaining: {len(active_items)}")

    if removed_count > 0 or len(active_items) != initial_count:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(active_items, f, ensure_ascii=False, indent=2)
        print(f"Updated {filename}")
    else:
        print(f"No changes for {filename}")

if __name__ == "__main__":
    clean_file(LISTINGS_FILE)
    clean_file(DEALS_FILE)
