# Save this as: search_new_york.py
import time
import re
import json
from urllib.request import urlopen
import requests
import pandas as pd
import os

# ========== SEARCH FOR NEW YORK ==========
state_input = "connecticut"
start_year = "1870"
end_year = "1874"
keyword = "coolie"

print("🌎 Searching Chronicling America")
print("=" * 50)
print(f"📍 State: {state_input.title()}")
print(f"📅 Period: {start_year}-{end_year}")
print(f"🔍 Keyword: '{keyword}'")
print("=" * 50)

# Format the state for URL
state_url = state_input.replace(" ", "+")

# Create dynamic search URL
searchURL = f'https://www.loc.gov/collections/chronicling-america/?dl=page&end_date={end_year}-12-31&ops=AND&qs={keyword}&searchType=advanced&start_date={start_year}-01-01&location_state={state_url}&fo=json'

print(f"\n🔗 Search URL: {searchURL}")

# ========== API FUNCTION ==========
def get_item_ids(url, items=[], conditional='True'):
    # Check that the query URL is not an item or resource link.
    exclude = ["loc.gov/item","loc.gov/resource"]
    if any(string in url for string in exclude):
        raise NameError('Your URL points directly to an item or resource page.')

    # request pages of 100 results at a time
    params = {"fo": "json", "c": 10, "at": "results,pagination"}
    
    try:
        call = requests.get(url, params=params)
        
        if call.status_code == 429:
            print("Rate limit reached. Waiting 5 seconds...")
            time.sleep(5)
            call = requests.get(url, params=params)
            
    except requests.exceptions.RequestException as e:
        print("Request failed:", e)
        return items

    if (call.status_code==200) & ('json' in call.headers.get('content-type')):
        data = call.json()
        results = data['results']
        for result in results:
            # Filter out anything that's a collection or web page
            filter_out = ("collection" in result.get("original_format", "")) \
                    or ("web page" in result.get("original_format", "")) \
                    or (eval(conditional)==False)
            if not filter_out:
                if result.get("id"):
                    item = result.get("id")
                    if item.startswith("http://www.loc.gov/resource"):
                      items.append(item)
                    if item.startswith("http://www.loc.gov/item"):
                        items.append(item)
        if data["pagination"]["next"] is not None:
            next_url = data["pagination"]["next"]
            time.sleep(1.5)
            get_item_ids(next_url, items, conditional)

        return items
    else:
            print('There was a problem. Try running again.')
            return items

# ========== MAIN EXECUTION ==========
print("\n🔍 Searching for articles...")
ids_list = get_item_ids(searchURL, items=[])

# Add 'fo=json' to the end of each row in ids_list
ids_list_json = []
for id in ids_list:
  if not id.endswith('&fo=json'):
    id += '&fo=json'
  ids_list_json.append(id)

print(f'\n✅ Success. Found {len(ids_list_json)} related newspaper pages.')

# ========== DOWNLOAD METADATA ==========
if len(ids_list_json) > 0:
    print(f"\n📥 Downloading metadata for {len(ids_list_json)} items...")
    print("   (Press Ctrl+C to stop early)")

    item_metadata_list = []
    total_items = len(ids_list_json)

    for i, item_id in enumerate(ids_list_json):
        if i % 10 == 0:  # Show progress every 10 items
            print(f"  Processed {i}/{total_items} items...")
        
        try:
            item_response = requests.get(item_id)
            
            if item_response.status_code == 429:
                print("    Rate limit reached. Waiting 3 seconds...")
                time.sleep(3)
                item_response = requests.get(item_id)
                
        except requests.exceptions.RequestException as e:
            print(f"    Request failed: {e}")
            continue

        if item_response.status_code == 200:
            item_data = item_response.json()
            
            if 'item' not in item_data or 'location_city' not in item_data['item']:
                continue

            Newspaper_Title = item_data['item'].get('newspaper_title', '')
            Issue_Date = item_data['item'].get('date', '')
            Page = item_data.get('pagination', {}).get('current', '')
            State = item_data['item'].get('location_state', '')
            City = item_data['item'].get('location_city', '')
            LCCN = item_data['item'].get('number_lccn', '')
            Contributor = item_data['item'].get('contributor_names', '')
            Batch = item_data['item'].get('batch', '')
            pdf = item_data.get('resource', {}).get('pdf', '')

            item_metadata_list.append({
                'Newspaper Title': Newspaper_Title,
                'Issue Date': Issue_Date,
                'Page Number': Page,
                'LCCN': LCCN,
                'City': City,
                'State': State,
                'Contributor': Contributor,
                'Batch': Batch,
                'PDF Link': pdf,
            })
            
            time.sleep(2)  # Reduced delay
            
        else:
            if i < 5:  # Only show first few errors
                print(f"    Failed: HTTP {item_response.status_code}")

    # ========== PROCESS DATA ==========
    for item in item_metadata_list:
        try:
            item['Issue Date'] = pd.to_datetime(item['Issue Date']).strftime('%m-%d-%Y')
        except:
            pass

    df = pd.DataFrame(item_metadata_list)

    # ========== SAVE RESULTS ==========
    saveTo = 'output'
    os.makedirs(saveTo, exist_ok=True)

    state_for_filename = state_input.replace(" ", "_").lower()
    filename = f'coolie_{state_for_filename}_{start_year}_{end_year}'

    print(f'\n💾 Saving to {saveTo}/{filename}.csv...')
    df.to_csv(saveTo + '/' + filename + '.csv', index=False)

    print('✅ Success! File saved.')
    
    # Quick analysis
    if not df.empty:
        print(f"\n📊 RESULTS SUMMARY:")
        print(f"   Total articles: {len(df)}")
        print(f"   Newspapers: {df['Newspaper Title'].nunique()}")
        print(f"   Cities: {df['City'].nunique()}")
        
        # Show distribution
        print(f"\n📰 Newspapers found:")
        papers = df['Newspaper Title'].value_counts().head(5)
        for paper, count in papers.items():
            print(f"   {paper}: {count} articles")
        
        print(f"\n🏙️  Cities with coverage:")
        cities = df['City'].value_counts().head(5)
        for city, count in cities.items():
            print(f"   {city}: {count} articles")

else:
    print("❌ No articles found for this search.")

print("\n" + "=" * 50)
print("✨ Search for New York completed!")