"""
Run once to generate data/final_data.csv used by the Streamlit app.
Usage: python prepare_data.py <CENSUS_API_KEY>
Get a free key at: https://api.census.gov/data/key_signup.html
"""

import sys
import pandas as pd
import numpy as np
import requests
import os

if len(sys.argv) < 2:
    print("Usage: python prepare_data.py <CENSUS_API_KEY>")
    print("Get a free key at: https://api.census.gov/data/key_signup.html")
    sys.exit(1)

CENSUS_KEY = sys.argv[1]
os.makedirs("data", exist_ok=True)

# ── 1. CENSUS ACS 2021 (poverty, income, education) ──────────────────────────
print("Fetching Census ACS data...")
BASE_URL = "https://api.census.gov/data/2021/acs/acs5"
params = {
    "get": "NAME,B19013_001E,B15002_001E,B17001_002E,B01001_001E",
    "for": "county:*",
    "key": CENSUS_KEY
}
r = requests.get(BASE_URL, params=params, timeout=60)
data = r.json()
acs = pd.DataFrame(data[1:], columns=data[0])

num_cols = ["B19013_001E", "B15002_001E", "B17001_002E", "B01001_001E"]
acs[num_cols] = acs[num_cols].apply(pd.to_numeric, errors="coerce")
acs = acs.rename(columns={
    "B19013_001E": "median_income",
    "B15002_001E": "education_universe",
    "B17001_002E": "poverty_count",
    "B01001_001E": "population"
})
acs["poverty_rate"]  = acs["poverty_count"] / acs["population"]
acs["county_clean"]  = (acs["NAME"].str.split(",").str[0]
                        .str.replace(" County","",regex=False)
                        .str.replace(" Parish","",regex=False)
                        .str.lower().str.strip())
acs["state_clean"]   = acs["NAME"].str.split(",").str[1].str.lower().str.strip()
acs["fips"]          = acs["state"].str.zfill(2) + acs["county"].str.zfill(3)
print(f"  ACS: {len(acs)} counties")

# ── 2. EPA AQI (2017–2021 averages) ──────────────────────────────────────────
print("Loading EPA AQI data...")
aqi_raw = pd.read_excel(
    "/Users/sadafsarbazi/Merged(2017-2022)_EPA_AQI.xlsx",
    engine="openpyxl"
)
epa = aqi_raw[(aqi_raw["Year"] >= 2017) & (aqi_raw["Year"] <= 2021)].copy()
epa["county_clean"] = epa["County"].str.lower().str.strip()
epa["state_clean"]  = epa["State"].str.lower().str.strip()

epa_wanted = [
    "Days with AQI", "Good Days", "Moderate Days",
    "Unhealthy for Sensitive Groups Days", "Unhealthy Days",
    "Very Unhealthy Days", "Hazardous Days",
    "Max AQI", "90th Percentile AQI", "Median AQI",
    "Days Ozone", "Days PM2.5", "Days PM10",
    "Days CO", "Days NO2",
]
epa_cols = [c for c in epa_wanted if c in epa.columns]
epa_avg = (epa.groupby(["state_clean", "county_clean"])[epa_cols]
           .mean().reset_index())
if "Days PM2.5" in epa_avg.columns:
    epa_avg["pm25_share"] = epa_avg["Days PM2.5"] / epa_avg["Days with AQI"]
if "Days Ozone" in epa_avg.columns:
    epa_avg["ozone_share"] = epa_avg["Days Ozone"] / epa_avg["Days with AQI"]
epa_avg = epa_avg.replace([np.inf, -np.inf], np.nan)
print(f"  EPA: {len(epa_avg)} county-averages")

# ── 3. CDC PLACES (2017–2021 averages) ───────────────────────────────────────
print("Loading PLACES data...")
places_raw = pd.read_csv("/Users/sadafsarbazi/PLACES_wide_(2017_2021).csv")
health_vars = [
    "Data_Value_CASTHMA", "Data_Value_CHD", "Data_Value_COPD",
    "Data_Value_DIABETES", "Data_Value_STROKE",
    "Data_Value_MHLTH", "Data_Value_PHLTH", "Data_Value_CSMOKING"
]
state_map = {
    "AL":"alabama","AK":"alaska","AZ":"arizona","AR":"arkansas",
    "CA":"california","CO":"colorado","CT":"connecticut","DE":"delaware",
    "FL":"florida","GA":"georgia","HI":"hawaii","ID":"idaho",
    "IL":"illinois","IN":"indiana","IA":"iowa","KS":"kansas",
    "KY":"kentucky","LA":"louisiana","ME":"maine","MD":"maryland",
    "MA":"massachusetts","MI":"michigan","MN":"minnesota","MS":"mississippi",
    "MO":"missouri","MT":"montana","NE":"nebraska","NV":"nevada",
    "NH":"new hampshire","NJ":"new jersey","NM":"new mexico","NY":"new york",
    "NC":"north carolina","ND":"north dakota","OH":"ohio","OK":"oklahoma",
    "OR":"oregon","PA":"pennsylvania","RI":"rhode island","SC":"south carolina",
    "SD":"south dakota","TN":"tennessee","TX":"texas","UT":"utah",
    "VT":"vermont","VA":"virginia","WA":"washington","WV":"west virginia",
    "WI":"wisconsin","WY":"wyoming"
}
places_filt = places_raw[
    (places_raw["Year"] >= 2017) & (places_raw["Year"] <= 2021)
][["LocationName", "StateAbbr", "Year"] + health_vars].copy()

places_avg = (places_filt.groupby(["StateAbbr", "LocationName"])[health_vars]
              .mean().reset_index())
places_avg["state_clean"]  = places_avg["StateAbbr"].map(state_map)
places_avg["county_clean"] = (places_avg["LocationName"]
                              .str.replace(r"\s*(county|parish|borough)\s*$","",regex=True)
                              .str.lower().str.strip())
places_avg = places_avg.rename(columns={
    "Data_Value_CASTHMA": "asthma_pct",
    "Data_Value_CHD":     "heart_disease_pct",
    "Data_Value_COPD":    "copd_pct",
    "Data_Value_DIABETES":"diabetes_pct",
    "Data_Value_STROKE":  "stroke_pct",
    "Data_Value_MHLTH":   "poor_mental_health_pct",
    "Data_Value_PHLTH":   "poor_physical_health_pct",
    "Data_Value_CSMOKING":"smoking_pct",
})
print(f"  PLACES: {len(places_avg)} county-averages")

# ── 4. MERGE ──────────────────────────────────────────────────────────────────
print("Merging all three datasets...")
health_cols = ["asthma_pct","heart_disease_pct","copd_pct","diabetes_pct",
               "stroke_pct","poor_mental_health_pct","poor_physical_health_pct","smoking_pct"]

m1 = epa_avg.merge(
    places_avg[["state_clean","county_clean","StateAbbr"] + health_cols],
    on=["state_clean","county_clean"], how="inner"
)
m2 = m1.merge(
    acs[["state_clean","county_clean","fips",
         "median_income","education_universe","poverty_count","population","poverty_rate"]],
    on=["state_clean","county_clean"], how="inner"
)

m2["state_label"]  = m2["state_clean"].str.title()
m2["county_label"] = m2["county_clean"].str.title()

print(f"  Final: {len(m2)} counties with complete data")

# ── 5. K-MEANS CLUSTERS ───────────────────────────────────────────────────────
print("Computing community clusters...")
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

cluster_features = ["Median AQI", "median_income", "poverty_rate"]
cluster_df = m2[cluster_features].dropna()
scaler = StandardScaler()
X_scaled = scaler.fit_transform(cluster_df)
kmeans = KMeans(n_clusters=3, random_state=42, n_init="auto")
m2.loc[cluster_df.index, "cluster"] = kmeans.fit_predict(X_scaled)

# Label clusters by poverty rate (ascending)
cluster_poverty = m2.groupby("cluster")["poverty_rate"].mean().sort_values()
label_map = {
    cluster_poverty.index[0]: "Low-burden",
    cluster_poverty.index[1]: "Mid-burden",
    cluster_poverty.index[2]: "High-burden",
}
m2["cluster_label"] = m2["cluster"].map(label_map).fillna("Unknown")

# ── 6. SAVE ───────────────────────────────────────────────────────────────────
m2.to_csv("data/final_data.csv", index=False)
print(f"\nSaved: data/final_data.csv  ({len(m2)} rows, {len(m2.columns)} cols)")
print("Now run: streamlit run app.py")
