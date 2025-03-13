import os
import pandas as pd
import matplotlib.pyplot as plt

data_folder = 'dataset'

confirmed_file = os.path.join(data_folder, 'converted_confirmed_data.csv')
deaths_file    = os.path.join(data_folder, 'converted_deaths_data.csv')
recovered_file = os.path.join(data_folder, 'converted_recovered_data.csv')

df_confirmed = pd.read_csv(confirmed_file)
df_deaths    = pd.read_csv(deaths_file)
df_recovered = pd.read_csv(recovered_file)

df_confirmed['Date'] = pd.to_datetime(df_confirmed['Date'])
df_deaths['Date']    = pd.to_datetime(df_deaths['Date'])
df_recovered['Date'] = pd.to_datetime(df_recovered['Date'])

confirmed_grouped = df_confirmed.groupby(['Country/Region', 'Date'])['Confirmed'].sum().reset_index()
deaths_grouped    = df_deaths.groupby(['Country/Region', 'Date'])['Deaths'].sum().reset_index()
recovered_grouped = df_recovered.groupby(['Country/Region', 'Date'])['Recovered'].sum().reset_index()

df_global = pd.merge(confirmed_grouped, deaths_grouped, on=['Country/Region', 'Date'], how='outer')
df_global = pd.merge(df_global, recovered_grouped, on=['Country/Region', 'Date'], how='outer')

df_global = df_global.sort_values(['Country/Region', 'Date'])
df_global['New_Confirmed'] = df_global.groupby('Country/Region')['Confirmed'].diff().fillna(0)
df_global['New_Deaths']    = df_global.groupby('Country/Region')['Deaths'].diff().fillna(0)
df_global['New_Recovered'] = df_global.groupby('Country/Region')['Recovered'].diff().fillna(0)

latest_date = df_global['Date'].max()
print("最新日期:", latest_date)

df_latest = df_global[df_global['Date'] == latest_date]
df_latest_agg = df_latest.groupby('Country/Region')['Confirmed'].sum().reset_index()
top_n = 10
top_countries = df_latest_agg.sort_values('Confirmed', ascending=False)['Country/Region'].head(top_n).tolist()
print("前 10 个国家:", top_countries)

plt.figure(figsize=(14, 7))
for country in top_countries:
    country_data = df_global[df_global['Country/Region'] == country]
    country_agg = country_data.groupby('Date')['Confirmed'].sum().reset_index()
    plt.plot(country_agg['Date'], country_agg['Confirmed'], label=country)

plt.xlabel('日期')
plt.ylabel('累计确诊病例')
plt.title('全球 COVID-19 累计确诊趋势 - 前 10 国家')
plt.legend()
plt.show()
