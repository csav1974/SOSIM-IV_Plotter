from dash import dcc, html
import dash_bootstrap_components as dbc
import time

from data_processing.file_processing import process_file_extern

def update_output_extern(list_of_contents, list_of_names, existing_data):
    """
    Verarbeitet neu hochgeladene Dateien sequentiell und vereint sie mit bereits bestehenden Daten.
    Dabei werden alle Filenamen in existing_data['file_names'] gesammelt, damit sie 
    beim nächsten Upload-Event nicht verloren gehen. Zudem werden Checkboxes für 
    alle Dateien neu aufgebaut.
    
    :param list_of_contents: Inhalten der neu hochgeladenen Dateien (Base64-Strings)
    :param list_of_names:    Liste der Dateinamen, die hochgeladen wurden
    :param existing_data:    Alter Datenbestand aus dem dcc.Store (Dictionary), 
                             der 'file_names', 'data', 'parameters' und 'checkbox_info'
                             enthalten kann.
    :return:                 Tuple aus:
                             1) HTML-Liste aller Dateinamen (alt + neu),
                             2) gemergte existing_data,
                             3) Checkboxes für alle Dateien
    """

    # ------------------
    # 1) INITIALISIERUNG
    # ------------------
    if existing_data is None:
        existing_data = {}

    # Sichere Schlüssel anlegen
    if 'data' not in existing_data:
        existing_data['data'] = {}
    if 'parameters' not in existing_data:
        existing_data['parameters'] = {}
    if 'file_names' not in existing_data:
        existing_data['file_names'] = []
    if 'checkbox_info' not in existing_data:
        existing_data['checkbox_info'] = {}

    # -------------------------------------
    # 2) FALL: KEINE NEUEN DATEIEN HOCHGELADEN
    # -------------------------------------
    if list_of_contents is None or list_of_names is None:
        checkboxes = []
        for filename in existing_data['file_names']:
            ds_count = existing_data['checkbox_info'].get(filename, {}).get('ds_count', 1)
            dataset_labels = [f'Datensatz {i + 1}' for i in range(ds_count)]
            dataset_checklist = dcc.Checklist(
                id={'type': 'dataset-checklist', 'index': filename},
                options=[{'label': lbl, 'value': i} for i, lbl in enumerate(dataset_labels)],
                value=list(range(ds_count)),
                labelStyle={'display': 'block', 'margin-left': '20px'}
            )
            file_checkbox = dcc.Checklist(
                id={'type': 'file-checkbox', 'index': filename},
                options=[{'label': filename, 'value': filename}],
                value=[filename],
                labelStyle={'font-weight': 'bold'}
            )
            col = dbc.Col([file_checkbox, dataset_checklist], width="auto")
            checkboxes.append(col)

        checkbox_row = dbc.Row(
            checkboxes,
            justify="start",
            className="g-0",
            style={
                "overflowX": "auto",
                "whiteSpace": "nowrap",
                "display": "flex",
                "flexWrap": "nowrap",
                "paddingBottom": "20px"
            }
        )
        all_file_names_html = [html.Li(fn) for fn in existing_data['file_names']]
        return html.Ul(all_file_names_html), existing_data, checkbox_row

    # --------------------------------------------
    # 3) FALL: ES GIBT NEUE DATEIEN ZU VERARBEITEN
    # --------------------------------------------
    # Verarbeite jede Datei sequentiell in einer Queue-Schleife:
    for contents, filename in zip(list_of_contents, list_of_names):
        # Datei verarbeiten (DataFrame-Liste + Parameterwerte)
        df_list, parameter_values_list = process_file_extern(contents, filename)

        # DataFrames in JSON konvertieren, damit sie in dcc.Store speicherbar sind
        new_data = {filename: [df.to_json(date_format='iso', orient='split') for df in df_list]}
        new_parameters = {filename: parameter_values_list}

        # Falls diese Datei noch nicht vorhanden ist, einfügen
        if filename not in existing_data['file_names']:
            existing_data['file_names'].append(filename)
        # Speichere die Anzahl der Datensätze
        existing_data['checkbox_info'][filename] = {'ds_count': len(df_list)}

        # Mergen: Erzeuge neue Dictionaries, um den State zu ändern
        existing_data['data'] = {**existing_data.get('data', {}), **new_data}
        existing_data['parameters'] = {**existing_data.get('parameters', {}), **new_parameters}
        # Optional: Eine kurze Pause, um die sequentielle Verarbeitung zu erzwingen
        time.sleep(0.1)

    # -------------------------------------
    # 4) AUFBAU DES LAYOUTS (DATEIEN + CHECKBOXES)
    # -------------------------------------
    all_file_names_html = [html.Li(fn) for fn in existing_data['file_names']]
    checkboxes = []
    for filename in existing_data['file_names']:
        ds_count = existing_data['checkbox_info'][filename]['ds_count']
        dataset_labels = [f'Datensatz {i + 1}' for i in range(ds_count)]
        dataset_checklist = dcc.Checklist(
            id={'type': 'dataset-checklist', 'index': filename},
            options=[{'label': lbl, 'value': i} for i, lbl in enumerate(dataset_labels)],
            value=list(range(ds_count)),
            labelStyle={'display': 'block', 'margin-left': '20px'}
        )
        file_checkbox = dcc.Checklist(
            id={'type': 'file-checkbox', 'index': filename},
            options=[{'label': filename, 'value': filename}],
            value=[filename],
            labelStyle={'font-weight': 'bold'}
        )
        col = dbc.Col([file_checkbox, dataset_checklist], width="auto")
        checkboxes.append(col)

    checkbox_row = dbc.Row(
        checkboxes,
        justify="start",
        className="g-0",
        style={"overflowX": "auto", "whiteSpace": "nowrap", "display": "flex", "flexWrap": "nowrap"}
    )

    # -------------------------------------
    # 5) RÜCKGABE
    # -------------------------------------
    return html.Ul(all_file_names_html), existing_data, checkbox_row
