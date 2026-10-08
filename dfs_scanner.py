import streamlit as st
import pandas as pd
import numpy as np

# Page Config
st.set_page_config(page_title="DFS +EV Slip Scanner", layout="wide")

st.title("🎯 DFS Pick'em +EV & Discrepancy Scanner")
st.markdown("Scan projections, devig sharp lines, and build optimal 2- or 3-leg slips.")

# Sidebar Controls for Bankroll & Unit Sizing
st.sidebar.header("Bankroll & Risk Management")
bankroll = st.sidebar.number_input("Total Bankroll ($)", value=2500.0, step=100.0)
unit_pct = st.sidebar.slider("Unit Size (%)", min_value=0.5, max_value=5.0, value=1.0, step=0.5)
unit_size = bankroll * (unit_pct / 100.0)
st.sidebar.success(f"Calculated Unit Size: **${unit_size:.2f}**")

st.sidebar.header("Filter Settings")
min_edge = st.sidebar.slider("Minimum Edge (%)", min_value=0.0, max_value=10.0, value=2.0, step=0.5)

# Mocking data structure for demonstration (In production, plug your API/scraper source here)
@st.cache_data
def load_market_data():
    data = [
        {
            "Player": "Patrick Mahomes", "Prop": "Passing Yards", "Line": 275.5,
            "DFS_Platform": "PrizePicks", "Sharp_Over_Odds": -135, "Sharp_Under_Odds": +105,
            "Recommendation": "Over"
        },
        {
            "Player": "Nikola Jokic", "Prop": "Rebounds", "Line": 11.5,
            "DFS_Platform": "Underdog", "Sharp_Over_Odds": +110, "Sharp_Under_Odds": -140,
            "Recommendation": "Under"
        },
        {
            "Player": "Connor McDavid", "Prop": "Shots on Goal", "Line": 3.5,
            "DFS_Platform": "Sleeper", "Sharp_Over_Odds": -150, "Sharp_Under_Odds": +120,
            "Recommendation": "Under"
        },
        {
            "Player": "Shohei Ohtani", "Prop": "Total Bases", "Line": 1.5,
            "DFS_Platform": "PrizePicks", "Sharp_Over_Odds": -125, "Sharp_Under_Odds": -105,
            "Recommendation": "Over"
        }
    ]
    return pd.DataFrame(data)

def devig_odds(over_odds, under_odds):
    """Converts American odds to implied probabilities and removes the vig."""
    def to_dec(odds):
        return (odds / 100.0) + 1.0 if odds > 0 else (100.0 / abs(odds)) + 1.0
    
    dec_over = to_dec(over_odds)
    dec_under = to_dec(under_odds)
    
    implied_over = 1.0 / dec_over
    implied_under = 1.0 / dec_under
    total_vig = implied_over + implied_under
    
    # Fair/True probabilities
    fair_over = implied_over / total_vig
    fair_under = implied_under / total_vig
    return fair_over, fair_under

df = load_market_data()

# Process probabilities
processed_rows = []
for idx, row in df.iterrows():
    f_over, f_under = devig_odds(row["Sharp_Over_Odds"], row["Sharp_Under_Odds"])
    if row["Recommendation"] == "Over":
        true_prob = f_over
        sharp_line = row["Sharp_Over_Odds"]
    else:
        true_prob = f_under
        sharp_line = row["Sharp_Under_Odds"]
        
    # DFS assumed break-even for 2-leg power is roughly 54.2% (1 / sqrt(3.0) or standard 3x payout)
    # Edge = True Prob - Break-even baseline (54.2%)
    edge = (true_prob - 0.542) * 100.0
    
    processed_rows.append({
        "Player": row["Player"],
        "Prop": row["Prop"],
        "Line": row["Line"],
        "Platform": row["DFS_Platform"],
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
    
    # Combined probability estimation for independent events
    combined_prob = np.prod(selected_table["True Prob (%)"].values / 100.0) * 100.0
    st.info(f"**Estimated Combined True Probability of Hit:** {combined_prob:.2f}% | **Recommended Stake:** ${unit_size:.2f} ({unit_pct}% of bankroll)")
else:
    st.info("Select 2 or 3 legs above to preview your combined entry metrics.")
  
