# Import required libraries
import pickle
import copy
import pathlib
import dash
import math
import datetime as dt
import pandas as pd
from dash.dependencies import Input, Output, State, ClientsideFunction
import dash_core_components as dcc
import dash_html_components as html

import numpy as np
import cufflinks as cf
import sqlite3

# Multi-dropdown options
from controls import GENRES, ARTISTS

# get relative data folder
PATH = pathlib.Path(__file__).parent
DATA_PATH = PATH.joinpath("data").resolve()

app = dash.Dash(
    __name__, meta_tags=[{"name": "viewport", "content": "width=device-width"}]
)
server = app.server

# Create controls
genre_options = [
    {"label": str(GENRES[genre]), "value": str(genre)} for genre in GENRES
]
artist_options = [
    {"label": str(ARTISTS[artist]), "value": str(artist)} for artist in ARTISTS
]

# Load data
db_path = 'data/chinook.db'
connection = sqlite3.connect(DATA_PATH.joinpath("chinook.db"))

df_albums = pd.read_sql_query("SELECT * FROM albums", connection)
df_artists = pd.read_sql_query("SELECT * FROM artists", connection)
df_customers = pd.read_sql_query("SELECT * FROM customers", connection)
df_employees = pd.read_sql_query("SELECT * FROM employees", connection)
df_genres = pd.read_sql_query("SELECT * FROM genres", connection)
df_invoice_items = pd.read_sql_query("SELECT * FROM invoice_items", connection)
df_invoices = pd.read_sql_query("SELECT * FROM invoices", connection)
df_invoices['InvoiceDate'] = pd.to_datetime(df_invoices['InvoiceDate'])
df_media_types = pd.read_sql_query("SELECT * FROM media_types", connection)
df_playlist_track = pd.read_sql_query("SELECT * FROM playlist_track", connection)
df_playlists = pd.read_sql_query("SELECT * FROM playlists", connection)
df_tracks = pd.read_sql_query("SELECT * FROM tracks", connection)

query1 = """SELECT  
ivi.InvoiceLineId ,ivi.InvoiceID ,ivi.TrackId ,ivi.UnitPrice ,ivi.Quantity,
iv.InvoiceDate, iv.BillingCountry,
genres.Name as GenreName,
artists.Name as ArtistName

FROM invoice_items as ivi
LEFT JOIN invoices as iv ON ivi.InvoiceID = iv.InvoiceID
LEFT JOIN tracks as tr ON ivi.TrackID = tr.TrackID
LEFT JOIN genres ON tr.GenreId = genres.GenreId
LEFT JOIN albums ON tr.AlbumId = albums.AlbumId
LEFT JOIN artists ON albums.ArtistId = artists.ArtistId
"""
total_transactions_raw = pd.read_sql_query(query1, connection)
total_transactions_raw['InvoiceDate'] = pd.to_datetime(total_transactions_raw['InvoiceDate'])

invoice_date_range = pd.date_range(start=df_invoices['InvoiceDate'].min(),end=df_invoices['InvoiceDate'].max())


# Create global chart template
# mapbox_access_token = "pk.eyJ1IjoiamFja2x1byIsImEiOiJjajNlcnh3MzEwMHZtMzNueGw3NWw5ZXF5In0.fk8k06T96Ml9CLGgKmk81w"

layout = dict(
    autosize=True,
    automargin=True,
    margin=dict(l=30, r=30, b=20, t=40),
    hovermode="closest",
    plot_bgcolor="#F9F9F9",
    paper_bgcolor="#F9F9F9",
    legend=dict(font=dict(size=10), orientation="h")
)

# Create app layout
app.layout = html.Div(
    [
        dcc.Store(id="aggregate_data"),
        # empty Div to trigger javascript file for graph resizing
        html.Div(id="output-clientside"),

        # ------------------------------------------------------------------------
        # Header
        html.Div(
            [
                html.Div(
                    [
                    ],
                    className="one-third column",
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.H3(
                                    "Digital Media",
                                    style={"margin-bottom": "0px"},
                                ),
                                html.H5(
                                    "Overview", style={"margin-top": "0px"}
                                ),
                            ]
                        )
                    ],
                    className="one-half column",
                    id="title",
                ),
                html.Div(
                    [
                        html.A(
                            html.Button("View Source", id="learn-more-button"),
                            href="https://github.com/iqbalbasyar/",
                        )
                    ],
                    className="one-third column",
                    id="button",
                ),
            ],
            id="header",
            className="row flex-display",
            style={"margin-bottom": "25px"},
        ),

        # ------------------------------------------------------------------------
        # Count Bar and Filter
        html.Div(
            [
                html.Div(
                    [
                        # Filter Year
                        html.P(
                            "Filter by transaction year (or select range in histogram):",
                            className="control_label",
                        ),
                        html.P(
                            "Year Selected: ", id="output_container_year_slider",
                            className="control_label"
                        ),
                        dcc.RangeSlider(
                            id="year_slider",
                            min=2009,
                            max=2013,
                            value=[2010, 2012],
                            className="dcc_control",
                        ),
                         
                        # Filter Genre 
                        html.P("Filter by Genre:", className="control_label"),
                        dcc.RadioItems(
                            id="genre_selector",
                            options=[
                                {"label": "All ", "value": "all"},
                                {"label": "Top ", "value": "top"},
                                {"label": "Customize ", "value": "custom"},
                            ],
                            value="top",
                            labelStyle={"display": "inline-block"},
                            className="dcc_control",
                        ),
                        dcc.Dropdown(
                            id="genres_dropdown",
                            options=genre_options,
                            multi=True,
                            value=list(GENRES.keys()),
                            className="dcc_control",
                        ),

                        # Filter Artist 
                        html.P("Filter by Artist:", className="control_label"),
                        dcc.RadioItems(
                            id="artist_selector",
                            options=[
                                {"label": "All ", "value": "all"},
                                {"label": "Customize ", "value": "custom"},
                            ],
                            value="all",
                            labelStyle={"display": "inline-block"},
                            className="dcc_control",
                        ),
                        dcc.Dropdown(
                            id="artists_dropdown",
                            options=artist_options,
                            multi=True,
                            value=list(ARTISTS.keys()),
                            className="dcc_control",
                        ),
                    ],
                    className="pretty_container four columns",
                    id="cross-filter-options",
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [html.H6(id="no_sales_text"), html.P("No. of Sales")],
                                    id="wells",
                                    className="mini_container",
                                ),
                                html.Div(
                                    [html.H6(id="sales_text"), html.P("Total Sales")],
                                    id="gas",
                                    className="mini_container",
                                ),
                                html.Div(
                                    [html.H6(id="genre_text"), html.P("Unique Tracks")],
                                    id="oil",
                                    className="mini_container",
                                ),
                                html.Div(
                                    [html.H6(id="country_text"), html.P("Unique Countries")],
                                    id="water",
                                    className="mini_container",
                                ),
                            ],
                            id="info-container",
                            className="row container-display",
                        ),
                        html.Div(
                            [dcc.Graph(id="count_graph")],
                            id="countGraphContainer",
                            className="pretty_container",
                        ),
                    ],
                    id="right-column",
                    className="eight columns",
                ),
            ],
            className="row flex-display",
        ),

        # Pie and Aggregate
        html.Div(
            [
                html.Div(
                    [dcc.Graph(id="pie_graph")],
                    className="pretty_container seven columns",
                ),
                html.Div(
                    [dcc.Graph(id="aggregate_graph")],
                    className="pretty_container five columns",
                ),
            ],
            className="row flex-display",
        ),
    ],
    id="mainContainer",
    style={"display": "flex", "flex-direction": "column"},
)


# Helper functions
def human_format(num):
    if num == 0:
        return "0"

    magnitude = int(math.log(num, 1000))
    mantissa = str(int(num / (1000 ** magnitude)))
    return mantissa + ["", "K", "M", "G", "T", "P"][magnitude]


# def filter_dataframe(df, well_statuses, well_types, year_slider):
#     dff = df[
#         df["Well_Status"].isin(well_statuses)
#         & df["Well_Type"].isin(well_types)
#         & (df["Date_Well_Completed"] > dt.datetime(year_slider[0], 1, 1))
#         & (df["Date_Well_Completed"] < dt.datetime(year_slider[1], 1, 1))
#     ]
#     return dff

def filter_dataframe2(df, artists, genres, year_slider):
    if 'A0' in artists:
        filter_artist = df_artists['Name'].values.tolist()
    else:
        filter_artist = [ARTISTS[x] for x in artists]
    filter_genre = [GENRES[x] for x in genres]
    filter_year = range(year_slider[0], year_slider[1]+1)
    mask_genre = df['GenreName'].isin(filter_genre)
    mask_artist = df['ArtistName'].isin(filter_artist)
    mask_year = df['InvoiceDate'].apply(lambda x: x.year in filter_year)
    dff = df[mask_genre & mask_artist & mask_year]
    return dff

def pie_dataframe(df, column, threshold_count=5, threshold_percentage=0.05):
    df_count = df[column].value_counts()
    if len(df_count) <= threshold_count:
        return df_count
    else:
        df_prcnt = df_count/df_count.sum()
        mask = df_prcnt<threshold_percentage
        dff1 = df_count[~mask]
        dff2 = df_count[mask]
        if len(dff2) != 0 :
            other_count = dff2.sum()
            return dff1.append(pd.Series([other_count], index=['Other < 5%']))
        else:
            return dff1
    

# def produce_individual(api_well_num):
#     try:
#         points[api_well_num]
#     except:
#         return None, None, None, None

#     index = list(
#         range(min(points[api_well_num].keys()), max(points[api_well_num].keys()) + 1)
#     )
#     gas = []
#     oil = []
#     water = []

#     for year in index:
#         try:
#             gas.append(points[api_well_num][year]["Gas Produced, MCF"])
#         except:
#             gas.append(0)
#         try:
#             oil.append(points[api_well_num][year]["Oil Produced, bbl"])
#         except:
#             oil.append(0)
#         try:
#             water.append(points[api_well_num][year]["Water Produced, bbl"])
#         except:
#             water.append(0)

#     return index, gas, oil, water


def produce_aggregate(selected, year_slider):

    index = list(range(max(year_slider[0], 1985), 2016))
    gas = []
    oil = []
    water = []

    for year in index:
        count_gas = 0
        count_oil = 0
        count_water = 0
        for api_well_num in selected:
            try:
                count_gas += points[api_well_num][year]["Gas Produced, MCF"]
            except:
                pass
            try:
                count_oil += points[api_well_num][year]["Oil Produced, bbl"]
            except:
                pass
            try:
                count_water += points[api_well_num][year]["Water Produced, bbl"]
            except:
                pass
        gas.append(count_gas)
        oil.append(count_oil)
        water.append(count_water)

    return index, gas, oil, water


# Create callbacks
app.clientside_callback(
    ClientsideFunction(namespace="clientside", function_name="resize"),
    Output("output-clientside", "children"),
    [Input("count_graph", "figure")],
)

# Update Dataframe
@app.callback(
    Output("aggregate_data", "data"),
    [
        Input("artists_dropdown", "value"),
        Input("genres_dropdown", "value"),
        Input("year_slider", "value"),
    ],
)
def update_sales_text(artists_dropdown, genres_dropdown, year_slider):
    dff = filter_dataframe2(total_transactions_raw, artists_dropdown, genres_dropdown, year_slider)
    total_sales = dff['UnitPrice'].sum()
    unique_tracks = dff['TrackId'].nunique()
    unique_country = dff['BillingCountry'].nunique()
    return [human_format(total_sales), human_format(unique_tracks), human_format(unique_country)]

# Radio -> multi (Genre)
@app.callback(Output("genres_dropdown", "value"), [Input("genre_selector", "value")])
def display_genre(selector):
    if selector == "all":
        return list(GENRES.keys())
    elif selector == "top":
        return ["RK", "MT","LT","AP","JZ"]
    return []

# Radio -> multi (Artist)
@app.callback(Output("artists_dropdown", "value"), [Input("artist_selector", "value")])
def display_artist(selector):
    if selector == "all":
        return ["A0"]
    return []

# Slider -> count graph
@app.callback(Output("year_slider", "value"), [Input("count_graph", "selectedData")])
def update_year_slider(count_graph_selected):
    if count_graph_selected is None:
        return [2010, 2012]
        # return [1990, 2010]

    nums = [int(point["pointNumber"]) for point in count_graph_selected["points"]]
    # return [min(nums) + 1960, max(nums) + 1961]
    return [min(nums)//12 + 2009, max(nums)//12 + 2009]

# Slider Output #UPDATE
@app.callback(
    dash.dependencies.Output('output_container_year_slider', 'children'),
    [dash.dependencies.Input('year_slider', 'value')])
def update_output(value):
    if value:
        return f"Year Selected: {min(value)} - {max(value)}"
    else : 
        return "Year Selected: None"

# Selectors -> well text
@app.callback(
    [
        Output("sales_text", "children"),
        Output("genre_text", "children"),
        Output("country_text", "children"),
    ],
    [Input("aggregate_data", "data")],
)
def update_text(data):
    return data[0] + " USD", data[1] + " Songs", data[2] + " Countries"

# Selectors -> sales
@app.callback(
    Output("no_sales_text", "children"),
    [
        Input("artists_dropdown", "value"),
        Input("genres_dropdown", "value"),
        Input("year_slider", "value"),
    ],
)
def update_sale_text(artists, genres, year_slider):
    dff = filter_dataframe2(total_transactions_raw, artists, genres, year_slider)
    return dff.shape[0]


# Selectors, main graph -> aggregate graph

@app.callback(
    Output("aggregate_graph", "figure"),
    [
        Input("artists_dropdown", "value"),
        Input("genres_dropdown", "value"),
        Input("year_slider", "value")
    ],
)
def make_aggregate_figure(artists_dropdown, genres_dropdown, year_slider):

    layout_aggregate = copy.deepcopy(layout)
    dff = filter_dataframe2(total_transactions_raw, artists_dropdown, genres_dropdown, year_slider)

    dff= dff\
    .set_index('InvoiceDate')[['TrackId', 'BillingCountry', 'UnitPrice']]\
    .resample('D')\
    .agg({'UnitPrice':'sum', 'TrackId':'nunique','BillingCountry':'nunique' })\
    .reindex(invoice_date_range, fill_value=0).resample('M', convention='end').sum()

    data = [
        dict(
            type="scatter",
            mode="lines",
            name="Sales (USD)",
            x=dff.index,
            y=dff['UnitPrice'],
            line=dict(shape="spline", smoothing="2", color="#F9ADA0"),
        ),
        dict(
            type="scatter",
            mode="lines",
            name="Tracks",
            x=dff.index,
            y=dff['TrackId'],
            line=dict(shape="spline", smoothing="2", color="#849E68"),
        ),
        dict(
            type="scatter",
            mode="lines",
            name="Countries",
            x=dff.index,
            y=dff['BillingCountry'],
            line=dict(shape="spline", smoothing="2", color="#59C3C3"),
        ),
    ]
    layout_aggregate["title"] = "Monthly Data Aggregate"
    figure = dict(data=data, layout=layout_aggregate)
    return figure



# Selectors, main graph -> pie graph
@app.callback(
    Output("pie_graph", "figure"),
    [
        Input("artists_dropdown", "value"),
        Input("genres_dropdown", "value"),
        Input("year_slider", "value"),
    ],
)
def make_pie_figure(artists_dropdown, genres_dropdown, year_slider):
    layout_pie = copy.deepcopy(layout)
    dff = filter_dataframe2(total_transactions_raw, artists_dropdown, genres_dropdown, year_slider)
    pie_country = pie_dataframe(dff, 'BillingCountry')
    pie_genre = pie_dataframe(dff, 'GenreName')
    pie_artist = pie_dataframe(dff, 'ArtistName')

    data = [
        dict( #country
            type="pie",
            labels=pie_country.index,
            values=pie_country,
            name="Countries Breakdown",
            hoverinfo="label+text+value+percent",
            textinfo="label+percent+name",
            hole=0.5,
            domain={"x": [0, 0.3], "y": [0.2, 0.8]},
        ),
        dict(
            type="pie",
            labels=pie_genre.index,
            values=pie_genre,
            name="Genres Breakdown",
            hoverinfo="label+text+value+percent",
            textinfo="label+percent+name",
            hole=0.5,
            domain={"x": [0.35, 0.65], "y": [0.2, 0.8]},
        ),
        dict(
            type="pie",
            labels=pie_artist.index,
            values=pie_artist,
            name="Genres Breakdown",
            hoverinfo="label+text+value+percent",
            textinfo="label+percent+name",
            hole=0.5,
            domain={"x": [0.7, 1], "y": [0.2, 0.8]},
        ),
        
    ]
    layout_pie["title"] = "Sales Summary: {} to {}".format(
        year_slider[0], year_slider[1]
    )
    layout_pie["font"] = dict(color="#777777")
    layout_pie["legend"] = dict(
        font=dict(color="#CCCCCC", size="10"), orientation="h", bgcolor="rgba(0,0,0,0)"
    )
    layout_pie["showlegend"] = False
    layout_pie.update(dict(annotations= [{'x': 0.16, 'y':0.95 ,
                                        'align': 'center',
                                        'text': 'Countries Proportion ',
                                        'font': { 'color': 'rgb(55, 128, 191)', 'size': 14},
                                        'showarrow':False, 'xanchor':'center' },
                                        {'x': 0.5, 'y':0.95 ,
                                        'align': 'center',
                                        'text': 'Genres Proportion',
                                        'font': { 'color': 'rgb(55, 128, 191)', 'size': 14},
                                        'showarrow':False, 'xanchor':'center' },
                                        {'x': 0.85, 'y':0.95,
                                        'align': 'center', 
                                        'text': 'Artists Proportion' ,
                                        'font': { 'color': 'rgb(55, 128, 191)', 'size': 14},
                                        'showarrow':False, 'xanchor':'center' } ]))

    figure = dict(data=data, layout=layout_pie)
    return figure


# Selectors -> count graph
@app.callback(
    Output("count_graph", "figure"),
    [
        Input("artists_dropdown", "value"),
        Input("genres_dropdown", "value"),
        Input("year_slider", "value"),
    ],
)
def make_count_figure(artists_dropdown, genres_dropdown, year_slider):
    layout_count = copy.deepcopy(layout)
    dff = filter_dataframe2(total_transactions_raw, artists_dropdown, genres_dropdown, [2007, 2013])

    total_transactions = dff.set_index('InvoiceDate')[['UnitPrice','Quantity']].resample('D').sum().reindex(invoice_date_range, fill_value=0).resample('M', convention='end').sum()
    g = total_transactions

    colors = []
    for i in g.index:
        if i.year >= int(year_slider[0]) and i.year <= int(year_slider[1]):
            colors.append("rgb(123, 199, 255)") # Light Blue
            # colors.append("rgb(137, 25, 33)")
        else:
            colors.append("rgba(123, 199, 255, 0.2)") # light grey
            # colors.append("rgba(50, 50, 50, 0.4)")
            

    data = [
        dict(
            type="scatter",
            mode="markers",
            x=g.index,
            y=g["Quantity"] / 2,
            opacity=0,
            hoverinfo="skip",
        ),
        dict(
            type="bar",
            x=g.index,
            y=g["Quantity"],
            name="Total Transactions",
            marker=dict(color=colors),
        ),
    ]

    layout_count["title"] = "Number of Sales/Month"
    layout_count["dragmode"] = "select"
    layout_count["showlegend"] = False
    layout_count["autosize"] = True

    figure = dict(data=data, layout=layout_count)
    return figure


# Main
if __name__ == "__main__":
    app.run_server(debug=True)
