"""
Clippd Scoreboard Scraper
Pulls tournament leaderboard data including player, school, score, and points.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import os
import re
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)


def get_tournament_leaderboard(tournament_id: int) -> pd.DataFrame:
    """
    Scrapes the player leaderboard for a given tournament ID.
    URL format: https://scoreboard.clippd.com/tournaments/{id}/scoring/player
    Returns a DataFrame with all players, scores, and points.
    """
    url = f"https://scoreboard.clippd.com/tournaments/{tournament_id}/scoring/player"
    print(f"  Fetching: {url}")

    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    # Extract tournament name from page title/header
    tournament_name = "Unknown Tournament"
    h1 = soup.find("h1")
    if h1:
        tournament_name = h1.get_text(strip=True)

    # Find the leaderboard table
    table = soup.find("table")
    if not table:
        print(f"  WARNING: No table found for tournament {tournament_id}")
        return pd.DataFrame()

    rows = []
    for tr in table.find_all("tr")[1:]:  # skip header row
        cols = tr.find_all("td")
        if len(cols) < 9:
            continue

        finish      = cols[0].get_text(strip=True)
        move        = cols[1].get_text(strip=True)
        player_cell = cols[2].get_text(separator="|", strip=True)
        ranking     = cols[3].get_text(strip=True)
        total       = cols[4].get_text(strip=True)
        thru        = cols[5].get_text(strip=True)
        rd1         = cols[6].get_text(strip=True)
        rd2         = cols[7].get_text(strip=True)
        rd3         = cols[8].get_text(strip=True) if len(cols) > 8 else ""
        pts_raw     = cols[-1].get_text(strip=True)

        # Player cell format: "School|Player Name|School|#Rank" or similar
        parts = [p for p in player_cell.split("|") if p.strip()]
        player_name = ""
        school = ""
        if len(parts) >= 2:
            # Usually: School, Player Name, School, Rank
            school = parts[0]
            player_name = parts[1]
        elif len(parts) == 1:
            player_name = parts[0]

        # Clean up score values
        def clean_score(val):
            val = val.strip()
            if val in ["E", "", "-"]:
                return 0
            try:
                return int(val)
            except ValueError:
                return None

        pts = None
        try:
            pts = float(pts_raw)
        except ValueError:
            pass

        rows.append({
            "tournament_id":   tournament_id,
            "tournament_name": tournament_name,
            "finish":          finish,
            "player_name":     player_name,
            "school":          school,
            "ranking":         ranking,
            "total_score":     clean_score(total),
            "rd1":             clean_score(rd1),
            "rd2":             clean_score(rd2),
            "rd3":             clean_score(rd3),
            "points":          pts,
            "scraped_at":      datetime.now().isoformat()
        })

    df = pd.DataFrame(rows)
    print(f"  Found {len(df)} players in '{tournament_name}'")
    return df


def scrape_tournaments(tournament_ids: list) -> pd.DataFrame:
    """Scrape multiple tournaments and return combined DataFrame."""
    all_dfs = []
    for tid in tournament_ids:
        print(f"\nScraping tournament {tid}...")
        try:
            df = get_tournament_leaderboard(tid)
            if not df.empty:
                all_dfs.append(df)
        except Exception as e:
            print(f"  ERROR scraping tournament {tid}: {e}")

    if not all_dfs:
        return pd.DataFrame()

    combined = pd.concat(all_dfs, ignore_index=True)
    return combined


def save_tournament_data(df: pd.DataFrame, filename: str = "tournament_data.csv"):
    """Save scraped data to CSV."""
    path = os.path.join(DATA_DIR, filename)
    df.to_csv(path, index=False)
    print(f"\nSaved {len(df)} rows to {path}")
    return path


if __name__ == "__main__":
    # Long Beach State 2024-25 tournament IDs
    # Add/update these as needed each season
    LBSU_TOURNAMENTS = {
        238883: "Thunderbird Collegiate",
        # 240002: "Ram Masters Invitational",
        # 239974: "William H. Tucker Intercollegiate",
        # 238697: "Mark Simpson Colorado Invitational",
        # 239901: "Saint Mary's Invitational",
        # 238648: "The Preserve Golf Club Collegiate",
        # 238577: "John A. Burns Intercollegiate",
        # 238773: "R.E. Lamkin Invitational",
        # 239371: "Arizona Thunderbirds Intercollegiate",
        # 239221: "The Goodwin",
    }

    print("=== Clippd Scoreboard Scraper ===")
    print(f"Scraping {len(LBSU_TOURNAMENTS)} tournaments...\n")

    df = scrape_tournaments(list(LBSU_TOURNAMENTS.keys()))

    if not df.empty:
        save_tournament_data(df)
        print("\nSample output:")
        print(df[["tournament_name", "finish", "player_name", "school", "total_score", "points"]].head(10).to_string(index=False))
    else:
        print("No data scraped.")
