import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import statsmodels.api as sm
from scipy import stats as sp_stats
from urllib.request import urlopen
import json

st.set_page_config(
    page_title="Air Quality, Poverty, and Chronic Disease",
    page_icon="",
    layout="wide"
)

# ── DATA ──────────────────────────────────────────────────────────────────────

@st.cache_data
def load_data():
    df = pd.read_csv("data/final_data.csv", dtype={"fips": str})
    df["fips"] = df["fips"].astype(str).str.zfill(5)
    df["income_k"] = df["median_income"] / 1000
    df["poverty_pct"] = df["poverty_rate"] * 100
    return df

@st.cache_data
def load_geojson():
    with urlopen(
        "https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json"
    ) as r:
        return json.load(r)

SES_CONTROLS = ["poverty_rate", "income_k"]

@st.cache_data
def compute_all_regressions(data_csv_hash):
    results = []
    for label, col in HEALTH.items():
        sub = df[[col, "Median AQI"] + SES_CONTROLS].dropna()
        y = sub[col]
        X_simple = sm.add_constant(sub[["Median AQI"]])
        m_simple = sm.OLS(y, X_simple).fit()
        X_adj = sm.add_constant(sub[["Median AQI"] + SES_CONTROLS])
        m_adj = sm.OLS(y, X_adj).fit()
        results.append({
            "Health Outcome": label,
            "Simple R2": round(m_simple.rsquared, 3),
            "Adjusted R2": round(m_adj.rsquared, 3),
            "R2 Gain": round(m_adj.rsquared - m_simple.rsquared, 3),
            "n": len(sub),
        })
    return pd.DataFrame(results)

df = load_data()
counties_geo = load_geojson()

# ── LABELS ────────────────────────────────────────────────────────────────────

HEALTH = {
    "Asthma":                "asthma_pct",
    "COPD":                  "copd_pct",
    "Coronary Heart Disease": "heart_disease_pct",
    "Diabetes":              "diabetes_pct",
    "Stroke":                "stroke_pct",
    "Poor Mental Health":    "poor_mental_health_pct",
    "Poor Physical Health":  "poor_physical_health_pct",
    "Smoking":               "smoking_pct",
}

MAP_OPTIONS = {
    "Poverty Rate (%)":          "poverty_pct",
    "Median Household Income":   "income_k",
    "Median AQI":                "Median AQI",
    "PM2.5 Share of AQI Days":   "pm25_share",
    "Asthma Prevalence (%)":     "asthma_pct",
    "COPD Prevalence (%)":       "copd_pct",
    "Diabetes Prevalence (%)":   "diabetes_pct",
}

STATES = sorted(df["state_label"].dropna().unique())

# ── SIDEBAR ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("Filters")
    state_filter = st.multiselect("State(s)", STATES, default=[], placeholder="All states")
    st.divider()
    st.caption(
        "Data: EPA AQI (2017-2021), CDC PLACES (2017-2021), "
        "Census SAIPE 2021. County-level 5-year averages."
    )
    st.caption(f"{len(df):,} counties across 48 states.")

filtered = df[df["state_label"].isin(state_filter)] if state_filter else df.copy()

# ── HEADER ────────────────────────────────────────────────────────────────────

st.title("Air Quality, Poverty, and Chronic Disease")
st.markdown(
    "County-level analysis across the United States (2017-2021). "
    "Core finding: socioeconomic conditions, not air pollution exposure alone, "
    "predict chronic disease burden. Data: EPA AQI, CDC PLACES, Census SAIPE."
)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Counties analyzed", f"{len(filtered):,}")
m2.metric("Avg poverty rate", f"{filtered['poverty_pct'].mean():.1f}%")
m3.metric("Avg Median AQI", f"{filtered['Median AQI'].mean():.1f}")
m4.metric("Avg COPD prevalence", f"{filtered['copd_pct'].mean():.1f}%")

st.divider()

# ── TABS ──────────────────────────────────────────────────────────────────────

tab_find, tab_map, tab_clust, tab_explore, tab_methods = st.tabs(
    ["Core Finding", "Geographic Map", "Community Clusters", "Data Explorer", "Methods"]
)

# ── TAB 1: CORE FINDING ───────────────────────────────────────────────────────

with tab_find:
    st.subheader("Pollution alone cannot explain chronic disease prevalence")
    st.markdown(
        "PM2.5 exposure by itself explains almost none of the county-level variation in chronic disease. "
        "Adding two socioeconomic controls (poverty rate and median household income) "
        "raises explanatory power by 50 to 65 percentage points across all outcomes."
    )

    outcome_label = st.selectbox("Select health outcome", list(HEALTH.keys()), key="find_outcome")
    outcome_col   = HEALTH[outcome_label]

    reg_df = filtered[["Median AQI", "pm25_share", "poverty_rate", "income_k",
                        outcome_col, "county_label", "state_label",
                        "poverty_pct"]].dropna()

    # Simple model
    X_s = sm.add_constant(reg_df[["Median AQI"]])
    m_s = sm.OLS(reg_df[outcome_col], X_s).fit()

    # Adjusted model
    X_a = sm.add_constant(reg_df[["Median AQI"] + SES_CONTROLS])
    m_a = sm.OLS(reg_df[outcome_col], X_a).fit()

    col_left, col_right = st.columns(2)

    # LEFT: simple
    with col_left:
        st.markdown("#### Without socioeconomic controls")
        r2_s = m_s.rsquared
        st.metric(
            label=f"R-squared: AQI alone predicts {outcome_label}",
            value=f"{r2_s:.3f}",
            delta=None,
            help="R-squared = proportion of variance explained by the model"
        )
        if r2_s < 0.05:
            st.error(f"R-squared = {r2_s:.3f}: Median AQI explains less than 5% of the county-level variation in {outcome_label}.")

        x_vals = reg_df["Median AQI"]
        y_vals = reg_df[outcome_col]
        x_line = np.linspace(x_vals.min(), x_vals.max(), 200)
        y_line = m_s.params["const"] + m_s.params["Median AQI"] * x_line

        fig_s = go.Figure()
        fig_s.add_trace(go.Scatter(
            x=x_vals, y=y_vals, mode="markers",
            marker=dict(size=4, opacity=0.4, color="#aaa"),
            text=reg_df["county_label"] + ", " + reg_df["state_label"],
            name="County",
        ))
        fig_s.add_trace(go.Scatter(
            x=x_line, y=y_line, mode="lines",
            line=dict(color="#e63946", width=2),
            name=f"OLS (R2={r2_s:.3f})",
        ))
        fig_s.update_layout(
            xaxis_title="Median AQI", yaxis_title=f"{outcome_label} (%)",
            height=380, margin=dict(l=20, r=20, t=30, b=20),
            showlegend=True,
        )
        st.plotly_chart(fig_s, use_container_width=True)

    # RIGHT: adjusted
    with col_right:
        st.markdown("#### With poverty and income controls")
        r2_a = m_a.rsquared
        st.metric(
            label=f"R-squared: SES-adjusted model predicts {outcome_label}",
            value=f"{r2_a:.3f}",
            delta=f"+{r2_a - r2_s:.3f} vs. simple model",
        )
        st.success(f"R-squared = {r2_a:.3f}: Adding socioeconomic controls explains {r2_a*100:.0f}% of county-level variation in {outcome_label}.")

        # Partial residual: controlling for poverty, income, education
        # Plot residuals of outcome ~ SES against residuals of AQI ~ SES
        X_ses = sm.add_constant(reg_df[SES_CONTROLS])
        resid_outcome = sm.OLS(reg_df[outcome_col], X_ses).fit().resid
        resid_aqi     = sm.OLS(reg_df["Median AQI"],    X_ses).fit().resid

        slope_partial, intercept_partial, r_partial, p_partial, _ = sp_stats.linregress(
            resid_aqi, resid_outcome
        )
        x_pr = np.linspace(resid_aqi.min(), resid_aqi.max(), 200)
        y_pr = slope_partial * x_pr + intercept_partial

        fig_a = go.Figure()
        fig_a.add_trace(go.Scatter(
            x=resid_aqi, y=resid_outcome, mode="markers",
            marker=dict(size=4, opacity=0.4, color=reg_df["poverty_pct"],
                        colorscale="Reds", showscale=True,
                        colorbar=dict(title="Poverty %", thickness=12, len=0.6)),
            text=reg_df["county_label"] + ", " + reg_df["state_label"],
            name="County (color = poverty rate)",
        ))
        fig_a.add_trace(go.Scatter(
            x=x_pr, y=y_pr, mode="lines",
            line=dict(color="#2a9d8f", width=2),
            name=f"Partial OLS (p={p_partial:.3f})",
        ))
        fig_a.update_layout(
            xaxis_title="AQI residuals (after removing SES)",
            yaxis_title=f"{outcome_label} residuals",
            height=380, margin=dict(l=20, r=20, t=30, b=20),
        )
        st.plotly_chart(fig_a, use_container_width=True)
        st.caption(
            "Partial regression plot: variation in each variable after removing the linear "
            "effect of poverty rate and median income. Color indicates county poverty rate. "
            "Source: EPA AQI, CDC PLACES, Census SAIPE (2017-2021)."
        )

    st.divider()
    st.markdown("#### R-squared across all health outcomes")
    st.markdown("How much of the county-level variance each model explains:")

    reg_table = compute_all_regressions(len(df))
    reg_table = reg_table.sort_values("Adjusted R2", ascending=False)

    fig_r2 = go.Figure()
    fig_r2.add_trace(go.Bar(
        x=reg_table["Health Outcome"],
        y=reg_table["Simple R2"],
        name="PM2.5 alone",
        marker_color="#e63946",
    ))
    fig_r2.add_trace(go.Bar(
        x=reg_table["Health Outcome"],
        y=reg_table["Adjusted R2"],
        name="SES-adjusted",
        marker_color="#2a9d8f",
    ))
    fig_r2.update_layout(
        barmode="group",
        yaxis_title="R-squared",
        xaxis_title="Health outcome",
        height=380,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=40, b=20),
        yaxis_range=[0, 1],
    )
    st.plotly_chart(fig_r2, use_container_width=True)

    display_table = reg_table.rename(columns={
        "Simple R2": "R2 (AQI only)",
        "Adjusted R2": "R2 (SES-adjusted)",
        "R2 Gain": "R2 gain from SES",
    })
    st.dataframe(display_table.reset_index(drop=True), use_container_width=True)

# ── TAB 2: MAP ────────────────────────────────────────────────────────────────

with tab_map:
    st.subheader("Geographic distribution")
    st.markdown(
        "High poverty, high pollution, and high disease burden often co-occur in the same counties. "
        "Use the selector below to explore each layer individually."
    )

    map_label = st.selectbox("Show on map:", list(MAP_OPTIONS.keys()))
    map_col   = MAP_OPTIONS[map_label]

    map_df = filtered[["fips", "county_label", "state_label", map_col]].dropna().copy()
    map_df["fips"] = map_df["fips"].astype(str).str.zfill(5)

    fig_map = px.choropleth(
        map_df,
        geojson=counties_geo,
        locations="fips",
        color=map_col,
        color_continuous_scale="RdYlGn_r" if "aqi" in map_col.lower() or "pct" in map_col.lower() or "rate" in map_col.lower() else "Blues_r",
        scope="usa",
        hover_data={"county_label": True, "state_label": True, "fips": False},
        labels={map_col: map_label, "county_label": "County", "state_label": "State"},
    )
    fig_map.update_layout(
        margin=dict(l=0, r=0, t=10, b=0),
        coloraxis_colorbar=dict(title=map_label, thickness=15),
        height=540,
    )
    st.plotly_chart(fig_map, use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Top 10 counties (highest values)**")
        top10 = (map_df.sort_values(map_col, ascending=False)
                 [["county_label","state_label",map_col]].head(10)
                 .rename(columns={"county_label":"County","state_label":"State",map_col:map_label}))
        st.dataframe(top10.reset_index(drop=True), use_container_width=True)
    with col_b:
        st.markdown("**Bottom 10 counties (lowest values)**")
        bot10 = (map_df.sort_values(map_col, ascending=True)
                 [["county_label","state_label",map_col]].head(10)
                 .rename(columns={"county_label":"County","state_label":"State",map_col:map_label}))
        st.dataframe(bot10.reset_index(drop=True), use_container_width=True)

# ── TAB 3: CLUSTERS ───────────────────────────────────────────────────────────

with tab_clust:
    st.subheader("Three distinct community profiles")
    st.markdown(
        "K-means clustering (k=3) on Median AQI, median household income, and poverty rate "
        "identifies three structurally distinct county types that appear across the US."
    )

    cluster_df = filtered[["Median AQI", "income_k", "poverty_pct", "cluster_label",
                            "county_label", "state_label",
                            "asthma_pct", "copd_pct", "diabetes_pct"]].dropna()

    cluster_colors = {
        "Low-burden":  "#2a9d8f",
        "Mid-burden":  "#e9c46a",
        "High-burden": "#e63946",
    }

    col_l, col_r = st.columns([2, 1])

    with col_l:
        fig_cl = px.scatter(
            cluster_df,
            x="Median AQI",
            y="income_k",
            color="cluster_label",
            color_discrete_map=cluster_colors,
            size="poverty_pct",
            size_max=18,
            hover_data={"county_label": True, "state_label": True,
                        "poverty_pct": True, "income_k": True},
            labels={
                "Median AQI":   "Median AQI",
                "income_k":     "Median Income ($thousands)",
                "poverty_pct":  "Poverty Rate (%)",
                "cluster_label":"Community type",
                "county_label": "County",
                "state_label":  "State",
            },
            height=480,
        )
        fig_cl.update_layout(
            legend=dict(title="Community type", orientation="v"),
            margin=dict(l=20, r=20, t=20, b=20),
        )
        st.plotly_chart(fig_cl, use_container_width=True)
        st.caption("Bubble size = poverty rate. Each bubble is one US county.")

    with col_r:
        st.markdown("**Cluster profiles**")
        profile = (cluster_df.groupby("cluster_label")
                   .agg(
                       Counties=("county_label", "count"),
                       Avg_AQI=("Median AQI", "mean"),
                       Avg_Income=("income_k", "mean"),
                       Avg_Poverty=("poverty_pct", "mean"),
                       Avg_COPD=("copd_pct", "mean"),
                       Avg_Diabetes=("diabetes_pct", "mean"),
                   ).round(1))
        profile.columns = ["Counties", "Avg AQI", "Avg Income ($k)", "Poverty (%)",
                           "COPD (%)", "Diabetes (%)"]
        st.dataframe(profile, use_container_width=True)

        st.markdown("""
**Low-burden:** Higher incomes, lower poverty, lower disease rates.
Pollution exposure is moderate to low.

**Mid-burden:** Middle-income counties with intermediate health and pollution outcomes.
The most geographically dispersed group, with intermediate health and pollution outcomes.

**High-burden:** Lower incomes, higher poverty rates, and elevated chronic disease prevalence.
Often in Appalachia, the Mississippi Delta, and the rural South.
""")

    st.divider()
    st.markdown("#### Cluster distribution on map")

    cluster_map_df = filtered[["fips","cluster_label","county_label","state_label"]].dropna().copy()
    cluster_map_df["fips"] = cluster_map_df["fips"].astype(str).str.zfill(5)
    cluster_map_df["cluster_num"] = cluster_map_df["cluster_label"].map(
        {"Low-burden": 0, "Mid-burden": 1, "High-burden": 2}
    )

    fig_cm = px.choropleth(
        cluster_map_df,
        geojson=counties_geo,
        locations="fips",
        color="cluster_num",
        color_continuous_scale=[(0,"#2a9d8f"),(0.5,"#e9c46a"),(1,"#e63946")],
        range_color=[0,2],
        scope="usa",
        hover_data={"county_label": True, "state_label": True,
                    "cluster_label": True, "fips": False},
        labels={"cluster_num": "Community type"},
    )
    fig_cm.update_layout(
        margin=dict(l=0, r=0, t=10, b=0), height=460,
        coloraxis_showscale=False,
    )
    st.plotly_chart(fig_cm, use_container_width=True)
    st.caption("Green = Low-burden, Yellow = Mid-burden, Red = High-burden communities.")

# ── TAB 4: EXPLORER ───────────────────────────────────────────────────────────

with tab_explore:
    st.subheader("Custom scatter explorer")

    ALL_NUMERIC = {
        "Median AQI":            "Median AQI",
        "PM2.5 Share (%)":       "pm25_share",
        "Poverty Rate (%)":      "poverty_pct",
        "Median Income ($k)":    "income_k",
        "Asthma (%)":            "asthma_pct",
        "COPD (%)":              "copd_pct",
        "Coronary Heart Disease (%)": "heart_disease_pct",
        "Diabetes (%)":          "diabetes_pct",
        "Stroke (%)":            "stroke_pct",
        "Poor Mental Health (%)":"poor_mental_health_pct",
        "Poor Physical Health (%)":"poor_physical_health_pct",
        "Smoking (%)":           "smoking_pct",
    }
    COLOR_BY = {
        "Poverty Rate":      "poverty_pct",
        "Median Income":     "income_k",
        "Median AQI":        "Median AQI",
        "Community cluster": "cluster_label",
        "None":              None,
    }

    ex_col1, ex_col2, ex_col3 = st.columns(3)
    x_label = ex_col1.selectbox("X axis", list(ALL_NUMERIC.keys()), index=0)
    y_label = ex_col2.selectbox("Y axis", list(ALL_NUMERIC.keys()), index=5)
    c_label = ex_col3.selectbox("Color by", list(COLOR_BY.keys()))

    x_col  = ALL_NUMERIC[x_label]
    y_col  = ALL_NUMERIC[y_label]
    c_col  = COLOR_BY[c_label]

    ex_df = filtered[[x_col, y_col, "county_label", "state_label"] +
                     ([c_col] if c_col else [])].dropna()

    if c_col == "cluster_label":
        fig_ex = px.scatter(
            ex_df, x=x_col, y=y_col, color=c_col,
            color_discrete_map=cluster_colors,
            hover_data={"county_label": True, "state_label": True},
            labels={x_col: x_label, y_col: y_label, c_col: c_label},
            opacity=0.6, height=500,
        )
    elif c_col:
        fig_ex = px.scatter(
            ex_df, x=x_col, y=y_col, color=c_col,
            color_continuous_scale="RdYlGn_r",
            hover_data={"county_label": True, "state_label": True},
            labels={x_col: x_label, y_col: y_label, c_col: c_label},
            opacity=0.6, height=500,
        )
    else:
        fig_ex = px.scatter(
            ex_df, x=x_col, y=y_col,
            hover_data={"county_label": True, "state_label": True},
            labels={x_col: x_label, y_col: y_label},
            opacity=0.6, height=500, color_discrete_sequence=["#457b9d"],
        )

    if x_col != c_col and y_col != c_col:
        sub_ex = ex_df[[x_col, y_col]].dropna()
        slope_ex, int_ex, r_ex, p_ex, _ = sp_stats.linregress(sub_ex[x_col], sub_ex[y_col])
        xr = np.linspace(sub_ex[x_col].min(), sub_ex[x_col].max(), 200)
        yr = slope_ex * xr + int_ex
        fig_ex.add_trace(go.Scatter(
            x=xr, y=yr, mode="lines",
            line=dict(color="black", width=1.5, dash="dash"),
            name=f"OLS (r={r_ex:.2f}, p {'< 0.001' if p_ex < 0.001 else f'= {p_ex:.3f}'})",
        ))

    fig_ex.update_layout(margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(fig_ex, use_container_width=True)

    if x_col != c_col and y_col != c_col:
        e1, e2, e3, e4 = st.columns(4)
        e1.metric("Pearson r", f"{r_ex:.3f}")
        e2.metric("p-value", "< 0.001" if p_ex < 0.001 else f"{p_ex:.3f}")
        e3.metric("R-squared", f"{r_ex**2:.3f}")
        e4.metric("n (counties)", f"{len(sub_ex):,}")

# ── TAB 5: METHODS ────────────────────────────────────────────────────────────

with tab_methods:
    st.subheader("Data sources")
    st.markdown("""
| Source | Description | Years | Coverage |
|--------|-------------|-------|----------|
| [EPA Air Quality System](https://www.epa.gov/aqs) | County-level AQI, PM2.5, ozone, NO2 monitoring data | 2017-2021 | 1,061 monitored counties |
| [CDC PLACES](https://www.cdc.gov/places) | County-level prevalence estimates for 27 chronic conditions | 2017-2021 | 3,144 counties |
| [Census SAIPE 2021](https://www.census.gov/programs-surveys/saipe.html) | County-level poverty rate and median household income estimates | 2021 | All US counties |

**Processing:** 5-year averages computed for EPA and PLACES (2017-2021). SAIPE 2021 used for socioeconomic variables. Counties merged on FIPS code. Final dataset: 1,022 counties with complete data across all three sources.
""")

    st.subheader("Regression methodology")
    st.markdown("""
**Simple OLS:** `health_outcome ~ median_AQI`

**SES-adjusted OLS:** `health_outcome ~ median_AQI + poverty_rate + median_income`

Socioeconomic controls sourced from SAIPE (Small Area Income and Poverty Estimates), Census Bureau 2021. Models run separately for each of the eight health outcomes from CDC PLACES.

**Partial regression plots (Core Finding tab):** Each axis shows residuals after removing the linear effect of poverty rate and median income, isolating the AQI-health relationship net of those socioeconomic controls.

**K-means clustering:** Features: Median AQI, median household income (SAIPE 2021), poverty rate (SAIPE 2021). Standardized before clustering. k=3 selected based on within-cluster sum of squares elbow analysis from the underlying BSAN 6050 project. Clusters labeled by ascending poverty rate.
""")

    st.subheader("Key findings summary")
    st.markdown("""
Across 1,022 US counties (2017-2021):

1. **PM2.5 alone has near-zero explanatory power.** R-squared values from simple AQI regressions range from 0.000 to 0.03 across all eight chronic disease outcomes. Air quality monitoring data, by itself, does not predict where chronic disease burden is highest.

2. **Socioeconomic controls explain 55-68% of variance.** Adding county-level poverty rate and median household income raises R-squared to 0.55-0.68 across health outcomes, representing a gain of 50 to 65 percentage points.

3. **Three structurally distinct community types exist.** K-means clustering identifies low-burden (higher income, lower poverty), mid-burden, and high-burden (lower income, higher poverty, higher disease) county profiles that are geographically concentrated but appear in every region of the country.

4. **Implication for policy.** Interventions targeting air quality improvements alone, without addressing the underlying socioeconomic conditions that concentrate disease burden, are unlikely to reduce chronic disease disparities at the population level.
""")

    st.subheader("Limitations")
    st.markdown("""
- **Ecological fallacy.** County-level correlations do not imply individual-level causation.
- **Monitor placement bias.** EPA monitoring stations are not randomly placed; rural and lower-income counties are underrepresented in the EPA AQI dataset.
- **Socioeconomic confounding not fully resolved.** The adjusted model controls for two SES dimensions (poverty rate and median income) but does not capture educational attainment, healthcare access, occupational exposure, dietary factors, or historical redlining.
- **Cross-sectional design.** This analysis cannot establish temporal ordering between pollution exposure and health outcomes.
- **Educational attainment not modeled.** Adding a measure such as share of adults without a high school diploma would improve model specification and is a proposed extension.
""")

    st.subheader("Proposed extensions")
    st.markdown("""
1. **Behavioral and access mediators.** Add Google Trends search volume for health-related terms (smoking, fast food, mental health) and CMS/HRSA measures of healthcare access as mediating variables between SES and health outcomes.
2. **Longitudinal panel analysis.** Test whether counties that improved AQI between 2017 and 2022 saw corresponding health improvements, and whether improvement was moderated by SES level (interaction between AQI change and poverty rate).
3. **Spatial regression.** Apply a spatial lag or spatial error model to account for geographic autocorrelation in both pollution and health outcomes.
4. **Sub-county resolution.** Expand to ZIP code or census tract level using CDC PLACES tract-level data and EPA monitoring interpolation.
    """)

    st.subheader("About this project")
    st.markdown("""
This dashboard originated from research conducted in BSAN 6050 at Loyola Marymount University and has been extended into an interactive public tool.

**Author:** Sadaf Sarbazi, M.Env.Sc. (University of Toronto), M.S. Business Analytics (Loyola Marymount University)

**Contact:** sadaf.sarbazi@yahoo.com

**GitHub:** [github.com/Sadifs/aqi-health-dashboard](https://github.com/Sadifs/aqi-health-dashboard)
""")
