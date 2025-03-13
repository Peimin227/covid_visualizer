import os
import pandas as pd


output_folder = 'dataset'
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

def load_and_melt(filename, value_name):
    df = pd.read_csv(filename)
    df_long = df.melt(
        id_vars=["Province/State", "Country/Region", "Lat", "Long"],
        var_name="Date",
        value_name=value_name
    )
    df_long["Date"] = pd.to_datetime(df_long["Date"])
    return df_long


df_confirmed = load_and_melt('time_series_covid19_confirmed_global.csv', 'Confirmed')
df_deaths    = load_and_melt('time_series_covid19_deaths_global.csv', 'Deaths')
df_recovered = load_and_melt('time_series_covid19_recovered_global.csv', 'Recovered')

df_confirmed.to_csv(os.path.join(output_folder, 'converted_confirmed_data.csv'), index=False)
df_deaths.to_csv(os.path.join(output_folder, 'converted_deaths_data.csv'), index=False)
df_recovered.to_csv(os.path.join(output_folder, 'converted_recovered_data.csv'), index=False)

print("转换后的文件已保存在 'dataset' 文件夹中。")
