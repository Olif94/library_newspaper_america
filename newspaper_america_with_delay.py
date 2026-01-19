import time
import requests
import pandas as pd
import os
from datetime import datetime
import random

print("=" * 60)
print("📰 CHRONICLING AMERICA - RATE LIMIT SAFE VERSION")
print("=" * 60)
print(f"📅 Script started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# CRITICAL: Initial cooldown if previously rate limited
print("🕒 Applying initial 5-minute cooldown (due to previous rate limits)...")
for i in range(300, 0, -30):  # 5 minutes = 300 seconds
    if i % 60 == 0:
        print(f"   Waiting... {i//60} minutes remaining")
    time.sleep(30 if i > 30 else i)
print("✅ Cooldown complete. Starting fresh query...")
print()

# Enhanced Rate Limiter with jitter
class RateLimiter:
    def __init__(self, min_delay=6.0, max_jitter=1.0):  # Increased base delay
        self.min_delay = min_delay
        self.max_jitter = max_jitter
        self.last_request_time = 0
    
    def wait(self):
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_delay:
            time.sleep(self.min_delay - time_since_last)
        # Add random jitter to avoid pattern detection
        jitter = random.uniform(0, self.max_jitter)
        time.sleep(jitter)
        self.last_request_time = time.time()

# Initialize with longer delays
limiter = RateLimiter(min_delay=6.0, max_jitter=2.0)

# Test connection before main query
def test_api_connection():
    """Test if API is accessible before running full query"""
    test_url = 'https://www.loc.gov/collections/chronicling-america/?qs=test&fo=json&c=1'
    print("🔌 Testing API connection...")
    
    try:
        response = requests.get(test_url, timeout=10)
        print(f"   Test Status: {response.status_code}")
        
        if response.status_code == 429:
            print("   ⚠️ Still rate limited! Need longer wait.")
            return False
        elif response.status_code == 200:
            print("   ✅ API accessible")
            return True
        else:
            print(f"   ❌ Unexpected status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Connection test failed: {e}")
        return False

# Run connection test
if not test_api_connection():
    print("\n🔄 Testing again in 2 minutes...")
    time.sleep(120)
    if not test_api_connection():
        print("❌ API still not accessible. Try again in 1 hour.")
        exit(1)

# Perform Query
searchURL = 'https://www.loc.gov/collections/chronicling-america/?dl=page&end_date=1874-12-31&ops=AND&qs=coolie&searchType=advanced&start_date=1872-01-01&location_state=connecticut&fo=json'

def get_item_ids(url, items=[]):
    limiter.wait()
    
    params = {"fo": "json", "c": 5, "at": "results,pagination"}  # Reduced from 10 to 5
    
    try:
        call = requests.get(url, params=params, timeout=20)
        print(f"  API Status: {call.status_code}")
        
        if call.status_code == 429:
            retry_wait = 300  # 5 minutes for burst limit
            print(f"  ⚠️ Rate limited! Waiting {retry_wait//60} minutes...")
            time.sleep(retry_wait)
            limiter.wait()
            call = requests.get(url, params=params, timeout=20)
            
        if call.status_code == 200 and 'json' in call.headers.get('content-type', ''):
            data = call.json()
            total_results = data.get('pagination', {}).get('total', 0)
            print(f"  📊 Total results found: {total_results}")
            
            if total_results == 0:
                print("  ❌ No results found. Check your query parameters.")
                return items
            
            results = data['results']
            items_found = 0
            
            for result in results:
                original_format = result.get("original_format", "")
                filter_out = ("collection" in original_format) or ("web page" in original_format)
                
                if not filter_out and result.get("id"):
                    item = result.get("id")
                    if item.startswith("http://www.loc.gov/"):
                        items.append(item)
                        items_found += 1
            
            print(f"  ✅ Added {items_found} items from this page")
            
            # Check for next page with longer delay
            if data["pagination"]["next"] is not None:
                print("  ↪️ Fetching next page...")
                time.sleep(3)  # Extra delay between pages
                get_item_ids(data["pagination"]["next"], items)
        
        return items
        
    except requests.exceptions.RequestException as e:
        print(f"  Request failed: {e}")
        return items

print("\n🔍 Searching for 'coolie' in West Virginia (1870-1874)...")
ids_list = get_item_ids(searchURL, items=[])

if len(ids_list) == 0:
    print("\n❌ No items found. Possible reasons:")
    print("   1. Still rate limited (wait 1 hour)")
    print("   2. Query has 0 results")
    print("   3. API is down")
    print("\n💡 Try this query in your browser to verify:")
    print("   https://chroniclingamerica.loc.gov/search/pages/results/?state=West+Virginia&date1=1870&date2=1874&proxtext=coolie")
    exit(0)

print(f'\n✅ Found {len(ids_list)} items. Processing metadata...')

# Continue with metadata collection (similar to before but with more caution)
# ... [rest of your metadata collection code] ...

print("\n🎯 To avoid rate limits in the future:")
print("   1. Run scripts only once per hour")
print("   2. Use longer delays (6+ seconds between requests)")
print("   3. Test with small batches first")
print("   4. Consider using official bulk download options")

print(f"\n📅 Script finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)
