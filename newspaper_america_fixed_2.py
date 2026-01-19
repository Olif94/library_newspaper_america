import time
import requests
import pandas as pd
import os
from datetime import datetime

# Rate limiter class to prevent hitting API limits
class RateLimiter:
    """Simple rate limiter for loc.gov API."""
    def __init__(self, min_delay=4.0):
        self.min_delay = min_delay
        self.last_request_time = 0

    def wait(self):
        """Ensures a minimum delay between requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_delay:
            time_to_wait = self.min_delay - time_since_last
            time.sleep(time_to_wait)
        self.last_request_time = time.time()

# Initialize rate limiter
limiter = RateLimiter(min_delay=4.0)

print("=" * 60)
print("🚀 CHRONICLING AMERICA NEWSPAPER SCRAPER")
print("=" * 60)
print(f"📅 Script started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Test the basic query first
searchURL = 'https://www.loc.gov/collections/chronicling-america/?dl=page&end_date=1874-12-31&ops=AND&qs=coolie&searchType=advanced&start_date=1870-01-01&location_state=west+virginia&fo=json'

print("🔍 STEP 1: Testing API connection...")
print(f"   Query URL: {searchURL[:80]}...")  # Show first 80 chars of URL

# First, let's test if we can even reach the API
try:
    print("   Testing connection (timeout: 10 seconds)...")
    test_response = requests.get(searchURL, params={"fo": "json", "c": 1}, timeout=10)
    print(f"   ✅ Connection successful! Status code: {test_response.status_code}")
    print(f"   ⏱️  Response time: {test_response.elapsed.total_seconds():.2f} seconds")
    
    if test_response.status_code == 200:
        test_data = test_response.json()
        if 'pagination' in test_data and 'total' in test_data['pagination']:
            total_results = test_data['pagination']['total']
            print(f"   📊 Total results found: {total_results}")
        else:
            print("   ⚠️  Could not find 'total' in pagination data")
    else:
        print(f"   ❌ API returned error status: {test_response.status_code}")
        print(f"   Response preview: {test_response.text[:200]}...")
        
except requests.exceptions.Timeout:
    print("   ❌ Connection timeout! The API is not responding.")
    print("   Try: 1) Check your internet connection")
    print("        2) Visit https://chroniclingamerica.loc.gov in your browser")
    print("        3) The API might be temporarily down")
    exit(1)
except requests.exceptions.RequestException as e:
    print(f"   ❌ Connection failed: {e}")
    exit(1)

print()
print("🔄 STEP 2: Starting main data collection...")
print("-" * 40)

def get_item_ids(url, items=[], conditional='True'):
    """Get item IDs from search results with detailed logging."""
    
    # Apply rate limiting
    limiter.wait()
    
    print(f"   📄 Fetching page {len(items)//10 + 1}...")
    
    params = {"fo": "json", "c": 10, "at": "results,pagination"}
    
    try:
        call = requests.get(url, params=params, timeout=15)
        
        print(f"   ⏱️  Request completed in {call.elapsed.total_seconds():.2f}s")
        print(f"   📊 Status: {call.status_code}")
        
        if call.status_code == 429:
            print("   ⚠️  Rate limit hit! Waiting 30 seconds...")
            time.sleep(30)
            limiter.wait()
            call = requests.get(url, params=params, timeout=15)
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Request failed: {e}")
        return items

    if call.status_code == 200 and 'json' in call.headers.get('content-type', ''):
        data = call.json()
        
        # Show what we found
        page_results = len(data.get('results', []))
        print(f"   📑 This page has {page_results} results")
        
        for i, result in enumerate(data.get('results', [])):
            format_type = result.get("original_format", "unknown")
            item_id = result.get("id", "")
            
            print(f"     Result {i+1}: {format_type[:20]}... | ID: {item_id[:50]}...")
            
            # Filter logic
            filter_out = ("collection" in format_type) or ("web page" in format_type)
            if not filter_out and item_id:
                if item_id.startswith(("http://www.loc.gov/resource", "http://www.loc.gov/item")):
                    items.append(item_id)
                    print(f"       ✅ Added to list (Total: {len(items)})")
        
        # Check for next page
        next_url = data.get("pagination", {}).get("next")
        if next_url:
            print(f"   ➡️  More pages available, continuing...")
            get_item_ids(next_url, items, conditional)
        else:
            print(f"   ✅ Reached last page")
    
    else:
        print(f"   ❌ Bad response: Status {call.status_code}")
        print(f"   Preview: {call.text[:100]}...")
    
    return items

print("Starting search for 'coolie' in West Virginia (1870-1874)...")
ids_list = get_item_ids(searchURL, items=[])

print()
print("📋 STEP 3: Processing results...")
print(f"Total items found: {len(ids_list)}")

if len(ids_list) == 0:
    print()
    print("⚠️  NO RESULTS FOUND")
    print("Possible reasons:")
    print("1. The search term 'coolie' might not appear in West Virginia newspapers 1870-1874")
    print("2. Try removing location_state filter to search nationally")
    print("3. Try alternative terms: 'Chinese', 'immigrant', 'laborer'")
    print("4. Try a broader date range")
    print()
    
    # Let's test a simpler query
    print("🧪 Testing alternative query...")
    test_url = 'https://www.loc.gov/collections/chronicling-america/?qs=railroad&state=West+Virginia&dates=1870&fo=json&c=5'
    print(f"   Testing: 'railroad' in West Virginia, 1870")
    
    try:
        test_resp = requests.get(test_url, timeout=10)
        if test_resp.status_code == 200:
            test_data = test_resp.json()
            total = test_data.get('pagination', {}).get('total', 0)
            print(f"   ✅ Alternative query found {total} results")
            print("   This confirms the API is working.")
    except:
        print("   Could not test alternative query")
    
    exit(0)

# Continue with metadata collection if we have items
print()
print("📥 STEP 4: Downloading metadata...")
print(f"Will process {len(ids_list)} items")
print("Estimated time: ~{:.1f} minutes".format(len(ids_list) * 4.5 / 60))

# Add 'fo=json' to item URLs
ids_list_json = []
for i, item_id in enumerate(ids_list):
    if not item_id.endswith('&fo=json'):
        item_id += '&fo=json'
    ids_list_json.append(item_id)

item_metadata_list = []

for i, item_id in enumerate(ids_list_json):
    limiter.wait()
    
    print(f"   [{i+1}/{len(ids_list_json)}] Fetching metadata...")
    
    try:
        item_response = requests.get(item_id, timeout=15)
        
        if item_response.status_code == 200:
            item_data = item_response.json()
            
            # Extract metadata
            metadata = {
                'Newspaper Title': item_data.get('item', {}).get('newspaper_title', ''),
                'Issue Date': item_data.get('item', {}).get('date', ''),
                'Page Number': item_data.get('pagination', {}).get('current', ''),
                'State': item_data.get('item', {}).get('location_state', ''),
                'City': item_data.get('item', {}).get('location_city', ''),
                'LCCN': item_data.get('item', {}).get('number_lccn', ''),
                'PDF Link': item_data.get('resource', {}).get('pdf', '')
            }
            
            item_metadata_list.append(metadata)
            print(f"       ✅ Got: {metadata.get('Newspaper Title', 'Unknown')[:30]}...")
            
        elif item_response.status_code == 429:
            print("       ⚠️ Rate limited, waiting 30s...")
            time.sleep(30)
            i -= 1  # Retry this item
            
        else:
            print(f"       ❌ Failed: HTTP {item_response.status_code}")
            
    except Exception as e:
        print(f"       ❌ Error: {e}")

print()
print("=" * 60)
print("📊 FINAL RESULTS")
print("=" * 60)

if item_metadata_list:
    df = pd.DataFrame(item_metadata_list)
    
    print(f"✅ Successfully collected {len(df)} items")
    print()
    print("📋 Sample of collected data:")
    print(df[['Newspaper Title', 'Issue Date', 'City', 'State']].head())
    
    # Save to CSV
    saveTo = 'output'
    os.makedirs(saveTo, exist_ok=True)
    filename = f'coolie_West_Virginia_1870_1874_{datetime.now().strftime("%Y%m%d_%H%M")}.csv'
    df.to_csv(f'{saveTo}/{filename}', index=False)
    
    print()
    print(f"💾 Data saved to: {saveTo}/{filename}")
    
else:
    print("❌ No metadata was collected")
    print("The initial search found items but couldn't retrieve their metadata")

print()
print(f"📅 Script finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)