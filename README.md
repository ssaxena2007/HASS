# HASS: Doom scrolling…… with a purpose



A full-stack application that builds a local, categorized database of educational YouTube Shorts and provides an instant search interface.

## Project Overview

This project is designed to solve the problem of finding high-quality, educational short-form content on YouTube without the algorithm's distractions.

Instead of relying on live, expensive API calls, this app's backend is a three-stage data pipeline. This architecture ensures the final user-facing search is instant and free to operate.

## Here is the pipeline:

**Build Database (main.py)**
This Python script uses the YouTube Data API to fetch the entire video history from a curated whitelist of 15+ educational channels. It uses pagination to process all 19,000+ videos, then performs a duration check on each one to accurately filter the list down to 1,800+ actual shorts (60 seconds or less). The final list is saved as shorts_db.json.

Categorize Database (categorize_database.py)
This second script reads the shorts_db.json file. It sends the 1,800+ shorts to the Gemini API in batches to enrich the data. It calls the AI twice for each batch: once to assign a specific category (e.g., "Python", "System Design") and a second time to extract 3-5 relevant keywords from the title. The final, enriched list is saved as categorized_db.json.

**Serve API (test.py)**
This is the actual FastAPI server that the user interacts with. When it starts, it loads the final categorized_db.json file into memory. When a user sends a search query from the React app, this server performs an instant search against the local list, checking the user's query against the video title, its category, and its keywords

**Auth0 authentication (public/js/app.js)**
This script was used to query the authentication required for 
features such as custom curated channel lists.

Base html and JavaScript was used for the frontend.


