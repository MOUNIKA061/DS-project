# GeoVerse — Time-Series Data Structures Demo

This small project simulates a location-tracking backend to demonstrate internal data structures:
- Hash table (phone -> userID)
- Doubly linked list (timeline)
- AVL tree (timestamp index)
- Queue (offline buffer)

Quick start (Windows PowerShell):

1. Create a virtual env and install dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Run the app

```powershell
python app.py
```

3. Open http://127.0.0.1:5000

Notes:
- This is a prototype. User data is stored in `storage.json` (password hashes only), data structures live in memory.
- Use the dashboard to generate online/offline points and sync the offline queue.
