import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from contextlib import asynccontextmanager

# --- Database File ---
SHORTS_DB_FILE = "categorized_db.json"
SHORTS_DATABASE = []

# --- Load Database on Startup ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Server startup: Loading database into memory...")
    try:
        with open(SHORTS_DB_FILE, "r", encoding="utf-8") as f:
            global SHORTS_DATABASE
            SHORTS_DATABASE = json.load(f)
        print(f"✅ Successfully loaded {len(SHORTS_DATABASE)} categorized shorts from {SHORTS_DB_FILE}")
    except FileNotFoundError:
        print(f"❌ ERROR: Database file '{SHORTS_DB_FILE}' not found.")
        print("Please run `python build_database.py` and `python categorize_database.py` first.")
    except Exception as e:
        print(f"❌ ERROR: Could not load database: {e}")
    
    yield  # Your app runs here
    
    print("Server shutdown complete.")

# --- Pass the lifespan function to the app ---
app = FastAPI(lifespan=lifespan)

# --- Add CORS Middleware ---
origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Endpoint (Smart, Fast, Free Search) ---
@app.get("/api/search")
def search_shorts(query: str):
    """
    Searches the in-memory database by title, category, AND keywords.
    This search is fast and costs 0 API quota.
    """
    if not SHORTS_DATABASE:
        return {"results": []} # Return empty list if DB isn't loaded

    query_lower = query.lower()
    
    # --- THIS IS THE CORRECTED LOGIC ---
    filtered_results = []
    
    if not query_lower: # If search is empty, return everything
        filtered_results = SHORTS_DATABASE
    else:
        for video in SHORTS_DATABASE:
            title_lower = video["snippet"]["title"].lower()
            category_lower = video.get("category", "Other").lower()
            keywords_lower = " ".join(video.get("keywords", [])).lower()

            if (query_lower in title_lower or 
                query_lower == category_lower or 
                query_lower in keywords_lower):
                
                filtered_results.append(video)
    
    # --- HERE IS YOUR NEW FEATURE (Backend Log) ---
    print(f"Search for '{query}' found {len(filtered_results)} results.")
            
    # Return the *FILTERED* list, not the whole database
    return {"results": filtered_results}

# --- Main entry point to run the server ---
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)