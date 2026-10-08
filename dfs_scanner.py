import streamlit as st
import pandas as pd
import numpy as np
import requests

# Page Config
st.set_page_config(page_title="Major League Main Market +EV Scanner", layout="wide")

st.title("🎯 Major League Main Market +EV Scanner")
st.markdown("Scanning North American major leagues (**NFL, NCAAF, NBA, NCAAB, MLB, NHL**) for main lines (**Spreads, Moneyline, Totals**) across your books with **Multi-Format Odds (American, Decimal, & Implied %)**.")

# Sidebar Configuration Controls
api_key = st.sidebar.text_input("Odds API Key", value="aa80562ae5fb97cfd71d78bc63a0cb1e", type="password")

st.sidebar.header("Bankroll & Risk Management")
st.sidebar.info("Fixed Stake: **$5.00 per straight bet**")
flat_stake = 5.00

st.sidebar.header("Filter Settings")
min_edge = st.sidebar.slider("Minimum EV Floor (%)", min_value=1.0, max_value=25.0, value=5.0, step=0.5)
st.sidebar.caption("💡 *Lower threshold floor. All higher positive EV plays will automatically display.*")

# Main Screen Master Scan Button
scan_button = st.button("🚀 Run Major League EV Scan", type="primary", use_container_width=True)

st.markdown("---")

def convert_odds_formats(american_odds):
    """Converts American odds to Decimal and Implied Probability (%)"""
    if american_odds > 0:
        dec = (american_odds / 100.0) + 1.0
        prob = 100.0 / (american_odds + 100.0)
    else:
        dec = (100.0 / abs(american_odds)) + 1.0
        prob = abs(american_odds) / (abs(american_odds) + 100.0)
    return round(dec, 2), round(prob * 100.0, 2)

def devig_and_calc_ev(over_odds, under_odds, chosen_odds):
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
    # Soccer excluded entirely; focused strictly on North American major sports leagues
    sports_list = [
        "americanfootball_nfl", "americanfootball_ncaaf",
        "basketball_nba", "basketball_ncaab",
        "baseball_mlb", "icehockey_nhl"
    ]
    main_markets = "h2h,spreads,totals"
    
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
            odds_url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds"
            odds_res = requests.get(odds_url, params={
                "apiKey": key,
                "regions": "us,us2",
                "markets": main_markets,
                "oddsFormat": "american"
            })
            
            if odds_res.status_code != 200:
                continue
                
            events_data = odds_res.json()
            
            for event in events_data:
                home_team = event.get("home_team", "Home")
                away_team = event.get("away_team", "Away")
                matchup_str = f"{away_team} @ {home_team}"
                
                for book in event.get("bookmakers", []):
                    book_key = book.get("key")
                    if book_key in target_books:
                        book_title = target_books[book_key]
                        for m in book.get("markets", []):
                            market_key = m.get("key")
                            outcomes = m.get("outcomes", [])
                            
                            if len(outcomes) >= 2:
                                price1 = outcomes[0].get("price", -110)
                                price2 = outcomes[1].get("price", -110)
                                
                                for outcome in outcomes:
                                    side_name = outcome.get("name")
                                    line_val = outcome.get("point", "")
                                    price = outcome.get("price", -110)
                                    
                                    market_label = market_key.upper()
                                    if line_val != "":
                                        market_label = f"{market_key.capitalize()} ({line_val})"
                                    
                                    true_prob, ev_pct = devig_and_calc_ev(price1, price2, price)
                                    
                                    if ev_pct >= min_ev:
                                        dec_val, implied_pct = convert_odds_formats(price)
                                        formatted_odds = f"{price:+d} | Dec: {dec_val} | Impl: {implied_pct}%"
                                        
                                        all_rows.append({
                                            "Sport": sport.upper(),
                                            "Matchup": matchup_str,
                                            "Market": market_label,
                                            "Bookmaker": book_title,
                                            "Pick": side_name,
                                            "Odds Info": formatted_odds,
                                            "Raw EV": ev_pct,
                                            "EV (%)": f"+{round(ev_pct, 2)}%"
                                        })
        if all_rows:
            return pd.DataFrame(all_rows)
    except Exception as e:
        pass
        
    return pd.DataFrame()

# Execution Flow on Scan Button Click
if scan_button:
    st.session_state["scanned"] = True
    with st.spinner("⚡ Scanning North American major leagues..."):
        st.session_state["df_data"] = fetch_main_market_bets(api_key, min_edge)

# Render Results
if st.session_state.get("scanned", False):
    df = st.session_state.get("df_data", pd.DataFrame())
    
    if not df.empty:
        filtered_df = df[df["Raw EV"] >= min_edge].sort_values(by="Raw EV", ascending=False).reset_index(drop=True)

        if not filtered_df.empty:
            st.subheader(f"🔥 Major League Main Market Board (EV ≥ {min_edge}%)")
            st.markdown(f"Flat stake configured: **${flat_stake:.2f}** per straight bet.")
            
            st.dataframe(
                filtered_df[["Sport", "Bookmaker", "Matchup", "Market", "Pick", "Odds Info", "EV (%)"]], 
                use_container_width=True
            )
            
            st.markdown("---")
            st.subheader("📋 Actionable Straight Bets ($5.00 Unit)")
            
            for idx, row in filtered_df.iterrows():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**{row['Bookmaker']}** | [{row['Sport']}] {row['Matchup']} — **{row['Market']}**")
                    st.caption(f"Pick: **{row['Pick']}** | Odds: **{row['Odds Info']}** | Edge: **{row['EV (%)']}**")
                with col2:
                    st.markdown(f"**Stake:**\n💰 **${flat_stake:.2f}**")
                st.markdown("---")
        else:
            st.warning(f"The market has no plays meeting or exceeding +{min_edge}% EV right now.")
    else:
        st.warning("The market has no plays right now. Live/upcoming odds feeds are currently empty for the selected North American sports and books.")
else:
    st.info("👆 Click the **🚀 Run Major League EV Scan** button above to load live straight bets.")
    
