import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

from pybaseball import playerid_reverse_lookup
from pybaseball import batting_stats
from pybaseball import statcast_batter

from datetime import date, datetime, timedelta
import pandas as pd
import numpy as np
from math import sqrt
import plotly.graph_objects as go
import matplotlib.pyplot as plt

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

dff = pd.read_csv('~/desktop/mlb_batter_spray/batting.csv')

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

STATCAST_VALID_DATES = {
    2008: (date(2008, 3, 25), date(2008, 10, 27)),
    2009: (date(2009, 4, 5), date(2009, 11, 4)),
    2010: (date(2010, 4, 4), date(2010, 11, 1)),
    2011: (date(2011, 3, 31), date(2011, 10, 28)),
    2012: (date(2012, 3, 28), date(2012, 10, 28)),
    2013: (date(2013, 3, 31), date(2013, 10, 30)),
    2014: (date(2014, 3, 22), date(2014, 10, 29)),
    2015: (date(2015, 4, 5), date(2015, 11, 1)),
    2016: (date(2016, 4, 3), date(2016, 11, 2)),
    2017: (date(2017, 4, 2), date(2017, 11, 1)),
    2018: (date(2018, 3, 29), date(2018, 10, 28)),
    2019: (date(2019, 3, 20), date(2019, 10, 30)),
    2020: (date(2020, 7, 23), date(2020, 10, 27))
}

app.layout = html.Div([
    html.H1('MLB Batter’s Left-Center-Right Field Percentage', style = {'textAlign': 'center'}),

    html.Hr(),

    html.Label("Season:", style={'fontSize':30}),
    dcc.Dropdown(
        id='season',
        options=[{'label': s, 'value': s} for s in STATCAST_VALID_DATES],
        value=2008,
        clearable=False
    ),
    html.Hr(),

    html.Label("Team:", style={'fontSize':30}),
    dcc.Dropdown(id='team'),

    html.Hr(),

    html.Label("Player:", style={'fontSize':30}),
    dcc.Dropdown(id='player'),

    html.Hr(),

    dcc.Graph(id='graph'),

    html.Hr(),

    dcc.Markdown('''
    ##### Note

    Please note that the available options for season, team, and player are selected based on the following criteria:

     - Season: 2008 to 2020
     - Player: Made over 50 plate appearance in one season and have not been traded in the season.

    ''')


])

@app.callback(
    Output('team', 'options'),
    Input('season', 'value'))
def set_team_options(selected_season):
    teams = dff.loc[dff['Season'] == selected_season,'Team'].unique()
    teams = np.delete(teams, teams == '- - -', 0)
    return [{'label': i, 'value': i} for i in sorted(teams)]

@app.callback(
    Output('team', 'value'),
    Input('team', 'options'))
def set_team_value(available_options):
    return available_options[0]['value']

@app.callback(
    Output('player', 'options'),
    Input('season', 'value'),
    Input('team', 'value'))
def set_player_options(selected_season, selected_team):
    players = dff[(dff['Season'] == selected_season) & (dff['Team'] == selected_team)]['Name']
    return [{'label': i, 'value': i} for i in sorted(players)]

@app.callback(
    Output('player', 'value'),
    Input('player', 'options'))
def set_player_value(available_options):
    return available_options[0]['value']

@app.callback(
    Output('graph', 'figure'),
    Input('season', 'value'),
    Input('team', 'value'),
    Input('player', 'value'))
def update_graph(selected_season, selected_team, selected_player):
    players = dff[(dff['Season'] == selected_season) & (dff['Team'] == selected_team)]['Name']
    player_fg = dff[dff['Name'] == selected_player]['IDfg']
    player_id = playerid_reverse_lookup(player_fg, "fangraphs")['key_mlbam']
    player = statcast_batter(STATCAST_VALID_DATES[selected_season][0].isoformat(), 
           STATCAST_VALID_DATES[selected_season][1].isoformat(), player_id[0])
    df = player[['hc_x', 'hc_y']].dropna().reset_index().drop(['index'], axis = 1)
    df['x'] = df['hc_x'].apply(lambda x: x - 125.42)
    df['y'] = df['hc_y'].apply(lambda x: 198.27 - x)
    
    tan75 = (sqrt(3)+1)/(sqrt(3)-1)

    for i in range(len(df)):
        if df.iloc[i]['x'] < 0:
            a = df.iloc[i]['x']
            b = -tan75*a + df['y'].min()
            if df.iloc[i]['y'] < b:
                df.loc[i, 'region']=1
            else:
                df.loc[i, 'region']=2
        else:
            a = df.iloc[i]['x']
            b = tan75*a + df['y'].min()
            if df.iloc[i]['y'] < b:
                df.loc[i, 'region']=3
            else:
                df.loc[i, 'region']=2
    id_max = (df['region'].value_counts().sort_index() / len(df)).idxmax()
    df['max'] = df['region'].apply(lambda x: x == id_max)

    colorsIdx = {True: 'red', False: 'green'}
    cols = df['max'].map(colorsIdx)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x = df['x'], y = df['y'], mode = 'markers', marker=dict(color=cols)))

    fig.update_xaxes(range=[-150, 150], showgrid=False, zeroline=False, visible=False)
    fig.update_yaxes(range=[-20, 200], showgrid=False, zeroline=False, visible=False)

    fig.update_yaxes(
        scaleanchor = "x",
        scaleratio = 1,
    )

    x = np.array([-150, 0])
    y = -x + df['y'].min()
    fig.add_trace(go.Scatter(x = x,y = y, mode = 'lines', line=dict(color="#000000")))

    x2 = np.array([0, 150])
    y2 = x2 +  df['y'].min()
    fig.add_trace(go.Scatter(x = x2,y = y2, mode = 'lines', line=dict(color="#000000")))

    x3 = np.array([-50, 0])
    y3 = -tan75* x3 + df['y'].min()
    fig.add_trace(go.Scatter(x = x3,y = y3, mode = 'lines', line=dict(color="#000000")))

    x4 = np.array([0, 50])
    y4 = tan75 * x4 +  df['y'].min()
    fig.add_trace(go.Scatter(x = x4,y = y4, mode = 'lines', line=dict(color="#000000")))

    fig.update_layout(
        margin=dict(l=20, r=20, t=20, b=20)
    )

    fig.update_layout(template="simple_white", showlegend=False, height=700)

    if id_max == 1:
        fig.add_annotation(x=-75, y=125,
                text=str(round((df['region'] == 1).mean()*100, 2)) + "%",
                showarrow=False,
                font=dict(
                    family="Courier New, monospace",
                    size=16,
                    color="#ffffff"
                    ),
                align="center",
                bordercolor="#c7c7c7",
                borderwidth=2,
                borderpad=4,
                bgcolor="red",
                opacity=0.8)
        fig.add_annotation(x= 0 , y= 135,
                text=str(round((df['region'] == 2).mean()*100, 2)) + "%",
                showarrow=False,
                font=dict(
                    family="Courier New, monospace",
                    size=16,
                    color="#ffffff"
                    ),
                align="center",
                bordercolor="#c7c7c7",
                borderwidth=2,
                borderpad=4,
                bgcolor="green",
                opacity=0.8)
        fig.add_annotation(x= 75 , y= 125,
                text=str(round((df['region'] == 3).mean()*100, 2)) + "%",
                showarrow=False,
                font=dict(
                    family="Courier New, monospace",
                    size=16,
                    color="#ffffff"
                    ),
                align="center",
                bordercolor="#c7c7c7",
                borderwidth=2,
                borderpad=4,
                bgcolor="green",
                opacity=0.8)
        return fig

    elif id_max == 2:
        fig.add_annotation(x=-75, y=125,
                text=str(round((df['region'] == 1).mean()*100, 2)) + "%",
                showarrow=False,
                font=dict(
                    family="Courier New, monospace",
                    size=16,
                    color="#ffffff"
                    ),
                align="center",
                bordercolor="#c7c7c7",
                borderwidth=2,
                borderpad=4,
                bgcolor="green",
                opacity=0.8)
        fig.add_annotation(x= 0 , y= 135,
                text=str(round((df['region'] == 2).mean()*100, 2)) + "%",
                showarrow=False,
                font=dict(
                    family="Courier New, monospace",
                    size=16,
                    color="#ffffff"
                    ),
                align="center",
                bordercolor="#c7c7c7",
                borderwidth=2,
                borderpad=4,
                bgcolor="red",
                opacity=0.8)
        fig.add_annotation(x= 75 , y= 125,
                text=str(round((df['region'] == 3).mean()*100, 2)) + "%",
                showarrow=False,
                font=dict(
                    family="Courier New, monospace",
                    size=16,
                    color="#ffffff"
                    ),
                align="center",
                bordercolor="#c7c7c7",
                borderwidth=2,
                borderpad=4,
                bgcolor="green",
                opacity=0.8)
        return fig

    else:
        fig.add_annotation(x=-75, y=125,
                text=str(round((df['region'] == 1).mean()*100, 2)) + "%",
                showarrow=False,
                font=dict(
                    family="Courier New, monospace",
                    size=16,
                    color="#ffffff"
                    ),
                align="center",
                bordercolor="#c7c7c7",
                borderwidth=2,
                borderpad=4,
                bgcolor="green",
                opacity=0.8)
        fig.add_annotation(x= 0 , y= 135,
                text=str(round((df['region'] == 2).mean()*100, 2)) + "%",
                showarrow=False,
                font=dict(
                    family="Courier New, monospace",
                    size=16,
                    color="#ffffff"
                    ),
                align="center",
                bordercolor="#c7c7c7",
                borderwidth=2,
                borderpad=4,
                bgcolor="green",
                opacity=0.8)
        fig.add_annotation(x= 75 , y= 125,
                text=str(round((df['region'] == 3).mean()*100, 2)) + "%",
                showarrow=False,
                font=dict(
                    family="Courier New, monospace",
                    size=16,
                    color="#ffffff"
                    ),
                align="center",
                bordercolor="#c7c7c7",
                borderwidth=2,
                borderpad=4,
                bgcolor="red",
                opacity=0.8)
        return fig

if __name__ == '__main__':
    app.run_server(debug=True)


# @app.callback(
#     Output('display-selected-values', 'children'),
#     Input('season', 'value'),
#     Input('team', 'value'),
#     Input('player', 'value'))   
# def set_display_children(selected_season, selected_team, selected_player):
#     return u'{} was a player of {} team in {}'.format(
#         selected_player, selected_team, selected_season,
#     )

# if __name__ == '__main__':
#     app.run_server(debug=True)
