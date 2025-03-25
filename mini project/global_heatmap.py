import os
import pandas as pd
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output
import plotly.graph_objs as go
import plotly.express as px
import requests

# -----------------------------------
# 1. Load and preprocess local CSV data
# -----------------------------------
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

df_latest = df_grouped.sort_values("Date").groupby("Country/Region").last().reset_index()
countries = sorted(df_grouped["Country/Region"].unique())

# -----------------------------------
# 2. Page Layouts
# -----------------------------------
global_layout = dbc.Container([
    dbc.Row(dbc.Col(html.H2("Global COVID-19 Data Dashboard", className="text-center mb-4"))),
    dbc.Row([
        dbc.Col([
            html.Label("Select Countries:", className="font-weight-bold"),
            dcc.Dropdown(
                id="country-dropdown",
                options=[{"label": c, "value": c} for c in countries],
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
    dbc.Row(dbc.Col(dcc.Graph(id="cumulative-graph"))),
    dbc.Row(dbc.Col(dcc.Graph(id="daily-new-graph")))
], fluid=True)

us_map_layout = dbc.Container([
    dbc.Row(dbc.Col(html.H2("US COVID-19 Map", className="text-center mb-4"))),
    dbc.Row(dbc.Col(html.Iframe(
        src="/assets/us_covid_county_map.html",
        style={"width": "100%", "height": "600px", "border": "none"}
    )))
], fluid=True)

global_map_layout = dbc.Container([
    dbc.Row(dbc.Col(html.H2("Global COVID-19 Heatmap", className="text-center mb-4"))),
    dbc.Row(dbc.Col(dcc.Graph(id="global-heatmap"))),
    dbc.Row(dbc.Col([
        html.Label("Query country-level COVID data:", className="font-weight-bold"),
        dcc.Input(
            id="country-query-input",
            type="text",
            placeholder="e.g. United States",
            debounce=True,
            style={"width": "100%", "fontSize": "16px", "marginTop": "10px"}
        ),
        html.Div(id="country-query-output", style={"marginTop": "15px"})
    ], width=6))
], fluid=True)

# -----------------------------------
# 3. App Layout
# -----------------------------------
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
server = app.server

app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    dbc.NavbarSimple(
        brand="COVID-19 Dashboard",
        brand_href="/global",
        children=[
            dbc.NavItem(dbc.NavLink("Global Dashboard", href="/global")),
            dbc.NavItem(dbc.NavLink("US Map", href="/usmap")),
            dbc.NavItem(dbc.NavLink("Global Heatmap", href="/heatmap"))
        ],
        color="primary",
        dark=True,
        fluid=True
    ),
    html.Div(id="page-content")
])

# -----------------------------------
# 4. Page Routing
# -----------------------------------
@app.callback(Output("page-content", "children"), Input("url", "pathname"))
def display_page(pathname):
    if pathname == "/usmap":
        return us_map_layout
    elif pathname == "/heatmap":
        return global_map_layout
    else:
        return global_layout

# -----------------------------------
# 5. Global Dashboard Graphs
# -----------------------------------
@app.callback(
    [Output("cumulative-graph", "figure"),
     Output("daily-new-graph", "figure")],
    [Input("country-dropdown", "value"),
     Input("date-picker-range", "start_date"),
     Input("date-picker-range", "end_date")]
)
def update_global_graphs(selected_countries, start_date, end_date):
    mask = (
        (df_grouped["Date"] >= start_date) & 
        (df_grouped["Date"] <= end_date) & 
        (df_grouped["Country/Region"].isin(selected_countries))
    )
    filtered = df_grouped[mask]

    fig_cum = go.Figure()
    fig_daily = go.Figure()

    for country in selected_countries:
        country_data = filtered[filtered["Country/Region"] == country]
        fig_cum.add_trace(go.Scatter(
            x=country_data["Date"], y=country_data["Confirmed"],
            mode="lines+markers", name=f"{country} Cumulative Confirmed"
        ))
        fig_daily.add_trace(go.Scatter(
            x=country_data["Date"], y=country_data["New_Confirmed"],
            mode="lines+markers", name=f"{country} New Confirmed"
        ))

    fig_cum.update_layout(title="Cumulative Trends", template="plotly_white")
    fig_daily.update_layout(title="Daily New Trends", template="plotly_white")

    return fig_cum, fig_daily

# -----------------------------------
# 6. Heatmap using df_latest
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
# 7. Country Query from OWID
# -----------------------------------
@app.callback(
    Output("country-query-output", "children"),
    Input("country-query-input", "value")
)
def query_country_data(country_name):
    if not country_name:
        return ""

    url = "https://covid.ourworldindata.org/data/owid-covid-data.csv"
    try:
        df = pd.read_csv(url)
        df = df.sort_values("date").groupby("location").last().reset_index()
        match = df[df["location"].str.lower() == country_name.strip().lower()]

        if match.empty:
            return html.Div(f"No data found for '{country_name}'.", style={"color": "red"})

        row = match.iloc[0]
        return html.Div([
            html.P(f"Country: {row['location']}"),
            html.P(f"Total Confirmed: {row['total_cases']:,}"),
            html.P(f"Total Deaths: {row['total_deaths']:,}"),
            html.P(f"Population: {row['population']:,}"),
            html.P(f"Last Updated: {row['date']}")
        ], style={"backgroundColor": "#f8f9fa", "padding": "10px", "borderRadius": "5px"})

    except Exception as e:
        return html.Div(f"Error fetching OWID data: {e}", style={"color": "red"})

# -----------------------------------
# 8. Run the app
# -----------------------------------
if __name__ == '__main__':
    app.run(debug=True)
