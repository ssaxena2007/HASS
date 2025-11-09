#!/usr/bin/env python3
"""
Find educational creators using the Gemini API and fetch their latest shorts via the YouTube Data API.

Usage:
  - Set environment variables `GEMINI_API_KEY` and `YOUTUBE_API_KEY` (or pass --mock).
  - Run: python gemini_youtube_search.py --topic "python" --num-creators 5 --shorts-per-creator 5

The script outputs a JSON file with creators and up to N shorts each.
"""
import os
import json
import time
import argparse
from typing import List, Dict, Any

import httpx
import requests


def parse_iso8601_duration(dur: str) -> int:
    """Parse an ISO 8601 duration like PT1M30S into seconds."""
    # Simple parser for formats used by YouTube like PT#M#S, PT#S, PT#M
    dur = dur.upper()
    if not dur.startswith("PT"):
        return 0
    dur = dur[2:]
    minutes = 0
    seconds = 0
    if "M" in dur:
        parts = dur.split("M")
        minutes = int(parts[0]) if parts[0] else 0
        if parts[1].endswith("S"):
            seconds = int(parts[1][:-1]) if parts[1][:-1] else 0
    elif dur.endswith("S"):
        seconds = int(dur[:-1]) if dur[:-1] else 0
    return minutes * 60 + seconds


def call_gemini_for_creators(topic: str, num_creators: int, api_key: str) -> List[str]:
    """Call Google's Generative Language (Gemini) to request creators.

    Returns a list of channel IDs as strings. The Gemini response MUST be a JSON array
    containing only channel ID strings (e.g. ["UC_x5XG1OV2P6uZZ5FSM9Ttw", ...]).
    """
    if not api_key:
        raise ValueError("GEMINI API key is required")

    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={api_key}"

    prompt = (
        f"Provide a JSON array of {num_creators} YouTube CHANNEL IDs (strings) for high-quality educational channels"
        f" that focus on '{topic}'. The response MUST be valid JSON containing only an array of channel ID strings"
        " and nothing else. Example: [\"UC_x5XG1OV2P6uZZ5FSM9Ttw\", \"UCabcd...\"]"
    )

    payload = {
        "systemInstruction": {"parts": [{"text": "You are a helpful assistant that returns valid JSON."}]},
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"}
    }

    client = httpx.Client(timeout=30.0)
    try:
        r = client.post(gemini_url, json=payload)
        r.raise_for_status()
        resp = r.json()
        text = resp["candidates"][0]["content"]["parts"][0]["text"]
        channel_ids = json.loads(text)
        if not isinstance(channel_ids, list) or not all(isinstance(x, str) for x in channel_ids):
            raise ValueError("Gemini response JSON must be a list of channel ID strings")
        return channel_ids
    finally:
        client.close()


def youtube_get_channel_details(yt_key: str, channel_id: str) -> Dict[str, Any]:
    """Fetch channel snippet (title/description) for a given channel ID."""
    url = "https://www.googleapis.com/youtube/v3/channels"
    params = {"part": "snippet", "id": channel_id, "key": yt_key}
    r = requests.get(url, params=params, timeout=15.0)
    r.raise_for_status()
    items = r.json().get("items", [])
    print(items)
    if not items:
        return {}
    return items[0].get("snippet", {})


def youtube_find_channel_id(yt_key: str, name: str) -> str:
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": name,
        "type": "channel",
        "maxResults": 1,
        "key": yt_key,
    }
    r = requests.get(url, params=params, timeout=15.0)
    r.raise_for_status()
    items = r.json().get("items", [])
    print(items)
    if not items:
        return ""
    return items[0]["snippet"]["channelId"] if "snippet" in items[0] else items[0]["id"].get("channelId", "")


def youtube_list_recent_video_ids(yt_key: str, channel_id: str, max_results: int = 50) -> List[str]:
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "channelId": channel_id,
        "order": "date",
        "type": "video",
        "maxResults": min(max_results, 50),
        "key": yt_key,
    }
    r = requests.get(url, params=params, timeout=15.0)
    r.raise_for_status()
    items = r.json().get("items", [])
    return [it["id"]["videoId"] for it in items if "id" in it and "videoId" in it["id"]]


def youtube_get_videos_details(yt_key: str, video_ids: List[str]) -> List[Dict[str, Any]]:
    if not video_ids:
        return []
    url = "https://www.googleapis.com/youtube/v3/videos"
    # Chunk to 50
    results = []
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i : i + 50]
        params = {"part": "snippet,contentDetails,statistics", "id": ",".join(chunk), "key": yt_key}
        r = requests.get(url, params=params, timeout=15.0)
        r.raise_for_status()
        items = r.json().get("items", [])
        results.extend(items)
    return results


def find_shorts_for_channel(yt_key: str, channel_id: str, shorts_needed: int = 5) -> List[Dict[str, Any]]:
    video_ids = youtube_list_recent_video_ids(yt_key, channel_id, max_results=50)
    if not video_ids:
        return []
    details = youtube_get_videos_details(yt_key, video_ids)
    shorts = []
    for v in details:
        dur = v.get("contentDetails", {}).get("duration", "")
        seconds = parse_iso8601_duration(dur)
        if seconds <= 60 and seconds > 0:
            shorts.append({
                "videoId": v.get("id"),
                "title": v.get("snippet", {}).get("title"),
                "duration_seconds": seconds,
                "publishedAt": v.get("snippet", {}).get("publishedAt"),
                "url": f"https://www.youtube.com/watch?v={v.get('id')}"
            })
        if len(shorts) >= shorts_needed:
            break
        print(shorts, v)
    return shorts


def main():
    parser = argparse.ArgumentParser(description="Find educational creators via Gemini and fetch shorts via YouTube API")
    parser.add_argument("--topic", type=str, default="programming", help="Topic to search creators for")
    parser.add_argument("--num-creators", type=int, default=5)
    parser.add_argument("--shorts-per-creator", type=int, default=5)
    parser.add_argument("--output", type=str, default="creators_shorts.json")
    parser.add_argument("--mock", action="store_true", help="Run in mock mode without Gemini/YT keys (returns sample data)")
    args = parser.parse_args()

    gemini_key = "AIzaSyAgfRz6Mx5Lv1liZmQbNEe4-FsL5NWdOLY"
    yt_key = "AIzaSyDlDocvLsGvxbZf37dmCDrkr__fEzQj7VA"

    if args.mock:
        # In mock mode Gemini would return channel ID strings
        creators = [
            "MOCK_CHANNEL_1",
            "MOCK_CHANNEL_2",
        ][: args.num_creators]
    else:
        if not gemini_key:
            print("ERROR: GEMINI_API_KEY env var is required (or use --mock)")
            return
        print(f"Calling Gemini to find {args.num_creators} creators (channel IDs) for topic '{args.topic}'...")
        try:
            creators = ["UC8butISFwT-WefMIGgVojng", "UCuSwb-7_vKz06N98g_XmS2Q","UCJ_ddn4P_tJq_fM_x-xS1_g", "UCfzlK8k6eQYwBfNghpnTqdA", "UCbiGfy_Q9ENF9FwPZ_m3tUA"] #call_gemini_for_creators(args.topic, args.num_creators, gemini_key)
        except Exception as e:
            print(f"Failed to call Gemini: {e}")
            return

    # Now for each creator, find channel and shorts
    results = []
    for c in creators:
        # Each item from Gemini should be a channel ID string
        channel_id = str(c)
        if args.mock:
            print(f"Processing mock channel id: {channel_id}")
            results.append({"name": channel_id, "description": "", "channelId": channel_id, "shorts": [
                {"videoId": "MOCK1", "title": f"{channel_id} - Short Sample", "duration_seconds": 45, "url": "https://youtu.be/mock"}
            ]})
            continue

        if not yt_key:
            print("ERROR: YOUTUBE_API_KEY env var is required for real mode")
            return

        print(f"Processing channel ID: {channel_id}")
        # fetch channel details for display
        try:
            snippet = youtube_get_channel_details(yt_key, channel_id)
            print(snippet)
            channel_title = snippet.get("title", "")
            channel_description = snippet.get("description", "")
        except Exception as e:
            print(f"  Failed to fetch channel details for {channel_id}: {e}")
            channel_title = ""
            channel_description = ""

        # get shorts
        try:
            shorts = find_shorts_for_channel(yt_key, channel_id, shorts_needed=args.shorts_per_creator)
        except Exception as e:
            print(f"  Error fetching shorts for channel {channel_id}: {e}")
            shorts = []

        results.append({"name": channel_title or channel_id, "description": channel_description, "channelId": channel_id, "shorts": shorts})

        # polite sleep to avoid quota issues
        time.sleep(1)

    # Save results
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f)

    print(f"Saved results to {args.output}")
    print(results)

if __name__ == "__main__":
    main()
