"""
Moderation analysis (suggested by Prof. Richard Tang): does poverty change the strength of
(A) the air quality -> health relationship and (B) the economic growth -> health relationship?

Reproduces the results reported in the research update. Not shown on the dashboard.

Models (OLS, mean-centered predictors, HC3 heteroskedasticity-robust standard errors):
  A: outcome ~ AQI * poverty + median income
  B: outcome ~ growth * poverty + AQI + median income
Robustness: model B with state fixed effects, Bonferroni threshold 0.05 / 8.

Run:  python moderation_analysis.py   (reads data/final_data.csv)
"""
import pandas as pd
import statsmodels.formula.api as smf

HEALTH = {
    "Asthma": "asthma_pct",
    "COPD": "copd_pct",
    "Coronary heart disease": "heart_disease_pct",
    "Diabetes": "diabetes_pct",
    "Stroke": "stroke_pct",
    "Poor mental health": "poor_mental_health_pct",
    "Poor physical health": "poor_physical_health_pct",
    "Smoking": "smoking_pct",
}
SE = "HC3"
BONFERRONI = 0.05 / len(HEALTH)

df = pd.read_csv("data/final_data.csv")
for col, name in [("Median AQI", "aqi_c"), ("poverty_rate", "pov_c"),
                  ("median_income", "inc_c"), ("growth_w", "growth_c")]:
    df[name] = df[col] - df[col].mean()

rows = []
for label, y in HEALTH.items():
    a = smf.ols(f"{y} ~ aqi_c * pov_c + inc_c", df).fit(cov_type=SE)
    b = smf.ols(f"{y} ~ growth_c * pov_c + aqi_c + inc_c", df).fit(cov_type=SE)
    b_fe = smf.ols(f"{y} ~ growth_c * pov_c + aqi_c + inc_c + C(state_clean)", df).fit(cov_type=SE)
    rows.append({
        "Outcome": label,
        "AQI x poverty p": a.pvalues["aqi_c:pov_c"],
        "Growth x poverty b": b.params["growth_c:pov_c"],
        "Growth x poverty p": b.pvalues["growth_c:pov_c"],
        "Growth x poverty p (state FE)": b_fe.pvalues["growth_c:pov_c"],
    })

res = pd.DataFrame(rows)
res["Survives Bonferroni (state FE)"] = res["Growth x poverty p (state FE)"] < BONFERRONI
pd.set_option("display.width", 160)
print(res.round(4).to_string(index=False))
print(f"\nAQI x poverty significant (p<.05): {int((res['AQI x poverty p'] < .05).sum())} of 8")
print(f"Growth x poverty significant, base model: {int((res['Growth x poverty p'] < .05).sum())} of 8")
print(f"Growth x poverty significant, state FE: {int((res['Growth x poverty p (state FE)'] < .05).sum())} of 8")
print(f"Survive Bonferroni (p < {BONFERRONI:.5f}): {int(res['Survives Bonferroni (state FE)'].sum())}")
print(f"COPD-smoking correlation: r = {df['copd_pct'].corr(df['smoking_pct']):.2f}")
