from dash import dcc, html
import dash_bootstrap_components as dbc

from data_processing.file_processing import process_file_extern

def update_output_extern(list_of_contents, list_of_names, existing_data):
    """
    Verarbeitet neu hochgeladene Dateien und vereint sie mit bereits bestehenden Daten.
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
    # Falls wir noch keine bestehenden Daten haben, erstellen wir ein leeres Grundgerüst
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
        # Wir bauen trotzdem die Checkboxes und Dateinamen-Liste für alle schon vorhandenen Dateien
        checkboxes = []
        for filename in existing_data['file_names']:
            # Anzahl Datensätze, die wir zur Datei gespeichert haben
            ds_count = existing_data['checkbox_info'].get(filename, {}).get('ds_count', 1)

            dataset_labels = [f'Datensatz {i + 1}' for i in range(ds_count)]
            dataset_checklist = dcc.Checklist(
                id={'type': 'dataset-checklist', 'index': filename},
                options=[{'label': lbl, 'value': i} for i, lbl in enumerate(dataset_labels)],
                value=list(range(ds_count)),  # standardmäßig alle ausgewählt
                labelStyle={'display': 'block', 'margin-left': '20px'}
            )
            file_checkbox = dcc.Checklist(
                id={'type': 'file-checkbox', 'index': filename},
                options=[{'label': filename, 'value': filename}],
                value=[filename],  # standardmäßig ausgewählt
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

        # Liste von HTML <li> für alle bisher bekannten Dateinamen
        all_file_names_html = [html.Li(fn) for fn in existing_data['file_names']]

        return html.Ul(all_file_names_html), existing_data, checkbox_row

    # --------------------------------------------
    # 3) FALL: ES GIBT NEUE DATEIEN ZU VERARBEITEN
    # --------------------------------------------
    # Hier erzeugen wir die neuen Entries für data/parameters
    data = {}
    parameters = {}

    # Wir gehen die neu hochgeladenen Dateien durch:
    for contents, filename in zip(list_of_contents, list_of_names):
        # Datei verarbeiten (DataFrame-Liste + Parameterwerte)
        df_list, parameter_values = process_file_extern(contents, filename)

        # DataFrames in JSON konvertieren, damit sie in dcc.Store speicherbar sind
        data[filename] = [df.to_json(date_format='iso', orient='split') for df in df_list]
        parameters[filename] = parameter_values

        # Falls wir diese Datei noch nicht kennen, fügen wir sie in die Liste der Filenamen ein
        if filename not in existing_data['file_names']:
            existing_data['file_names'].append(filename)

        # Merke dir, wie viele Datensätze (DataFrames) diese Datei hat
        existing_data['checkbox_info'][filename] = {'ds_count': len(df_list)}

    # Mergen: alte und neue Daten
    existing_data['data'].update(data)
    existing_data['parameters'].update(parameters)

    # -------------------------------------
    # 4) AUFBAU DES LAYOUTS (DATEIEN + CHECKBOXES)
    # -------------------------------------
    # Liste aller Dateinamen
    all_file_names_html = [html.Li(fn) for fn in existing_data['file_names']]

    # Checkboxes für alle Dateien (alte + neue)
    checkboxes = []
    for filename in existing_data['file_names']:
        ds_count = existing_data['checkbox_info'][filename]['ds_count']
        dataset_labels = [f'Datensatz {i + 1}' for i in range(ds_count)]
        dataset_checklist = dcc.Checklist(
            id={'type': 'dataset-checklist', 'index': filename},
            options=[{'label': lbl, 'value': i} for i, lbl in enumerate(dataset_labels)],
            value=list(range(ds_count)),  # standardmäßig alle ausgewählt
            labelStyle={'display': 'block', 'margin-left': '20px'}
        )

        file_checkbox = dcc.Checklist(
            id={'type': 'file-checkbox', 'index': filename},
            options=[{'label': filename, 'value': filename}],
            value=[filename],  # standardmäßig ausgewählt
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
    #  - HTML-Liste sämtlicher Dateien (alt + neu)
    #  - Das gemergte existing_data (enthält Data, Parameter, Dateinamen, Checkbox-Infos)
    #  - Checkboxes für alle Dateien
    return html.Ul(all_file_names_html), existing_data, checkbox_row
