#!/usr/bin/env python3
import requests
import time

# Your exact working query
searchURL = 'https://www.loc.gov/collections/chronicling-america/?dl=page&end_date=1874-12-31&ops=AND&qs=coolie&searchType=advanced&start_date=1870-01-01&location_state=west+virginia&fo=json'

print("🔍 DEBUGGING get_item_ids LOGIC")
print("=" * 60)

# Step 1: Get first page of results
params = {"fo": "json", "c": 10, "at": "results,pagination"}
response = requests.get(searchURL, params=params, timeout=15)

if response.status_code != 200:
    print(f"❌ API request failed: {response.status_code}")
    exit(1)

data = response.json()
print(f"✅ API Response OK")
print(f"📊 Total in pagination: {data.get('pagination', {}).get('total', 'N/A')}")
print(f"📄 Results on this page: {len(data.get('results', []))}")
print()

# Step 2: Examine each result
items_found = []
for i, result in enumerate(data.get('results', [])):
    print(f"\n--- Result {i+1} ---")
    
    # Show what we get
    print(f"ID: {result.get('id', 'NO ID')}")
    print(f"Format: {result.get('original_format', 'NO FORMAT')}")
    print(f"Title: {result.get('title', 'NO TITLE')[:50]}...")
    
    # Apply your filter logic
    original_format = result.get("original_format", "")
    filter_out = ("collection" in original_format) or ("web page" in original_format)
    
    print(f"Filter check: 'collection' in format? {'collection' in original_format}")
    print(f"Filter check: 'web page' in format? {'web page' in original_format}")
    print(f"Would be filtered out? {filter_out}")
    
    # Check if it's a valid item
    if not filter_out and result.get("id"):
        item_id = result.get("id")
        if item_id.startswith("http://www.loc.gov/item"):
            items_found.append(item_id)
            print(f"✅ ADDED to items list")
        elif item_id.startswith("http://www.loc.gov/resource"):
            print(f"⚠️  Resource link (not item), but your code adds it")
        else:
            print(f"⚠️  Unknown ID type: {item_id[:50]}...")
    else:
        print(f"❌ NOT ADDED (filtered out or no ID)")

print("\n" + "=" * 60)
print(f"📋 FINAL COUNT: {len(items_found)} items collected from first page")
print(f"📦 Item IDs collected:")
for item in items_found:
    print(f"  - {item}")

# Step 3: Check what happens when we add &fo=json
print("\n" + "=" * 60)
print("Checking &fo=json addition...")
if items_found:
    test_id = items_found[0]
    print(f"Original ID: {test_id}")
    
    if not test_id.endswith('&fo=json'):
        test_id += '&fo=json'
        print(f"With &fo=json: {test_id}")
        
        # Test if this URL works
        print("Testing the modified URL...")
        test_resp = requests.get(test_id, timeout=10)
        print(f"  Status: {test_resp.status_code}")
        if test_resp.status_code == 200:
            print("  ✅ URL works with &fo=json")
        else:
            print(f"  ❌ URL fails: {test_resp.status_code}")
            print(f"  Try without &fo=json?")
    else:
        print("Already has &fo=json")
