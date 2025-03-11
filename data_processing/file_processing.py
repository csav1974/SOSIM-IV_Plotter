import pandas as pd
from input_handling.parser import read_input


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


def process_file_extern(contents, filename):
    alle_zeilen = read_input(contents)

    alle_zeilen = [
        [cell.replace('\r\n', '\n').replace('\r', '\n') if isinstance(cell, str) else cell for cell in row]
        for row in alle_zeilen
    ]
    # Überprüfen, ob genügend Zeilen vorhanden sind
    if len(alle_zeilen) < 2:
        parameter_values_list = None
    else:
        parameter_values_list = []
        # Annahme: Erste Zeile ist der Header
        i = 1
        # Solange die Zeile als Parameterzeile interpretiert werden kann, hinzufügen.
        # Hier muss definiert werden, wann eine Zeile als Parameterzeile gilt.
        while i < len(alle_zeilen):
            if is_parameter_row(alle_zeilen[i]):
                parameter_values_list.append(alle_zeilen[i])
            i += 1
        # Die verbleibenden Zeilen enthalten dann die eigentlichen Daten
        alle_zeilen = alle_zeilen[2:]


    # Schritt 2: Verarbeitung der Datenabschnitte
    df_list = []
    i = 0
    while i < len(alle_zeilen):
        # Überspringe leere Zeilen
        while i < len(alle_zeilen) and all(zelle == '' or zelle is None for zelle in alle_zeilen[i][:10]):
            i += 1
        if i >= len(alle_zeilen):
            break  # Ende der Daten erreicht
        daten_zeilen = []
        while i < len(alle_zeilen) and not all(zelle == '' or zelle is None for zelle in alle_zeilen[i][:10]):
            if i + 1 < len(alle_zeilen):
                non_empty_cells_in_next_row = sum(
                    1 for zelle in alle_zeilen[i + 1][:20] if zelle != '' and zelle is not None
                )
                if non_empty_cells_in_next_row > 8:
                    i += 1
                    break
            daten_zeilen.append(alle_zeilen[i])
            i += 1
        if len(daten_zeilen) < 2:
            continue  # Überspringe Abschnitte mit nicht genügend Daten
        daten = daten_zeilen[1:]  # Ignoriere die erste Zeile (Überschrift)
        df = pd.DataFrame(daten, columns=header)
        df['Voltage [mV]'] = pd.to_numeric(df['Voltage [mV]'], errors='coerce') 
        df['Current [mA]'] = pd.to_numeric(df['Current [mA]'], errors='coerce') * -1
        df = df.dropna(subset=['Voltage [mV]', 'Current [mA]'])
        df_list.append(df)
    
    return df_list, parameter_values_list

def is_parameter_row(row):
    count = sum(1 for cell in row if cell is not None and cell != '')
    return count >= 10
