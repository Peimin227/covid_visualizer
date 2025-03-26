import os
import requests
import pandas as pd
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, dash_table
import plotly.graph_objs as go
import plotly.express as px

# -----------------------------------
# 1. Real-time Data Fetching and Processing from disease.sh API (历史数据部分)
# -----------------------------------
def fetch_all_global_data():
    url = "https://disease.sh/v3/covid-19/historical?lastdays=all"
    response = requests.get(url)
    data = response.json()
    rows = []
    for country_data in data:
        country = country_data.get("country")
        timeline = country_data.get("timeline", {})
        cases = timeline.get("cases", {})
        deaths = timeline.get("deaths", {})
        recovered = timeline.get("recovered", {})
        for date_str, confirmed in cases.items():
            death_count = deaths.get(date_str, 0)
            recovered_count = recovered.get(date_str, 0)
            try:
                date_parsed = pd.to_datetime(date_str, format="%m/%d/%y")
            except Exception:
                date_parsed = pd.NaT
            rows.append({
                "Country/Region": country,
                "Date": date_parsed,
                "Confirmed": confirmed,
                "Deaths": death_count,
                "Recovered": recovered_count
            })
    df = pd.DataFrame(rows)
    df = df.dropna(subset=["Date"])
    return df

def process_global_data():
    df = fetch_all_global_data()
    df_grouped = df.groupby(["Country/Region", "Date"]).agg({
        "Confirmed": "sum",
        "Deaths": "sum",
        "Recovered": "sum"
    }).reset_index()
    df_grouped = df_grouped.sort_values(["Country/Region", "Date"])
    df_grouped["New_Confirmed"] = df_grouped.groupby("Country/Region")["Confirmed"].diff().fillna(0)
    df_grouped["New_Deaths"] = df_grouped.groupby("Country/Region")["Deaths"].diff().fillna(0)
    df_grouped["New_Recovered"] = df_grouped.groupby("Country/Region")["Recovered"].diff().fillna(0)
    return df_grouped


df_global = pd.read_csv("dataset/global_covid19_dataset.csv")
df_global["Date"] = pd.to_datetime(df_global["Date"])
df_grouped = df_global.groupby(["Country/Region", "Date"]).agg({
    "Confirmed": "sum",
    "Deaths": "sum",
    "Recovered": "sum"
}).reset_index()
df_grouped = df_grouped.sort_values(["Country/Region", "Date"])
df_grouped["New_Confirmed"] = df_grouped.groupby("Country/Region")["Confirmed"].diff().fillna(0)
df_grouped["New_Deaths"] = df_grouped.groupby("Country/Region")["Deaths"].diff().fillna(0)
df_grouped["New_Recovered"] = df_grouped.groupby("Country/Region")["Recovered"].diff().fillna(0)

countries = sorted(df_grouped["Country/Region"].unique())
latest_date = df_grouped["Date"].max()
df_latest = df_grouped[df_grouped["Date"] == latest_date]

# -----------------------------------
# 2. Define page layouts
# -----------------------------------


global_layout = dbc.Container([
    dbc.Row(
        dbc.Col(html.H2("Global COVID-19 Data Dashboard", className="text-center mb-4"), width=12)
    ),
    dbc.Row([
        dbc.Col([
            html.Label("Select Countries:", className="font-weight-bold"),
            dcc.Dropdown(
                id="country-dropdown",
                options=[{"label": country, "value": country} for country in countries],
                value=["US", "India", "Italy"],
                multi=True,
                style={"font-size": "16px"}
            )
        ], md=6),
        dbc.Col([
            html.Label("Select Date Range:", className="font-weight-bold"),
            dcc.DatePickerRange(
                id="date-picker-range",
                min_date_allowed=df_grouped["Date"].min(),
                max_date_allowed=df_grouped["Date"].max(),
                start_date=df_grouped["Date"].min(),
                end_date=df_grouped["Date"].max(),
                display_format="YYYY-MM-DD"
            )
        ], md=6)
    ], className="mb-4"),
    dbc.Row(dbc.Col(dcc.Graph(id="cumulative-graph"), width=12)),
    dbc.Row(dbc.Col(dcc.Graph(id="daily-new-graph"), width=12))
], fluid=True, style={"backgroundColor": "#f7f7f7", "padding": "20px"})


us_map_layout = dbc.Container([
    dbc.Row(dbc.Col(html.H2("US COVID-19 County Map", className="text-center mb-4"), width=12)),
    dbc.Row(dbc.Col(html.Iframe(
        src="/assets/us_covid_county_map.html",
        style={"width": "100%", "height": "600px", "border": "none"}
    ), width=12))
], fluid=True)


global_heatmap_layout = dbc.Container([
    dbc.Row(dbc.Col(html.H2("Global COVID-19 Heatmap", className="text-center mb-4"), width=12)),
    dbc.Row(dbc.Col(dcc.Graph(id="global-heatmap"), width=12))
], fluid=True)


daily_info_layout = dbc.Container([
    dbc.Row(
        dbc.Col(html.H1("Daily COVID-19 Detailed Information", className="text-center text-primary mb-4"), width=12)
    ),
    dbc.Row(
        dbc.Col(
            dbc.Card([
                dbc.CardHeader("Select Country"),
                dbc.CardBody([
                    dcc.Dropdown(
                        id="daily-info-country-dropdown",
                        options=[{"label": c, "value": c} for c in countries],
                        value="US",
                        multi=False,
                        style={"font-size": "16px"}
                    ),
                  
                    dcc.Interval(id="interval-summary", interval=60000, n_intervals=0)
                ])
            ], className="mb-4", outline=True, color="secondary"),
            md=6, className="mb-4"
        )
    ),
    dbc.Row(
        dbc.Col(
            dbc.Card([
                dbc.CardHeader("Latest 30 Days Data"),
                dbc.CardBody([
                    dash_table.DataTable(
                        id="daily-info-table",
                        columns=[
                            {"name": "Country/Region", "id": "Country/Region"},
                            {"name": "Confirmed", "id": "Confirmed"},
                            {"name": "Deaths", "id": "Deaths"},
                            {"name": "Recovered", "id": "Recovered"},
                            {"name": "Active", "id": "Active"},
                            {"name": "New Confirmed", "id": "New_Confirmed"},
                            {"name": "New Deaths", "id": "New_Deaths"},
                            {"name": "New Recovered", "id": "New_Recovered"}
                        ],
                        data=[],
                        style_cell={'textAlign': 'center', 'fontSize': '14px'},
                        style_header={
                            'backgroundColor': 'rgb(230, 230, 230)',
                            'fontWeight': 'bold'
                        },
                        page_size=10,
                        style_table={'overflowX': 'auto'}
                    )
                ])
            ], className="mb-4", outline=True, color="light"),
            width=12
        )
    ),
    dbc.Row([
        dbc.Col(
            dbc.Card([
                dbc.CardHeader("Real-Time Country Summary"),
                dbc.CardBody([
                    dcc.Graph(id="real-time-summary-graph")
                ])
            ], className="mb-4", outline=True, color="light"),
            md=6
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardHeader("New Cases Trend (Last 7 Days)"),
                dbc.CardBody([
                    dcc.Graph(id="daily-info-bar-chart")
                ])
            ], className="mb-4", outline=True, color="light"),
            md=6
        )
    ])
], fluid=True, style={"backgroundColor": "#f7f7f7", "padding": "20px"})

# -----------------------------------
# 3. 构建多页面路由布局
# -----------------------------------
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY], suppress_callback_exceptions=True)
server = app.server

app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    dbc.NavbarSimple(
        brand="COVID-19 Dashboard",
        brand_href="/global",
        children=[
            dbc.NavItem(dbc.NavLink("Global Dashboard", href="/global")),
            dbc.NavItem(dbc.NavLink("US Map", href="/usmap")),
            dbc.NavItem(dbc.NavLink("Global Heatmap", href="/heatmap")),
            dbc.NavItem(dbc.NavLink("Daily Info", href="/dailyinfo"))
        ],
        color="primary",
        dark=True,
        fluid=True,
        className="mb-4"
    ),
    html.Div(id="page-content")
], style={"backgroundColor": "#e9ecef"})

# -----------------------------------
# 4. 页面路由回调
# -----------------------------------
@app.callback(Output("page-content", "children"),
              Input("url", "pathname"))
def display_page(pathname):
    print("Current pathname:", pathname)
    if pathname == "/usmap":
        return us_map_layout
    elif pathname == "/heatmap":
        return global_heatmap_layout
    elif pathname == "/dailyinfo":
        return daily_info_layout
    else:
        return global_layout

# -----------------------------------
# 5. Global Dashboard 图表更新回调
# -----------------------------------
@app.callback(
    [Output("cumulative-graph", "figure"),
     Output("daily-new-graph", "figure")],
    [Input("country-dropdown", "value"),
     Input("date-picker-range", "start_date"),
     Input("date-picker-range", "end_date")]
)
def update_global_graphs(selected_countries, start_date, end_date):
    if not selected_countries:
        selected_countries = []
    mask = (
        (df_grouped["Date"] >= start_date) & 
        (df_grouped["Date"] <= end_date) &
        (df_grouped["Country/Region"].isin(selected_countries))
    )
    filtered = df_grouped[mask]

    fig_cum = go.Figure()
    for country in selected_countries:
        country_data = filtered[filtered["Country/Region"] == country]
        fig_cum.add_trace(go.Scatter(
            x=country_data["Date"],
            y=country_data["Confirmed"],
            mode="lines+markers",
            name=f"{country} Cumulative Confirmed"
        ))
        fig_cum.add_trace(go.Scatter(
            x=country_data["Date"],
            y=country_data["Deaths"],
            mode="lines+markers",
            name=f"{country} Cumulative Deaths"
        ))
        fig_cum.add_trace(go.Scatter(
            x=country_data["Date"],
            y=country_data["Recovered"],
            mode="lines+markers",
            name=f"{country} Cumulative Recovered"
        ))
    fig_cum.update_layout(
        title="Cumulative Trends",
        xaxis_title="Date",
        yaxis_title="Cumulative Count",
        template="plotly_white",
        font=dict(size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    fig_daily = go.Figure()
    for country in selected_countries:
        country_data = filtered[filtered["Country/Region"] == country]
        fig_daily.add_trace(go.Scatter(
            x=country_data["Date"],
            y=country_data["New_Confirmed"],
            mode="lines+markers",
            name=f"{country} New Confirmed"
        ))
        fig_daily.add_trace(go.Scatter(
            x=country_data["Date"],
            y=country_data["New_Deaths"],
            mode="lines+markers",
            name=f"{country} New Deaths"
        ))
        fig_daily.add_trace(go.Scatter(
            x=country_data["Date"],
            y=country_data["New_Recovered"],
            mode="lines+markers",
            name=f"{country} New Recovered"
        ))
    fig_daily.update_layout(
        title="Daily New Trends",
        xaxis_title="Date",
        yaxis_title="Daily Count",
        template="plotly_white",
        font=dict(size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    return fig_cum, fig_daily

# -----------------------------------
# 6. Daily Info 表格更新回调（最近 30 天数据）
# -----------------------------------
@app.callback(
    Output("daily-info-table", "data"),
    Input("daily-info-country-dropdown", "value")
)
def update_daily_info(selected_country):
    if not selected_country:
        return []
 
    one_month_ago = latest_date - pd.Timedelta(days=30)
    df_last_month = df_grouped[df_grouped["Date"] >= one_month_ago]
    if isinstance(selected_country, str):
        df_daily = df_last_month[df_last_month["Country/Region"] == selected_country].copy()
    else:
        df_daily = df_last_month[df_last_month["Country/Region"].isin(selected_country)].copy()
    return df_daily.to_dict('records')

# -----------------------------------
# 7. Daily Info 页面：实时国家摘要和右侧条形图更新回调
# 使用 disease.sh API 调用实时数据获取国家实时摘要，每 60 秒更新；右侧条形图调用 disease.sh 历史接口获取过去 7 天数据
# -----------------------------------
@app.callback(
    [Output("real-time-summary-graph", "figure"),
     Output("daily-info-bar-chart", "figure")],
    [Input("daily-info-country-dropdown", "value"),
     Input("interval-summary", "n_intervals")]
)
def update_real_time_summary_and_bar(selected_country, n):
    if not selected_country:
        return go.Figure(), go.Figure()
                         
    url = f"https://disease.sh/v3/covid-19/countries/{selected_country}?strict=true"
    try:
        r = requests.get(url)
        if r.status_code != 200:
            summary_fig = go.Figure(data=[go.Indicator(
                mode="number",
                value=0,
                title={"text": f"Error fetching data for {selected_country}"}
            )])
        else:
            data = r.json()
            summary_df = pd.DataFrame({
                "Metric": ["Total Cases", "Active", "Deaths", "Recovered", "Critical"],
                "Value": [data.get("cases", 0), data.get("active", 0), data.get("deaths", 0), data.get("recovered", 0), data.get("critical", 0)]
            })
            summary_fig = px.bar(summary_df, x="Metric", y="Value", text="Value",
                                 title=f"Real-Time Summary for {selected_country}")
            summary_fig.update_traces(texttemplate='%{text:,}', textposition='outside')
            summary_fig.update_layout(yaxis_tickformat=",")
    except Exception as e:
        summary_fig = go.Figure(data=[go.Indicator(
            mode="number",
            value=0,
            title={"text": f"Error: {str(e)}"}
        )])
    

    hist_url = f"https://disease.sh/v3/covid-19/historical/{selected_country}?lastdays=8"
    try:
        r_hist = requests.get(hist_url)
        if r_hist.status_code != 200:
            new_bar_fig = go.Figure()
        else:
            hist_data = r_hist.json()
            timeline = hist_data.get("timeline", {})
            cases = timeline.get("cases", {})
            deaths = timeline.get("deaths", {})
            recovered = timeline.get("recovered", {})
      
            df_hist = pd.DataFrame({
                "Date": pd.to_datetime(list(cases.keys()), format="%m/%d/%y"),
                "Confirmed": list(cases.values()),
                "Deaths": list(deaths.values()),
                "Recovered": list(recovered.values())
            }).sort_values("Date")
            if df_hist.shape[0] < 2:
                new_bar_fig = go.Figure()
            else:
       
                df_hist["New_Confirmed"] = df_hist["Confirmed"].diff().fillna(df_hist["Confirmed"])
                df_hist["New_Deaths"] = df_hist["Deaths"].diff().fillna(df_hist["Deaths"])
                df_hist["New_Recovered"] = df_hist["Recovered"].diff().fillna(df_hist["Recovered"])
         
                df_recent = df_hist.iloc[-7:]
                new_bar_fig = go.Figure()
                new_bar_fig.add_trace(go.Bar(
                    x=df_recent["Date"],
                    y=df_recent["New_Confirmed"],
                    name="New Confirmed"
                ))
                new_bar_fig.add_trace(go.Bar(
                    x=df_recent["Date"],
                    y=df_recent["New_Deaths"],
                    name="New Deaths"
                ))
                new_bar_fig.add_trace(go.Bar(
                    x=df_recent["Date"],
                    y=df_recent["New_Recovered"],
                    name="New Recovered"
                ))
                new_bar_fig.update_layout(
                    title=f"{selected_country} New Cases Trend (Last 7 Days)",
                    xaxis_title="Date",
                    yaxis_title="Daily New Count",
                    barmode="group",
                    template="plotly_white"
                )
    except Exception as e:
        new_bar_fig = go.Figure()
    
    return summary_fig, new_bar_fig

# -----------------------------------
# 8. Callback for updating global heatmap
# -----------------------------------
@app.callback(
    Output("global-heatmap", "figure"),
    Input("url", "pathname")
)
def update_global_heatmap(pathname):
    if pathname != "/heatmap":
        raise dash.exceptions.PreventUpdate
    try:
        fig = px.choropleth(
            df_latest,
            locations="Country/Region",
            locationmode="country names",
            color="Confirmed",
            hover_name="Country/Region",
            color_continuous_scale="Reds",
            title="Global COVID-19 Confirmed Cases"
        )
        return fig
    except Exception as e:
        print(f"Error building heatmap: {e}")
        return go.Figure()

# -----------------------------------
# 9. Run the Dash server
# -----------------------------------
if __name__ == '__main__':
    app.run_server(debug=True)
