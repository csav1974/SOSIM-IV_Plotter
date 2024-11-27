import plotly.graph_objects as go
import pandas as pd
import io


def update_graph_extern(selected_datasets_per_file, data_store, ids):
    # Erstelle eine leere Figur mit go.Figure
    fig = go.Figure()
    
    if not data_store or 'data' not in data_store:
        return fig  # Leere Grafik zurückgeben

    all_x_values = []
    all_y_values = []

    for selected_datasets, id_dict in zip(selected_datasets_per_file, ids):
        filename = id_dict['index']
        df_json_list = data_store['data'].get(filename, [])
        for idx in selected_datasets:
            df_json = df_json_list[idx]
            df = pd.read_json(io.StringIO(df_json), orient='split')
            label = f'{filename} - Datensatz {idx + 1}'

            # Sammle alle x- und y-Werte für die Achsenskalierung
            all_x_values.extend(df['Voltage [mV]'].tolist())
            all_y_values.extend(df['Current [mA]'].tolist())

            # Füge die Daten dem Graphen hinzu
            fig.add_trace(go.Scatter(
                x=df['Voltage [mV]'],
                y=df['Current [mA]'],
                mode='lines',
                name=label
            ))
    
    # Bestimme die minimalen und maximalen Werte, einschließlich 0
    x_min = min(all_x_values + [0])
    x_max = max(all_x_values + [0])
    y_min = min(all_y_values + [0])
    y_max = max(all_y_values + [0])

    # Aktualisiere das Layout der Figur
    fig.update_layout(
        title='IV-Plot',
        xaxis_title='Voltage [mV]',
        yaxis_title='Current [mA]',
        legend_title='Datensätze',
        xaxis=dict(
            zeroline=True,
            zerolinewidth=2,
            zerolinecolor='black',
            showgrid=True,
            gridcolor='lightgray',
            range=[x_min, x_max]
        ),
        yaxis=dict(
            zeroline=True,
            zerolinewidth=2,
            zerolinecolor='black',
            showgrid=True,
            gridcolor='lightgray',
            range=[y_min, y_max]
        )
    )
    
    return fig