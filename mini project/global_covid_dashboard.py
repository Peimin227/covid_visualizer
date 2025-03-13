import os
import pandas as pd
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output
import plotly.graph_objs as go

# -----------------------------------
# 1. Load and preprocess global data
# -----------------------------------
df_global = pd.read_csv("dataset/global_covid19_dataset.csv")
df_global["Date"] = pd.to_datetime(df_global["Date"])

# Aggregate data by Country/Region and Date
df_grouped = df_global.groupby(["Country/Region", "Date"]).agg({
    "Confirmed": "sum",
    "Deaths": "sum",
    "Recovered": "sum"
}).reset_index()

# Sort by Country/Region and Date, and compute daily new counts
df_grouped = df_grouped.sort_values(["Country/Region", "Date"])
df_grouped["New_Confirmed"] = df_grouped.groupby("Country/Region")["Confirmed"].diff().fillna(0)
df_grouped["New_Deaths"] = df_grouped.groupby("Country/Region")["Deaths"].diff().fillna(0)
df_grouped["New_Recovered"] = df_grouped.groupby("Country/Region")["Recovered"].diff().fillna(0)

# List of all countries (sorted)
countries = sorted(df_grouped["Country/Region"].unique())

# -----------------------------------
# 2. Define page layouts
# -----------------------------------

# Global Dashboard layout
global_layout = dbc.Container([
    dbc.Row(
        dbc.Col(
            html.H2("Global COVID-19 Data Dashboard", className="text-center mb-4"),
            width=12
        )
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
    dbc.Row(
        dbc.Col(dcc.Graph(id="cumulative-graph"), width=12)
    ),
    dbc.Row(
        dbc.Col(dcc.Graph(id="daily-new-graph"), width=12)
    )
], fluid=True)

# US Map layout – embed pre-generated folium map via IFrame (ensure file exists in assets folder)
us_map_layout = dbc.Container([
    dbc.Row(
        dbc.Col(
            html.H2("US COVID-19 Map", className="text-center mb-4"),
            width=12
        )
    ),
    dbc.Row(
        dbc.Col(
            html.Iframe(
                src="/assets/us_covid_county_map.html",
                style={"width": "100%", "height": "600px", "border": "none"}
            ),
            width=12
        )
    )
], fluid=True)

# -----------------------------------
# 3. Build multi-page app layout
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
            dbc.NavItem(dbc.NavLink("US Map", href="/usmap"))
        ],
        color="primary",
        dark=True,
        fluid=True
    ),
    html.Div(id="page-content")
])

# -----------------------------------
# 4. Page routing callback
# -----------------------------------
@app.callback(Output("page-content", "children"),
              Input("url", "pathname"))
def display_page(pathname):
    if pathname == "/usmap":
        return us_map_layout
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
# 6. Run the Dash server
# -----------------------------------
if __name__ == '__main__':
    app.run_server(debug=True)
