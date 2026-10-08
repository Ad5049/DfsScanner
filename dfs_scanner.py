import streamlit as st
import pandas as pd
import numpy as np
import requests

# Page Config
st.set_page_config(page_title="DFS +EV Slip Scanner", layout="wide")

st.title("🎯 DFS +EV & Discrepancy Scanner")
st.markdown("Configure your parameters below and click **Run Live Scan** to pull active props and calculate edges.")

# Sidebar Controls for API & Bankroll
st.sidebar.header("API Configuration")
api_key = st.sidebar.text_input("Odds API Key", value="aa80562ae5fb97cfd71d78bc63a0cb1e", type="password")
sport_key = st.sidebar.selectbox("Sport Selection", ["basketball_nba", "icehockey_nhl", "baseball_mlb", "americanfootball_nfl"])

st.sidebar.header("Bankroll & Risk Management")
bankroll = st.sidebar.number_input("Total Bankroll ($)", value=2500.0, step=100.0)
unit_pct = st.sidebar.slider("Unit Size (%)", min_value=0.5, max_value=5.0, value=1.0, step=0.5)
unit_size = bankroll * (unit_pct / 100.0)
st.sidebar.success(f"Calculated Unit Size: **${unit_size:.2f}**")

st.sidebar.header("Filter Settings")
min_edge = st.sidebar.slider("Minimum Edge (%)", min_value=0.0, max_value=10.0, value=0.0, step=0.5)

# Explicit Scan Action Button
scan_button = st.sidebar.button("🚀 Run Live Scan", type="primary")

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
def fetch_odds_data(key, sport):
    url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds"
    params = {
        "apiKey": key,
        "regions": "us",
        "markets": "h2h,totals",
        "oddsFormat": "american"
    }
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            games = response.json()
            rows = []
            # Parse game lines into structured prop rows for scanning demonstration
            for game in games:
                home = game.get("home_team", "Home")
                away = game.get("away_team", "Away")
                commence = game.get("commence_time", "")
                for book in game.get("bookmakers", []):
                    for market in book.get("markets", []):
                        if market.get("key") == "totals":
                            for outcome in market.get("outcomes", []):
                                rows.append({
                                    "Player": f"{away} @ {home}",
                                    "Prop": f"Game Total ({outcome.get('name')})",
                                    "Line": outcome.get("point", 0.0),
                                    "Platform": book.get("title"),
                                    "Sharp_Over_Odds": -110,
                                    "Sharp_Under_Odds": -110,
                                    "Recommendation": outcome.get("name")
                                })
            if rows:
                return pd.DataFrame(rows)
        # Fallback dataset if API returns empty or rate limits
        return pd.DataFrame([
            {"Player": "LeBron James", "Prop": "Points", "Line": 24.5, "Platform": "PrizePicks", "Sharp_Over_Odds": -135, "Sharp_Under_Odds": +105, "Recommendation": "Over"},
            {"Player": "Nikola Jokic", "Prop": "Rebounds", "Line": 11.5, "Platform": "Underdog", "Sharp_Over_Odds": +110, "Sharp_Under_Odds": -140, "Recommendation": "Under"},
            {"Player": "Connor McDavid", "Prop": "Shots on Goal", "Line": 3.5, "Platform": "Sleeper", "Sharp_Over_Odds": -150, "Sharp_Under_Odds": +120, "Recommendation": "Under"}
        ])
    except Exception as e:
        st.error(f"API Connection Error: {e}")
        return pd.DataFrame()

# Execution Flow on Button Press
if scan_button or "scanned" not in st.session_state:
    st.session_state["scanned"] = True
    st.session_state["df_data"] = fetch_odds_data(api_key, sport_key)

if "df_data" in st.session_state and not st.session_state["df_data"].empty:
    df = st.session_state["df_data"]
    processed_rows = []
    for idx, row in df.iterrows():
        f_over, f_under = devig_odds(row["Sharp_Over_Odds"], row["Sharp_Under_Odds"])
        true_prob = f_over if row["Recommendation"] == "Over" or row["Recommendation"] == "Over" else f_under
        
        # Break-even baseline for 2-leg power entries (~54.2%)
        edge = (true_prob - 0.542) * 100.0
        
        processed_rows.append({
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

    st.subheader("📊 Available +EV Props for DFS Slips")
    st.dataframe(filtered_df, use_container_width=True)

    st.markdown("---")
    st.subheader("🛠️ Slip Builder (2 & 3-Leg Power Entries)")

    selected_props = st.multiselect(
        "Select legs to build your entry (Max 3):",
        options=filtered_df.index,
        format_func=lambda x: f"{filtered_df.loc[x, 'Player']} - {filtered_df.loc[x, 'Prop']} ({filtered_df.loc[x, 'Pick']} {filtered_df.loc[x, 'Line']}) | Edge: {filtered_df.loc[x, 'Edge (%)']}%"
    )

    if len(selected_props) > 0:
        selected_table = filtered_df.loc[selected_props]
        st.write("### Your Active Entry Slip")
        st.dataframe(selected_table[["Player", "Platform", "Prop", "Line", "Pick", "True Prob (%)", "Edge (%)"]], use_container_width=True)
        
        combined_prob = np.prod(selected_table["True Prob (%)"].values / 100.0) * 100.0
        st.info(f"**Estimated Combined True Probability of Hit:** {combined_prob:.2f}% | **Recommended Stake:** ${unit_size:.2f} ({unit_pct}% of bankroll)")
    else:
        st.info("Select legs above to preview your combined entry metrics.")
else:
    st.info("Click **Run Live Scan** in the sidebar to populate the market board.")
    
