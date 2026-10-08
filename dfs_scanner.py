import streamlit as st
import pandas as pd
import numpy as np
import requests

# Page Config
st.set_page_config(page_title="Main Market Straight Bet +EV Scanner", layout="wide")

st.title("🎯 Main Market Straight Bet +EV Scanner")
st.markdown("Scanning high-liquidity markets (**Spreads, Moneyline, Totals, Alternate Lines**) for **DraftKings, Hard Rock, Fliff, Novig, ProphetX, Bovada, and MyBookie** (Flat **$5.00** units).")

# Sidebar Configuration Controls
st.sidebar.header("API Configuration")
api_key = st.sidebar.text_input("Odds API Key", value="aa80562ae5fb97cfd71d78bc63a0cb1e", type="password")

st.sidebar.header("Bankroll & Risk Management")
st.sidebar.info("Fixed Stake: **$5.00 per straight bet**")
flat_stake = 5.00

st.sidebar.header("Filter Settings")
# Starts at 5.0%, floor at 1.0%, upper cap extended to 25.0%
min_edge = st.sidebar.slider("Minimum EV (%)", min_value=1.0, max_value=25.0, value=5.0, step=0.5)

# Main Screen Master Scan Button
scan_button = st.button("🚀 Run Main Market EV Scan", type="primary", use_container_width=True)

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
def fetch_main_market_bets(key, min_ev):
    sports_list = ["basketball_nba", "icehockey_nhl", "baseball_mlb", "americanfootball_nfl"]
    main_markets = ["h2h", "spreads", "totals"]
    
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
                home_team = event.get("home_team", "Home")
                away_team = event.get("away_team", "Away")
                matchup_str = f"{away_team} @ {home_team}"
                
                for market in main_markets:
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
                                        if len(outcomes) >= 2:
                                            price1 = outcomes[0].get("price", -110)
                                            price2 = outcomes[1].get("price", -110)
                                            
                                            for outcome in outcomes:
                                                side_name = outcome.get("name")
                                                line_val = outcome.get("point", "")
                                                price = outcome.get("price", -110)
                                                
                                                market_label = market.upper()
                                                if line_val != "":
                                                    market_label = f"{market.capitalize()} ({line_val})"
                                                
                                                true_prob, ev_pct = devig_and_calc_ev(price1, price2, price)
                                                
                                                if ev_pct >= min_ev:
                                                    all_rows.append({
                                                        "Sport": sport.split("_")[1].upper(),
                                                        "Matchup": matchup_str,
                                                        "Market": market_label,
                                                        "Bookmaker": book_title,
                                                        "Pick": side_name,
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
    st.session_state["df_data"] = fetch_main_market_bets(api_key, min_edge)

# Render Results
if st.session_state.get("scanned", False):
    df = st.session_state.get("df_data", pd.DataFrame())
    
    if not df.empty:
        filtered_df = df[df["EV (%)"] >= min_edge].sort_values(by="EV (%)", ascending=False).reset_index(drop=True)

        if not filtered_df.empty:
            st.subheader(f"🔥 Main Market Straight Bet +EV Board (EV ≥ {min_edge}%)")
            st.markdown(f"Flat stake configured: **${flat_stake:.2f}** per straight bet on high-liquidity markets.")
            
            st.dataframe(
                filtered_df[["Sport", "Bookmaker", "Matchup", "Market", "Pick", "Odds", "EV (%)"]], 
                use_container_width=True
            )
            
            st.markdown("---")
            st.subheader("📋 Actionable Main Market Bets ($5.00 Unit)")
            
            for idx, row in filtered_df.iterrows():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**{row['Bookmaker']}** | {row['Matchup']} — **{row['Market']}**")
                    st.caption(f"Pick: **{row['Pick']}** @ **{row['Odds']:+d}** | Calculated Edge: **+{row['EV (%)']}%** | True Prob: **{row['True Prob']*100:.1f}%**")
                with col2:
                    st.markdown(f"**Stake:**\n💰 **${flat_stake:.2f}**")
                st.markdown("---")
        else:
            st.warning(f"The market has no plays meeting or exceeding +{min_edge}% EV right now. Try lowering your EV threshold or scanning closer to game times.")
    else:
        st.warning("The market has no plays right now. Live odds feeds are currently empty for the selected sports and books.")
else:
    st.info("👆 Click the **🚀 Run Main Market EV Scan** button above to load live straight bets.")
    
