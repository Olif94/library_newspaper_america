import time
import re
import json
from urllib.request import urlopen
import requests
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import pprint
import os

# Perform Query - Use your Arizona 1870-74 search for "coolie"
searchURL = 'https://www.loc.gov/collections/chronicling-america/?dl=page&end_date=1874-12-31&ops=AND&qs=coolie&searchType=advanced&start_date=1870-01-01&location_state=vermont&fo=json'

# Run Function - OFFICIAL CODE FROM CHRONICLING AMERICA
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

    # request pages of 100 results at a time
    params = {"fo": "json", "c": 10, "at": "results,pagination"}
    
    # ADD RATE LIMIT HANDLING
    try:
        call = requests.get(url, params=params)
        
        # Handle rate limits
        if call.status_code == 429:
            print("Rate limit reached. Waiting 10 seconds...")
            time.sleep(20)
            call = requests.get(url, params=params)
            
    except requests.exceptions.RequestException as e:
        print("Request failed:", e)
        return items

    # Check that the API request was successful
    if (call.status_code==200) & ('json' in call.headers.get('content-type')):
        data = call.json()
        results = data['results']
        for result in results:
            # Filter out anything that's a colletion or web page
            filter_out = ("collection" in result.get("original_format", "")) \
                    or ("web page" in result.get("original_format", "")) \
                    or (eval(conditional)==False)
            if not filter_out:
                # Get the link to the item record
                if result.get("id"):
                    item = result.get("id")
                    # Filter out links to Catalog or other platforms
                    if item.startswith("http://www.loc.gov/resource"):
                      resource = item  # Assign item to resource
                      items.append(resource)
                    if item.startswith("http://www.loc.gov/item"):
                        items.append(item)
        # Repeat the loop on the next page, unless we're on the last page.
        if data["pagination"]["next"] is not None:
            next_url = data["pagination"]["next"]
            # ADD DELAY BETWEEN PAGES
            time.sleep(2)
            get_item_ids(next_url, items, conditional)

        return items
    else:
            print('There was a problem. Try running the cell again, or check your searchURL.')
            return items

# Generate a list of records found from performing a query and save these Item IDs.
print("🔍 Searching for 'coolie' in 1870 something...")
ids_list = get_item_ids(searchURL, items=[])

# Add 'fo=json' to the end of each row in ids_list
ids_list_json = []
for id in ids_list:
  if not id.endswith('&fo=json'):
    id += '&fo=json'
  ids_list_json.append(id)
ids = ids_list_json

print('\n✅ Success. Your API Search Query found '+str(len(ids_list_json))+' related newspaper pages.')

# Get Basic Metadata/Information for your Query and Store It in a List
print(f"\n📥 Downloading metadata for {len(ids_list_json)} items...")

# Create a list of dictionaries to store the item metadata
item_metadata_list = []

# Iterate over the list of item IDs with rate limit handling
for i, item_id in enumerate(ids_list_json):
    print(f"  Processing {i+1}/{len(ids_list_json)}...")
    
    # ADD RATE LIMIT HANDLING FOR METADATA REQUESTS
    try:
        item_response = requests.get(item_id)
        
        # Handle rate limits
        if item_response.status_code == 429:
            print("    Rate limit reached. Waiting 10 seconds...")
            time.sleep(10)
            item_response = requests.get(item_id)
            
    except requests.exceptions.RequestException as e:
        print(f"    Request failed: {e}")
        continue

    # Check if the API call was successful and Parse the JSON response
    if item_response.status_code == 200:
        # Iterate over the ids_list_json list and extract the relevant metadata from each dictionary.
        item_data = item_response.json()
        
        # Skip if no location data
        if 'item' not in item_data or 'location_city' not in item_data['item']:
            continue

        # Extract the relevant item metadata
        Newspaper_Title = item_data['item'].get('newspaper_title', '')
        Issue_Date = item_data['item'].get('date', '')
        Page = item_data.get('pagination', {}).get('current', '')
        State = item_data['item'].get('location_state', '')
        City = item_data['item'].get('location_city', '')
        LCCN = item_data['item'].get('number_lccn', '')
        Contributor = item_data['item'].get('contributor_names', '')
        Batch = item_data['item'].get('batch', '')
        pdf = item_data.get('resource', {}).get('pdf', '')

        # Add the item metadata to the list
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
        
        # ADD SMALL DELAY BETWEEN REQUESTS
        time.sleep(15)
        
    else:
        print(f"    Failed to fetch metadata: HTTP {item_response.status_code}")

# Change date format to MM-DD-YYYY
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

# Set File Name
filename = 'coolie_STATE_1870_1874'

print(f'\n💾 Saving to {saveTo}/{filename}.csv...')

metadata_dataframe = pd.DataFrame(item_metadata_list)
metadata_dataframe.to_csv(saveTo + '/' + filename + '.csv', index=False)

print('✅ Success! Please check your saveTo location to see the saved csv file. See Preview Below:\n')
print(metadata_dataframe.head())

# Additional analysis
if not df.empty:
    print(f"\n📊 ANALYSIS:")
    print(f"   Total articles: {len(df)}")
    print(f"   Newspapers: {df['Newspaper Title'].nunique()}")
    print(f"   Cities: {df['City'].nunique()}")
    
    # Show newspaper distribution
    print(f"\n📰 Newspaper Distribution:")
    newspaper_counts = df['Newspaper Title'].value_counts()
    for paper, count in newspaper_counts.items():
        print(f"   {paper}: {count}")