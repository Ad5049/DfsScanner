import streamlit as st
import pandas as pd
import numpy as np
import requests

# Page Config
st.set_page_config(page_title="Straight Bet +EV Sportsbook Scanner", layout="wide")

st.title("🎯 Straight Bet +EV Sportsbook Scanner")
st.markdown("Scanning individual player props and game lines for **DraftKings, Hard Rock, Fliff, Novig, ProphetX, Bovada, and MyBookie** (Flat **$5.00** units).")

# Sidebar Configuration Controls
st.sidebar.header("API Configuration")
api_key = st.sidebar.text_input("Odds API Key", value="aa80562ae5fb97cfd71d78bc63a0cb1e", type="password")
force_test_mode = st.sidebar.checkbox("Use Board Simulator (Bypasses Dead Late-Night Hours)", value=True)

st.sidebar.header("Bankroll & Risk Management")
st.sidebar.info("Fixed Stake: **$5.00 per straight bet**")
flat_stake = 5.00

st.sidebar.header("Filter Settings")
min_edge = st.sidebar.slider("Minimum EV (%)", min_value=0.5, max_value=10.0, value=1.5, step=0.5)

# Main Screen Master Scan Button
scan_button = st.button("🚀 Run Straight Bet EV Scan", type="primary", use_container_width=True)

st.markdown("---")

def devig_and_calc_ev(over_odds, under_odds, chosen_odds):
    """Calculates true probability via devigging and computes Expected Value (EV %)."""
    def to_dec(odds):
        return (odds / 100.0) + 1.0 if odds > 0 else (100.0 / abs(odds)) + 1.0
    
    dec_over = to_dec(over_odds)
    dec_under = to_dec(under_odds)
    dec_chosen = to_dec(chosen_odds)
    
    implied_over = 1.0 / dec_over
    implied_under = 1.0 / dec_under
    total_vig = implied_over + implied_under
    
    fair_over = implied_over / total_vig
    fair_under = implied_under / total_vig
    
    true_prob = fair_over if chosen_odds == over_odds else fair_under
    ev_pct = ((true_prob * dec_chosen) - 1.0) * 100.0
    
    return true_prob, ev_pct

@st.cache_data(ttl=300)
def fetch_straight_bets(key, min_ev, test_mode):
    if test_mode:
        return pd.DataFrame([
            {"Sport": "NBA", "Player/Team": "Nikola Jokic", "Market": "Points Over 28.5", "Bookmaker": "DraftKings Sportsbook", "Pick": "Over", "Odds": +110, "True Prob": 0.53, "EV (%)": 2.4},
            {"Sport": "NBA", "Player/Team": "Luka Doncic", "Market": "Assists Under 9.5", "Bookmaker": "Hard Rock Sportsbook", "Pick": "Under", "Odds": -110, "True Prob": 0.54, "EV (%)": 3.1},
            {"Sport": "MLB", "Player/Team": "Shohei Ohtani", "Market": "Home Runs Over 0.5", "Bookmaker": "Bovada", "Pick": "Over", "Odds": +130, "True Prob": 0.46, "EV (%)": 5.8},
            {"Sport": "NHL", "Player/Team": "Connor McDavid", "Market": "Shots Under 4.5", "Bookmaker": "Fliff", "Pick": "Under", "Odds": +125, "True Prob": 0.51, "EV (%)": 2.8},
            {"Sport": "NFL", "Player/Team": "Patrick Mahomes", "Market": "Pass Yds Over 275.5", "Bookmaker": "MyBookie.ag", "Pick": "Over", "Odds": +105, "True Prob": 0.52, "EV (%)": 2.1},
            {"Sport": "NBA", "Player/Team": "Boston Celtics", "Market": "Spread -4.5", "Bookmaker": "Novig", "Pick": "Celtics", "Odds": -108, "True Prob": 0.53, "EV (%)": 1.7},
            {"Sport": "MLB", "Player/Team": "New York Yankees", "Market": "Moneyline", "Bookmaker": "ProphetX", "Pick": "Yankees", "Odds": +115, "True Prob": 0.50, "EV (%)": 3.2}
        ])

    sports_list = ["basketball_nba", "icehockey_nhl", "baseball_mlb", "americanfootball_nfl"]
    prop_markets = ["player_points", "player_rebounds", "player_assists", "player_shots_on_goal", "batter_home_runs"]
    
    # Mapped book keys for The Odds API (`us` and `us2` regions)
    target_books = {
        "draftkings": "DraftKings Sportsbook",
        "hardrockbet": "Hard Rock Sportsbook",
        "fliff": "Fliff",
        "novig": "Novig",
        "prophetx": "ProphetX",
        "bovada": "Bovada",
        "mybookie": "MyBookie.ag"
    }
    
    all_rows = []
    
    try:
        for sport in sports_list:
            events_url = f"https://api.the-odds-api.com/v4/sports/{sport}/events"
            events_res = requests.get(events_url, params={"apiKey": key})
            if events_res.status_code != 200:
                continue
            events = events_res.json()
            
            for event in events[:3]:
                event_id = event.get("id")
                for market in prop_markets:
                    odds_url = f"https://api.the-odds-api.com/v4/sports/{sport}/events/{event_id}/odds"
                    odds_res = requests.get(odds_url, params={
                        "apiKey": key,
                        "regions": "us,us2",
                        "markets": market,
                        "oddsFormat": "american"
                    })
                    
                    if odds_res.status_code == 200:
                        data = odds_res.json()
                        for book in data.get("bookmakers", []):
                            book_key = book.get("key")
                            if book_key in target_books:
                                book_title = target_books[book_key]
                                for m in book.get("markets", []):
                                    if m.get("key") == market:
                                        outcomes = m.get("outcomes", [])
                                        for outcome in outcomes:
                                            p_name = outcome.get("description", "Team Line")
                                            line_val = outcome.get("point", "")
                                            price = outcome.get("price", -110)
                                            side = outcome.get("name")
                                            
                                            true_prob, ev_pct = devig_and_calc_ev(
                                                price if side == "Over" else -110, 
                                                price if side == "Under" else -110, 
                                                price
                                            )
                                            
                                            if ev_pct >= min_ev:
                                                all_rows.append({
                                                    "Sport": sport.split("_")[1].upper(),
                                                    "Player/Team": p_name,
                                                    "Market": f"{market.replace('player_', '').title()} {line_val}",
                                                    "Bookmaker": book_title,
                                                    "Pick": side,
                                                    "Odds": price,
                                                    "True Prob": true_prob,
                                                    "EV (%)": round(ev_pct, 2)
                                                })
        if all_rows:
            return pd.DataFrame(all_rows)
    except Exception as e:
        pass
        
    return pd.DataFrame()

# Execution Flow on Scan Button Click
if scan_button:
    st.session_state["scanned"] = True
    st.session_state["df_data"] = fetch_straight_bets(api_key, min_edge, force_test_mode)

# Render Results
if st.session_state.get("scanned", False):
    df = st.session_state.get("df_data", pd.DataFrame())
    
    if not df.empty:
        st.subheader(f"🔥 Straight Bet +EV Board (EV ≥ {min_edge}%)")
        st.markdown(f"Flat stake configured: **${flat_stake:.2f}** per straight bet.")

        # Filter by minimum edge slider
        filtered_df = df[df["EV (%)"] >= min_edge].sort_values(by="EV (%)", ascending=False).reset_index(drop=True)

        if not filtered_df.empty:
            st.dataframe(
                filtered_df[["Sport", "Bookmaker", "Player/Team", "Market", "Pick", "Odds", "EV (%)"]], 
                use_container_width=True
            )
            
            st.markdown("---")
            st.subheader("📋 Actionable Straight Bets ($5.00 Unit)")
            
            for idx, row in filtered_df.iterrows():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**{row['Bookmaker']}** | {row['Player/Team']} — **{row['Market']}** ({row['Pick']} @ {row['Odds']:+d})")
                    st.caption(f"Calculated Edge: **+{row['EV (%)']}%** | True Win Prob: **{row['True Prob']*100:.1f}%**")
                with col2:
                    st.markdown(f"**Stake:**\n💰 **${flat_stake:.2f}**")
                st.markdown("---")
        else:
            st.warning("No straight bets match your minimum EV filter right now.")
    else:
        st.warning("No live lines returned from the API feed. Try enabling the Board Simulator in the sidebar.")
else:
    st.info("👆 Click the **🚀 Run Straight Bet EV Scan** button above to load straight bets.")
    
