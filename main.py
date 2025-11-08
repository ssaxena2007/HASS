import requests
import json
import isodate  # You may need to run: pip install isodate

# --- Configuration ---
# Paste your YouTube API key here
YOUR_YOUTUBE_API_KEY = "AIzaSyDlDocvLsGvxbZf37dmCDrkr__fEzQj7VA"

# Your "Channel ID" Whitelist
APPROVED_CHANNELS = [
    # --- Long-Form Channels (Might have some shorts) ---
    "UCCezIgC97PvUuR4_gbFUs5g",  # Corey Schafer (Correct ID)
    "UC29ju8bIPH5as8OGnQzwJyA",  # Traversy Media (Was correct)
    "UCcabW7890RKJzL968QWEykA",  # CS50 (Correct ID)
    "UC_x5XG1OV2P6uZZ5FSM9Ttw",  # Khan Academy (Was correct)
    "UCWv7vMbMWH4-V0ZXdmDpPBA",  # Programming with Mosh (Was correct)
    "UCFbNIlppjAuEX4znoulh0Cw",  # Web Dev Simplified (Correct ID)
    "UCW5YeuERMmlnqo4oq8vwUpg",  # The Net Ninja (Was correct)
    
    # --- Shorts-Focused Channels (Correct 'UC...' IDs) ---
    "UCsBjURrPoezykLs9EqgamOA",  # Fireship (Was correct)
    "UC8butISFwT-Wl7EV0hUK0BQ",  # freeCodeCamp.org (Was correct)
    "UC4SVo0Ue36XCfOyb5Lh1viQ",  # Bro Code (Was correct)
    "UCuudpdbKmQWq2PPzYgVCWlA",  # Indently (Correct ID, was UU...)
    "UCaiL2GDNpLYH6Wokkk1VNcg",  # mCoding (Correct ID, was UU...)
    "UCZgt6AzoyjslHTC9dz0UoTw",  # ByteByteGo (Correct ID, was UU...)
    "UCzNf0liwUzMN6_pixbQlMhQ",  # Coder Coder (Correct ID, was UU...)
]
# ---------------------

def parse_duration(duration_str):
    """Converts a YouTube ISO 8601 duration string to total seconds."""
    try:
        return isodate.parse_duration(duration_str).total_seconds()
    except Exception:
        return -1

def build_shorts_database():
    """
    Fetches ALL shorts from approved channels using pagination 
    and saves them to a JSON file.
    """
    all_video_ids = []
    
    channel_url = "https://www.googleapis.com/youtube/v3/channels"
    playlist_url = "https://www.googleapis.com/youtube/v3/playlistItems"
    videos_url = "https://www.googleapis.com/youtube/v3/videos"

    print("--- (Builder) Starting Step 1: Get ALL Video IDs (with Pagination) ---")

    # --- STEP 1: Get ALL video IDs from each channel ---
    for channel_id in APPROVED_CHANNELS:
        # Use set() to avoid processing the same ID twice (like Traversy Media)
        unique_channels = set(APPROVED_CHANNELS)
    
    for channel_id in unique_channels:
        print(f"\nProcessing Channel: {channel_id}")
        
        # 1a: Find the 'uploads' playlist ID
        channel_params = { "part": "contentDetails", "id": channel_id, "key": YOUR_YOUTUBE_API_KEY }
        try:
            response = requests.get(channel_url, params=channel_params)
            response.raise_for_status()
            results = response.json()
            if not results.get("items"):
                print(f"!!! WARNING: Channel not found: {channel_id}. Skipping.")
                continue
            uploads_id = results["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        except Exception as e:
            print(f"!!! ERROR finding uploads for {channel_id}: {e}. Skipping.")
            continue

        # 1b: Get ALL videos from that 'uploads' playlist using pagination
        next_page_token = None
        page_count = 1
        
        while True: # This loop will run for each "page" of 50 videos
            print(f"  Fetching page {page_count}...")
            playlist_params = { 
                "part": "snippet", 
                "playlistId": uploads_id, 
                "key": YOUR_YOUTUBE_API_KEY, 
                "maxResults": 50,
                "pageToken": next_page_token # Will be None on the first loop
            }
            
            try:
                response = requests.get(playlist_url, params=playlist_params)
                response.raise_for_status()
                results = response.json()
                
                for item in results.get("items", []):
                    all_video_ids.append(item["snippet"]["resourceId"]["videoId"])
                
                # Check if there's another page
                next_page_token = results.get("nextPageToken")
                if not next_page_token:
                    print(f"  Reached the end for channel {channel_id}.")
                    break # Exit the 'while True' loop
                
                page_count += 1
                
            except Exception as e:
                print(f"!!! ERROR fetching playlist items for {uploads_id}: {e}. Skipping rest of this channel.")
                break # Stop processing this channel if an error occurs

    print(f"\n--- (Builder) Step 1 Complete: Found {len(all_video_ids)} total video IDs ---")
    
    # --- STEP 2: Get the duration for all videos in batches of 50 ---
    all_shorts_details = []
    batch_size = 50
    
    print(f"--- (Builder) Starting Step 2: Checking duration for {len(all_video_ids)} videos ---")
    
    for i in range(0, len(all_video_ids), batch_size):
        batch_ids = all_video_ids[i : i + batch_size]
        ids_string = ",".join(batch_ids)

        video_params = {
            "part": "contentDetails,snippet", # Ask for details AND snippet
            "id": ids_string,
            "key": YOUR_YOUTUBE_API_KEY
        }
        
        print(f"  Checking duration for batch {int(i/batch_size) + 1}...")
        try:
            response = requests.get(videos_url, params=video_params)
            response.raise_for_status()
            results = response.json()
            
            # --- STEP 3: Filter this batch by duration ---
            for item in results.get("items", []):
                duration_str = item["contentDetails"]["duration"]
                duration_sec = parse_duration(duration_str)
                
                if duration_sec > 0 and duration_sec <= 61: # 100% accurate filter
                    all_shorts_details.append(item) 
        except Exception as e:
            print(f"!!! ERROR checking video durations: {e}. Skipping batch.")
            continue
            
    print(f"\n--- (Builder) Feed build complete: Found {len(all_shorts_details)} total shorts ---")

    # --- STEP 4: Save the final list to a JSON file ---
    db_filename = "shorts_db.json"
    with open(db_filename, "w", encoding="utf-8") as f:
        json.dump(all_shorts_details, f, indent=2, ensure_ascii=False)
        
    print(f"\n✅ SUCCESS! Database saved to {db_filename}")
    print(f"Total videos processed: {len(all_video_ids)}")
    print(f"Total shorts found: {len(all_shorts_details)}")

# --- This makes the script runnable from the command line ---
if __name__ == "__main__":
    build_shorts_database()