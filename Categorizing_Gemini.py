import json
import time     # To add delays for the API
import httpx    

# --- Configuration ---
YOUR_GEMINI_API_KEY = "AIzaSyAgfRz6Mx5Lv1liZmQbNEe4-FsL5NWdOLY" 
INPUT_DB_FILE = "shorts_db.json"
OUTPUT_DB_FILE = "categorized_db.json"
# ---------------------

def categorize_database_with_gemini():
    """
    Reads 'shorts_db.json', enriches it with Gemini, and saves to 'categorized_db.json'.
    """
    print(f"--- (Categorizer) Starting Step 3: Enriching with Gemini ---")
    
    # 1. Load the uncategorized database
    try:
        with open(INPUT_DB_FILE, "r", encoding="utf-8") as f:
            shorts_list = json.load(f)
        print(f"  Loaded {len(shorts_list)} shorts from {INPUT_DB_FILE}")
    except FileNotFoundError:
        print(f"ERROR: Input file '{INPUT_DB_FILE}' not found.")
        print("Please run `python build_database.py` first.")
        return
    except Exception as e:
        print(f"ERROR: Could not load {INPUT_DB_FILE}: {e}")
        return

    # This is the list of categories we will force Gemini to use.
    categories = [
        "Python", "JavaScript", "Java", "C/C++", "HTML/CSS", "React", 
        "Vue/Angular", "UI/UX Design", "Node.js", "Databases & SQL", 
        "DevOps & Cloud", "AI & Machine Learning", "Data Science", 
        "Cybersecurity", "Game Development", "Mobile Development", 
        "Computer Science", "System Design", "Career Advice", 
        "Productivity & Tools", "Other"
    ]
    
    # Prompt 1: For Categorization
    categorizer_prompt = f"""
    You are an expert content categorizer. I will provide a list of video objects.
    Assign *one* category to each video from this list: {json.dumps(categories)}
    Your response *must* be a valid JSON object only, mapping 'videoId' to 'category'.
    Example: {{"vid1": "Python", "vid2": "Career Advice"}}
    """

    # Prompt 2: For Keywords
    keywords_prompt = f"""
    You are an expert keyword extractor. I will provide a list of video objects.
    For each video, list 3-5 relevant search keywords (all lowercase).
    Your response *must* be a valid JSON object only, mapping 'videoId' to a list of strings.
    Example: {{"vid1": ["python", "loops", "beginner"], "vid2": ["job", "interview", "resume"]}}
    """
    
    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={YOUR_GEMINI_API_KEY}"
    
    enriched_videos = []
    batch_size = 50 # Sends 50 videos to Gemini at a time to avoid reaching token limits for Input/Output
    
    client = httpx.Client()
    #Going through the shorts list in batches of (maximum) 50 videos each
    for i in range(0, len(shorts_list), batch_size):
        batch = shorts_list[i : i + batch_size]
        print(f"  Processing Batch {int(i/batch_size) + 1} / {int(len(shorts_list)/batch_size) + 1}...")
        
        # Create the simple list of titles for Gemini
        titles_to_process = [
            {"videoId": video["id"], "title": video["snippet"]["title"]}
            for video in batch
        ]
        
        # 1. Call Gemini for CATEGORIES
        try:
            payload = {
                "systemInstruction": {"parts": [{"text": categorizer_prompt}]},
                "contents": [{"parts": [{"text": json.dumps(titles_to_process)}]}],
                "generationConfig": {"responseMimeType": "application/json"}
            }
            response = client.post(gemini_url, json=payload, timeout=60.0)
            response.raise_for_status()
            categories_map = json.loads(response.json()["candidates"][0]["content"]["parts"][0]["text"])
        except Exception as e:
            print(f"    !!! ERROR on categorization: {e}. Assigning 'Other'.")
            categories_map = {} 

        # 2. Call Gemini for KEYWORDS
        try:
            payload = {
                "systemInstruction": {"parts": [{"text": keywords_prompt}]},
                "contents": [{"parts": [{"text": json.dumps(titles_to_process)}]}],
                "generationConfig": {"responseMimeType": "application/json"}
            }
            response = client.post(gemini_url, json=payload, timeout=60.0)
            response.raise_for_status()
            keywords_map = json.loads(response.json()["candidates"][0]["content"]["parts"][0]["text"])
        except Exception as e:
            print(f"    !!! ERROR on keywords: {e}. Assigning empty list.")
            keywords_map = {}

        # 3. Merging both categories and keywords results we got from gemini api and appending the batch of videos to enriched_videos
        for video in batch:
            video_id = video["id"]
            video["category"] = categories_map.get(video_id, "Other")
            video["keywords"] = keywords_map.get(video_id, [])
            enriched_videos.append(video)

        # 4. IMPORTANT: Respect the 60 RPM limit (2 calls per loop)
        print("  Batch complete. Waiting 2 seconds...")
        time.sleep(2) # Wait 2 seconds to be safe (2 calls per loop)

    client.close()
    
    # 5. Save the final categorized list, using write to prevent duplicate videos when this script is ran more than once
    with open(OUTPUT_DB_FILE, "w", encoding="utf-8") as f:
        json.dump(enriched_videos, f, indent=2, ensure_ascii=False)
        
    print(f"\nSUCCESS! Enriched database saved to {OUTPUT_DB_FILE}")
    print(f"Total shorts enriched: {len(enriched_videos)}")

if __name__ == "__main__":
    categorize_database_with_gemini()
