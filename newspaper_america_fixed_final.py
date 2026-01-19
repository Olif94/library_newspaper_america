import time
import requests
import pandas as pd
import os

class RateLimiter:
    def __init__(self, min_delay=4.0):
        self.min_delay = min_delay
        self.last_request_time = 0
    def wait(self):
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_delay:
            time.sleep(self.min_delay - time_since_last)
        self.last_request_time = time.time()

limiter = RateLimiter(min_delay=4.0)

searchURL = 'https://www.loc.gov/collections/chronicling-america/?dl=page&end_date=1874-12-31&ops=AND&qs=coolie&searchType=advanced&start_date=1872-01-01&location_state=west+virginia&fo=json'

def get_item_ids(url, items=[]):
    limiter.wait()
    
    params = {"fo": "json", "c": 10, "at": "results,pagination"}
    call = requests.get(url, params=params, timeout=15)
    
    if call.status_code == 200:
        data = call.json()
        print(f"📄 Processing page with {len(data.get('results', []))} results")
        
        for result in data.get('results', []):
            original_format = result.get("original_format", "")
            filter_out = ("collection" in original_format) or ("web page" in original_format)
            
            if not filter_out and result.get("id"):
                item = result.get("id")
                # FIXED: Properly add both resource and item links
                if item.startswith("http://www.loc.gov/"):
                    items.append(item)
                    print(f"  ✅ Added: {item[:60]}...")
        
        if data.get("pagination", {}).get("next"):
            limiter.wait()
            get_item_ids(data["pagination"]["next"], items)
    
    return items

print("🔍 Searching for 'coolie' in West Virginia (1870-1874)...")
ids_list = get_item_ids(searchURL, items=[])

print(f"\n📊 Found {len(ids_list)} items total")

# Fix the &fo=json addition
ids_list_json = []
for id in ids_list:
    if 'fo=json' not in id:
        if '?' in id:
            id += '&fo=json'
        else:
            id += '?fo=json'
    ids_list_json.append(id)

print(f"\n📥 Downloading metadata for {len(ids_list_json)} items...")
item_metadata_list = []

for i, item_id in enumerate(ids_list_json):
    limiter.wait()
    print(f"  [{i+1}/{len(ids_list_json)}] Fetching {item_id[:70]}...")
    
    try:
        item_response = requests.get(item_id, timeout=15)
        if item_response.status_code == 200:
            item_data = item_response.json()
            
            # Extract metadata
            item_metadata_list.append({
                'Newspaper Title': item_data.get('item', {}).get('newspaper_title', ''),
                'Issue Date': item_data.get('item', {}).get('date', ''),
                'Page': item_data.get('pagination', {}).get('current', ''),
                'State': item_data.get('item', {}).get('location_state', ''),
                'City': item_data.get('item', {}).get('location_city', ''),
                'PDF': item_data.get('resource', {}).get('pdf', '')
            })
    except Exception as e:
        print(f"    ❌ Error: {e}")

print(f"\n✅ Collected {len(item_metadata_list)} items with metadata")

if item_metadata_list:
    df = pd.DataFrame(item_metadata_list)
    saveTo = 'output'
    os.makedirs(saveTo, exist_ok=True)
    df.to_csv(f'{saveTo}/coolie_wv_1870_1874.csv', index=False)
    print(f"💾 Saved to {saveTo}/coolie_wv_1870_1874.csv")
    print("\n📋 Sample data:")
    print(df.head())
else:
    print("❌ No metadata collected")
