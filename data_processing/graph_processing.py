import plotly.graph_objects as go
import pandas as pd
import io

def update_graph_extern(selected_datasets_per_file, axis_range_toggle, x_min_input, x_max_input, y_min_input, y_max_input, x_flip_btn, y_flip_btn, data_store, ids):
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


            # Bereite die x- und y-Werte vor und flippe sie ggf.
            x_vals = df['Voltage [mV]']
            y_vals = df['Current [mA]']

            if x_flip_btn:      # hier deine Variable aus dem Callback
                x_vals = -1 * x_vals
            if y_flip_btn:      # hier deine Variable aus dem Callback
                y_vals = -1 * y_vals

            # Sammle alle x- und y-Werte für die Achsenskalierung
            all_x_values.extend(x_vals.tolist())
            all_y_values.extend(y_vals.tolist())

            # Füge die (ggf. geflippten) Daten dem Graphen hinzu
            fig.add_trace(
                go.Scatter(
                    x=x_vals,
                    y=y_vals,
                    mode='lines',
                    name=label
                )
            )
    
    if axis_range_toggle == 'manual':
        # Verwende die vom Benutzer eingegebenen Werte
        try:
            x_min = float(x_min_input) if x_min_input is not None else None
            x_max = float(x_max_input) if x_max_input is not None else None
            y_min = float(y_min_input) if y_min_input is not None else None
            y_max = float(y_max_input) if y_max_input is not None else None
        except ValueError:
            # Falls die Eingaben keine gültigen Zahlen sind, verwende automatische Bereiche
            x_min = None
            x_max = None
            y_min = None
            y_max = None
    else:
        # Bestimme die minimalen und maximalen Werte, einschließlich 0
        x_min = min(all_x_values + [0])
        x_max = max(all_x_values + [0])
        y_min = min(all_y_values + [0])
        y_max = max(all_y_values + [0])
        
        # Füge etwas Abstand hinzu (15% des Bereichs)
        x_margin = abs((x_max - x_min) * 0.15)
        y_margin = abs((y_max - y_min) * 0.15)
        x_min -= x_margin
        x_max += x_margin
        y_min -= y_margin
        y_max += y_margin

    # Aktualisiere das Layout der Figur
    fig.update_layout(
        xaxis_title='Voltage [mV]',
        yaxis_title='Current [mA]',
        legend_title='Datensätze',
        showlegend=True,
        xaxis=dict(
            zeroline=True,
            zerolinewidth=2,
            zerolinecolor='black',
            showgrid=True,
            gridcolor='lightgray',
            range=[x_min, x_max] if x_min is not None and x_max is not None else None
        ),
        yaxis=dict(
            zeroline=True,
            zerolinewidth=2,
            zerolinecolor='black',
            showgrid=True,
            gridcolor='lightgray',
            range=[y_min, y_max] if y_min is not None and y_max is not None else None
        )
    )
    
    return fig
