# Golf Recruit Overlay

Transfer portal analysis tool. Overlays a recruit's strokes gained data onto your schedule to project finish position, points, and team placement.

---

## Deploy to Streamlit Community Cloud (free)

1. Push this entire folder to a GitHub repository
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click **New app**
4. Connect your GitHub repo
5. Set **Main file path** to `app.py`
6. Click **Deploy**

That's it. You'll get a live URL in ~2 minutes.

---

## Run locally

```bash
pip install -r requirements.txt
python scraper.py        # pull tournament data first
python watchlist.py      # seed recruit data
streamlit run app.py
```

---

## File structure

```
golf_app/
├── app.py               # Streamlit web app
├── scraper.py           # Pulls tournament data from Clippd
├── watchlist.py         # Manages recruit watchlist + overlay logic
├── requirements.txt     # Python dependencies
├── .streamlit/
│   └── config.toml      # App theme
└── data/                # Auto-created on first run
    ├── tournament_data.csv
    └── watchlist.json
```

---

## Weekly update workflow

Every Wednesday/Thursday when rankings update:
1. Check Clippd for new tournament IDs
2. Add to `LBSU_TOURNAMENTS` in `scraper.py`
3. Run `python scraper.py`
4. Push to GitHub → Streamlit auto-redeploys

---

## Adding a new recruit

In `watchlist.py`, add a `Recruit` object with their SG data and run the script. Or manually edit `data/watchlist.json`.
