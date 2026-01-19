cat > newspaper_america_january.py << 'EOF'

import time
import requests
import pandas as pd
import os
from datetime import datetime

# Rate limiter class to prevent hitting API limits
class RateLimiter:
    def __init__(self, min_delay=0.5):
        self.min_delay = min_delay
        self.last_request_time = 0
    
    def wait(self):
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_delay:
            time.sleep(self.min_delay - time_since_last)
        self.last_request_time = time.time()

# Initialize rate limiter
limiter = RateLimiter(min_delay=0.5)

# Perform Query - West Virginia 1870-74 search for "coolie"
searchURL = 'https://www.loc.gov/collections/chronicling-america/?dl=page&end_date=1874-12-31&ops=AND&qs=coolie&searchType=advanced&start_date=1872-01-01&location_state=maryland&fo=json'

# Run Function - OFFICIAL CODE FROM CHRONICLING AMERICA (WITH FIXES)
def get_item_ids(url, items=[], conditional='True'):
    # Check that the query URL is not an item or resource link.
    exclude = ["loc.gov/item","loc.gov/resource"]
    if any(string in url for string in exclude):
        raise NameError('Your URL points directly to an item or '
                        'resource page (you can tell because "item" '
                        'or "resource" is in the URL). Please use '
                        'a search URL instead. For example, instead '
                        'of \"https://www.loc.gov/item/2009581123/\", '
                        'try \"https://www.loc.gov/maps/?q=2009581123\". ')

    # Apply rate limiting before request
    limiter.wait()
    
    # request pages of 100 results at a time
    params = {"fo": "json", "c": 10, "at": "results,pagination"}
    
    # ADD RATE LIMIT HANDLING
    try:
        call = requests.get(url, params=params, timeout=15)
        
        # Handle rate limits
        if call.status_code == 429:
            print("Rate limit reached. Waiting 10 seconds...")
            time.sleep(10)
            limiter.wait()
            call = requests.get(url, params=params, timeout=15)
            
    except requests.exceptions.RequestException as e:
        print("Request failed:", e)
        return items

    # Check that the API request was successful
    if (call.status_code == 200) and ('json' in call.headers.get('content-type', '')):
        data = call.json()
        results = data['results']
        
        for result in results:
            # Filter out anything that's a collection or web page
            original_format = result.get("original_format", "")
            filter_out = ("collection" in original_format) \
                    or ("web page" in original_format) \
                    or (eval(conditional) == False)
            
            if not filter_out:
                # Get the link to the item record
                if result.get("id"):
                    item = result.get("id")
                    # FIXED: Proper indentation - accept BOTH resource and item links
                    if item.startswith("http://www.loc.gov/resource"):
                        items.append(item)  # This line was incorrectly indented before!
                    if item.startswith("http://www.loc.gov/item"):
                        items.append(item)
        
        # Repeat the loop on the next page, unless we're on the last page.
        if data["pagination"]["next"] is not None:
            next_url = data["pagination"]["next"]
            get_item_ids(next_url, items, conditional)

        return items
    else:
        print(f'There was a problem. Status: {call.status_code}')
        return items

print("=" * 60)
print("📰 CHRONICLING AMERICA - ORIGINAL SCRIPT WITH FIXES")
print("=" * 60)
print(f"📅 Script started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Generate a list of records found from performing a query and save these Item IDs.
print("🔍 Searching for 'coolie' in West Virginia (1870-1874)...")
ids_list = get_item_ids(searchURL, items=[])

# Add 'fo=json' to the end of each row in ids_list
ids_list_json = []
for item_id in ids_list:
    if not item_id.endswith('&fo=json'):
        item_id += '&fo=json'
    ids_list_json.append(item_id)

print(f'\n✅ Success. Your API Search Query found {len(ids_list_json)} related newspaper pages.')

# Get Basic Metadata/Information for your Query and Store It in a List
print(f"\n📥 Downloading metadata for {len(ids_list_json)} items...")
print(f"   Estimated time: ~{len(ids_list_json) * 4.5 / 60:.1f} minutes")

# Create a list of dictionaries to store the item metadata
item_metadata_list = []

# Iterate over the list of item IDs with rate limit handling
for i, item_id in enumerate(ids_list_json):
    # Progress indicator
    if i % 10 == 0 and i > 0:
        print(f"   Processed {i}/{len(ids_list_json)} items...")
    
    # Apply rate limiting
    limiter.wait()
    
    # ADD RATE LIMIT HANDLING FOR METADATA REQUESTS
    try:
        item_response = requests.get(item_id, timeout=15)
        
        # Handle rate limits
        if item_response.status_code == 429:
            print("    Rate limit reached. Waiting 10 seconds...")
            time.sleep(10)
            limiter.wait()
            item_response = requests.get(item_id, timeout=15)
            
    except requests.exceptions.RequestException as e:
        print(f"    Request failed: {e}")
        continue

    # Check if the API call was successful and Parse the JSON response
    if item_response.status_code == 200:
        item_data = item_response.json()
        
        # Skip if no location data (keeping your original logic)
        if 'item' not in item_data or 'location_city' not in item_data['item']:
            continue

        # Extract the relevant item metadata (ALL ORIGINAL FIELDS)
        Newspaper_Title = item_data['item'].get('newspaper_title', '')
        Issue_Date = item_data['item'].get('date', '')
        Page = item_data.get('pagination', {}).get('current', '')
        State = item_data['item'].get('location_state', '')
        City = item_data['item'].get('location_city', '')
        LCCN = item_data['item'].get('number_lccn', '')
        Contributor = item_data['item'].get('contributor_names', '')
        Batch = item_data['item'].get('batch', '')
        pdf = item_data.get('resource', {}).get('pdf', '')

        # Add the item metadata to the list (ALL ORIGINAL FIELDS)
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
        
    else:
        print(f"    Failed to fetch metadata: HTTP {item_response.status_code}")

print(f"\n📊 Collected metadata for {len(item_metadata_list)} items")

# Change date format to MM-DD-YYYY (keeping your original logic)
for item in item_metadata_list:
    try:
        item['Issue Date'] = pd.to_datetime(item['Issue Date']).strftime('%m-%d-%Y')
    except:
        pass  # Keep original format if conversion fails

# Create a Pandas DataFrame from the list of dictionaries
df = pd.DataFrame(item_metadata_list)

print(f'\n✅ Ready! {len(df)} items collected.')

# Export Metadata of Search Results to a CSV File
# Create output directory
saveTo = 'output'
os.makedirs(saveTo, exist_ok=True)

# Set File Name (keeping your original naming convention)
filename = 'coolie_STATE_1870_1874'

print(f'\n💾 Saving to {saveTo}/{filename}.csv...')

metadata_dataframe = pd.DataFrame(item_metadata_list)
metadata_dataframe.to_csv(saveTo + '/' + filename + '.csv', index=False)

print('✅ Success! Please check your saveTo location to see the saved csv file.')
print()

if not df.empty:
    print("📋 Preview of collected data:")
    print(metadata_dataframe.head())
    
    # Additional analysis (keeping your original analysis)
    print(f"\n📊 ANALYSIS:")
    print(f"   Total articles: {len(df)}")
    print(f"   Newspapers: {df['Newspaper Title'].nunique()}")
    print(f"   Cities: {df['City'].nunique()}")
    
    # Show newspaper distribution
    print(f"\n📰 Newspaper Distribution:")
    newspaper_counts = df['Newspaper Title'].value_counts()
    for paper, count in newspaper_counts.items():
        print(f"   {paper}: {count}")
else:
    print("❌ No data was collected. The query returned 0 results.")

print()
print(f"📅 Script finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)
