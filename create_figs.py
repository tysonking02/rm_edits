import pandas as pd
import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import scipy.stats as stats
from great_tables import GT, style, loc, md

#### Read Data ####

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

#### Create Accepted Rate Rolling Average Line Graph ####

daily_avg = baseline_merged.groupby('RecommendationDate')['accepted_range'].mean()
rolling_avg = daily_avg.rolling(window=60, min_periods=1).mean()

plt.figure(figsize=(10, 6))
plt.plot(rolling_avg, label='60-Day Rolling Average of Accepted Rate', color='steelblue', linewidth=2)
plt.xlabel('Date', fontsize=12)
plt.ylabel('Accepted Rate (%)', fontsize=12)
plt.title('60-Day Rolling Average of Accepted Rate Over Time', fontsize=14)
plt.xlim(pd.to_datetime('2024-06-01'), max(daily_avg.index))
plt.ylim(0.4, 0.8)
plt.yticks([0.4, 0.5, 0.6, 0.7, 0.8], ['40%', '50%', '60%', '70%', '80%'])
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
plt.xticks(rotation=45, ha='right')
plt.grid(True, linestyle='--', alpha=0.7)
plt.style.use('seaborn-v0_8-muted')
plt.tight_layout()

plt.savefig('rm_edits/figures/acc_over_time.png')

#### Create table by Unit Group ####

by_unitgroup = baseline_merged.groupby('FloorPlanGroupName').agg(
    count = ('accepted', 'count'),
    acceptance_rate = ('accepted_range', 'mean'),
    median_adjustment = ('Diff', 'median')
).sort_values('acceptance_rate', ascending=False).reset_index()

by_unitgroup = by_unitgroup[by_unitgroup['count'] > 50]

# Create a GT object
table = GT(by_unitgroup[['FloorPlanGroupName', 'acceptance_rate', 'median_adjustment']])

table = (
    table
    .cols_label(FloorPlanGroupName = md("**Unit Group**"),
                acceptance_rate = md("**Acceptance Rate**"),
                median_adjustment = md("**Median Adjustment**"))
    .tab_header(title = "Price Change Metrics by Unit Group")
    .fmt_currency(columns = 2)
    .fmt_percent(columns = 1)
    .fmt_number(columns="median_adjustment", decimals=2)
    .tab_style(
        style=style.text(style="italic"),
        locations = loc.body(columns=0)
    )
)

table.save('rm_edits/figures/acc_by_unitgroup.png')

#### Create Table by Market ####

baseline_merged['AcquisitionDate_numeric'] = pd.to_datetime(baseline_merged['AcquisitionDate']).astype(int) / 10**9

# Perform the aggregation
by_market = baseline_merged.groupby(['MarketName']).agg(
    count=('accepted', 'count'),
    acceptance_rate=('accepted_range', 'mean'),
    num_assets=('AssetName', 'nunique'),
    acquisition_date_numeric=('AcquisitionDate_numeric', 'min'),
    median_adjustment=('Diff', 'median')
).sort_values('acceptance_rate', ascending=False).reset_index()

# Convert the numeric values back to dates
by_market['acquisition_date'] = pd.to_datetime(by_market['acquisition_date_numeric'], unit='s')
by_market.drop(columns=['acquisition_date_numeric'], inplace=True)

by_market = by_market[['MarketName', 'num_assets', 'acquisition_date', 'acceptance_rate', 'median_adjustment']]

table = GT(by_market)

table = (
    table
    .cols_label(MarketName = md("**Market**"),
                num_assets = md("**# Assets**"),
                acquisition_date = md("**Earliest Acquisition**"),
                acceptance_rate = md("**Acceptance Rate**"),
                median_adjustment = md("**Median Adjustment**"))
    .tab_header(title = "Price Change Metrics by Market")
    .fmt_currency(columns = 4)
    .fmt_percent(columns = 3)
    .fmt_number(columns="median_adjustment", decimals=2)
    .tab_style(
        style=style.text(style="italic"),
        locations = loc.body(columns=0)
    )
)

# Display the table
table.save('rm_edits/figures/acc_bymarket.png')

#### Create Table of Low Acceptance Rate Properties ####

by_property = baseline_merged.groupby(['AssetName', 'User']).agg(
    count = ('accepted', 'count'),
    acceptance_rate = ('accepted_range', 'mean'),
    median_adjustment = ('Diff', 'median')
).sort_values('acceptance_rate', ascending=False).reset_index()

by_property = by_property[by_property['count'] > 20]

# Calculate the overall mean acceptance rate
overall_mean_acceptance_rate = baseline_merged['accepted_range'].mean()

# Function to perform the hypothesis test
def perform_hypothesis_test(asset_name, overall_mean):
    # Get the acceptance rates for the current asset
    asset_data = baseline_merged[baseline_merged['AssetName'] == asset_name]['accepted_range']
    
    # Check if there are enough data points to perform the test
    if len(asset_data) > 1:  # We need at least two data points for a valid t-test
        t_stat, p_value = stats.ttest_1samp(asset_data, overall_mean)
        return p_value
    else:
        return float('nan')  # Return NaN if not enough data to perform t-test


# Apply the hypothesis test for each market and store the results in a new column 'p_value'
by_property['p_value'] = by_property['AssetName'].apply(lambda x: perform_hypothesis_test(x, overall_mean_acceptance_rate))

# Adding a new column 'is_significant' to indicate if p-value is less than 0.05 (95% confidence)
by_property['is_significant'] = by_property['p_value'] < 0.05

by_property = by_property[['AssetName', 'User', 'acceptance_rate', 'median_adjustment', 'count', 'p_value', 'is_significant']]

# Filter markets that are significantly different from the overall mean (p-value < 0.05)
significant_properties = by_property[by_property['is_significant']]

below_average_properties = significant_properties[significant_properties['acceptance_rate'] < overall_mean_acceptance_rate]

# Drop 'p_value' and 'is_significant' columns
below_average_properties = below_average_properties.drop(columns=['count', 'p_value', 'is_significant']).tail(10)

# Create a GT object
table = GT(below_average_properties)

table = (
    table
    .cols_label(AssetName = md("**Property**"),
                User = md("**RM**"),
                acceptance_rate = md("**Acceptance Rate**"),
                median_adjustment = md("**Median Adjustment**"))
    .tab_header(title = "Price Change Metrics by Property",
                subtitle = "(Properties with Significantly Low Acceptance Rate)")
    .fmt_currency(columns = 3)
    .fmt_percent(columns = 2)
    .fmt_number(columns="median_adjustment", decimals=2)
    .tab_style(
        style=style.text(style="italic"),
        locations = loc.body(columns=0)
    )
)

table.save('rm_edits/figures/low_acc_byproperty.png')

#### Create Adjustment over Time Figures ####

def get_adj_over_time(asset_name=None, market_name=None):

    if asset_name:
        filtered = baseline_merged[baseline_merged['AssetName'] == asset_name]
    elif market_name:
        filtered = baseline_merged[baseline_merged['MarketName'] == market_name]

    filtered = filtered.sort_values('RecommendationDate').reset_index()

    avg_range = (filtered['recc_rate'] - filtered['recc_rate_lower']).mean()

    plt.figure(figsize=(10, 6))
    plt.scatter(filtered['RecommendationDate'], filtered['Diff'])
    plt.xlabel("Date")
    plt.ylabel("Change from Recommended Rate")

    if asset_name:
        plt.title(f"{asset_name} Adjustments over Time")
    elif market_name:
        plt.title(f"{market_name} Adjustments over Time")
    
    plt.fill_between(filtered['RecommendationDate'], -avg_range, avg_range, color='red', alpha=0.1)
    plt.hlines(0, min(filtered['RecommendationDate']), max(filtered['RecommendationDate']), linestyles="dashed", colors="black")
    plt.xticks(rotation=45)
    plt.style.use('seaborn-v0_8-muted')
    plt.tight_layout()
    if asset_name:
        plt.savefig(f'rm_edits/figures/adj_over_time/{asset_name}')
    elif market_name:
        plt.savefig(f'rm_edits/figures/adj_over_time/{market_name}')

get_adj_over_time(asset_name="Cortland Northlake")
# get_adj_over_time(asset_name="Cortland 3131")
# get_adj_over_time(market_name="Phoenix-Mesa-Scottsdale, AZ")
# get_adj_over_time(market_name="West Palm Beach-Boca Raton-Delray Beach, FL")
get_adj_over_time(market_name="Denver-Aurora-Lakewood, CO")
# get_adj_over_time(market_name="Colorado Springs, CO")