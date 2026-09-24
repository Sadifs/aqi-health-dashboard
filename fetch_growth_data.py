"""
Adds a county-level economic growth measure to data/final_data.csv, used by the
"Economic Growth" dashboard tab. Unlike the ACS pull in prepare_data.py, this
uses the Census Bureau's public bulk County Business Patterns files directly,
no API key required.

Usage: python fetch_growth_data.py
(Run prepare_data.py first to generate data/final_data.csv.)
"""

import pandas as pd
import numpy as np
import requests
import zipfile
import io

CBP_URLS = {
    2017: "https://www2.census.gov/programs-surveys/cbp/datasets/2017/cbp17co.zip",
    2021: "https://www2.census.gov/programs-surveys/cbp/datasets/2021/cbp21co.zip",
}


def load_cbp_establishments(year):
    print(f"Downloading CBP {year} county file...")
    r = requests.get(CBP_URLS[year], timeout=120)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    fname = [n for n in z.namelist() if n.endswith(".txt")][0]
    df = pd.read_csv(z.open(fname), dtype=str)
    df.columns = [c.strip() for c in df.columns]
    # naics == "------" is the total-across-all-industries row for each county
    tot = df[df["naics"].str.strip() == "------"].copy()
    tot["fips"] = (tot["fipstate"].str.zfill(2) + tot["fipscty"].str.zfill(3)).astype(int)
    tot["est"] = pd.to_numeric(tot["est"], errors="coerce")
    return tot[["fips", "est"]].rename(columns={"est": f"est_{year}"})


def main():
    c21 = load_cbp_establishments(2021)
    c17 = load_cbp_establishments(2017)
    growth = c21.merge(c17, on="fips", how="inner")
    growth["growth_5yr_pct"] = (growth["est_2021"] - growth["est_2017"]) / growth["est_2017"]

    df = pd.read_csv("data/final_data.csv")
    df = df.drop(columns=[c for c in ["est_2017", "est_2021", "growth_5yr_pct", "growth_w"] if c in df.columns])
    merged = df.merge(growth, on="fips", how="left")

    lo, hi = merged["growth_5yr_pct"].quantile([0.01, 0.99])
    merged["growth_w"] = merged["growth_5yr_pct"].clip(lo, hi)

    print(f"Matched growth data for {merged['growth_w'].notna().sum()} of {len(merged)} counties")
    merged.to_csv("data/final_data.csv", index=False)
    print("Saved: data/final_data.csv (with growth_w column)")


if __name__ == "__main__":
    main()
