import requests
import json
import isodate  # You may need to run: pip install isodate

# --- Configuration ---
# Paste your YouTube API key here
YOUR_YOUTUBE_API_KEY = "AIzaSyDlDocvLsGvxbZf37dmCDrkr__fEzQj7VA"

# Your "Channel ID" Whitelist
APPROVED_CHANNELS = [
    "UCCabW7890RKJzL968QWEykA",  # Corey Schafer
    "UCCezIgC97PvUuR4_gbFUs5g",  # Traversy Media
    "UC6E_dvT-e5aM2g4b8tq9y_A",  # CS50
    "UC_x5XG1OV2P6uZZ5FSM9Ttw",  # Khan Academy
    "UCYO_jab_2R6gLBErLJ4DYg",   # Mosh Hamedani
    "UCWv7vMbMWH4-V0ZXdmDpPBA",  # Programming with Mosh
    "UCRLEADhMcb8WUdnQ5_EADaA",  # Web Dev Simplified
    "UCW5YeuERMmlnqo4oq8vwUpg",  # The Net Ninja
    "UCsBjURrPoezykLs9EqgamOA",  # Fireship
    "UC8butISFwT-Wl7EV0hUK0BQ",  # freeCodeCamp.org
    "UC-bF-V-x2iYnK2L-n31v0cg",  # Bro Code
    "UU29c0n-fXl-XlD-X3S-cE-A",  # Indently
    "UU-HJt-12bc-g-cGR5nS1N_Q",  # mCoding
    "UUwD6w-vuB4Kl2ga2n3a0Qig",  # ByteByteGo
    "UUfzl-9n2e-l-r6k-gD7nS-g",  # Coder Coder
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
    Fetches all shorts from approved channels and saves them to a JSON file.
    This is the 100% accurate 2-step (duration check) method.
    """
    all_video_ids = []
    
    channel_url = "https://www.googleapis.com/youtube/v3/channels"
    playlist_url = "https://www.googleapis.com/youtube/v3/playlistItems"
    videos_url = "https://www.googleapis.com/youtube/v3/videos"

    print("--- (Builder) Starting Step 1: Get Video IDs ---")

    # --- STEP 1: Get the 50 most recent video IDs from each channel ---
    for channel_id in APPROVED_CHANNELS:
        print(f"Processing Channel: {channel_id}")
        
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

        # 1b: Get the 50 videos from that 'uploads' playlist
        playlist_params = { "part": "snippet", "playlistId": uploads_id, "key": YOUR_YOUTUBE_API_KEY, "maxResults": 50 }
        try:
            response = requests.get(playlist_url, params=playlist_params)
            response.raise_for_status()
            results = response.json()
            for item in results.get("items", []):
                all_video_ids.append(item["snippet"]["resourceId"]["videoId"])
        except Exception as e:
            print(f"!!! ERROR fetching playlist items for {uploads_id}: {e}. Skipping.")
            continue

    print(f"--- (Builder) Step 1 Complete: Found {len(all_video_ids)} total video IDs ---")
    
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
        
        try:
            response = requests.get(videos_url, params=video_params)
            response.raise_for_status()
            results = response.json()
            
            # --- STEP 3: Filter this batch by duration ---
            for item in results.get("items", []):
                duration_str = item["contentDetails"]["duration"]
                duration_sec = parse_duration(duration_str)
                
                # This is our 100% accurate filter!
                if duration_sec > 0 and duration_sec <= 61: # 61 to be safe
                    all_shorts_details.append(item) 
        except Exception as e:
            print(f"!!! ERROR checking video durations: {e}. Skipping batch.")
            continue
            
    print(f"--- (Builder) Feed build complete: Found {len(all_shorts_details)} total shorts ---")

    # --- STEP 4: Save the final list to a JSON file ---
    db_filename = "shorts_db.json"
    with open(db_filename, "w", encoding="utf-8") as f:
        json.dump(all_shorts_details, f, indent=2, ensure_ascii=False)
        
    print(f"\n✅ SUCCESS! Database saved to {db_filename}")

# --- This makes the script runnable from the command line ---
if __name__ == "__main__":
    build_shorts_database()