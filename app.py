import streamlit as st
import pandas as pd
import json
import os

st.set_page_config(page_title="Recruit Overlay", layout="wide")

st.markdown("""
<style>
  [data-testid="stAppViewContainer"] { background: #f9f9f9; }
  [data-testid="stSidebar"] { background: #ffffff; border-right: 1px solid #e5e5e5; }
  h1, h2, h3 { font-weight: 500; }
  .metric-label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; color: #888; }
  .metric-value { font-size: 28px; font-weight: 500; color: #111; }
  .metric-value-red { font-size: 28px; font-weight: 500; color: #c0392b; }
  .recruit-tag { background: #fdecea; color: #c0392b; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: 500; }
  .lbsu-tag { background: #f0f0f0; color: #333; padding: 2px 8px; border-radius: 12px; font-size: 12px; }
</style>
""", unsafe_allow_html=True)

DATA_DIR = "data"
WATCHLIST_FILE = os.path.join(DATA_DIR, "watchlist.json")
TOURNAMENT_FILE = os.path.join(DATA_DIR, "tournament_data.csv")

LBSU_TEAM = [
    "Alejandro De Castro",
    "Steen Zeman",
    "Krishnav Nikhil Chopraa",
    "Jaden Huggins",
    "Norwin Gohm",
    "Jack Cantlay",
]


@st.cache_data
def load_watchlist():
    if not os.path.exists(WATCHLIST_FILE):
        return []
    with open(WATCHLIST_FILE) as f:
        return json.load(f)


@st.cache_data
def load_tournament_data():
    if not os.path.exists(TOURNAMENT_FILE):
        return pd.DataFrame()
    return pd.read_csv(TOURNAMENT_FILE)


def project_recruit(recruit, tournament_df):
    """Project recruit across all tournaments using their SG data."""
    rows = []
    for entry in recruit.get("sg_data", []):
        t_name = entry["tournament_name"]
        sg = entry["sg"]
        t_df = tournament_df[tournament_df["tournament_name"] == t_name].copy()
        if t_df.empty:
            continue
        field_avg = t_df["total_score"].mean()
        recruit_score = round(field_avg - sg, 1)
        players_ahead = int((t_df["total_score"] < recruit_score).sum())
        finish = players_ahead + 1
        t_df["diff"] = abs(t_df["total_score"] - recruit_score)
        closest = t_df.nsmallest(2, "diff")
        proj_pts = round(closest["points"].mean(), 2) if not closest.empty else None
        lbsu_df = t_df[t_df["player_name"].isin(LBSU_TEAM)]
        team_place = int((lbsu_df["total_score"] < recruit_score).sum()) + 1
        rows.append({
            "Tournament": t_name,
            "SG": sg,
            "Proj. Score": int(recruit_score),
            "Finish": f"T-{finish}",
            "Points": proj_pts,
            "Team Place": team_place,
        })
    return pd.DataFrame(rows)


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Watchlist")
    watchlist = load_watchlist()
    if not watchlist:
        st.info("No recruits found. Run `watchlist.py` to seed data.")
        st.stop()

    names = [r["name"] for r in watchlist]
    selected_name = st.radio("", names, label_visibility="collapsed")
    recruit = next(r for r in watchlist if r["name"] == selected_name)

    st.divider()
    st.markdown(f"**{recruit['school']}**")
    st.markdown(f"{recruit.get('country','')} · {recruit.get('ranking','')}")
    st.caption(recruit.get("notes", ""))


# ── Main area ──────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["Schedule overlay", "Tournament leaderboard"])

tournament_df = load_tournament_data()

with tab1:
    st.markdown(f"#### {recruit['name']}")

    if tournament_df.empty:
        st.warning("No tournament data found. Run `scraper.py` first.")
    else:
        proj_df = project_recruit(recruit, tournament_df)

        if proj_df.empty:
            st.info("No SG data entered for this recruit yet.")
        else:
            avg_pts = proj_df["Points"].mean()
            avg_finish = proj_df["Finish"].str.replace("T-", "").astype(float).mean()
            avg_team = proj_df["Team Place"].mean()
            events = len(proj_df)

            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown('<div class="metric-label">Avg points</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="metric-value-red">{avg_pts:.1f}</div>', unsafe_allow_html=True)
            with c2:
                st.markdown('<div class="metric-label">Avg finish</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="metric-value">T-{avg_finish:.0f}</div>', unsafe_allow_html=True)
            with c3:
                st.markdown('<div class="metric-label">Avg team place</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="metric-value">{avg_team:.1f}</div>', unsafe_allow_html=True)
            with c4:
                st.markdown('<div class="metric-label">Events</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="metric-value">{events}</div>', unsafe_allow_html=True)

            st.divider()
            st.dataframe(
                proj_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "SG": st.column_config.NumberColumn(format="%.2f"),
                    "Points": st.column_config.NumberColumn(format="%.1f"),
                }
            )

with tab2:
    if tournament_df.empty:
        st.warning("No tournament data found. Run `scraper.py` first.")
    else:
        tournaments = tournament_df["tournament_name"].unique().tolist()
        col1, col2 = st.columns([2, 2])
        with col1:
            selected_tourn = st.selectbox("Tournament", tournaments)
        with col2:
            slot_in = st.selectbox("Slot recruit into leaderboard", ["None"] + names)

        field = tournament_df[tournament_df["tournament_name"] == selected_tourn].copy()
        field = field[["finish", "player_name", "school", "total_score", "points"]].copy()
        field.columns = ["Pos", "Player", "School", "Score", "Points"]

        if slot_in != "None":
            r = next(x for x in watchlist if x["name"] == slot_in)
            sg_entry = next(
                (e for e in r.get("sg_data", []) if e["tournament_name"] == selected_tourn),
                None
            )
            if sg_entry:
                field_avg = field["Score"].mean()
                recruit_score = round(field_avg - sg_entry["sg"], 1)
                field_ahead = (field["Score"] < recruit_score).sum()
                closest = field.iloc[(field["Score"] - recruit_score).abs().argsort()[:2]]
                proj_pts = round(closest["Points"].mean(), 1)
                new_row = pd.DataFrame([{
                    "Pos": f"T-{int(field_ahead)+1}",
                    "Player": f"★ {slot_in}",
                    "School": r["school"],
                    "Score": recruit_score,
                    "Points": proj_pts,
                }])
                field = pd.concat([field, new_row], ignore_index=True)
                field = field.sort_values("Score").reset_index(drop=True)

        def highlight_recruit(row):
            if str(row.get("Player", "")).startswith("★"):
                return ["color: #c0392b; font-weight: 600"] * len(row)
            elif row.get("School") in ["Long Beach State", "LBSU"]:
                return ["font-weight: 600"] * len(row)
            return [""] * len(row)

        styled = field.style.apply(highlight_recruit, axis=1)
        st.dataframe(styled, use_container_width=True, hide_index=True)
