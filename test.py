import json, random, time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from contextlib import asynccontextmanager

# --- Database File ---
SHORTS_DB_FILE = "categorized_db.json"
SHORTS_DATABASE = []
SHORTS_DB_SIZE = -1

# --- Load Database on Startup ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Server startup: Loading database into memory...")
    try:
        with open(SHORTS_DB_FILE, "r", encoding="utf-8") as f:
            global SHORTS_DATABASE, SHORTS_DB_SIZE
            SHORTS_DATABASE = json.load(f)
            random.shuffle(SHORTS_DATABASE)
            SHORTS_DB_SIZE = len(SHORTS_DATABASE)
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
def search_shorts(query: str="[]", count: int =10):
    """
    Searches the in-memory database by title, category, AND keywords.
    This search is fast and costs 0 API quota.
    """
    start = time.time()
    query = eval(query)
    if count == -1:
        count = SHORTS_DB_SIZE
    if not SHORTS_DATABASE:
        print("FAILED", SHORTS_DATABASE)
        return {"results": []} # Return empty list if DB isn't loaded
     
    # --- THIS IS THE CORRECTED LOGIC ---
    filtered_results = []
    
    if len(query): # If search is empty, return everything
        filtered_results = [random.choice(SHORTS_DATABASE) for _ in range(count)]
    else:
        query_lower = [q.lower() for q in query]
        index = 0
        while index < SHORTS_DB_SIZE and len(filtered_results) < count:
            title_lower = SHORTS_DATABASE[index]["snippet"]["title"].lower()
            category_lower = SHORTS_DATABASE[index].get("category", "Other").lower()
            keywords_lower = " ".join(SHORTS_DATABASE[index].get("keywords", [])).lower()
            q_low = random.choice(query_lower)
            if (q_low in title_lower or 
                q_low == category_lower or 
                q_low in keywords_lower):
                
                filtered_results.append(SHORTS_DATABASE[index])
            index+=1
    # --- HERE IS YOUR NEW FEATURE (Backend Log) ---
    print(f"Search for '{query}' found {len(filtered_results)} results.")
            
    # Return the *FILTERED* list, not the whole database
    shuffle()
    return {"results": filtered_results, "time_taken": time.time()-start}


@app.get("/api/randomize")
def shuffle():
    global SHORTS_DATABASE
    start = time.time()
    random.shuffle(SHORTS_DATABASE)
    return (time.time()-start, time.time(), start)
# --- Main entry point to run the server ---
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)