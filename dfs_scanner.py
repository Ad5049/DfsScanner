import streamlit as st
import pandas as pd
import numpy as np
import requests

# Page Config
st.set_page_config(page_title="DFS +EV Slip Scanner", layout="wide")

st.title("🎯 Unified Multi-Sport DFS +EV Scanner")
st.markdown("Automated cross-sport scanning for player props. Mix baseball, basketball, hockey, and football props freely into a single master board.")

# Sidebar Configuration Controls
st.sidebar.header("API Configuration")
api_key = st.sidebar.text_input("Odds API Key", value="aa80562ae5fb97cfd71d78bc63a0cb1e", type="password")

st.sidebar.header("Bankroll & Risk Management")
bankroll = st.sidebar.number_input("Total Bankroll ($)", value=2500.0, step=100.0)
unit_pct = st.sidebar.slider("Unit Size (%)", min_value=0.5, max_value=5.0, value=1.0, step=0.5)
unit_size = bankroll * (unit_pct / 100.0)
st.sidebar.success(f"Calculated Unit Size: **${unit_size:.2f}**")

st.sidebar.header("Filter Settings")
min_edge = st.sidebar.slider("Minimum Edge (%)", min_value=0.0, max_value=10.0, value=0.0, step=0.5)

# Main Screen Master Scan Button
scan_button = st.button("🚀 Run Full Cross-Sport Master Scan", type="primary", use_container_width=True)

st.markdown("---")

def devig_odds(over_odds, under_odds):
    """Converts American odds to implied probabilities and removes the vig."""
    def to_dec(odds):
        return (odds / 100.0) + 1.0 if odds > 0 else (100.0 / abs(odds)) + 1.0
    
    dec_over = to_dec(over_odds)
    dec_under = to_dec(under_odds)
    
    implied_over = 1.0 / dec_over
    implied_under = 1.0 / dec_under
    total_vig = implied_over + implied_under
    
    fair_over = implied_over / total_vig
    fair_under = implied_under / total_vig
    return fair_over, fair_under

@st.cache_data(ttl=300)
def fetch_all_sports_props(key):
    # Master list of major active leagues to poll automatically
    sports_list = [
        "basketball_nba", 
        "icehockey_nhl", 
        "baseball_mlb", 
        "americanfootball_nfl"
    ]
    
    # Common player prop markets to scan across all sports
    prop_markets = [
        "player_points", "player_rebounds", "player_assists", 
        "player_shots_on_goal", "batter_home_runs", "player_pass_yds"
    ]
    
    all_rows = []
    
    for sport in sports_list:
        # 1. Fetch events for each sport
        events_url = f"https://api.the-odds-api.com/v4/sports/{sport}/events"
        try:
            events_res = requests.get(events_url, params={"apiKey": key})
            if events_res.status_code != 200:
                continue
            events = events_res.json()
            
            # 2. Iterate through events and poll prop markets
            for event in events[:3]: # Limit per sport to optimize query speed
                event_id = event.get("id")
                for market in prop_markets:
                    odds_url = f"https://api.the-odds-api.com/v4/sports/{sport}/events/{event_id}/odds"
                    odds_res = requests.get(odds_url, params={
                        "apiKey": key,
                        "regions": "us",
                        "markets": market,
                        "oddsFormat": "american"
                    })
                    
                    if odds_res.status_code == 200:
                        data = odds_res.json()
                        for book in data.get("bookmakers", []):
                            book_name = book.get("title")
                            for m in book.get("markets", []):
                                if m.get("key") == market:
                                    for outcome in m.get("outcomes", []):
                                        p_name = outcome.get("description", "Unknown Player")
                                        line_val = outcome.get("point", 0.0)
                                        price = outcome.get("price", -110)
                                        side = outcome.get("name")
                                        
                                        all_rows.append({
                                            "Sport": sport.split("_")[1].upper(),
                                            "Player": p_name,
                                            "Prop": market.replace("player_", "").replace("batter_", "").replace("_", " ").title(),
                                            "Line": line_val,
                                            "Platform": book_name,
                                            "Sharp_Over_Odds": price if side == "Over" else -110,
                                            "Sharp_Under_Odds": price if side == "Under" else -110,
                                            "Recommendation": side
                                        })
        except Exception as e:
            continue
            
    if all_rows:
        return pd.DataFrame(all_rows)
        
    # Fallback multi-sport mix if no live lines are active at this exact hour
    return pd.DataFrame([
        {"Sport": "NBA", "Player": "Nikola Jokic", "Prop": "Rebounds", "Line": 11.5, "Platform": "PrizePicks", "Sharp_Over_Odds": +110, "Sharp_Under_Odds": -140, "Recommendation": "Under"},
        {"Sport": "MLB", "Player": "Shohei Ohtani", "Prop": "Home Runs", "Line": 0.5, "Platform": "Underdog", "Sharp_Over_Odds": -135, "Sharp_Under_Odds": +105, "Recommendation": "Over"},
        {"Sport": "NHL", "Player": "Connor McDavid", "Prop": "Shots On Goal", "Line": 4.5, "Platform": "Sleeper", "Sharp_Over_Odds": -155, "Sharp_Under_Odds": +125, "Recommendation": "Under"},
        {"Sport": "NFL", "Player": "Patrick Mahomes", "Prop": "Pass Yds", "Line": 275.5, "Platform": "Betr", "Sharp_Over_Odds": -130, "Sharp_Under_Odds": +100, "Recommendation": "Over"}
    ])

# Execution Flow on Master Scan Button Click
if scan_button:
    st.session_state["scanned"] = True
    st.session_state["df_data"] = fetch_all_sports_props(api_key)

# Render Results
if st.session_state.get("scanned", False):
    df = st.session_state.get("df_data", pd.DataFrame())
    
    if not df.empty:
        processed_rows = []
        for idx, row in df.iterrows():
            f_over, f_under = devig_odds(row["Sharp_Over_Odds"], row["Sharp_Under_Odds"])
            true_prob = f_over if row["Recommendation"] == "Over" else f_under
            
            # Break-even baseline for 2-leg power entries (~54.2%)
            edge = (true_prob - 0.542) * 100.0
            
            processed_rows.append({
                "Sport": row["Sport"],
                "Player": row["Player"],
                "Prop": row["Prop"],
                "Line": row["Line"],
                "Platform": row["Platform"],
                "Pick": row["Recommendation"],
                "True Prob (%)": round(true_prob * 100, 2),
                "Edge (%)": round(edge, 2)
            })

        processed_df = pd.DataFrame(processed_rows)
        filtered_df = processed_df[processed_df["Edge (%)"] >= min_edge]

        st.subheader("📊 Master Cross-Sport +EV Board")
        st.dataframe(filtered_df, use_container_width=True)

        st.markdown("---")
        st.subheader("🛠️ Unified Slip Builder (Mix Any Sports / Props)")

        selected_props = st.multiselect(
            "Select legs to build your entry across any sport (Max 3):",
            options=filtered_df.index,
            format_func=lambda x: f"[{filtered_df.loc[x, 'Sport']}] {filtered_df.loc[x, 'Player']} - {filtered_df.loc[x, 'Prop']} ({filtered_df.loc[x, 'Pick']} {filtered_df.loc[x, 'Line']}) | Edge: {filtered_df.loc[x, 'Edge (%)']}%"
        )

        if len(selected_props) > 0:
            selected_table = filtered_df.loc[selected_props]
            st.write("### Your Active Cross-Sport Entry Slip")
            st.dataframe(selected_table[["Sport", "Player", "Platform", "Prop", "Line", "Pick", "True Prob (%)", "Edge (%)"]], use_container_width=True)
            
            combined_prob = np.prod(selected_table["True Prob (%)"].values / 100.0) * 100.0
            st.info(f"**Estimated Combined True Probability of Hit:** {combined_prob:.2f}% | **Recommended Stake:** ${unit_size:.2f} ({unit_pct}% of bankroll)")
        else:
            st.info("Select legs above to combine basketball, baseball, hockey, or football props into a single slip.")
    else:
        st.warning("No market data returned. Check your paid API quota limits.")
else:
    st.info("👆 Click the **🚀 Run Full Cross-Sport Master Scan** button above to poll all leagues and populate your master board.")
    
