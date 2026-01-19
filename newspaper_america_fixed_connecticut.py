import time
import random
import requests
import pandas as pd
import os
import json
from datetime import datetime

# ============================================================================
# FIXED RATE LIMITER - DO NOT CHANGE THESE VALUES
# ============================================================================
class RateLimiter:
    def __init__(self, min_delay=7.0):  # 7 seconds = ~8.5 requests/min (SAFE)
        self.min_delay = min_delay
        self.last_request_time = 0
        self.consecutive_errors = 0
    
    def wait(self):
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        # Exponential backoff for errors
        error_multiplier = 2 ** min(self.consecutive_errors, 4)
        actual_delay = self.min_delay * error_multiplier
        
        # Random jitter (±15%)
        actual_delay *= random.uniform(0.85, 1.15)
        
        if time_since_last < actual_delay:
            sleep_time = actual_delay - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def record_success(self):
        if self.consecutive_errors > 0:
            self.consecutive_errors = max(0, self.consecutive_errors - 1)
    
    def record_error(self):
        self.consecutive_errors += 1

# ============================================================================
# MAIN SCRIPT
# ============================================================================
# Initialize rate limiter - 7 SECONDS (NOT 0.5!)
limiter = RateLimiter(min_delay=7.0)

# Headers for LOC API
headers = {
    'User-Agent': 'Academic Research - Historical Analysis',
    'Accept': 'application/json'
}

# Search for "coolie" in CONNECTICUT (1870-1874)
searchURL = 'https://www.loc.gov/collections/chronicling-america/?dl=page&end_date=1874-12-31&ops=AND&qs=coolie&searchType=advanced&start_date=1872-01-01&location_state=pennsylvania&fo=json'

def get_item_ids(url, items=[], conditional='True'):
    exclude = ["loc.gov/item","loc.gov/resource"]
    if any(string in url for string in exclude):
        raise NameError('Use a search URL, not item/resource URL')
    
    retry_count = 0
    max_retries = 5
    
    while retry_count <= max_retries:
        limiter.wait()
        
        try:
            call = requests.get(url, params={"fo": "json", "c": 10, "at": "results,pagination"}, 
                              headers=headers, timeout=20)
            
            if call.status_code == 429:
                retry_count += 1
                wait_time = 60 * (2 ** retry_count)  # 60, 120, 240, 480, 960 seconds
                print(f"Rate limit reached. Waiting {wait_time} seconds (retry {retry_count}/{max_retries})...")
                limiter.record_error()
                time.sleep(wait_time)
                continue
                
            elif call.status_code == 200 and 'json' in call.headers.get('content-type', ''):
                limiter.record_success()
                data = call.json()
                results = data['results']
                
                for result in results:
                    original_format = result.get("original_format", "")
                    filter_out = ("collection" in original_format) \
                              or ("web page" in original_format) \
                              or (eval(conditional) == False)
                    
                    if not filter_out and result.get("id"):
                        item = result.get("id")
                        if item.startswith("http://www.loc.gov/resource") or item.startswith("http://www.loc.gov/item"):
                            items.append(item)
                
                if data["pagination"]["next"] is not None:
                    # Small delay between pages
                    time.sleep(random.uniform(3, 7))
                    return get_item_ids(data["pagination"]["next"], items, conditional)
                
                return items
                
            else:
                print(f'HTTP {call.status_code} error')
                retry_count += 1
                if retry_count <= max_retries:
                    time.sleep(60)
                    
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            retry_count += 1
            if retry_count <= max_retries:
                time.sleep(60)
    
    return items

print("=" * 60)
print("📰 CHRONICLING AMERICA - CONNECTICUT SEARCH (FIXED)")
print("=" * 60)
print(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

print("🔍 Searching for 'coolie' in Connecticut (1870-1874)...")
ids_list = get_item_ids(searchURL, items=[])

# Add JSON parameter
ids_list_json = []
for item_id in ids_list:
    if not item_id.endswith('&fo=json'):
        item_id += '&fo=json'
    ids_list_json.append(item_id)

print(f'\n✅ Found {len(ids_list_json)} newspaper pages.')

# Fetch metadata with better rate limiting
item_metadata_list = []
print(f"\n📥 Downloading metadata for {len(ids_list_json)} items...")
print(f"   Rate: ~8.5 requests/minute (LOC limit: 20/minute)")
print(f"   Est. time: ~{(len(ids_list_json) * 7) / 60:.1f} minutes")

for i, item_id in enumerate(ids_list_json):
    if i % 5 == 0 and i > 0:
        print(f"   Processed {i}/{len(ids_list_json)} items...")
    
    retry_count = 0
    while retry_count < 3:
        limiter.wait()
        
        try:
            response = requests.get(item_id, headers=headers, timeout=20)
            
            if response.status_code == 429:
                retry_count += 1
                wait_time = 120 * (2 ** retry_count)
                print(f"    Rate limit. Waiting {wait_time} seconds...")
                limiter.record_error()
                time.sleep(wait_time)
                continue
                
            elif response.status_code == 200:
                limiter.record_success()
                item_data = response.json()
                
                if 'item' in item_data and 'location_city' in item_data['item']:
                    item_metadata_list.append({
                        'Newspaper Title': item_data['item'].get('newspaper_title', ''),
                        'Issue Date': item_data['item'].get('date', ''),
                        'Page Number': item_data.get('pagination', {}).get('current', ''),
                        'LCCN': item_data['item'].get('number_lccn', ''),
                        'City': item_data['item'].get('location_city', ''),
                        'State': item_data['item'].get('location_state', ''),
                        'Contributor': item_data['item'].get('contributor_names', ''),
                        'Batch': item_data['item'].get('batch', ''),
                        'PDF Link': item_data.get('resource', {}).get('pdf', ''),
                    })
                break
                
            else:
                print(f"    HTTP {response.status_code}")
                break
                
        except Exception as e:
            print(f"    Error: {e}")
            retry_count += 1
            if retry_count < 3:
                time.sleep(60)
    
    # Progress saving every 10 items
    if len(item_metadata_list) % 10 == 0 and len(item_metadata_list) > 0:
        backup_file = f'progress_backup_{len(item_metadata_list)}.json'
        with open(backup_file, 'w') as f:
            json.dump(item_metadata_list, f)
        print(f"    Backup saved: {backup_file}")

print(f"\n📊 Collected {len(item_metadata_list)} items")

# Save to CSV
if item_metadata_list:
    for item in item_metadata_list:
        try:
            item['Issue Date'] = pd.to_datetime(item['Issue Date']).strftime('%m-%d-%Y')
        except:
            pass
    
    saveTo = 'output'
    os.makedirs(saveTo, exist_ok=True)
    
    # Fixed filename - Connecticut, not "STATE"
    filename = 'coolie_MD_1872_1874'
    csv_path = os.path.join(saveTo, f'{filename}.csv')
    
    df = pd.DataFrame(item_metadata_list)
    df.to_csv(csv_path, index=False)
    
    print(f'\n💾 Saved to: {csv_path}')
    
    if not df.empty:
        print(f"\n📋 SUMMARY:")
        print(f"   Total articles: {len(df)}")
        print(f"   Newspapers: {df['Newspaper Title'].nunique()}")
        print(f"   Cities: {df['City'].nunique()}")
        
        print(f"\n📰 NEWSPAPERS:")
        for paper, count in df['Newspaper Title'].value_counts().items():
            print(f"   {paper}: {count}")
else:
    print("❌ No data collected.")

print()
print(f"📅 Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)
