import pandas as pd

# 加载三个转换后的 CSV 文件（假设它们都存放在 "dataset" 文件夹中）
df_confirmed = pd.read_csv('dataset/converted_confirmed_data.csv')
df_deaths = pd.read_csv('dataset/converted_deaths_data.csv')
df_recovered = pd.read_csv('dataset/converted_recovered_data.csv')

# 将日期列转换为 datetime 格式
df_confirmed['Date'] = pd.to_datetime(df_confirmed['Date'])
df_deaths['Date'] = pd.to_datetime(df_deaths['Date'])
df_recovered['Date'] = pd.to_datetime(df_recovered['Date'])

# 按 "Country/Region" 和 "Date" 聚合数据
confirmed_grouped = df_confirmed.groupby(['Country/Region', 'Date'])['Confirmed'].sum().reset_index()
deaths_grouped = df_deaths.groupby(['Country/Region', 'Date'])['Deaths'].sum().reset_index()
recovered_grouped = df_recovered.groupby(['Country/Region', 'Date'])['Recovered'].sum().reset_index()

# 合并数据
df_global = pd.merge(confirmed_grouped, deaths_grouped, on=['Country/Region', 'Date'], how='outer')
df_global = pd.merge(df_global, recovered_grouped, on=['Country/Region', 'Date'], how='outer')

# 保存全局数据集为 CSV 文件
df_global.to_csv('global_covid19_dataset.csv', index=False)
print("全局数据集已保存为 'global_covid19_dataset.csv'")
