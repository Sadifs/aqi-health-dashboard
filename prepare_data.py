"""
Run once to generate data/final_data.csv used by the Streamlit app.
Usage: python prepare_data.py
"""

import pandas as pd
import numpy as np
import requests
import os

os.makedirs("data", exist_ok=True)

# ── 1. FIPS LOOKUP ────────────────────────────────────────────────────────────
print("Fetching county FIPS lookup...")
fips_url = "https://www2.census.gov/geo/docs/reference/codes2020/national_county2020.txt"
fips_df = pd.read_csv(fips_url, sep="|", dtype=str, encoding="latin-1")
fips_df.columns = fips_df.columns.str.strip().str.upper()

state_abbr_to_name = {
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

fips_df["state_clean"] = fips_df["STATE"].map(state_abbr_to_name)
fips_df["county_clean"] = (
    fips_df["COUNTYNAME"]
    .str.lower()
    .str.replace(r"\s*(county|parish|borough|census area|municipality|city and borough|municipio)\s*$",
                 "", regex=True)
    .str.strip()
)
fips_df["fips"] = fips_df["STATEFP"].str.zfill(2) + fips_df["COUNTYFP"].str.zfill(3)
fips_lookup = fips_df[["state_clean", "county_clean", "fips"]].drop_duplicates()
print(f"  FIPS lookup: {len(fips_lookup)} counties")

# ── 2. EPA AQI (2017–2021) ────────────────────────────────────────────────────
print("Loading EPA AQI data...")
aqi = pd.read_excel(
    "/Users/sadafsarbazi/Merged(2017-2022)_EPA_AQI.xlsx",
    engine="openpyxl"
)
epa = aqi[(aqi["Year"] >= 2017) & (aqi["Year"] <= 2021)].copy()

epa["state_clean"] = epa["State"].str.lower().str.strip()
epa["county_clean"] = epa["County"].str.lower().str.strip()

epa_cols = [
    "Days with AQI", "Good Days", "Moderate Days",
    "Unhealthy for Sensitive Groups Days", "Unhealthy Days",
    "Very Unhealthy Days", "Hazardous Days",
    "Max AQI", "90th Percentile AQI", "Median AQI",
    "Days Ozone", "Days PM2.5", "Days PM10",
    "PM25_pct", "Ozone_pct", "NO2_pct", "PM10_pct"
]

epa_avg = (
    epa.groupby(["state_clean", "county_clean"])[epa_cols]
    .mean()
    .reset_index()
)

# Recompute PM2.5 share correctly
epa_avg["pm25_share"] = epa_avg["Days PM2.5"] / epa_avg["Days with AQI"]
epa_avg["ozone_share"] = epa_avg["Days Ozone"] / epa_avg["Days with AQI"]
epa_avg = epa_avg.replace([np.inf, -np.inf], np.nan)
print(f"  EPA: {len(epa_avg)} county-averages")

# ── 3. PLACES HEALTH DATA (2017–2021) ─────────────────────────────────────────
print("Loading PLACES data...")
places = pd.read_csv("/Users/sadafsarbazi/PLACES_wide_(2017_2021).csv")
places.columns = places.columns.str.strip()

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

places_sub = places[["LocationName", "StateAbbr", "Year"] + health_vars].copy()
places_filt = places_sub[(places_sub["Year"] >= 2017) & (places_sub["Year"] <= 2021)]

places_avg = (
    places_filt.groupby(["StateAbbr", "LocationName"])[health_vars]
    .mean()
    .reset_index()
)

places_avg["state_clean"] = places_avg["StateAbbr"].map(state_map)
places_avg["county_clean"] = (
    places_avg["LocationName"]
    .str.lower()
    .str.replace(r"\s*(county|parish|borough|census area|municipality|city and borough|municipio)\s*$",
                 "", regex=True)
    .str.strip()
)

rename_map = {
    "Data_Value_CASTHMA": "asthma_pct",
    "Data_Value_CHD":     "heart_disease_pct",
    "Data_Value_COPD":    "copd_pct",
    "Data_Value_DIABETES":"diabetes_pct",
    "Data_Value_STROKE":  "stroke_pct",
    "Data_Value_MHLTH":   "poor_mental_health_pct",
    "Data_Value_PHLTH":   "poor_physical_health_pct",
    "Data_Value_CSMOKING":"smoking_pct",
}
places_avg = places_avg.rename(columns=rename_map)
print(f"  PLACES: {len(places_avg)} county-averages")

# ── 4. MERGE ──────────────────────────────────────────────────────────────────
print("Merging datasets...")
merged = epa_avg.merge(places_avg[
    ["state_clean","county_clean","StateAbbr"] + list(rename_map.values())
], on=["state_clean","county_clean"], how="inner")

merged = merged.merge(fips_lookup, on=["state_clean","county_clean"], how="left")

merged["state_label"] = merged["state_clean"].str.title()
merged["county_label"] = merged["county_clean"].str.title()

fips_missing = merged["fips"].isna().sum()
print(f"  Merged: {len(merged)} counties, {fips_missing} missing FIPS")

# ── 5. SAVE ───────────────────────────────────────────────────────────────────
out = "data/final_data.csv"
merged.to_csv(out, index=False)
print(f"\nSaved: {out}  ({len(merged)} rows, {len(merged.columns)} cols)")
