#!/usr/bin/env python3
import requests
import json

# Your exact query
url = 'https://www.loc.gov/collections/chronicling-america/?dl=page&end_date=1874-12-31&ops=AND&qs=coolie&searchType=advanced&start_date=1870-01-01&location_state=west+virginia&fo=json'

print("🔍 Testing your West Virginia query...")
print(f"URL: {url}")

response = requests.get(url, params={"c": 1, "fo": "json"}, timeout=15)
print(f"Status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    total = data.get('pagination', {}).get('total', 0)
    print(f"📊 Total results: {total}")
    
    if total == 0:
        print("\n❌ Zero results found. Testing alternatives:")
        
        # Test 1: Without state filter
        print("\n1. Testing 'coolie' nationally 1870-1874:")
        url_national = 'https://www.loc.gov/collections/chronicling-america/?qs=coolie&start_date=1870-01-01&end_date=1874-12-31&fo=json'
        resp2 = requests.get(url_national, params={"c": 1}, timeout=10)
        if resp2.status_code == 200:
            nat_data = resp2.json()
            nat_total = nat_data.get('pagination', {}).get('total', 0)
            print(f"   National results: {nat_total}")
        
        # Test 2: West Virginia with different term
        print("\n2. Testing West Virginia 1870-1874 with 'railroad':")
        url_wv_rail = 'https://www.loc.gov/collections/chronicling-america/?qs=railroad&location_state=west+virginia&start_date=1870-01-01&end_date=1874-12-31&fo=json'
        resp3 = requests.get(url_wv_rail, params={"c": 1}, timeout=10)
        if resp3.status_code == 200:
            wv_data = resp3.json()
            wv_total = wv_data.get('pagination', {}).get('total', 0)
            print(f"   WV 'railroad' results: {wv_total}")
        
        # Test 3: Check parameter name
        print("\n3. Testing different state parameter names:")
        tests = [
            ("state=West+Virginia", 'https://www.loc.gov/collections/chronicling-america/?qs=coolie&state=West+Virginia&fo=json'),
            ("location=West+Virginia", 'https://www.loc.gov/collections/chronicling-america/?qs=coolie&location=West+Virginia&fo=json'),
        ]
        for name, test_url in tests:
            resp = requests.get(test_url, params={"c": 1}, timeout=10)
            if resp.status_code == 200:
                test_data = resp.json()
                test_total = test_data.get('pagination', {}).get('total', 0)
                print(f"   {name}: {test_total} results")
    
    else:
        print(f"\n✅ Found {total} results! The query works.")
        print("   The problem is in your script's processing logic.")
        
else:
    print(f"❌ API error: {response.status_code}")
    print(response.text[:200])
