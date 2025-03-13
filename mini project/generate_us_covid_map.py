import os
import pandas as pd
import folium
import folium.plugins as plugins
import webbrowser

# -------------------------------
# 1. Load US county-level data
# -------------------------------

df_confirmed_us = pd.read_csv('time_series_covid19_confirmed_US.csv')
df_deaths_us = pd.read_csv('time_series_covid19_deaths_US.csv')


id_vars = ['Province_State', 'Admin2', 'FIPS', 'Lat', 'Long_']


df_confirmed_us_long = df_confirmed_us.melt(id_vars=id_vars, var_name='Date', value_name='Confirmed')
df_deaths_us_long = df_deaths_us.melt(id_vars=id_vars, var_name='Date', value_name='Deaths')


df_confirmed_us_long['Date'] = pd.to_datetime(df_confirmed_us_long['Date'], errors='coerce')
df_deaths_us_long['Date'] = pd.to_datetime(df_deaths_us_long['Date'], errors='coerce')


df_us = pd.merge(df_confirmed_us_long, df_deaths_us_long, on=id_vars + ['Date'], how='outer')

# -------------------------------
# 2. 筛选最新日期数据并按县聚合
# -------------------------------
latest_date_us = df_us['Date'].max()
print("Latest US data date:", latest_date_us)

df_us_latest = df_us[df_us['Date'] == latest_date_us]

df_county = df_us_latest.groupby(['Province_State', 'Admin2']).agg({
    'Confirmed': 'sum',
    'Deaths': 'sum',
    'Lat': 'mean',
    'Long_': 'mean'
}).reset_index()

print("County-level aggregated data preview:")
print(df_county.head())

# -------------------------------
# 3. 使用 MarkerCluster 创建县级地图
# -------------------------------
us_map = folium.Map(location=[37.8, -96], zoom_start=5)

marker_cluster = plugins.MarkerCluster().add_to(us_map)

for idx, row in df_county.iterrows():
    county_name = f"{row['Admin2']}, {row['Province_State']}" if pd.notnull(row['Admin2']) else row['Province_State']
    popup_text = f"{county_name}: {int(row['Confirmed']):,} Confirmed, {int(row['Deaths']):,} Deaths"
    folium.Marker(
        location=[row['Lat'], row['Long_']],
        popup=popup_text,
        icon=folium.Icon(color="blue", icon="info-sign")
    ).add_to(marker_cluster)

output_file = 'us_covid_county_map.html'
us_map.save(output_file)
print(f"US county-level COVID-19 map saved as '{output_file}'")
webbrowser.open('file://' + os.path.realpath(output_file))
