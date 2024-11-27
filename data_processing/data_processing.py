from dash import dcc, html
import dash_bootstrap_components as dbc

from data_processing.file_processing import process_file_extern


def update_output_extern(list_of_contents, list_of_names):
    if list_of_contents is not None:
        data = {}
        file_names = []
        parameters = {}  # Speicher für die Parameterwerte
        checkboxes = []
        for contents, filename in zip(list_of_contents, list_of_names):
            df_list, parameter_values = process_file_extern(contents, filename)
            # DataFrames in JSON konvertieren
            data[filename] = [df.to_json(date_format='iso', orient='split') for df in df_list]
            parameters[filename] = parameter_values
            file_names.append(html.Li(filename))
            # Checkboxes erstellen
            dataset_labels = [f'Datensatz {idx + 1}' for idx in range(len(df_list))]
            dataset_checklist = dcc.Checklist(
                id={'type': 'dataset-checklist', 'index': filename},
                options=[{'label': label, 'value': idx} for idx, label in enumerate(dataset_labels)],
                value=list(range(len(df_list))),  # Standardmäßig alle ausgewählt
                labelStyle={'display': 'block', 'margin-left': '20px'}
            )
            # Checkbox für die Datei
            file_checkbox = dcc.Checklist(
                id={'type': 'file-checkbox', 'index': filename},
                options=[{'label': filename, 'value': filename}],
                value=[filename],  # Standardmäßig ausgewählt
                labelStyle={'font-weight': 'bold'}
            )
            # Erstelle eine Spalte für jede Datei
            col = dbc.Col([
                file_checkbox,
                dataset_checklist
            ], width="auto")
            checkboxes.append(col)
        # Ordne die Spalten nebeneinander in einer Zeile an
        checkbox_row = dbc.Row(checkboxes, justify="start", className="g-0")
        # Speichere sowohl die Daten als auch die Parameter
        return html.Ul(file_names), {'data': data, 'parameters': parameters}, checkbox_row
    else:
        return 'Keine Dateien hochgeladen.', {}, ''