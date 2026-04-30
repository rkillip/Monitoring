"""
Watchlist & Schedule Overlay
Core logic for slotting a recruit's SG into your tournament leaderboards
and projecting finish position, team placement, and points.
"""

import pandas as pd
import json
import os
from dataclasses import dataclass, field, asdict
from typing import Optional

DATA_DIR = "data"
WATCHLIST_FILE = os.path.join(DATA_DIR, "watchlist.json")
os.makedirs(DATA_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class RecruitSGEntry:
    """One tournament's SG result for a recruit."""
    tournament_name: str   # e.g. "Ram Masters" — matched to your schedule
    sg: float              # Strokes Gained value
    actual_tournament: str = ""  # The real tournament they played (for reference)


@dataclass
class Recruit:
    """A player on your watchlist."""
    name: str
    school: str
    country: str                        # "USA" or country code for internationals
    points_avg: float = 0.0
    scoring_avg: float = 0.0
    ranking: str = ""
    notes: str = ""
    sg_data: list[RecruitSGEntry] = field(default_factory=list)

    def to_dict(self):
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, d):
        sg_entries = [RecruitSGEntry(**e) for e in d.pop("sg_data", [])]
        return cls(**d, sg_data=sg_entries)


# ---------------------------------------------------------------------------
# Watchlist Management
# ---------------------------------------------------------------------------

def load_watchlist() -> list[Recruit]:
    """Load watchlist from JSON file."""
    if not os.path.exists(WATCHLIST_FILE):
        return []
    with open(WATCHLIST_FILE, "r") as f:
        data = json.load(f)
    return [Recruit.from_dict(r) for r in data]


def save_watchlist(recruits: list[Recruit]):
    """Save watchlist to JSON file."""
    with open(WATCHLIST_FILE, "w") as f:
        json.dump([r.to_dict() for r in recruits], f, indent=2)
    print(f"Saved {len(recruits)} recruits to {WATCHLIST_FILE}")


def add_recruit(recruit: Recruit):
    """Add or update a recruit in the watchlist."""
    recruits = load_watchlist()
    # Replace if already exists
    recruits = [r for r in recruits if r.name != recruit.name]
    recruits.append(recruit)
    save_watchlist(recruits)
    print(f"Added/updated: {recruit.name} ({recruit.school})")


def remove_recruit(name: str):
    """Remove a recruit by name."""
    recruits = load_watchlist()
    recruits = [r for r in recruits if r.name != name]
    save_watchlist(recruits)
    print(f"Removed: {name}")


# ---------------------------------------------------------------------------
# Schedule Overlay & Projection
# ---------------------------------------------------------------------------

LBSU_TEAM = [
    "Alejandro De Castro",
    "Steen Zeman",
    "Krishnav Nikhil Chopraa",
    "Jaden Huggins",
    "Norwin Gohm",
    "Jack Cantlay",
    # Add/update your full roster here
]


def load_tournament_data() -> pd.DataFrame:
    """Load scraped tournament data."""
    path = os.path.join(DATA_DIR, "tournament_data.csv")
    if not os.path.exists(path):
        print("No tournament data found. Run scraper.py first.")
        return pd.DataFrame()
    return pd.read_csv(path)


def score_to_sg_approx(total_score: float, field_avg_score: float) -> float:
    """
    Approximate SG from score relative to field average.
    SG ≈ -(player_score - field_avg) / rounds
    This is a simplified version — actual Clippd SG also adjusts for SoF.
    """
    return -(total_score - field_avg_score)


def project_recruit_in_tournament(
    recruit: Recruit,
    tournament_name: str,
    tournament_df: pd.DataFrame
) -> Optional[dict]:
    """
    Given a recruit's SG for a tournament and the full field data,
    project where they would have finished.
    
    Returns a dict with finish, points, team placement, etc.
    """
    # Find recruit's SG entry for this tournament
    sg_entry = next(
        (e for e in recruit.sg_data if e.tournament_name == tournament_name),
        None
    )
    if sg_entry is None:
        return None

    recruit_sg = sg_entry.sg

    # Get field data for this tournament
    tourn_df = tournament_df[tournament_df["tournament_name"] == tournament_name].copy()
    if tourn_df.empty:
        print(f"  No data for tournament: {tournament_name}")
        return None

    # Approximate recruit's total score using field average
    # SG = -(score - field_avg), so score = field_avg - SG
    field_avg = tourn_df["total_score"].mean()
    recruit_score = field_avg - recruit_sg

    # Find where recruit slots into the leaderboard by score
    field_scores = sorted(tourn_df["total_score"].dropna().tolist())

    # Count how many players beat the recruit
    players_ahead = sum(1 for s in field_scores if s < recruit_score)
    finish_position = players_ahead + 1
    total_players = len(field_scores)

    # Interpolate points based on surrounding players
    # Find the closest actual score and use their points
    tourn_df["score_diff"] = abs(tourn_df["total_score"] - recruit_score)
    closest = tourn_df.nsmallest(2, "score_diff")
    projected_points = closest["points"].mean() if not closest.empty else None

    # Team placement — where among LBSU players would recruit finish?
    lbsu_df = tourn_df[tourn_df["player_name"].isin(LBSU_TEAM)].copy()
    lbsu_scores = sorted(lbsu_df["total_score"].dropna().tolist())
    lbsu_ahead = sum(1 for s in lbsu_scores if s < recruit_score)
    team_placement = lbsu_ahead + 1

    return {
        "tournament":       tournament_name,
        "recruit_sg":       recruit_sg,
        "recruit_score":    round(recruit_score, 1),
        "field_avg_score":  round(field_avg, 1),
        "finish":           f"T{finish_position}" if finish_position > 1 else "1",
        "finish_num":       finish_position,
        "total_players":    total_players,
        "projected_points": round(projected_points, 2) if projected_points else None,
        "team_placement":   team_placement,
        "lbsu_players_in_event": len(lbsu_scores),
    }


def run_schedule_overlay(recruit: Recruit) -> pd.DataFrame:
    """
    Run the full schedule overlay for a recruit.
    Projects their finish in every tournament where we have SG data.
    """
    tournament_df = load_tournament_data()
    if tournament_df.empty:
        return pd.DataFrame()

    results = []
    for sg_entry in recruit.sg_data:
        projection = project_recruit_in_tournament(
            recruit,
            sg_entry.tournament_name,
            tournament_df
        )
        if projection:
            results.append(projection)

    if not results:
        print(f"No projections available for {recruit.name}")
        return pd.DataFrame()

    df = pd.DataFrame(results)

    # Summary stats
    avg_points = df["projected_points"].mean()
    avg_finish = df["finish_num"].mean()
    avg_team_placement = df["team_placement"].mean()

    print(f"\n{'='*60}")
    print(f"Schedule Overlay: {recruit.name} ({recruit.school})")
    print(f"{'='*60}")
    print(df[["tournament", "recruit_sg", "finish", "projected_points", "team_placement"]].to_string(index=False))
    print(f"\n  Avg Points:         {avg_points:.2f}")
    print(f"  Avg Finish:         {avg_finish:.1f}")
    print(f"  Avg Team Placement: {avg_team_placement:.1f}")
    print(f"{'='*60}\n")

    return df


# ---------------------------------------------------------------------------
# Seed watchlist with your current prospects
# ---------------------------------------------------------------------------

def seed_initial_watchlist():
    """Seed with the players from your Excel model."""

    jorge = Recruit(
        name="Jorge Martin Sampedro",
        school="UTRGV",
        country="ESP",
        points_avg=37.92,
        scoring_avg=71.5,
        ranking="#400",
        notes="4 Top-10's, 2nd place in first college start, 8th at Maridoe, needs to develop but game is there",
        sg_data=[
            RecruitSGEntry("Ram Masters", 0.7),
            RecruitSGEntry("Tucker Intercollegiate", -3.82),
            RecruitSGEntry("Mark Simpson", -1.39),
            RecruitSGEntry("Bayonet", -4.59),
            RecruitSGEntry("Preserve", -0.86),
            RecruitSGEntry("Hawaii", -1.99),
            RecruitSGEntry("Lamkin", -0.99),
            RecruitSGEntry("Arizona", -1.85),
            RecruitSGEntry("The Goodwin", 1.99),
            RecruitSGEntry("Thunderbird", -1.98),
        ]
    )

    rasmus = Recruit(
        name="Rasmus Ditzinger",
        school="Fairfield",
        country="SWE",
        points_avg=41.06,
        scoring_avg=71.0,
        ranking="#331",
        notes="Two wins. Worst finish is 11th in 6 starts",
        sg_data=[
            RecruitSGEntry("Ram Masters", -0.33),
            RecruitSGEntry("Tucker Intercollegiate", -0.04),
            RecruitSGEntry("Mark Simpson", -0.95),
            RecruitSGEntry("Bayonet", -1.81),
            RecruitSGEntry("Preserve", -2.39),
            RecruitSGEntry("Hawaii", -1.31),
            RecruitSGEntry("Lamkin", 0.42),
            RecruitSGEntry("Arizona", 1.8),
        ]
    )

    alvaro = Recruit(
        name="Alvaro Pastor",
        school="Tarlton State",
        country="ESP",
        points_avg=55.86,
        scoring_avg=70.0,
        ranking="#129",
        notes="3 Top-15's in 5 events, 4 events under par. Impressive consistency thru 5 tournaments",
    )

    drew = Recruit(
        name="Drew Sykes",
        school="Coastal Carolina",
        country="ENG",
        points_avg=47.3,
        scoring_avg=70.4,
        ranking="#213",
        notes="Super consistent",
    )

    save_watchlist([jorge, rasmus, alvaro, drew])
    print("Watchlist seeded with initial prospects.")


if __name__ == "__main__":
    print("=== Watchlist & Overlay Tool ===\n")

    # Seed if no watchlist exists
    if not os.path.exists(WATCHLIST_FILE):
        print("No watchlist found. Seeding with initial prospects...\n")
        seed_initial_watchlist()

    # Show watchlist
    recruits = load_watchlist()
    print(f"Watchlist: {len(recruits)} recruits\n")
    for r in recruits:
        print(f"  {r.name} | {r.school} | {r.ranking} | Pts Avg: {r.points_avg}")

    # Run overlay for recruits who have SG data
    print("\n--- Running Schedule Overlays ---")
    tournament_df = load_tournament_data()
    if tournament_df.empty:
        print("\nNo tournament data yet — run scraper.py first to pull tournament data.")
        print("Once you have tournament data, run this script again to see projections.")
    else:
        for recruit in recruits:
            if recruit.sg_data:
                run_schedule_overlay(recruit)
