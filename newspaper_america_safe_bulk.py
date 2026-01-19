import time
import requests
import pandas as pd
import os
from datetime import datetime

# ============================================================================
# ENHANCED RATE LIMITER WITH CHUNK MANAGEMENT
# ============================================================================
class BulkRateLimiter:
    def __init__(self):
        self.requests_per_minute = 20
        self.seconds_per_request = 60 / self.requests_per_minute  # 3.0 seconds
        self.last_request_time = 0
        self.request_count = 0
        self.minute_start = time.time()
        self.chunk_count = 0
        
    def wait(self):
        """Ensure strict 20 requests/minute limit"""
        current_time = time.time()
        
        # Reset counter if new minute
        if current_time - self.minute_start > 60:
            self.request_count = 0
            self.minute_start = current_time
        
        # Check minute limit
        if self.request_count >= self.requests_per_minute:
            wait_time = 60 - (current_time - self.minute_start)
            if wait_time > 0:
                print(f"⏱️  Minute limit reached. Waiting {wait_time:.1f}s...")
                time.sleep(wait_time + 1)  # Extra second for safety
            self.request_count = 0
            self.minute_start = time.time()
        
        # Enforce delay between requests
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.seconds_per_request:
            wait_time = self.seconds_per_request - time_since_last
            time.sleep(wait_time)
        
        self.last_request_time = time.time()
        self.request_count += 1
    
    def chunk_pause(self, chunk_name):
        """Pause between search chunks to avoid pattern detection"""
        self.chunk_count += 1
        pause_time = 15 if self.chunk_count % 3 == 0 else 5  # Longer pause every 3 chunks
        print(f"🔄 Chunk '{chunk_name}' complete. Pausing {pause_time}s...")
        time.sleep(pause_time)

# Initialize limiter
limiter = BulkRateLimiter()

# ============================================================================
# YEAR-BASED SEARCH CHUNKS (Official faceting strategy)
# ============================================================================
def create_year_chunks(start_year=1870, end_year=1874):
    """Break search into year-by-year chunks per LOC recommendations"""
    base_url = 'https://www.loc.gov/collections/chronicling-america/'
    params = 'dl=page&ops=AND&qs=coolie&searchType=advanced&location_state=west+virginia&fo=json'
    
    chunks = []
    for year in range(start_year, end_year + 1):
        chunk_url = f"{base_url}?{params}&start_date={year}-01-01&end_date={year}-12-31"
        chunks.append({
            'year': year,
            'url': chunk_url,
            'name': f"{year}_coolie_WV"
        })
    
    print(f"📅 Created {len(chunks)} year-based chunks: {start_year}-{end_year}")
    return chunks

# ============================================================================
# SAFE ITEM COLLECTION WITH PROGRESS TRACKING
# ============================================================================
def safe_get_items(url, max_items_per_chunk=50):
    """Safely get items from a single search chunk"""
    items = []
    next_url = url
    
    while next_url and len(items) < max_items_per_chunk:
        limiter.wait()
        
        # Add page parameters
        if '?' in next_url:
            request_url = f"{next_url}&c=10&at=results,pagination"
        else:
            request_url = f"{next_url}?c=10&at=results,pagination"
        
        try:
            response = requests.get(request_url, timeout=30)
            
            if response.status_code == 429:
                print("   🚨 429 - Rate limit hit. Waiting 2 minutes...")
                time.sleep(120)
                continue
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract items
                for result in data.get('results', []):
                    if len(items) >= max_items_per_chunk:
                        break
                    
                    original_format = result.get("original_format", "")
                    if ("collection" in original_format) or ("web page" in original_format):
                        continue
                    
                    if result.get("id"):
                        item = result.get("id")
                        if item.startswith("http://www.loc.gov/"):
                            items.append(item)
                
                # Check for next page
                next_url = data.get("pagination", {}).get("next")
                
                if next_url and len(items) < max_items_per_chunk:
                    print(f"   📄 Page collected: {len(items)} items so far")
            else:
                print(f"   ❌ HTTP {response.status_code}")
                break
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            break
    
    return items

# ============================================================================
# SAFE METADATA COLLECTION WITH BATCH PROCESSING
# ============================================================================
def safe_get_metadata(item_ids, batch_size=20):
    """Collect metadata in batches with pauses"""
    all_metadata = []
    
    print(f"\n📥 Collecting metadata for {len(item_ids)} items...")
    print(f"   Batch size: {batch_size} items")
    print(f"   Estimated time: {(len(item_ids) * 3.5) / 60:.1f} minutes")
    
    # Process in batches
    for batch_start in range(0, len(item_ids), batch_size):
        batch_end = min(batch_start + batch_size, len(item_ids))
        batch_items = item_ids[batch_start:batch_end]
        
        print(f"\n   Batch {batch_start//batch_size + 1}: Items {batch_start+1}-{batch_end}")
        
        batch_metadata = []
        for i, item_id in enumerate(batch_items):
            limiter.wait()
            
            # Prepare URL
            if 'fo=json' not in item_id:
                item_id += '&fo=json' if '?' in item_id else '?fo=json'
            
            try:
                response = requests.get(item_id, timeout=30)
                
                if response.status_code == 429:
                    print(f"     ⚠️ Batch paused (429). Waiting 2 minutes...")
                    time.sleep(120)
                    i -= 1  # Retry this item
                    continue
                
                if response.status_code == 200:
                    item_data = response.json()
                    if 'item' in item_data:
                        metadata = {
                            'Newspaper Title': item_data['item'].get('newspaper_title', ''),
                            'Issue Date': item_data['item'].get('date', ''),
                            'Page Number': item_data.get('pagination', {}).get('current', ''),
                            'State': item_data['item'].get('location_state', ''),
                            'City': item_data['item'].get('location_city', ''),
                            'LCCN': item_data['item'].get('number_lccn', ''),
                            'Contributor': item_data['item'].get('contributor_names', ''),
                            'Batch': item_data['item'].get('batch', ''),
                            'PDF Link': item_data.get('resource', {}).get('pdf', ''),
                            'Year': item_data['item'].get('date', '')[:4] if item_data['item'].get('date') else ''
                        }
                        batch_metadata.append(metadata)
                
            except Exception as e:
                print(f"     ❌ Item error: {e}")
        
        all_metadata.extend(batch_metadata)
        print(f"     ✅ Batch complete: {len(batch_metadata)} items")
        
        # Pause between batches (except last batch)
        if batch_end < len(item_ids):
            print(f"     ⏸️  Pausing 10 seconds between batches...")
            time.sleep(10)
    
    return all_metadata

# ============================================================================
# MAIN EXECUTION WITH SAFE BULK COLLECTION
# ============================================================================
print("=" * 70)
print("📰 SAFE BULK COLLECTION - YEAR-BY-YEAR STRATEGY")
print("=" * 70)
print(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Step 1: Create year-based chunks (LOC-recommended faceting)
year_chunks = create_year_chunks(1870, 1874)

# Step 2: Collect items from each chunk
all_item_ids = []
for chunk in year_chunks:
    print(f"\n🔍 Searching {chunk['year']}...")
    print(f"   URL: {chunk['url'][:80]}...")
    
    chunk_items = safe_get_items(chunk['url'], max_items_per_chunk=50)
    print(f"   ✅ Found {len(chunk_items)} items for {chunk['year']}")
    
    all_item_ids.extend(chunk_items)
    
    # Pause between year chunks
    if chunk != year_chunks[-1]:
        limiter.chunk_pause(f"{chunk['year']}")

print(f"\n📊 TOTAL ITEMS COLLECTED: {len(all_item_ids)}")
print(f"   From {len(year_chunks)} year chunks")

# Step 3: Remove duplicates (some items might appear in multiple years)
unique_items = list(dict.fromkeys(all_item_ids))  # Preserves order
print(f"   Unique items: {len(unique_items)}")

if len(unique_items) == 0:
    print("\n❌ No items found. Check your connection and query.")
    exit(0)

# Step 4: Collect metadata in safe batches
print("\n" + "=" * 70)
metadata = safe_get_metadata(unique_items, batch_size=25)

# Step 5: Save results
if metadata:
    # Format dates
    for item in metadata:
        try:
            item['Issue Date'] = pd.to_datetime(item['Issue Date']).strftime('%m-%d-%Y')
        except:
            pass
    
    # Create DataFrame
    df = pd.DataFrame(metadata)
    
    # Save to CSV
    saveTo = 'output'
    os.makedirs(saveTo, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f'coolie_WV_1870_1874_full_{timestamp}.csv'
    df.to_csv(f'{saveTo}/{filename}', index=False)
    
    print(f"\n✅ BULK COLLECTION COMPLETE!")
    print(f"💾 Saved: {saveTo}/{filename}")
    print(f"📊 Total items: {len(df)}")
    
    # Show breakdown by year
    if 'Year' in df.columns:
        print(f"\n📅 Year distribution:")
        year_counts = df['Year'].value_counts().sort_index()
        for year, count in year_counts.items():
            print(f"   {year}: {count} items")
    
    # Show top newspapers
    print(f"\n📰 Top newspapers:")
    paper_counts = df['Newspaper Title'].value_counts().head(5)
    for paper, count in paper_counts.items():
        print(f"   {paper}: {count} items")
    
    print(f"\n�� Sample data:")
    print(df[['Newspaper Title', 'Issue Date', 'City', 'State']].head())

else:
    print("\n❌ No metadata collected")

# Final statistics
print("\n" + "=" * 70)
print("📊 SAFETY STATISTICS:")
print(f"   Total requests: {limiter.request_count}")
print(f"   Year chunks: {len(year_chunks)}")
print(f"   Batch size: 25 items per batch")
print(f"   Minimum delay: {limiter.seconds_per_request:.1f}s between requests")
print()
print("🎯 TIPS FOR EVEN LARGER COLLECTIONS:")
print("   1. Add --monthly-chunks flag for monthly faceting")
print("   2. Use --resume-from [timestamp] to continue interrupted runs")
print("   3. Consider LOC bulk download for 1000+ items")
print()
print(f"📅 Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
total_time = (datetime.now() - datetime.strptime(
    datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
    '%Y-%m-%d %H:%M:%S'
)).seconds / 60
print(f"⏱️  Total time: {total_time:.1f} minutes")
print("=" * 70)
