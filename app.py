import streamlit as st
import pandas as pd
import os
import matplotlib.pyplot as plt
import seaborn as sns

def get_adj_over_time(asset_name=None, market_name=None):

    if asset_name:
        filtered = baseline_merged[baseline_merged['AssetName'] == asset_name]
    elif market_name:
        filtered = baseline_merged[baseline_merged['MarketName'] == market_name]

    filtered = filtered.sort_values('RecommendationDate').reset_index()

    avg_range = (filtered['recc_rate'] - filtered['recc_rate_lower']).mean()

    def sort_key(floor_plan):
        bedrooms, bathrooms = floor_plan.split('x')
        return (float(bedrooms), float(bathrooms)) 

    # Generate unique categories and sort them
    unique_categories = sorted(filtered['FloorPlanGroupName'].unique(), key=sort_key)
    palette = dict(zip(unique_categories, sns.color_palette("tab10", len(unique_categories))))

    # Create the scatter plot with categorical colors
    fig, ax = plt.subplots(figsize=(10,6))

    for category, color in palette.items():
        subset = filtered[filtered['FloorPlanGroupName'] == category]
        if asset_name:
            ax.scatter(subset['RecommendationDate'], subset['Diff'], color=color, label=category)
        elif market_name:
            ax.scatter(subset['RecommendationDate'], subset['Diff'], color='#1f77b4')

    # Add legend
    if asset_name:
        ax.legend(title="Floor Plan Group", bbox_to_anchor=(1.05, 1), loc='upper left')
    
    plt.xlabel("Date")
    plt.ylabel("Change from Recommended Rate")

    if asset_name:
        plt.title(f"{asset_name} Adjustments over Time")
    elif market_name:
        plt.title(f"{market_name} Adjustments over Time")
    
    plt.fill_between(filtered['RecommendationDate'], -avg_range, avg_range, color='red', alpha=0.1)
    plt.hlines(0, min(filtered['RecommendationDate']), max(filtered['RecommendationDate']), linestyles="dashed", colors="black")
    plt.xticks(rotation=45)
    if market_name == "Phoenix-Mesa-Scottsdale, AZ":
        plt.text(x=pd.to_datetime('2024-10-01'), y=avg_range + 5, s="Top of Recommended Range", size=8, ha='center')
        plt.text(x=pd.to_datetime('2024-10-01'), y=-avg_range - 20, s="Bottom of Recommended Range", size=8, ha='center')
    plt.style.use('seaborn-v0_8-muted')
    plt.tight_layout()
    if asset_name:
        plt.savefig(f'rm_edits/figures/adj_over_time/{asset_name}', )
    elif market_name:
        plt.savefig(f'rm_edits/figures/adj_over_time/{market_name}')

files = os.listdir('rm_edits/baseline_merged')
files = [file for file in files if file.endswith('.csv')]

baseline_merged = pd.concat([pd.read_csv(f'rm_edits/baseline_merged/{file}') for file in files])

baseline_merged.dropna(subset='recc_rate', inplace=True)

baseline_merged=baseline_merged[~baseline_merged['User'].isin(['Nathan Worrell','Liam Jagrowski','Henry Cross','Dylan Orr','Jacob Swain','John Hazelton','Brian Dietrich'])]

baseline_merged['InputtedRent'] = baseline_merged['InputtedRent'].str.replace(',','').astype(float)
baseline_merged['RecommendationDate'] = pd.to_datetime(baseline_merged['RecommendationDate'])

AssetDetailActive = pd.read_csv('rm_edits/data/vw_AssetDetailActive.csv')

baseline_merged = baseline_merged.merge(AssetDetailActive, on='AssetName')

baseline_merged['Diff'] = baseline_merged['InputtedRent'] - baseline_merged['recc_rate']

baseline_merged['accepted'] = abs(baseline_merged['InputtedRent'] - baseline_merged['recc_rate']) < 1
baseline_merged['accepted_range'] = (baseline_merged['InputtedRent'] >= baseline_merged['recc_rate_lower']) & (baseline_merged['InputtedRent'] <= baseline_merged['recc_rate_upper'])

st.set_page_config(page_title="RM Price Change Analysis", layout="centered")

st.title("RM Price Change Analysis")

st.image("rm_edits/figures/acc_over_time.png", caption="Rate of acceptance of RMP recommendation has steadily decreased since its inception")


st.divider()

st.header("Breakdown by Market")
st.image("rm_edits/figures/acc_bymarket.png", caption="Acceptance by market")

st.image("rm_edits/figures/adj_over_time/Phoenix-Mesa-Scottsdale, AZ.png", caption="Adjustment trends in Phoenix market")
st.image("rm_edits/figures/adj_over_time/West Palm Beach-Boca Raton-Delray Beach, FL.png", caption="Adjustment trends in West Palm Beach market")

st.markdown("Each dot is an individual baseline rent adjustment.")

st.divider()

st.header("Breakdown by Property")
st.image("rm_edits/figures/low_acc_byproperty.png")

st.subheader("View Adjustments over Time by Asset/Market:")

# create a dropdown for asset and market that calls get_adj_over_time
market_input = st.selectbox("Select Market", [""] + list(pd.unique(baseline_merged['MarketName'])))
asset_input = st.selectbox("Select Asset", [""] + list(pd.unique(baseline_merged['AssetName'])))

if st.button("Enter"):
    if asset_input:
        get_adj_over_time(asset_name = asset_input)
        st.image(f"rm_edits/figures/adj_over_time/{asset_input}.png")
    if market_input:
        get_adj_over_time(market_name = market_input)
        st.image(f"rm_edits/figures/adj_over_time/{market_input}.png")