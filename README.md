# Air Quality & Public Health Dashboard

Interactive county-level analysis of air pollution exposure and chronic disease prevalence across the United States (2017–2021).

**Live app:** [Link after Streamlit Cloud deploy]

## What it shows

- **US choropleth map** of PM2.5 exposure or health outcome prevalence by county
- **Correlation explorer** with OLS regression line and significance statistics for any pollutant × health outcome pair
- **County and state rankings** for pollution burden and disease prevalence
- **Regression findings table** across eight health outcomes with PM2.5 exposure
- **Methods and limitations** section documenting data sources, processing steps, and interpretation caveats

## Data sources

| Source | Description | Coverage |
|--------|-------------|----------|
| [EPA Air Quality System](https://www.epa.gov/outdoor-air-quality-data) | Annual county-level AQI, PM2.5, ozone, NO2 monitoring data (2017–2021) | 1,061 monitored counties |
| [CDC PLACES](https://www.cdc.gov/places/) | County-level prevalence estimates for 27 chronic conditions (2017–2021) | 3,144 counties |

Final merged dataset: **1,022 counties** across 48 states with complete air quality and health outcome data.

## Health outcomes included

Asthma · COPD · Coronary heart disease · Diabetes · Stroke · Poor mental health days · Poor physical health days · Smoking prevalence

## Setup

```bash
# Clone the repo
git clone https://github.com/Sadifs/aqi-health-dashboard
cd aqi-health-dashboard

# Install dependencies
pip install -r requirements.txt

# Generate the processed data file (run once)
python prepare_data.py

# Launch the dashboard
streamlit run app.py
```

> Note: `prepare_data.py` reads the source EPA and PLACES files and writes `data/final_data.csv`. The source files are not included in the repo due to size; see the EPA and CDC PLACES links above to download them.

## Key findings

Across 1,022 US counties (2017–2021 averages):

- Counties with higher PM2.5 exposure show statistically significant positive associations with COPD, asthma, and coronary heart disease prevalence (p < 0.001)
- Associations persist after controlling for ozone co-exposure
- High-burden counties are concentrated in California's Central Valley, Appalachia, and parts of the industrial Midwest
- Ecological correlations; individual-level causal inference requires confounder adjustment (see Methods tab in app)

## Author

Sadaf Sarbazi · M.Env.Sc., University of Toronto · M.S. Business Analytics, Loyola Marymount University  
[linkedin.com/in/sadaf-sarbazi](https://linkedin.com/in/sadaf-sarbazi) · [github.com/Sadifs](https://github.com/Sadifs)
