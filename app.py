import streamlit as st
import pandas as pd
import json
import os

st.set_page_config(page_title="Golf Recruit Tool", layout="wide", page_icon="⛳")

st.markdown("""
<style>
  /* ── Base ── */
  [data-testid="stAppViewContainer"] { background: #f7f7f7; }
  [data-testid="stSidebar"] { background: #ffffff; border-right: 1px solid #e0e0e0; }
  h1, h2, h3, h4 { font-weight: 500; color: #111; }

  /* ── Metric cards ── */
  .card {
    background: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 14px 16px;
  }
  .card-label {
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #888;
    margin-bottom: 4px;
  }
  .card-value { font-size: 26px; font-weight: 600; color: #111; }
  .card-value-red { font-size: 26px; font-weight: 600; color: #c0392b; }

  /* ── Row highlights ── */
  .recruit-row { color: #c0392b !important; font-weight: 600 !important; }

  /* ── Badges ── */
  .badge-red {
    background: #fdecea; color: #c0392b;
    padding: 2px 8px; border-radius: 12px;
    font-size: 11px; font-weight: 600;
  }
  .badge-grey {
    background: #f0f0f0; color: #444;
    padding: 2px 8px; border-radius: 12px;
    font-size: 11px;
  }

  /* ── Tabs ── */
  button[data-baseweb="tab"] { font-size: 13px !important; }

  /* ── Divider spacing ── */
  hr { margin: 12px 0 !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADERS
# ─────────────────────────────────────────────────────────────────────────────

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
    df = pd.read_csv(TOURNAMENT_FILE)
    df["total_score"] = pd.to_numeric(df["total_score"], errors="coerce")
    df["points"] = pd.to_numeric(df["points"], errors="coerce")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# CORE MODEL
# ─────────────────────────────────────────────────────────────────────────────

def sg_to_projection(field_df, sg_value):
    """
    Given a field leaderboard and a recruit's SG, return:
    - projected score (relative to field average)
    - projected finish position (integer)
    - projected points (interpolated from closest actual finishers)
    """
    field_avg = field_df["total_score"].mean()
    proj_score = field_avg - sg_value

    finish_pos = int((field_df["total_score"] < proj_score).sum()) + 1

    closest = field_df.iloc[
        (field_df["total_score"] - proj_score).abs().argsort()[:2]
    ]
    proj_pts = closest["points"].mean() if not closest.empty else None

    return round(proj_score, 1), finish_pos, proj_pts


def get_team_place(field_df, proj_score):
    """Where would a recruit place among LBSU players in this event?"""
    lbsu = field_df[field_df["player_name"].isin(LBSU_TEAM)]
    return int((lbsu["total_score"] < proj_score).sum()) + 1


# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("## ⛳ Golf Recruit Overlay Tool")
st.markdown("---")

tournament_df = load_tournament_data()
watchlist = load_watchlist()

if tournament_df.empty:
    st.error("No tournament data found. Run `scraper.py` first to pull data from Clippd.")
    st.stop()

tournaments = sorted(tournament_df["tournament_name"].dropna().unique().tolist())
all_players = sorted(tournament_df["player_name"].dropna().unique().tolist())
recruit_names = [r["name"] for r in watchlist]


# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────

tab1, tab2, tab3 = st.tabs([
    "🏆  Tournament leaderboard",
    "👤  Player profile",
    "📊  Schedule overlay",
])


# ═════════════════════════════════════════════════════════════════════════════
# TAB 1 — TOURNAMENT LEADERBOARD
# Recreates any scraped tournament leaderboard. Optionally slot a watchlist
# recruit into the field to see where they would have finished.
# ═════════════════════════════════════════════════════════════════════════════

with tab1:
    st.markdown("#### Tournament leaderboard")
    st.caption("Recreate any tournament from your schedule. Slot a recruit in to see their projected finish.")

    col_l, col_r = st.columns([2, 2])
    with col_l:
        selected_tourn = st.selectbox("Select tournament", tournaments, key="t1_tourn")
    with col_r:
        slot_recruit = st.selectbox(
            "Slot recruit into field (optional)",
            ["— None —"] + recruit_names,
            key="t1_recruit"
        )

    field_df = tournament_df[tournament_df["tournament_name"] == selected_tourn].copy()

    # ── Summary metrics ──────────────────────────────────────────────────────
    num_players = len(field_df)
    num_schools = field_df["school"].nunique()
    avg_score = field_df["total_score"].mean()

    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(f'<div class="card"><div class="card-label">Players</div><div class="card-value">{num_players}</div></div>', unsafe_allow_html=True)
    with m2:
        st.markdown(f'<div class="card"><div class="card-label">Schools</div><div class="card-value">{num_schools}</div></div>', unsafe_allow_html=True)
    with m3:
        avg_display = f"{avg_score:+.1f}" if avg_score != 0 else "E"
        st.markdown(f'<div class="card"><div class="card-label">Field avg score</div><div class="card-value">{avg_display}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Build display table ───────────────────────────────────────────────────
    display = field_df[["finish", "player_name", "school", "total_score", "points"]].copy()
    display.columns = ["Pos", "Player", "School", "Score", "Points"]
    display["Is LBSU"] = display["School"].isin(["Long Beach State"])
    display["Is Recruit"] = False

    # Slot recruit in if selected
    proj_row_info = None
    if slot_recruit != "— None —":
        r = next((x for x in watchlist if x["name"] == slot_recruit), None)
        if r:
            sg_entry = next(
                (e for e in r.get("sg_data", []) if e["tournament_name"] == selected_tourn),
                None
            )
            if sg_entry:
                proj_score, proj_finish, proj_pts = sg_to_projection(field_df, sg_entry["sg"])
                team_place = get_team_place(field_df, proj_score)

                new_row = pd.DataFrame([{
                    "Pos": f"T-{proj_finish}",
                    "Player": f"★ {slot_recruit}",
                    "School": r.get("school", ""),
                    "Score": proj_score,
                    "Points": round(proj_pts, 2) if proj_pts else None,
                    "Is LBSU": False,
                    "Is Recruit": True,
                }])
                display = pd.concat([display, new_row], ignore_index=True)
                display = display.sort_values("Score").reset_index(drop=True)
                proj_row_info = {"finish": proj_finish, "pts": proj_pts, "team_place": team_place, "sg": sg_entry["sg"]}
            else:
                st.info(f"No SG data entered for {slot_recruit} in {selected_tourn}.")

    # ── Projection banner ─────────────────────────────────────────────────────
    if proj_row_info:
        st.markdown(
            f'<div style="background:#fdecea;border:1px solid #e57373;border-radius:6px;padding:10px 14px;margin-bottom:8px;font-size:13px;color:#7f1d1d;">'
            f'<strong>{slot_recruit}</strong> projected finish: <strong>T-{proj_row_info["finish"]}</strong> · '
            f'<strong>{proj_row_info["pts"]:.2f} pts</strong> · '
            f'SG: <strong>{proj_row_info["sg"]:+.2f}</strong> · '
            f'Team placement: <strong>{proj_row_info["team_place"]} of {len([p for p in LBSU_TEAM])}</strong>'
            f'</div>',
            unsafe_allow_html=True
        )

    # ── Style and render ──────────────────────────────────────────────────────
    # Track which rows are recruits/LBSU before dropping helper columns
    is_recruit = display["Is Recruit"].tolist()
    is_lbsu = display["Is LBSU"].tolist()
    display_clean = display.drop(columns=["Is LBSU", "Is Recruit"])

    def style_leaderboard(row):
        idx = row.name
        if idx < len(is_recruit) and is_recruit[idx]:
            return ["color: #c0392b; font-weight: 700"] * len(row)
        elif idx < len(is_lbsu) and is_lbsu[idx]:
            return ["font-weight: 600; background-color: #f5f5f5"] * len(row)
        return [""] * len(row)

    display_styled = display_clean.style.apply(style_leaderboard, axis=1)

    st.dataframe(
        display_styled,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Score": st.column_config.NumberColumn(format="%.1f"),
            "Points": st.column_config.NumberColumn(format="%.2f"),
        }
    )


# ═════════════════════════════════════════════════════════════════════════════
# TAB 2 — PLAYER PROFILE
# Shows any player's full season results across all scraped tournaments:
# finish position, score, points earned, and SG (approximated from field data).
# ═════════════════════════════════════════════════════════════════════════════

with tab2:
    st.markdown("#### Player profile")
    st.caption("View any player's results, points earned, and strokes gained across all tournaments in the database.")

    search_col, _ = st.columns([2, 2])
    with search_col:
        selected_player = st.selectbox("Search player", all_players, key="t2_player")

    player_df = tournament_df[tournament_df["player_name"] == selected_player].copy()

    if player_df.empty:
        st.info("No data found for this player.")
    else:
        school = player_df["school"].mode()[0] if not player_df["school"].isna().all() else "—"
        ranking = player_df["ranking"].dropna().iloc[0] if not player_df["ranking"].isna().all() else "—"

        # ── Header ────────────────────────────────────────────────────────────
        st.markdown(f"**{selected_player}** · {school} · {ranking}")

        # ── Metrics ───────────────────────────────────────────────────────────
        avg_pts = player_df["points"].mean()
        avg_score = player_df["total_score"].mean()
        num_events = len(player_df)

        # Approximate SG from score vs field average per tournament
        sg_list = []
        for _, row in player_df.iterrows():
            t_df = tournament_df[tournament_df["tournament_name"] == row["tournament_name"]]
            if not t_df.empty and pd.notna(row["total_score"]):
                field_avg = t_df["total_score"].mean()
                sg_approx = -(row["total_score"] - field_avg)
                sg_list.append(sg_approx)

        avg_sg = sum(sg_list) / len(sg_list) if sg_list else None

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(f'<div class="card"><div class="card-label">Events</div><div class="card-value">{num_events}</div></div>', unsafe_allow_html=True)
        with m2:
            st.markdown(f'<div class="card"><div class="card-label">Avg points</div><div class="card-value-red">{avg_pts:.2f}</div></div>', unsafe_allow_html=True)
        with m3:
            score_disp = f"{avg_score:+.1f}" if avg_score != 0 else "E"
            st.markdown(f'<div class="card"><div class="card-label">Avg score</div><div class="card-value">{score_disp}</div></div>', unsafe_allow_html=True)
        with m4:
            sg_disp = f"{avg_sg:+.2f}" if avg_sg is not None else "—"
            st.markdown(f'<div class="card"><div class="card-label">Avg SG (approx)</div><div class="card-value">{sg_disp}</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Results table ─────────────────────────────────────────────────────
        profile_rows = []
        for i, (_, row) in enumerate(player_df.iterrows()):
            t_df = tournament_df[tournament_df["tournament_name"] == row["tournament_name"]]
            sg_val = sg_list[i] if i < len(sg_list) else None
            profile_rows.append({
                "Tournament": row["tournament_name"],
                "Finish": row["finish"],
                "Score": row["total_score"],
                "Points": row["points"],
                "SG (approx)": round(sg_val, 2) if sg_val is not None else None,
            })

        profile_df = pd.DataFrame(profile_rows)

        # Totals row
        totals = pd.DataFrame([{
            "Tournament": "Season avg",
            "Finish": "—",
            "Score": round(avg_score, 1),
            "Points": round(avg_pts, 2),
            "SG (approx)": round(avg_sg, 2) if avg_sg is not None else None,
        }])
        profile_display = pd.concat([profile_df, totals], ignore_index=True)

        def style_profile(row):
            if row["Tournament"] == "Season avg":
                return ["font-weight: 600; background-color: #f5f5f5"] * len(row)
            return [""] * len(row)

        st.dataframe(
            profile_display.style.apply(style_profile, axis=1),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Score": st.column_config.NumberColumn(format="%.1f"),
                "Points": st.column_config.NumberColumn(format="%.2f"),
                "SG (approx)": st.column_config.NumberColumn(format="%.2f"),
            }
        )

        st.caption("SG is approximated as -(player score − field average). Clippd's official SG also adjusts for strength of field.")

        # ── Points bar chart ──────────────────────────────────────────────────
        st.markdown("**Points by event**")
        chart_df = profile_df[["Tournament", "Points"]].dropna()
        st.bar_chart(chart_df.set_index("Tournament"), color="#c0392b")


# ═════════════════════════════════════════════════════════════════════════════
# TAB 3 — SCHEDULE OVERLAY
# Takes a watchlist recruit's SG from each week of their actual season,
# and projects how they would have finished in your equivalent tournament
# that same week — showing finish, points, and team placement.
# ═════════════════════════════════════════════════════════════════════════════

with tab3:
    st.markdown("#### Schedule overlay")
    st.caption("Take a recruit's SG from their actual season and project how they would have finished in your equivalent tournaments.")

    if not watchlist:
        st.warning("No recruits in watchlist. Run `watchlist.py` to seed data.")
        st.stop()

    sidebar_col, _ = st.columns([2, 2])
    with sidebar_col:
        selected_recruit_name = st.selectbox("Select recruit", recruit_names, key="t3_recruit")

    recruit = next(r for r in watchlist if r["name"] == selected_recruit_name)
    sg_data = recruit.get("sg_data", [])

    if not sg_data:
        st.info("No SG data entered for this recruit. Add their tournament SG values in `watchlist.py`.")
    else:
        # ── Header ────────────────────────────────────────────────────────────
        col_a, col_b = st.columns([3, 1])
        with col_a:
            st.markdown(f"**{recruit['name']}** · {recruit.get('school','—')} · {recruit.get('country','—')} · {recruit.get('ranking','—')}")
            if recruit.get("notes"):
                st.caption(recruit["notes"])

        # ── Run projections ───────────────────────────────────────────────────
        rows = []
        for entry in sg_data:
            t_name = entry["tournament_name"]
            sg = entry["sg"]

            t_df = tournament_df[tournament_df["tournament_name"] == t_name].copy()
            if t_df.empty:
                rows.append({
                    "Tournament": t_name,
                    "Their SG": sg,
                    "Proj. Score": "—",
                    "Proj. Finish": "No data",
                    "Proj. Points": None,
                    "Team Place": "—",
                })
                continue

            proj_score, proj_finish, proj_pts = sg_to_projection(t_df, sg)
            team_place = get_team_place(t_df, proj_score)

            rows.append({
                "Tournament": t_name,
                "Their SG": sg,
                "Proj. Score": proj_score,
                "Proj. Finish": f"T-{proj_finish}",
                "Proj. Points": round(proj_pts, 2) if proj_pts else None,
                "Team Place": f"{team_place} of {len(LBSU_TEAM)}",
            })

        overlay_df = pd.DataFrame(rows)

        # ── Summary metrics ───────────────────────────────────────────────────
        valid = overlay_df[overlay_df["Proj. Points"].notna()]
        avg_pts_proj = valid["Proj. Points"].mean() if not valid.empty else None
        avg_sg = overlay_df["Their SG"].mean()
        events_with_data = len(valid)
        actual_pts_avg = recruit.get("points_avg", None)

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            val = f"{avg_pts_proj:.2f}" if avg_pts_proj else "—"
            st.markdown(f'<div class="card"><div class="card-label">Proj. avg points</div><div class="card-value-red">{val}</div></div>', unsafe_allow_html=True)
        with m2:
            val = f"{actual_pts_avg:.2f}" if actual_pts_avg else "—"
            st.markdown(f'<div class="card"><div class="card-label">Actual pts avg</div><div class="card-value">{val}</div></div>', unsafe_allow_html=True)
        with m3:
            sg_disp = f"{avg_sg:+.2f}"
            st.markdown(f'<div class="card"><div class="card-label">Avg SG (their events)</div><div class="card-value">{sg_disp}</div></div>', unsafe_allow_html=True)
        with m4:
            st.markdown(f'<div class="card"><div class="card-label">Events matched</div><div class="card-value">{events_with_data}</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Overlay table ─────────────────────────────────────────────────────
        def style_overlay(row):
            if row["Tournament"] == "Season avg":
                return ["font-weight: 600; background-color: #f5f5f5"] * len(row)
            if pd.notna(row.get("Proj. Points")) and row["Proj. Points"] >= 65:
                return ["color: #c0392b"] * len(row)
            return [""] * len(row)

        # Add avg row
        avg_row = pd.DataFrame([{
            "Tournament": "Season avg",
            "Their SG": round(avg_sg, 2),
            "Proj. Score": "—",
            "Proj. Finish": "—",
            "Proj. Points": round(avg_pts_proj, 2) if avg_pts_proj else None,
            "Team Place": "—",
        }])
        display_overlay = pd.concat([overlay_df, avg_row], ignore_index=True)

        st.dataframe(
            display_overlay.style.apply(style_overlay, axis=1),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Their SG": st.column_config.NumberColumn(format="%.2f"),
                "Proj. Points": st.column_config.NumberColumn(format="%.2f"),
            }
        )

        # ── Points chart ──────────────────────────────────────────────────────
        st.markdown("**Projected points by tournament**")
        chart_data = valid[["Tournament", "Proj. Points"]].set_index("Tournament")
        st.bar_chart(chart_data, color="#c0392b")

        st.caption(
            "Projection method: Recruit's SG for that week is slotted into your tournament's actual field. "
            "Projected score = field average − SG. Points interpolated from nearest finishers."
        )
