# Air Quality, Poverty, and Chronic Disease

Interactive county-level analysis of air pollution exposure, socioeconomic conditions, and chronic disease prevalence across the United States (2017-2021).

**Live app:** [aqi-health.streamlit.app](https://aqi-health.streamlit.app)

## Core finding

PM2.5 air pollution exposure alone explains near-zero variance in county-level chronic disease burden (R-squared 0.00 to 0.04). Adding socioeconomic controls, poverty rate, median household income, and educational attainment, raises R-squared to 0.32-0.69 across all eight health outcomes (a gain of 31 to 67 percentage points). Poverty, not pollution exposure, is the primary predictor of chronic disease at the county level.

**Extension:** does local economic growth help or hurt this picture? County-level establishment growth (Census County Business Patterns, 2017-2021) predicts both worse air quality and better income/poverty conditions, confirming two real, competing channels. The income/poverty channel is 15 to over 100 times larger in magnitude, and growth's net effect on health is mixed rather than uniform, protective for asthma, COPD, and smoking, harmful for diabetes and poor physical health.

## Dashboard tabs

- **Core Finding:** Side-by-side comparison of simple vs. SES-adjusted OLS regression, R-squared comparison chart across all health outcomes, partial regression plots
- **Geographic Map:** Choropleth maps of poverty rate, AQI, income, and disease prevalence by county
- **Community Clusters:** K-means clustering (k=3) identifying low-burden, mid-burden, and high-burden county profiles; cluster map
- **Economic Growth:** Tests whether county-level economic growth (2017-2021 establishment growth) helps or hurts community health, and through which pathway, worsening air quality or improving income and poverty. The income/poverty pathway dominates in magnitude; growth's net effect on health is mixed by condition.
- **Data Explorer:** Custom scatter explorer for any variable pair with OLS overlay
- **Methods:** Data sources, regression methodology, limitations, and proposed extensions

## Data sources

| Source | Description | Coverage |
|--------|-------------|----------|
| [EPA Air Quality System](https://www.epa.gov/outdoor-air-quality-data) | Annual county-level AQI, PM2.5, ozone, NO2 monitoring data (2017-2021) | 1,061 monitored counties |
| [CDC PLACES](https://www.cdc.gov/places/) | County-level prevalence estimates for 27 chronic conditions (2017-2021) | 3,144 counties |
| [US Census ACS 5-year](https://www.census.gov/programs-surveys/acs) | Median household income, poverty rate, educational attainment (2021) | All US counties |
| [US Census County Business Patterns](https://www.census.gov/programs-surveys/cbp.html) | County-level establishment counts, used as an economic growth proxy | 2017, 2021 |

Final merged dataset: 1,022 counties across 48 states.

## Setup

```bash
# Clone the repo
git clone https://github.com/Sadifs/aqi-health-dashboard
cd aqi-health-dashboard

# Install dependencies
pip install -r requirements.txt

# Get a free Census API key at:
# https://api.census.gov/data/key_signup.html
# Then generate the processed data file (run once):
python prepare_data.py <YOUR_CENSUS_API_KEY>

# Add the economic growth measure (no API key needed, public bulk files)
python fetch_growth_data.py

# Launch the dashboard
streamlit run app.py
```

> Note: `prepare_data.py` reads the source EPA and PLACES files (not included due to size),
> fetches Census ACS data via API, and writes `data/final_data.csv`. `fetch_growth_data.py` then
> adds county-level establishment growth (2017-2021) from Census County Business Patterns.

## Health outcomes

Asthma, COPD, coronary heart disease, diabetes, stroke, poor mental health days, poor physical health days, smoking prevalence.

## Author

Sadaf Sarbazi

M.Env.Sc., University of Toronto

M.S. Business Analytics, Loyola Marymount University

[linkedin.com/in/sadaf-sarbazi](https://linkedin.com/in/sadaf-sarbazi)
