import os
import requests
import pandas as pd
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, dash_table
import plotly.graph_objs as go
import plotly.express as px

# -----------------------------------
# 1. Load and preprocess global data
# -----------------------------------
# 从本地 CSV 文件中加载全球数据（这里假设数据已合并在一个文件中）
df_global = pd.read_csv("dataset/global_covid19_dataset.csv")
df_global["Date"] = pd.to_datetime(df_global["Date"])

# 按 "Country/Region" 和 "Date" 聚合数据
df_grouped = df_global.groupby(["Country/Region", "Date"]).agg({
    "Confirmed": "sum",
    "Deaths": "sum",
    "Recovered": "sum"
}).reset_index()

df_grouped = df_grouped.sort_values(["Country/Region", "Date"])
df_grouped["New_Confirmed"] = df_grouped.groupby("Country/Region")["Confirmed"].diff().fillna(0)
df_grouped["New_Deaths"] = df_grouped.groupby("Country/Region")["Deaths"].diff().fillna(0)
df_grouped["New_Recovered"] = df_grouped.groupby("Country/Region")["Recovered"].diff().fillna(0)

# 获取所有国家列表
countries = sorted(df_grouped["Country/Region"].unique())

# 计算最新日期（视为当日数据）并过滤最新数据
latest_date = df_grouped["Date"].max()
df_latest = df_grouped[df_grouped["Date"] == latest_date]

# -----------------------------------
# 2. Define page layouts
# -----------------------------------

# Global Dashboard layout
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

# US Map layout – US county-level map embedded via Iframe (确保文件位于 assets/us_covid_county_map.html)
us_map_layout = dbc.Container([
    dbc.Row(dbc.Col(html.H2("US COVID-19 County Map", className="text-center mb-4"), width=12)),
    dbc.Row(dbc.Col(html.Iframe(
        src="/assets/us_covid_county_map.html",
        style={"width": "100%", "height": "600px", "border": "none"}
    ), width=12))
], fluid=True)

# Global Heatmap layout – 以 choropleth 显示全球累计确诊情况
global_heatmap_layout = dbc.Container([
    dbc.Row(dbc.Col(html.H2("Global COVID-19 Heatmap", className="text-center mb-4"), width=12)),
    dbc.Row(dbc.Col(dcc.Graph(id="global-heatmap"), width=12))
], fluid=True)

# Daily Detailed Info layout – 优化后的页面
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
                    )
                ])
            ], className="mb-4", outline=True, color="secondary"),
            md=6, className="mb-4"
        )
    ),
    dbc.Row(
        dbc.Col(
            dbc.Card([
                dbc.CardHeader("Latest Daily Data"),
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
                dbc.CardHeader("Data Composition Pie Chart"),
                dbc.CardBody([
                    dcc.Graph(id="daily-info-pie-chart")
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
# 3. Build multi-page app layout with routing
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
# 4. Page routing callback
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
# 5. Callback for updating global dashboard graphs
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
# 6. Callback for updating Daily Info table
# -----------------------------------
@app.callback(
    Output("daily-info-table", "data"),
    Input("daily-info-country-dropdown", "value")
)
def update_daily_info(selected_country):
    if not selected_country:
        return []
    # 如果为单选（multi=False），selected_country 是字符串
    if isinstance(selected_country, str):
        df_daily = df_latest[df_latest["Country/Region"] == selected_country].copy()
    else:
        df_daily = df_latest[df_latest["Country/Region"].isin(selected_country)].copy()
    return df_daily.to_dict('records')

# -----------------------------------
# 7. Callback for updating detailed charts (pie and bar) on Daily Info page
# -----------------------------------
@app.callback(
    [Output("daily-info-pie-chart", "figure"),
     Output("daily-info-bar-chart", "figure")],
    Input("daily-info-country-dropdown", "value")
)
def update_detailed_charts(selected_country):
    if not selected_country:
        return go.Figure(), go.Figure()
    
    # 如果为单选，selected_country 为字符串
    if isinstance(selected_country, str):
        df_daily = df_latest[df_latest["Country/Region"] == selected_country]
    else:
        df_daily = df_latest[df_latest["Country/Region"].isin(selected_country)]
    if df_daily.empty:
        return go.Figure(), go.Figure()
    row = df_daily.iloc[0]
    active = row["Confirmed"] - row["Deaths"] - row["Recovered"]
    pie_data = {
        "Category": ["Active", "Deaths", "Recovered"],
        "Count": [active, row["Deaths"], row["Recovered"]]
    }
    fig_pie = px.pie(pie_data, names="Category", values="Count",
                     title=f"{selected_country} Distribution on {row['Date'].date()}",
                     color_discrete_sequence=px.colors.sequential.RdBu)
    
    df_country = df_grouped[df_grouped["Country/Region"] == selected_country]
    recent_start = row["Date"] - pd.Timedelta(days=6)
    df_recent = df_country[df_country["Date"] >= recent_start]
    
    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        x=df_recent["Date"],
        y=df_recent["New_Confirmed"],
        name="New Confirmed"
    ))
    fig_bar.add_trace(go.Bar(
        x=df_recent["Date"],
        y=df_recent["New_Deaths"],
        name="New Deaths"
    ))
    fig_bar.add_trace(go.Bar(
        x=df_recent["Date"],
        y=df_recent["New_Recovered"],
        name="New Recovered"
    ))
    fig_bar.update_layout(
        title=f"{selected_country} New Cases Trend (Last 7 Days)",
        xaxis_title="Date",
        yaxis_title="Daily New Count",
        barmode="group",
        template="plotly_white"
    )
    
    return fig_pie, fig_bar

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
