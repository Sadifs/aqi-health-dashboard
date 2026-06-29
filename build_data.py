"""
Builds data/final_data.csv from existing EPA+PLACES data + SAIPE (no API key needed).
Run once: python build_data.py
"""

import requests, io, os
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

os.makedirs("data", exist_ok=True)

# ── 1. SAIPE 2021 (poverty + income, county level) ───────────────────────────
print("Fetching SAIPE 2021 data...")
url = "https://www2.census.gov/programs-surveys/saipe/datasets/2021/2021-state-and-county/est21all.xls"
r = requests.get(url, timeout=60)
saipe_raw = pd.read_excel(io.BytesIO(r.content), skiprows=3, dtype=str)

saipe = saipe_raw[
    (saipe_raw["County FIPS Code"] != "000") &
    (saipe_raw["County FIPS Code"].notna()) &
    (saipe_raw["State FIPS Code"] != "00")
].copy()

saipe["fips"] = saipe["State FIPS Code"].str.zfill(2) + saipe["County FIPS Code"].str.zfill(3)
saipe["poverty_rate"] = pd.to_numeric(saipe["Poverty Percent, All Ages"], errors="coerce") / 100
saipe["median_income"] = pd.to_numeric(saipe["Median Household Income"], errors="coerce")
saipe = saipe[["fips", "poverty_rate", "median_income"]].dropna()
print(f"  SAIPE: {len(saipe)} counties")

# ── 2. Existing EPA + PLACES data ─────────────────────────────────────────────
print("Loading existing EPA + PLACES data...")
base = pd.read_csv("data/final_data.csv", dtype={"fips": str})
base["fips"] = base["fips"].astype(str).str.zfill(5)
print(f"  Base: {len(base)} counties")

# ── 3. Merge ──────────────────────────────────────────────────────────────────
df = base.merge(saipe, on="fips", how="inner")
df["income_k"]    = df["median_income"] / 1000
df["poverty_pct"] = df["poverty_rate"] * 100
print(f"  Merged: {len(df)} counties")

# ── 4. K-means clusters ───────────────────────────────────────────────────────
print("Computing clusters...")
cluster_features = ["Median AQI", "income_k", "poverty_pct"]
cluster_df = df[cluster_features].dropna()

scaler = StandardScaler()
X = scaler.fit_transform(cluster_df)
km = KMeans(n_clusters=3, random_state=42, n_init="auto")
df.loc[cluster_df.index, "cluster"] = km.fit_predict(X)

# Label by ascending poverty
order = df.groupby("cluster")["poverty_pct"].mean().sort_values().index.tolist()
label_map = {order[0]: "Low-burden", order[1]: "Mid-burden", order[2]: "High-burden"}
df["cluster_label"] = df["cluster"].map(label_map).fillna("Unknown")

# ── 5. Save ───────────────────────────────────────────────────────────────────
df.to_csv("data/final_data.csv", index=False)
print(f"\nSaved: data/final_data.csv  ({len(df)} rows, {len(df.columns)} cols)")
print("Columns added: poverty_rate, median_income, income_k, poverty_pct, cluster, cluster_label")

# Quick sanity check
print("\nSanity check:")
print(f"  Avg poverty rate: {df['poverty_pct'].mean():.1f}%")
print(f"  Avg median income: ${df['median_income'].mean():,.0f}")
print(f"  Cluster counts:\n{df['cluster_label'].value_counts().to_string()}")
