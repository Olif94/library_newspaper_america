#!/usr/bin/env python3
import sys
import time
import requests

print("🔍 Python test script starting...")
print(f"Python version: {sys.version}")
print()

# Test 1: Can we import requests?
try:
    import requests
    print("✅ 'requests' library imported successfully")
    print(f"   Version: {requests.__version__}")
except ImportError as e:
    print(f"❌ FAILED to import 'requests': {e}")
    print("   Try: pip3 install requests")
    sys.exit(1)
print()

# Test 2: Can we make a simple HTTP request?
test_url = "https://httpbin.org/get"  # A reliable test site
print(f"📡 Testing network connection to {test_url}...")
try:
    response = requests.get(test_url, timeout=10)
    print(f"✅ Network test successful!")
    print(f"   Status: {response.status_code}")
    print(f"   Time: {response.elapsed.total_seconds():.2f} seconds")
except Exception as e:
    print(f"❌ Network test failed: {e}")
    print("   Check your internet connection or firewall")
print()

# Test 3: Can we reach Chronicling America API?
print("🌐 Testing Chronicling America API...")
api_url = "https://www.loc.gov/collections/chronicling-america/?qs=coolie&fo=json&c=1"
print(f"   URL: {api_url[:80]}...")
try:
    start = time.time()
    api_response = requests.get(api_url, timeout=15)
    elapsed = time.time() - start
    
    print(f"   Status: {api_response.status_code}")
    print(f"   Time: {elapsed:.2f} seconds")
    
    if api_response.status_code == 200:
        print("✅ API connection successful!")
        data = api_response.json()
        total = data.get('pagination', {}).get('total', 'Unknown')
        print(f"   Total results for 'coolie': {total}")
    else:
        print(f"❌ API returned error: {api_response.status_code}")
        print(f"   Response: {api_response.text[:200]}")
        
except requests.exceptions.Timeout:
    print("❌ API request timed out after 15 seconds")
    print("   The API might be down or blocked")
except Exception as e:
    print(f"❌ API test failed: {e}")
print()

print("�� Diagnostic complete.")
