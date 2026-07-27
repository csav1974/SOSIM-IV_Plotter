import socket
import sys
import math

import pandas as pd
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State, MATCH, ALL
from dash import dash_table
from dash.dash_table.Format import Format, Scheme
import dash_bootstrap_components as dbc

from data_processing.data_processing import update_output_extern
from data_processing.filename_formatting import normalize_filename
from data_processing.graph_processing import update_graph_extern


def check_port_available(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex((host, port))
    sock.close()
    return result != 0


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

# zentrale Präzisions-Map (Spalten -> Nachkommastellen) 
PRECISION_MAP = {
    'Isc [mA]': 1,
    'Voc [mV]': 0,
    'Vmpp [mV]': 0,
    'Impp [mA]': 1,
    'Pmpp [mW]': 2,
    'FF [%]': 2,
    'Rp [kOhm]': 2,
    'Rs [Ohm]': 2,
    'Rp Fit [kOhm]': 2,
    'Rs Fit [Ohm]': 2,
    'Cell Area [cm²]': 2,
    'Eta [%]': 1,
    'Jsc [mA/cm²]': 1,
}


DERIVED_PARAMETER_COLUMNS = [
    'Rp Fit [kOhm]',
    'Rs Fit [Ohm]',
    'Cell Area [cm²]'
]
PRIMARY_PARAMETER_COLUMNS = [
    'Voc [mV]',
    'Isc [mA]',
    'Jsc [mA/cm²]',
    'FF [%]',
    'Eta [%]',
    'Rp [kOhm]',
    'Rs [Ohm]',
    'Rp Fit [kOhm]',
    'Rs Fit [Ohm]',
    'Cell Area [cm²]'
]
ALL_PARAMETER_COLUMNS = header[3:-2] + DERIVED_PARAMETER_COLUMNS
PARAMETER_TABLE_COLUMNS = PRIMARY_PARAMETER_COLUMNS + [
    column for column in ALL_PARAMETER_COLUMNS
    if column not in PRIMARY_PARAMETER_COLUMNS
]
DOWNLOADABLE_COLUMNS = ['Datei'] + PARAMETER_TABLE_COLUMNS
DEFAULT_DOWNLOAD_COLUMNS = [
    column for column in ["Datei", "Voc [mV]", "Isc [mA]", "FF [%]", "Eta [%]"]
    if column in DOWNLOADABLE_COLUMNS
]

# Formatierung für den CSV-Download 
def format_df_for_download(df: pd.DataFrame, precision_map: dict) -> pd.DataFrame:
    df_out = df.copy()
    for col, prec in precision_map.items():
        if col in df_out.columns:
            def _fmt(v):
                # None/NaN/Platzhalter unverändert lassen
                if pd.isna(v) or (isinstance(v, str) and v.strip().upper() in ('INF', '#NV')):
                    return v
                try:
                    return f"{float(v):.{prec}f}"
                except Exception:
                    return v
            df_out[col] = df_out[col].map(_fmt)
    return df_out


def calculate_cell_area(isc, jsc):
    """Calculate cell area in cm² from matching mA-based Isc and Jsc values."""

    try:
        isc_value = float(isc)
        jsc_value = float(jsc)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(isc_value) or not math.isfinite(jsc_value):
        return None
    if jsc_value == 0.0:
        return None
    return isc_value / jsc_value


# Dash-App initialisieren
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

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

    # Achsenbereich einstellen
    dbc.Row([
        dbc.Col([
            dcc.Graph(
                id='IV-graph'
            )
        ], width=8),
        dbc.Col([
            html.H5('Achsenbereich einstellen:'),
            html.Div(
                [
                    dbc.Button(
                        'x-Flip',
                        id='x-flip-btn',
                        color='primary',
                        outline=True,
                        active=False,       # start inaktiv
                        className='me-2'
                    ),
                    dbc.Button(
                        'y-Flip',
                        id='y-flip-btn',
                        color='primary',
                        outline=True,
                        active=False,
                        className='me-2'
                    ),
                    dbc.Button(
                        'Fit-Kurve',
                        id='fit-overlay-btn',
                        color='info',
                        outline=False,
                        active=True
                    )
                ],
                className='d-flex align-items-center mb-3'
            ),
            dbc.RadioItems(
                id='axis-range-toggle',
                options=[
                    {'label': 'Automatisch', 'value': 'auto'},
                    {'label': 'Manuell', 'value': 'manual'}
                ],
                value='auto',
                inline=True
            ),
            # Preset-Optionen (werden nur angezeigt, wenn 'Manuell' ausgewählt ist)
            html.Div(id='preset-options', children=[
                dbc.RadioItems(
                    id='preset-toggle',
                    options=[
                        {'label': 'Preset-CIGS', 'value': 'preset1'},
                        {'label': 'Preset-Tandem', 'value': 'preset2'}
                    ],
                    value='preset1',
                    inline=True
                )
            ], style={'display': 'none'}),
            # X-Achse Eingabefelder
            dbc.Row([
                dbc.Col([
                    dbc.Label('X-Min:'),
                    dbc.Input(id='x-min-input', type='number', disabled=True)
                ], width=4),
                dbc.Col([
                    dbc.Label('X-Max:'),
                    dbc.Input(id='x-max-input', type='number', disabled=True)
                ], width=4)
            ]),
            # Y-Achse Eingabefelder
            dbc.Row([
                dbc.Col([
                    dbc.Label('Y-Min:'),
                    dbc.Input(id='y-min-input', type='number', disabled=True)
                ], width=4),
                dbc.Col([
                    dbc.Label('Y-Max:'),
                    dbc.Input(id='y-max-input', type='number', disabled=True)
                ], width=4)
            ])
        ], width=4)
    ], className="mt-4", align="center"),

    # Parameter-Tabelle
    dbc.Row([
        dbc.Col([
            html.H5('Parameter der hochgeladenen Dateien:'),
            dbc.Button(
                'Fit-Info anzeigen',
                id='fit-info-btn',
                color='info',
                outline=True,
                size='sm',
                className='mt-2 mb-2'
            ),
            dbc.Collapse(
                dbc.Alert(
                    [
                        html.H6(
                            'Info: Berechnung von Rs und Rp',
                            className='alert-heading'
                        ),
                        html.P(
                            [
                                'Als Startwerte werden die lokalen Steigungen verwendet: ',
                                html.Code('Rp ≈ -dV/dI bei V ≈ 0'),
                                ' und ',
                                html.Code('Rs ≈ -dV/dI bei I ≈ 0'),
                                '. Danach werden Rs und Rp gemeinsam mit Photostrom, '
                                'Sättigungsstrom und effektiver Diodenspannung durch eine '
                                'robuste nichtlineare Kleinste-Quadrate-Anpassung bestimmt.'
                            ],
                            className='mb-1'
                        ),
                        html.Small(
                            [
                                'Verwendetes Ein-Dioden-Modell: ',
                                html.Code(
                                    'I = Iph - I0·(exp((V + I·Rs)/a) - 1) '
                                    '- (V + I·Rs)/Rp'
                                ),
                                '. Die Fit-Werte stehen zusätzlich neben den aus der Datei '
                                'ausgelesenen Rs-/Rp-Werten.'
                            ]
                        )
                    ],
                    color='info',
                    className='mb-3'
                ),
                id='fit-info-collapse',
                is_open=False
            ),
            html.Div(
                [
                    dbc.Button('Download Data', id='download-btn', color='success'),
                    html.Div(
                        dbc.Checklist(
                            id='download-columns',
                            options=[{'label': c, 'value': c} for c in DOWNLOADABLE_COLUMNS],
                            value=DEFAULT_DOWNLOAD_COLUMNS,
                            inline=True,
                            # Abstand zwischen Häkchen und Text
                            inputClassName='me-2',
                            # Abstand zwischen Items
                            labelClassName='me-4',
                            # Jede Beschriftung bekommt eine „Spalten“-Breite und kein Umbruch
                            labelStyle={
                                'display': 'inline-block',
                                'minWidth': '2rem',     # anpassen (z.B. 10rem, 14rem, 18ch, …)
                                'whiteSpace': 'nowrap'
                            },
                            className='d-inline-flex flex-nowrap'
                        ),
                        className='ms-3 flex-grow-1 overflow-x-auto',
                        style={'minWidth': 0}  # wichtig, damit das Overflow greift
                    )
                ],
                className='d-flex align-items-center gap-2 mb-2'
            ),
            dcc.Download(id='download-data'),
            html.Div(id='header-parameters')
        ], width=12)
    ], className="mt-4"),

    # Versteckter Speicher für die Daten
    dcc.Store(id='data-store')
], fluid=True)

# Callback zum Verarbeiten der hochgeladenen Dateien
@app.callback(
    [
        Output('file-list', 'children'),
        Output('data-store', 'data'),
        Output('dataset-checkboxes', 'children')
    ],
    [Input('upload-data', 'contents')],
    [
        State('upload-data', 'filename'),
        State('data-store', 'data')
    ]
)
def update_output(list_of_contents, list_of_names, existing_data):
    """
    Callback, der alte Daten aus existing_data übernimmt und mit den neu hochgeladenen
    Dateien zusammenführt.
    """
    return update_output_extern(list_of_contents, list_of_names, existing_data)

# Callback zum Aktivieren/Deaktivieren der Eingabefelder und Anzeigen der Preset-Optionen
@app.callback(
    [Output('x-min-input', 'disabled'),
     Output('x-max-input', 'disabled'),
     Output('y-min-input', 'disabled'),
     Output('y-max-input', 'disabled'),
     Output('preset-options', 'style'),
     Output('preset-toggle', 'value')],
    Input('axis-range-toggle', 'value')
)
def toggle_axis_inputs(axis_range_toggle):
    if axis_range_toggle == 'manual':
        return [False, False, False, False, {'display': 'block'}, 'preset1']
    else:
        return [True, True, True, True, {'display': 'none'}, dash.no_update]

# Callback zum Setzen der Eingabefelder basierend auf dem ausgewählten Preset
@app.callback(
    [Output('x-min-input', 'value'),
     Output('x-max-input', 'value'),
     Output('y-min-input', 'value'),
     Output('y-max-input', 'value')],
    Input('preset-toggle', 'value')
)
def update_axis_inputs(preset_value):
    if preset_value == 'preset1':
        return [-500, 800, -200, 600]  # Werte für Preset-1
    elif preset_value == 'preset2':
        return [-800, 1500, -400, 800]  # Werte für Preset-2
    else:
        return [dash.no_update]*4

# Callback für Achsen Spiegelung
@app.callback(
    [
        Output('x-flip-btn', 'active'),
        Output('x-flip-btn', 'outline'),
        Output('y-flip-btn', 'active'),
        Output('y-flip-btn', 'outline'),
    ],
    [
        Input('x-flip-btn', 'n_clicks'),
        Input('y-flip-btn', 'n_clicks')
    ],
    [
        State('x-flip-btn', 'active'),
        State('y-flip-btn', 'active')
    ],
    prevent_initial_call=True
)
def toggle_flip_buttons(x_n, y_n, x_active, y_active):
    ctx = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
    if ctx == 'x-flip-btn':
        x_active = not x_active
    elif ctx == 'y-flip-btn':
        y_active = not y_active

    # outline umkehren, damit aktiv = gefüllt, inaktiv = outline
    return x_active, not x_active, y_active, not y_active


@app.callback(
    [
        Output('fit-overlay-btn', 'active'),
        Output('fit-overlay-btn', 'outline')
    ],
    Input('fit-overlay-btn', 'n_clicks'),
    State('fit-overlay-btn', 'active'),
    prevent_initial_call=True
)
def toggle_fit_overlay(_n_clicks, active):
    active = not active
    return active, not active


@app.callback(
    [
        Output('fit-info-collapse', 'is_open'),
        Output('fit-info-btn', 'children')
    ],
    Input('fit-info-btn', 'n_clicks'),
    State('fit-info-collapse', 'is_open'),
    prevent_initial_call=True
)
def toggle_fit_info(_n_clicks, is_open):
    is_open = not is_open
    button_label = 'Fit-Info ausblenden' if is_open else 'Fit-Info anzeigen'
    return is_open, button_label


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
    [Input({'type': 'dataset-checklist', 'index': ALL}, 'value'),
     Input('axis-range-toggle', 'value'),
     Input('x-min-input', 'value'),
     Input('x-max-input', 'value'),
     Input('y-min-input', 'value'),
     Input('y-max-input', 'value'),
     Input('x-flip-btn', 'active'),
     Input('y-flip-btn', 'active'),
     Input('fit-overlay-btn', 'active')],
    [State('data-store', 'data'),
     State({'type': 'dataset-checklist', 'index': ALL}, 'id')]
)
def update_graph(selected_datasets_per_file, axis_range_toggle, x_min_input,
                 x_max_input, y_min_input, y_max_input, x_flip_btn,
                 y_flip_btn, show_fit_overlay, data_store, ids):
    figure = update_graph_extern(
        selected_datasets_per_file,
        axis_range_toggle,
        x_min_input,
        x_max_input,
        y_min_input,
        y_max_input,
        x_flip_btn,
        y_flip_btn,
        show_fit_overlay,
        data_store,
        ids
    )
    
    return figure

# Hilfsfunktion zum Vorbereiten der Tabellendaten basierend auf den aktiven Auswahlen
def prepare_parameter_table_data(data_store, file_checkbox_values, file_checkbox_ids, dataset_checklist_values, dataset_checklist_ids):
    if not data_store:
        return []

    active_files = set()
    for val, comp_id in zip(file_checkbox_values, file_checkbox_ids):
        if val and comp_id.get('index'):
            active_files.add(comp_id['index'])  # -> IDs bleiben unverändert (Originalname)

    active_datasets = {}
    for val, comp_id in zip(dataset_checklist_values, dataset_checklist_ids):
        if comp_id.get('index'):
            active_datasets[comp_id['index']] = set(val) if val else set()

    table_data = []
    formatted_keys = ['Isc [mA]', 'Voc [mV]', 'Vmpp [mV]', 'Impp [mA]', 'Pmpp [mW]', 'FF [%]', 'Rp [kOhm]', 'Rs [Ohm]', 'Eta [%]', 'Jsc [mA/cm²]']

    file_names = data_store.get('file_names', [])
    if not file_names:
        file_names = list(data_store.get('data', {}).keys())

    for orig_fn in file_names:
        param_rows = data_store.get('parameters', {}).get(orig_fn) or []
        fit_rows = data_store.get('fits', {}).get(orig_fn) or []
        dataset_count = max(
            len(data_store.get('data', {}).get(orig_fn, [])),
            len(param_rows),
            len(fit_rows)
        )
        if orig_fn in active_datasets:
            selected_indices = active_datasets[orig_fn]
        elif orig_fn in active_files:
            selected_indices = set(range(dataset_count))
        else:
            continue

        display_fn = normalize_filename(orig_fn)
        for idx in range(dataset_count):
            if idx not in selected_indices:
                continue
            row = {'Datei': f"{display_fn} - Datensatz {idx + 1}"}
            if idx < len(param_rows):
                param_values = param_rows[idx]
                for key, value in zip(header, param_values):
                    if key not in PARAMETER_TABLE_COLUMNS:
                        continue
                    if key in formatted_keys and value is not None and value != 'Inf' and str(value).strip().upper() != '#NV':
                        row[key] = float(value) * 100 if key == 'FF [%]' else float(value)
                    else:
                        row[key] = value
            row['Cell Area [cm²]'] = calculate_cell_area(
                row.get('Isc [mA]'),
                row.get('Jsc [mA/cm²]')
            )
            fit = fit_rows[idx] if idx < len(fit_rows) else None
            if isinstance(fit, dict) and fit.get('success'):
                row['Rp Fit [kOhm]'] = fit.get('rp_kohm')
                row['Rs Fit [Ohm]'] = fit.get('rs_ohm')
            else:
                row['Rp Fit [kOhm]'] = None
                row['Rs Fit [Ohm]'] = None
            table_data.append(row)

    return table_data

# Callback zur Anzeige der Parameter in einer Tabelle
@app.callback(
    Output('header-parameters', 'children'),
    [
        Input('data-store', 'data'),
        Input({'type': 'file-checkbox', 'index': ALL}, 'value'),
        Input({'type': 'file-checkbox', 'index': ALL}, 'id'),
        Input({'type': 'dataset-checklist', 'index': ALL}, 'value'),
        Input({'type': 'dataset-checklist', 'index': ALL}, 'id')
    ]
)
def update_header_parameters(data_store, file_checkbox_values, file_checkbox_ids, dataset_checklist_values, dataset_checklist_ids):
    if not data_store:
        return ''

    table_data = prepare_parameter_table_data(
        data_store,
        file_checkbox_values,
        file_checkbox_ids,
        dataset_checklist_values,
        dataset_checklist_ids
    )

    # Spalten-Definition
    columns = [{'name': 'Datei', 'id': 'Datei'}]
    for param in PARAMETER_TABLE_COLUMNS:
        if param in PRECISION_MAP:
            columns.append({
                'name': param,
                'id': param,
                'type': 'numeric',
                'format': Format(precision=PRECISION_MAP[param], scheme=Scheme.fixed)
            })
        else:
            columns.append({'name': param, 'id': param})

    parameter_table = dash_table.DataTable(
        data=table_data,
        columns=columns,
        style_table={'overflowX': 'auto', 'paddingBottom': '20px'},
        style_cell={
            'textAlign': 'left',
            'padding': '5px',
            'minWidth': '60px',
            'whiteSpace': 'nowrap',  # verhindert Umbrüche
            'overflow': 'visible'    # Verhindert abgeschnittenen Text
        },
        style_header={'backgroundColor': 'lightgrey', 'fontWeight': 'bold'}
    )
    return parameter_table

# Callback zum Herunterladen der ausgewählten Parameter als CSV
@app.callback(
    Output('download-data', 'data'),
    Input('download-btn', 'n_clicks'),
    State('data-store', 'data'),
    State({'type': 'file-checkbox', 'index': ALL}, 'value'),
    State({'type': 'file-checkbox', 'index': ALL}, 'id'),
    State({'type': 'dataset-checklist', 'index': ALL}, 'value'),
    State({'type': 'dataset-checklist', 'index': ALL}, 'id'),
    State('download-columns', 'value'),
    prevent_initial_call=True
)
def download_selected_data(n_clicks, data_store, file_checkbox_values, file_checkbox_ids, dataset_checklist_values, dataset_checklist_ids, selected_columns):
    table_data = prepare_parameter_table_data(
        data_store,
        file_checkbox_values,
        file_checkbox_ids,
        dataset_checklist_values,
        dataset_checklist_ids
    )

    if not table_data or not selected_columns:
        return dash.no_update

    df = pd.DataFrame(table_data)
    valid_columns = [column for column in selected_columns if column in df.columns]
    if not valid_columns:
        return dash.no_update

    df = df[valid_columns]

    df = format_df_for_download(df, PRECISION_MAP)
    
    return dcc.send_data_frame(df.to_csv, 'selected_data.csv', index=False)

# Server starten
if __name__ == '__main__':
    HOST = '127.0.0.1'
    PORT = 8050

    # Prüfe, ob Port frei ist
    if not check_port_available(HOST, PORT):
        print(f"Port {PORT} ist bereits belegt. Das Programm wird beendet.")
        sys.exit(0)

    app.run(host=HOST, port=PORT, debug=False)
