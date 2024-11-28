import os
import base64
import io
import pylightxl
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State, MATCH, ALL
from dash import dash_table
from dash.dash_table.Format import Format, Scheme
import dash_bootstrap_components as dbc

from data_processing.data_processing import update_output_extern
from data_processing.file_processing import process_file_extern
from data_processing.graph_processing import update_graph_extern

# Header-Definition
header = [
    "Voltage [mV]",
    "Current [mA]",
    "Power [mW]",
    "Isc [mA]",
    "Voc [mV]",
    "Vmpp [mV]",
    "Impp [mA]",
    "Pmpp [mW]",
    "FF [%]",
    "Rp [kOhm]",
    "Rs [Ohm]",
    "Eta [%]",
    "Jsc [mA/cm²]",
    "Flashtime [ms]",
    "Voltage 2 [mV]",
    "Current 2 [mA]",
    "Power 2 [mW]",
    "Isc 2 [mA]",
    "Vmpp 2 [mV]",
    "Impp 2 [mA]",
    "Pmpp 2 [mW]",
    "Intensity [W/m²]",
    "Start Voltage [V]",
    "End Voltage [V]",
    "Max Current [A]",
    "Measurement Steps",
    "Trigger Delay [ms]",
    "Delay Between Sweep Steps [ms]",
    "Aperture [ms]",
    "AM1.5G",
    "Spectral Flux Density [W/m²]"
]

# Funktion zum Verarbeiten einer Datei und Extrahieren der DataFrames und Parameterwerte
def process_file(contents, filename):
    return process_file_extern(contents, filename)

# Dash-App initialisieren
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Layout der App definieren
app.layout = dbc.Container([
    # Navigationsleiste
    dbc.NavbarSimple(
        brand="SoSim - IV-Plotter",
        color="primary",
        dark=True,
        fixed="top"
    ),

    # Abstand zur Navigationsleiste
    html.Br(), html.Br(),

    # Upload-Bereich
    dbc.Row([
        dbc.Col([
            html.H5('Dateien zum Auswerten hochladen:'),
            dcc.Upload(
                id='upload-data',
                children=dbc.Button(
                    "Dateien auswählen",
                    color="secondary",
                    className="mr-2"
                ),
                multiple=True
            ),
            html.Div(id='file-list'),
        ], width=12)
    ], className="mt-4"),

    # Datensatz-Checkboxes
    dbc.Row([
        dbc.Col([
            html.H5('Datensätze Plotten:'),
            html.Div(id='dataset-checkboxes')
        ], width=12)
    ], className="mt-4"),

    # Graph
    dbc.Row([
        dbc.Col([
            dcc.Graph(
                id='IV-graph'
            )
        ], width=12)
    ], className="mt-4"),

    # Parameter-Tabelle
    dbc.Row([
        dbc.Col([
            html.H5('Parameter der hochgeladenen Dateien:'),
            html.Div(id='header-parameters')
        ], width=12)
    ], className="mt-4"),

    # Versteckter Speicher für die Daten
    dcc.Store(id='data-store')
], fluid=True)

# Callback zum Verarbeiten der hochgeladenen Dateien
@app.callback(
    [Output('file-list', 'children'),
     Output('data-store', 'data'),
     Output('dataset-checkboxes', 'children')],
    [Input('upload-data', 'contents')],
    [State('upload-data', 'filename')]
)
def update_output(list_of_contents, list_of_names):
    return update_output_extern(list_of_contents, list_of_names)

# Callback zur Synchronisation von Datei- und Datensatz-Checkboxes
@app.callback(
    Output({'type': 'dataset-checklist', 'index': MATCH}, 'value'),
    Input({'type': 'file-checkbox', 'index': MATCH}, 'value'),
    State({'type': 'dataset-checklist', 'index': MATCH}, 'options')
)
def update_dataset_checklist(file_checkbox_value, dataset_options):
    if file_checkbox_value == []:
        # Wenn die Datei-Checkbox deaktiviert ist, alle Datensätze deaktivieren
        return []
    else:
        # Wenn die Datei-Checkbox aktiviert ist, alle Datensätze aktivieren
        return [option['value'] for option in dataset_options]

# Callback zur Aktualisierung des Graphen basierend auf den ausgewählten Datensätzen
@app.callback(
    Output('IV-graph', 'figure'),
    [Input({'type': 'dataset-checklist', 'index': ALL}, 'value')],
    [State('data-store', 'data'),
     State({'type': 'dataset-checklist', 'index': ALL}, 'id')]
)
def update_graph(selected_datasets_per_file, data_store, ids):
    return update_graph_extern(selected_datasets_per_file, data_store, ids)
    
# Callback zur Anzeige der Parameter in einer Tabelle
@app.callback(
    Output('header-parameters', 'children'),
    Input('data-store', 'data')
)
def update_header_parameters(data_store):
    if not data_store or 'parameters' not in data_store:
        return ''
    else:
        parameters = data_store['parameters']
        table_data = []
        formatted_keys = ['Isc [mA]', 'Voc [mV]', 'Vmpp [mV]', 'Impp [mA]', 'Pmpp [mW]' 'FF [%]', 'Rp [kOhm]', 'Rs [Ohm]', 'Eta [%]', 'Jsc [mA/cm²]']
        for filename, param_values in parameters.items():
            if param_values is not None:
                # Erstelle ein Dictionary mit 'Datei' und den Parameterwerten
                row = {'Datei': filename}
                for key, value in zip(header, param_values):
                    if key in formatted_keys and value is not None and value != 'Inf':
                        if key == 'FF':
                            row[key] = float(value) *100
                        else:
                            row[key] = float(value)
                    else:
                        row[key] = value
                table_data.append(row)
        # Spalten definieren
        columns = [{'name': 'Datei', 'id': 'Datei'}]
        for param in header[3:-2]:
            if param == 'Isc [mA]':
                columns.append({
                    'name': param,
                    'id': param,
                    'type': 'numeric',
                    'format': Format(precision=1, scheme=Scheme.fixed)
                })
            elif param == 'Voc [mV]':
                columns.append({
                    'name': param,
                    'id': param,
                    'type': 'numeric',
                    'format': Format(precision=0, scheme=Scheme.fixed)
                })
            elif param == 'Vmpp [mV]':
                columns.append({
                    'name': param,
                    'id': param,
                    'type': 'numeric',
                    'format': Format(precision=0, scheme=Scheme.fixed)
                })
            elif param == 'Impp [mA]':
                columns.append({
                    'name': param,
                    'id': param,
                    'type': 'numeric',
                    'format': Format(precision=1, scheme=Scheme.fixed)
                })
            elif param == 'Pmpp [mW]':
                columns.append({
                    'name': param,
                    'id': param,
                    'type': 'numeric',
                    'format': Format(precision=2, scheme=Scheme.fixed)
                })
            elif param == 'FF [%]':
                columns.append({
                    'name': param,
                    'id': param,
                    'type': 'numeric',
                    'format': Format(precision = 2, scheme=Scheme.fixed)
                })
            elif param == 'Rp [kOhm]':
                columns.append({
                    'name': param,
                    'id': param,
                    'type': 'numeric',
                    'format': Format(precision=2, scheme=Scheme.fixed)
                })
            elif param == 'Rs [Ohm]':
                columns.append({
                    'name': param,
                    'id': param,
                    'type': 'numeric',
                    'format': Format(precision=1, scheme=Scheme.fixed)
                })
            elif param == 'Eta [%]':
                columns.append({
                    'name': param,
                    'id': param,
                    'type': 'numeric',
                    'format': Format(precision=1, scheme=Scheme.fixed)
                })
            elif param == 'Jsc [mA/cm²]':
                columns.append({
                    'name': param,
                    'id': param,
                    'type': 'numeric',
                    'format': Format(precision=1, scheme=Scheme.fixed)
                })
            else:
                columns.append({
                    'name': param,
                    'id': param
                })
        # DataTable erstellen
        parameter_table = dash_table.DataTable(
            data=table_data,
            columns=columns,
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'padding': '5px', 'minWidth': '60px', 'maxWidth': '500px'},
            style_header={'backgroundColor': 'lightgrey', 'fontWeight': 'bold'}
        )
        return parameter_table

# Server starten
if __name__ == '__main__':
    app.run_server(debug=True)
