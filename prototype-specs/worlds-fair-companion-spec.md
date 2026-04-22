# World's Fair Companion Specification  

## Project Overview  
**World's Fair Companion** is a purely offline-first web application designed for attendees of the AI Engineer World's Fair (June 29 – July 2, Moscone Center, SF). The application operates entirely without internet connectivity during event usage, bootstrapped during setup by downloading public schedule data onto a local server. All features are implemented with local processing only, ensuring complete data sovereignty and zero cloud dependencies. The app will run on a local machine or private Wi-Fi hotspot, with all data stored in locally accessible file formats.  

---

## Core Features  
### 1. Schedule Search & Filtering  
- **Cmd+K Command Palette** for real-time search of talks by keywords, technology stacks (e.g., "RAG pipelines", "local model orchestration"), and speakers.  
- Results displayed as a clean, dark-themed list with metadata (time, room, description).  
- All data queries handled via local SQLite database—no external API calls or cloud storage.  

### 2. QR-Based Networking  
- **Digital Badge UI** resembling a terminal console: displays name, GitHub handle, and project description in ASCII-style text.  
- **QR Code Generation** via client-side JavaScript (using `qrcode.js`) to encode user’s badge data.  
- **QR Scanning** via webcam or manual input: decodes JSON data from QR codes and stores contacts in browser `localStorage`.  

### 3. Offline Expo Floor Map  
- **Grid-Based SVG Map** of expo booths with no external mapping services (e.g., Google Maps). Booths marked as coordinates on a simple grid layout.  
- **Pinned Booths**: Users can select favorite booths to highlight on the map.  
- **Pathfinding**: Minimalist route calculation between pinned booths using Dijkstra’s algorithm in client-side JavaScript (optimized for grid-based obstacles).  

---

## Technical Specifications  
### Architecture & Tech Stack  
- **Frontend**: Plain HTML/CSS/JavaScript (no frameworks), with lightweight CSS for terminal-style styling (Bulma minimal template).  
- **Backend**: Python-based local HTTP server (`uvicorn` + `FastAPI`) to serve static assets and handle data queries.  
- **Data Storage**:  
  - `schedule.db`: SQLite database for talk schedules, speakers, and rooms.  
  - `expo.db`: SQLite database for booth locations (x/y coordinates, category).  
  - Browser `localStorage` for user contacts (QR-scanned data) and UI preferences (dark mode, pinned booths).  

### Data Models  
#### Talks Table (`schedule.db`)  
| Field          | Type    | Description                          |  
|----------------|---------|--------------------------------------|  
| `id`           | INTEGER | Primary key                          |  
| `title`        | TEXT    | Talk title                           |  
| `start_time`   | TEXT    | ISO8601 format (e.g., "2026-06-29 14:00") |  
| `end_time`     | TEXT    | ISO8601 format                       |  
| `room`         | TEXT    | Conference room (e.g., "Moscone West 201") |  
| `speakers`     | TEXT    | Comma-separated list of speaker names |  
| `tags`         | TEXT    | Comma-separated tech stacks (e.g., "RAG,local-models") |  

#### Booths Table (`expo.db`)  
| Field      | Type    | Description                          |  
|------------|---------|--------------------------------------|  
| `id`       | INTEGER | Primary key                          |  
| `name`     | TEXT    | Booth name (e.g., "Neuralink Demo")  |  
| `x`        | INTEGER | X-coordinate on grid (0–100)         |  
| `y`        | INTEGER | Y-coordinate on grid (0–100)         |  
| `category` | TEXT    | Booth type (e.g., "Hardware", "Software") |  

### Implementation Tasks  
#### Setup & Data Loading  
1. Initialize project directory structure:  
   ```bash  
   mkdir -p /home/admin/code/worlds-fair-companion/{frontend,backend,data}  
   cd /home/admin/code/worlds-fair-companion  
   git init  
   ```  

2. Preload public conference data into SQLite:  
   - Scrape official event data into CSV: `scripts/fetch_data.py`  
   - Convert CSV → SQLite schema:  
     ```python  
     # data_schema.py  
     import sqlite3  
     conn = sqlite3.connect('data/schedule.db')  
     c = conn.cursor()  
     c.execute('''CREATE TABLE talks (id INTEGER PRIMARY KEY, title TEXT, start_time TEXT, end_time TEXT, room TEXT, speakers TEXT, tags TEXT)''')  
     # Load CSV data...  
     ```  

3. Build FastAPI backend:  
   - Create `backend/main.py`:  
     ```python  
     from fastapi import FastAPI  
     app = FastAPI()  
     @app.get("/api/schedule")  
     def search_schedule(query: str = ""):  
         # Query SQLite DB for talks matching query  
         return {"results": [.\..]}  

     @app.get("/api/booths")  
     def get_booths():  
         # Return booth coordinates from expo.db  
         return {"booths": [...]}  
     ```  

#### Frontend Implementation  
4. **Command Palette UI**:  
   - Create `frontend/index.html` with a hidden modal triggered by `Ctrl+K`/`Cmd+K`  
   - Handle input with JavaScript:  
     ```javascript  
     document.addEventListener('DOMContentLoaded', () => {  
       window.addEventListener('keydown', (e) => {  
         if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {  
           document.getElementById('search-modal').classList.remove('hidden');  
         }  
       });  
     });  
     ```  

5. **QR Badge Generator**:  
   - Use `qrcode.js` library in frontend for client-side QR code generation:  
     ```javascript  
     const qr = new QRCode(document.getElementById("qr-code"), {  
       text: JSON.stringify({name: "John", github: "johnny", project: "RAG pipeline"}),  
       width: 128,  
       height: 128  
     });  
     ```  

6. **Expo Map Pathfinding**:  
   - Load booth coordinates from API, render as SVG in `frontend/expo-map.html`:  
     ```svg  
     <svg viewBox="0 0 100 100">  
       <circle cx="30" cy="40" r="2" fill="red" id="booth-1"/>  
       <path d="M 30,40 L 60,50" stroke="blue" stroke-width="1"/>  
     </svg>  
     ```  
   - Implement pathfinding logic in JavaScript:  
     ```javascript  
     function dijkstra(start, end, nodes) {  
       // Find shortest path between grid points  
       return path;  
     }  
     ```  

#### Validation & Air-Gap Compliance  
7. Test the app in disconnected mode:  
   - Run `uvicorn backend.main:app --port 8000`  
   - Confirm no external network calls during operation:  
     ```bash  
     # Verify no outbound connections  
     sudo tcpdump -i any -nn port not 22 and port not 8000  
     ```  

---

## Constraints & Assumptions  
- ✅ **No Internet Connectivity During Event**: All data pre-loaded before deployment; no cloud services or remote APIs.  
- ✅ **Zero Cloud Dependencies**: Strictly local data storage (SQLite) and client-side processing.  
- ⚠️ **QR Scanning Limitation**: Camera-based scanning requires user permission (handled in browser).  
- ⚠️ **Pathfinding Simplicity**: Grid-based algorithm assumes straight-line paths—no complex obstacle avoidance.  

---

## Next Steps  
Please choose your action:  
1. **Generate Prototype**  
   *Automatically build the app from these specs using Plandex. This includes:*  
   - Initializing the project directory  
   - Preloading schedule data  
   - Generating frontend/backend code  
   - Setting up the FastAPI server  
   *Expected time: 15–20 minutes*  

2. **Edit Specs**  
   *I want to revise the specifications before building (e.g., adjust data models, add features)*  

3. **Done for now**  
   *Save the specs and close this session*  

Your choice:  
[Option 1/2/3]