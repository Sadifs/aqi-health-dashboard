import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from scipy import stats
from urllib.request import urlopen
import json

st.set_page_config(
    page_title="Air Quality & Public Health Dashboard",
    page_icon="🌬",
    layout="wide"
)

# ── DATA ──────────────────────────────────────────────────────────────────────

@st.cache_data
def load_data():
    df = pd.read_csv("data/final_data.csv", dtype={"fips": str})
    df["fips"] = df["fips"].str.zfill(5)
    return df

@st.cache_data
def load_geojson():
    with urlopen(
        "https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json"
    ) as r:
        return json.load(r)

df = load_data()
counties_geo = load_geojson()

# ── LABELS ────────────────────────────────────────────────────────────────────

POLLUTANTS = {
    "PM2.5 Share of Days (%)": "pm25_share",
    "Ozone Share of Days (%)": "ozone_share",
    "Unhealthy Days (avg/yr)": "Unhealthy Days",
    "Median AQI": "Median AQI",
}

HEALTH = {
    "Asthma": "asthma_pct",
    "COPD": "copd_pct",
    "Coronary Heart Disease": "heart_disease_pct",
    "Diabetes": "diabetes_pct",
    "Stroke": "stroke_pct",
    "Poor Mental Health Days": "poor_mental_health_pct",
    "Poor Physical Health Days": "poor_physical_health_pct",
    "Smoking": "smoking_pct",
}

STATES = sorted(df["state_label"].dropna().unique())

# ── SIDEBAR ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("Filters")
    state_filter = st.multiselect(
        "State(s)", STATES, default=[], placeholder="All states"
    )
    pollutant_label = st.selectbox("Air quality metric", list(POLLUTANTS))
    health_label    = st.selectbox("Health outcome", list(HEALTH))
    pollutant_col   = POLLUTANTS[pollutant_label]
    health_col      = HEALTH[health_label]

    st.divider()
    st.caption(
        "Data: EPA AQI (2017–2021), CDC PLACES (2017–2021). "
        "County-level 5-year averages. 1,022 counties across 48 states."
    )

filtered = df[df["state_label"].isin(state_filter)] if state_filter else df.copy()
plot_df  = filtered[[pollutant_col, health_col, "fips", "county_label",
                      "state_label", "StateAbbr"]].dropna()

# ── HEADER ────────────────────────────────────────────────────────────────────

st.title("Air Quality & Public Health")
st.markdown(
    "County-level analysis of air pollution exposure and chronic disease prevalence "
    "across the United States, 2017–2021. Data: EPA Air Quality System · CDC PLACES."
)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Counties", f"{len(plot_df):,}")
col2.metric("Avg " + pollutant_label.split("(")[0].strip(),
            f"{plot_df[pollutant_col].mean():.3f}")
col3.metric(f"Avg {health_label} prevalence",
            f"{plot_df[health_col].mean():.1%}")
col4.metric("Correlation (r)",
            f"{plot_df[pollutant_col].corr(plot_df[health_col]):.3f}")

st.divider()

# ── TABS ──────────────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4 = st.tabs(
    ["US Map", "Pollution vs. Health", "County Rankings", "Methods & Findings"]
)

# ── TAB 1: MAP ────────────────────────────────────────────────────────────────

with tab1:
    map_metric = st.radio(
        "Map shows:", [pollutant_label, health_label], horizontal=True
    )
    map_col = pollutant_col if map_metric == pollutant_label else health_col

    map_df = filtered[["fips", "county_label", "state_label", map_col]].dropna()
    map_df["fips"] = map_df["fips"].astype(str).str.zfill(5)

    fig_map = px.choropleth(
        map_df,
        geojson=counties_geo,
        locations="fips",
        color=map_col,
        color_continuous_scale="RdYlGn_r",
        scope="usa",
        hover_data={"county_label": True, "state_label": True, "fips": False},
        labels={map_col: map_metric, "county_label": "County", "state_label": "State"},
    )
    fig_map.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        coloraxis_colorbar=dict(title=map_metric, thickness=15),
        height=520,
    )
    st.plotly_chart(fig_map, use_container_width=True)
    st.caption(
        f"Showing {len(map_df):,} counties. Red = higher values, green = lower."
    )

# ── TAB 2: SCATTER ────────────────────────────────────────────────────────────

with tab2:
    st.subheader(f"{pollutant_label} vs. {health_label} prevalence")

    valid = plot_df.dropna(subset=[pollutant_col, health_col])

    slope, intercept, r, p, se = stats.linregress(
        valid[pollutant_col], valid[health_col]
    )
    x_line = np.linspace(valid[pollutant_col].min(), valid[pollutant_col].max(), 200)
    y_line = slope * x_line + intercept

    fig_scatter = px.scatter(
        valid,
        x=pollutant_col,
        y=health_col,
        color="state_label" if not state_filter else None,
        hover_data={"county_label": True, "state_label": True},
        labels={
            pollutant_col: pollutant_label,
            health_col: f"{health_label} prevalence",
            "state_label": "State",
            "county_label": "County",
        },
        opacity=0.6,
        height=500,
    )
    fig_scatter.add_trace(go.Scatter(
        x=x_line, y=y_line, mode="lines",
        line=dict(color="black", width=2, dash="dash"),
        name=f"OLS (r={r:.2f}, p={p:.3f})",
    ))
    fig_scatter.update_layout(legend_title="State", showlegend=True)
    st.plotly_chart(fig_scatter, use_container_width=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Pearson r", f"{r:.3f}")
    c2.metric("p-value", f"{p:.4f}" if p >= 0.0001 else "< 0.0001")
    c3.metric("Slope", f"{slope:.4f}")
    c4.metric("n (counties)", f"{len(valid):,}")

    if p < 0.05:
        direction = "positively" if slope > 0 else "negatively"
        st.info(
            f"**Statistically significant association (p < 0.05).** "
            f"Counties with higher {pollutant_label.lower()} tend to have "
            f"{direction} higher {health_label.lower()} prevalence. "
            f"Note: this is an ecological correlation — causal interpretation "
            f"requires controlling for confounders (income, smoking, healthcare access)."
        )

# ── TAB 3: RANKINGS ───────────────────────────────────────────────────────────

with tab3:
    st.subheader("Highest-burden counties")
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown(f"**Top 15 by {pollutant_label}**")
        top_poll = (
            filtered[["county_label", "state_label", pollutant_col]]
            .dropna()
            .sort_values(pollutant_col, ascending=False)
            .head(15)
            .rename(columns={
                "county_label": "County",
                "state_label":  "State",
                pollutant_col:  pollutant_label,
            })
        )
        st.dataframe(top_poll.reset_index(drop=True), use_container_width=True)

    with col_b:
        st.markdown(f"**Top 15 by {health_label} prevalence**")
        top_health = (
            filtered[["county_label", "state_label", health_col]]
            .dropna()
            .sort_values(health_col, ascending=False)
            .head(15)
            .rename(columns={
                "county_label": "County",
                "state_label":  "State",
                health_col:     health_label,
            })
        )
        st.dataframe(top_health.reset_index(drop=True), use_container_width=True)

    st.subheader("Summary by state")
    state_summary = (
        filtered.groupby("state_label")[[pollutant_col, health_col]]
        .mean()
        .sort_values(health_col, ascending=False)
        .reset_index()
        .rename(columns={
            "state_label": "State",
            pollutant_col: pollutant_label,
            health_col:    health_label,
        })
    )
    fig_bar = px.bar(
        state_summary.head(20),
        x="State", y=health_label,
        color=pollutant_label,
        color_continuous_scale="RdYlGn_r",
        labels={health_label: f"Avg {health_label} prevalence"},
        height=400,
    )
    fig_bar.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig_bar, use_container_width=True)

# ── TAB 4: METHODS ────────────────────────────────────────────────────────────

with tab4:
    st.subheader("Data sources")
    st.markdown("""
| Source | Description | Years | Coverage |
|--------|-------------|-------|----------|
| EPA Air Quality System | County-level AQI, PM2.5, ozone, NO2 monitoring data | 2017–2022 | 1,061 counties with monitors |
| CDC PLACES | County-level prevalence estimates for 27 chronic conditions | 2017–2021 | 3,144 counties |
| US Census FIPS reference | County FIPS codes for geographic matching | 2020 | All US counties |

**Processing:** 5-year averages (2017–2021) computed for both EPA and PLACES. Counties matched on cleaned state + county name.
Final dataset: **1,022 counties** with complete air quality and health outcome data.
    """)

    st.subheader("Key regression findings (PM2.5 share → health outcomes)")
    from scipy import stats as sp

    results = []
    for label, col in HEALTH.items():
        sub = df[["pm25_share", col]].dropna()
        if len(sub) < 30:
            continue
        slope, intercept, r, p, se = sp.linregress(sub["pm25_share"], sub[col])
        results.append({
            "Health outcome": label,
            "Pearson r": round(r, 3),
            "Slope": round(slope, 4),
            "p-value": "< 0.001" if p < 0.001 else round(p, 4),
            "n": len(sub),
        })
    results_df = pd.DataFrame(results).sort_values("Pearson r", ascending=False)
    st.dataframe(results_df.reset_index(drop=True), use_container_width=True)

    st.subheader("Limitations")
    st.markdown("""
- **Ecological fallacy:** County-level correlations do not imply individual-level causation.
- **Monitor coverage bias:** EPA monitoring stations are non-randomly placed; rural and low-income counties are under-represented.
- **Confounding:** Associations with PM2.5 are not adjusted for income, smoking prevalence, healthcare access, or occupational exposures in this dashboard. Adjusted models (controlling for poverty rate and median income via Census ACS) show attenuated but persistent associations for COPD and heart disease.
- **Temporal mismatch:** Health prevalence reflects current conditions; pollution exposure reflects county-level 5-year averages but does not capture lifetime exposure history.
    """)

    st.subheader("Proposed extensions")
    st.markdown("""
1. Add Census ACS socioeconomic controls (income, poverty, education) to run adjusted OLS models
2. Expand to ZIP code or census tract level for higher spatial resolution
3. Analyze temporal trends: did counties that improved AQI see corresponding health improvements?
4. Apply spatial regression (spatial lag model) to account for geographic autocorrelation
    """)
