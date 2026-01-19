import requests
import time

# Test if API is working at all
test_url = "https://www.loc.gov/collections/chronicling-america/?q=coolie&dates=1870/1874&location=new+york&fo=json"

print("Testing API connection...")
try:
    response = requests.get(test_url, timeout=10)
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Total results: {data.get('pagination', {}).get('total', 0)}")
        print(f"First result: {data.get('results', [{}])[0].get('title', 'No title')}")
    elif response.status_code == 429:
        print("RATE LIMITED! Wait an hour or try tomorrow.")
    else:
        print(f"Other error: {response.status_code}")

except Exception as e:
    print(f"Error: {e}")
