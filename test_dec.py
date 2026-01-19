import time
import requests
import pandas as pd
import os
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

print("=== SCRIPT STARTING ===")

# Perform Query - Use your Connecticut 1870-74 search for "coolie"
searchURL = 'https://www.loc.gov/collections/chronicling-america/?dl=page&end_date=1874-12-31&ops=AND&qs=coolie&searchType=advanced&start_date=1870-01-01&location_state=connecticut&fo=json'

print(f"Search URL: {searchURL}")

# Run Function - MODIFIED CODE WITH FIXES
def get_item_ids(url, items=[], conditional='True'):
    print(f"\nFetching items from: {url[:100]}...")
    
    # Check that the query URL is not an item or resource link.
    exclude = ["loc.gov/item","loc.gov/resource"]
    if any(string in url for string in exclude):
        raise NameError('Your URL points directly to an item or resource page.')

    # Parse the URL and add/update parameters
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    
    # Ensure 'fo=json' is in the parameters
    query_params['fo'] = ['json']
    query_params['c'] = ['100']  # Increased from 10 to 100 for efficiency
    query_params['at'] = ['results,pagination']
    
    # Reconstruct the URL
    new_query = urlencode(query_params, doseq=True)
    api_url = urlunparse((
        parsed_url.scheme,
        parsed_url.netloc,
        parsed_url.path,
        parsed_url.params,
        new_query,
        parsed_url.fragment
    ))
    
    # ADD RATE LIMIT HANDLING
    try:
        print(f"  Calling API...")
        call = requests.get(api_url, timeout=30)
        
        # Handle rate limits
        if call.status_code == 429:
            print("  Rate limit reached. Waiting 20 seconds...")
            time.sleep(20)
            call = requests.get(api_url, timeout=30)
            
    except requests.exceptions.RequestException as e:
        print(f"  Request failed: {e}")
        return items

    # Check that the API request was successful
    if call.status_code == 200 and 'application/json' in call.headers.get('content-type', ''):
        try:
            data = call.json()
        except:
            print("  Failed to parse JSON response")
            return items
            
        # Check if results exist in response
        if 'results' not in data:
            print("  No 'results' key in response")
            return items
            
        results = data['results']
        print(f"  Found {len(results)} results on this page")
        
        for result in results:
            # Filter out anything that's a collection or web page
            filter_out = ("collection" in result.get("original_format", "")) \
                    or ("web page" in result.get("original_format", "")) \
                    or (eval(conditional)==False)
            if not filter_out:
                # Get the link to the item record
                if result.get("id"):
                    item = result.get("id")
                    # Filter out links to Catalog or other platforms
                    if item.startswith("https://www.loc.gov/resource/"):
                      resource = item.replace("https://www.loc.gov/resource/", "https://www.loc.gov/item/")
                      items.append(resource)
                    elif item.startswith("https://www.loc.gov/item/"):
                        items.append(item)
                    elif item.startswith("http://www.loc.gov/item/"):
                        items.append(item.replace("http://", "https://"))
        
        # Repeat the loop on the next page, unless we're on the last page.
        if "pagination" in data and data["pagination"].get("next") is not None:
            next_url = data["pagination"]["next"]
            print(f"  Moving to next page...")
            # ADD DELAY BETWEEN PAGES
            time.sleep(3)
            get_item_ids(next_url, items, conditional)
        else:
            print(f"  Finished collecting {len(items)} items")
            
        return items
    else:
        print(f'  There was a problem. Status code: {call.status_code}')
        return items

# Generate a list of records found from performing a query and save these Item IDs.
print("\n🔍 Searching for 'coolie' in Connecticut 1870-1874...")
ids_list = get_item_ids(searchURL, items=[])

print(f"\nRaw items found: {len(ids_list)}")

# Add 'fo=json' to the end of each row in ids_list
ids_list_json = []
for id in ids_list:
  if not id.endswith('&fo=json'):
    if '?' in id:
      id += '&fo=json'
    else:
      id += '?fo=json'
  ids_list_json.append(id)

print(f'\n✅ Success. Your API Search Query found {len(ids_list_json)} related newspaper pages.')

# Get Basic Metadata/Information for your Query and Store It in a List
if len(ids_list_json) == 0:
    print("No items found. Exiting...")
else:
    print(f"\n📥 Downloading metadata for {len(ids_list_json)} items...")
    
    # Create a list of dictionaries to store the item metadata
    item_metadata_list = []
    
    # Iterate over the list of item IDs with rate limit handling
    for i, item_id in enumerate(ids_list_json):
        print(f"  Processing {i+1}/{len(ids_list_json)}...")
        
        # ADD RATE LIMIT HANDLING FOR METADATA REQUESTS
        try:
            item_response = requests.get(item_id, timeout=30)
            
            # Handle rate limits
            if item_response.status_code == 429:
                print("    Rate limit reached. Waiting 15 seconds...")
                time.sleep(15)
                item_response = requests.get(item_id, timeout=30)
                
        except requests.exceptions.RequestException as e:
            print(f"    Request failed: {e}")
            continue

        # Check if the API call was successful and Parse the JSON response
        if item_response.status_code == 200:
            try:
                item_data = item_response.json()
            except:
                print(f"    Failed to parse JSON for item {i+1}")
                continue
            
            # Extract the relevant item metadata
            # Handle different response structures
            if 'item' in item_data:
                item_info = item_data['item']
            else:
                item_info = item_data
            
            # Extract metadata with defaults
            Newspaper_Title = item_info.get('newspaper_title', '')
            Issue_Date = item_info.get('date', '')
            
            # Handle page number extraction
            Page = ''
            if 'pagination' in item_data:
                Page = item_data['pagination'].get('current', '')
            
            State = item_info.get('location_state', '')
            City = item_info.get('location_city', '')
            LCCN = item_info.get('number_lccn', '')
            
            # Handle contributor - might be list or string
            Contributor = item_info.get('contributor_names', '')
            if isinstance(Contributor, list):
                Contributor = ', '.join(Contributor)
            
            Batch = item_info.get('batch', '')
            
            # Handle PDF link extraction
            pdf = ''
            if 'resources' in item_data:
                for resource in item_data['resources']:
                    if resource.get('pdf'):
                        pdf = resource.get('pdf')
                        break
            
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
            time.sleep(2)  # Reduced from 15 seconds
            
        else:
            print(f"    Failed to fetch metadata: HTTP {item_response.status_code}")

    # Create a Pandas DataFrame from the list of dictionaries
    if item_metadata_list:
        df = pd.DataFrame(item_metadata_list)
        
        # Change date format to MM-DD-YYYY
        for item in item_metadata_list:
            try:
                # Try to parse the date
                parsed_date = pd.to_datetime(item['Issue Date'], errors='coerce')
                if pd.notna(parsed_date):
                    item['Issue Date'] = parsed_date.strftime('%m-%d-%Y')
            except:
                pass  # Keep original format if conversion fails

        print(f'\n✅ Ready! {len(df)} items collected.')
        
        # Export Metadata of Search Results to a CSV File
        # Create output directory
        saveTo = 'output'
        os.makedirs(saveTo, exist_ok=True)
        
        # Set File Name
        filename = 'coolie_CONNECTICUT_1870_1874'  # Changed from STATE to CONNECTICUT
        
        print(f'\n💾 Saving to {saveTo}/{filename}.csv...')
        
        # Create DataFrame from updated list
        metadata_dataframe = pd.DataFrame(item_metadata_list)
        metadata_dataframe.to_csv(os.path.join(saveTo, filename + '.csv'), index=False)
        
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
    else:
        print("No metadata collected. CSV file not created.")

print("\n=== SCRIPT COMPLETED ===")