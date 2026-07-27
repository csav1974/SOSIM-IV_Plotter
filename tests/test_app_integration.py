import pandas as pd
from dash import html

from app import (
    PARAMETER_TABLE_COLUMNS,
    app,
    calculate_cell_area,
    header,
    prepare_parameter_table_data,
    server,
    toggle_fit_info,
    update_header_parameters,
)
from data_processing import data_processing
from data_processing.filename_formatting import (
    normalize_filename,
    split_filename_datetime,
)
from data_processing.graph_processing import update_graph_extern


def _data_store(filename="IV Measurement_sample.xlsx"):
    dataframe = pd.DataFrame(
        {
            "Voltage [mV]": [-100.0, 0.0, 500.0],
            "Current [mA]": [35.0, 34.0, 5.0],
        }
    )
    parameters = [None] * len(header)
    parameters[header.index("Voc [mV]")] = 620.0
    parameters[header.index("Isc [mA]")] = 120.0
    parameters[header.index("Jsc [mA/cm²]")] = 30.0
    parameters[header.index("Rp [kOhm]")] = 1.2
    parameters[header.index("Rs [Ohm]")] = 2.4
    return {
        "file_names": [filename],
        "data": {
            filename: [dataframe.to_json(orient="split")],
        },
        "parameters": {filename: [parameters]},
        "fits": {
            filename: [
                {
                    "success": True,
                    "rp_kohm": 1.5,
                    "rs_ohm": 1.8,
                    "voltage_mv": [-100.0, 0.0, 500.0],
                    "current_ma": [35.1, 34.1, 4.9],
                }
            ]
        },
    }


def test_wsgi_server_is_exported_for_container_runtime():
    assert server is app.server


def _find_component(component, component_id):
    if getattr(component, "id", None) == component_id:
        return component
    children = getattr(component, "children", None)
    if children is None:
        return None
    if not isinstance(children, (list, tuple)):
        children = [children]
    for child in children:
        found = _find_component(child, component_id)
        if found is not None:
            return found
    return None


def test_fit_info_is_hidden_by_default_and_can_be_toggled():
    collapse = _find_component(app.layout, "fit-info-collapse")
    button = _find_component(app.layout, "fit-info-btn")

    assert collapse is not None
    assert collapse.is_open is False
    assert button.children == "Fit-Info anzeigen"
    assert toggle_fit_info(1, False) == (True, "Fit-Info ausblenden")
    assert toggle_fit_info(2, True) == (False, "Fit-Info anzeigen")


def test_parameter_columns_start_in_requested_order_and_preserve_the_rest():
    requested_prefix = [
        "Voc [mV]",
        "Isc [mA]",
        "Jsc [mA/cm²]",
        "FF [%]",
        "Eta [%]",
        "Rp [kOhm]",
        "Rs [Ohm]",
        "Rp Fit [kOhm]",
        "Rs Fit [Ohm]",
        "Cell Area [cm²]",
    ]
    previous_columns = header[3:-2] + ["Rp Fit [kOhm]", "Rs Fit [Ohm]"]
    expected_remainder = [
        column for column in previous_columns if column not in requested_prefix
    ]

    assert PARAMETER_TABLE_COLUMNS[:10] == requested_prefix
    assert PARAMETER_TABLE_COLUMNS[10:] == expected_remainder


def test_cell_area_calculation_handles_valid_and_invalid_values():
    assert calculate_cell_area(120.0, 30.0) == 4.0
    assert calculate_cell_area("120", "30") == 4.0
    assert calculate_cell_area(None, 30.0) is None
    assert calculate_cell_area(120.0, 0.0) is None
    assert calculate_cell_area(float("inf"), 30.0) is None


def test_filename_display_removes_only_export_prefix_and_xlsx_suffix():
    assert normalize_filename("IV Measurement_sample.xlsx") == "sample"
    assert normalize_filename("IV Measurement_sample.XLSX") == "sample"
    assert normalize_filename("sample.xlsx") == "sample"
    assert normalize_filename("sample_IV Measurement_note.xlsx") == (
        "sample_IV Measurement_note"
    )


def test_filename_datetime_is_split_only_for_valid_trailing_values():
    assert normalize_filename(
        "IV Measurement_ref_24-09-30_1535.xlsx"
    ) == "ref_24-09-30_1535"
    assert split_filename_datetime(
        "IV Measurement_ref_24-09-30_1535.xlsx"
    ) == ("ref", "24-09-30_1535")
    assert split_filename_datetime(
        "IV Measurement_ref_24-13-30_1535.xlsx"
    ) == ("ref_24-13-30_1535", None)
    assert split_filename_datetime(
        "IV Measurement_ref_24-09-30_1535_note.xlsx"
    ) == ("ref_24-09-30_1535_note", None)


def test_checkbox_uses_clean_name_and_puts_datetime_on_second_line():
    filename = "IV Measurement_ref_24-09-30_1535.xlsx"
    existing_data = {
        "file_names": [filename],
        "data": {},
        "parameters": {},
        "fits": {},
        "checkbox_info": {filename: {"ds_count": 1}},
    }

    _, _, checkbox_row = data_processing.update_output_extern(
        None, None, existing_data
    )
    checkbox = _find_component(
        checkbox_row, {"type": "file-checkbox", "index": filename}
    )
    label = checkbox.options[0]["label"]

    assert isinstance(label, html.Span)
    assert label.children[0] == "ref"
    assert isinstance(label.children[1], html.Br)
    assert label.children[2] == "24-09-30_1535"
    assert checkbox.options[0]["value"] == filename


def test_datetime_filename_stays_on_one_line_in_table_and_plot():
    filename = "IV Measurement_ref_24-09-30_1535.xlsx"
    data_store = _data_store(filename)
    file_id = {"type": "file-checkbox", "index": filename}
    dataset_id = {"type": "dataset-checklist", "index": filename}

    rows = prepare_parameter_table_data(
        data_store,
        [[filename]],
        [file_id],
        [[0]],
        [dataset_id],
    )
    figure = update_graph_extern(
        [[0]],
        "auto",
        None,
        None,
        None,
        None,
        False,
        False,
        True,
        data_store,
        [dataset_id],
    )

    expected_name = "ref_24-09-30_1535 - Datensatz 1"
    assert rows[0]["Datei"] == expected_name
    assert figure.data[0].name == expected_name
    assert figure.data[1].name == f"{expected_name} - Fit"


def test_parameter_table_keeps_read_values_and_adds_fit_values():
    rows = prepare_parameter_table_data(
        _data_store(),
        [["IV Measurement_sample.xlsx"]],
        [{"type": "file-checkbox", "index": "IV Measurement_sample.xlsx"}],
        [[0]],
        [{"type": "dataset-checklist", "index": "IV Measurement_sample.xlsx"}],
    )

    assert len(rows) == 1
    assert rows[0]["Datei"] == "sample - Datensatz 1"
    assert rows[0]["Rp [kOhm]"] == 1.2
    assert rows[0]["Rs [Ohm]"] == 2.4
    assert rows[0]["Rp Fit [kOhm]"] == 1.5
    assert rows[0]["Rs Fit [Ohm]"] == 1.8
    assert rows[0]["Cell Area [cm²]"] == 4.0


def test_selected_dataset_parameters_show_when_parent_file_is_unselected():
    filename = "IV Measurement_sample.xlsx"
    file_id = {"type": "file-checkbox", "index": filename}
    dataset_id = {"type": "dataset-checklist", "index": filename}

    parameter_table = update_header_parameters(
        _data_store(),
        [[]],
        [file_id],
        [[0]],
        [dataset_id],
    )

    assert len(parameter_table.data) == 1
    assert parameter_table.data[0]["Datei"] == "sample - Datensatz 1"
    assert parameter_table.data[0]["Voc [mV]"] == 620.0
    assert parameter_table.data[0]["Rp Fit [kOhm]"] == 1.5


def test_unselected_file_with_no_selected_dataset_hides_parameters():
    filename = "IV Measurement_sample.xlsx"

    rows = prepare_parameter_table_data(
        _data_store(),
        [[]],
        [{"type": "file-checkbox", "index": filename}],
        [[]],
        [{"type": "dataset-checklist", "index": filename}],
    )

    assert rows == []


def test_selected_file_remains_fallback_when_dataset_state_is_absent():
    filename = "IV Measurement_sample.xlsx"

    rows = prepare_parameter_table_data(
        _data_store(),
        [[filename]],
        [{"type": "file-checkbox", "index": filename}],
        [],
        [],
    )

    assert len(rows) == 1
    assert rows[0]["Datei"] == "sample - Datensatz 1"


def test_upload_processing_stores_one_fit_per_dataset(monkeypatch):
    dataframe = pd.DataFrame(
        {
            "Voltage [mV]": [-100.0, 0.0, 500.0],
            "Current [mA]": [35.0, 34.0, 5.0],
        }
    )
    fit = {"success": True, "rp_kohm": 1.5, "rs_ohm": 1.8}
    monkeypatch.setattr(
        data_processing,
        "process_file_extern",
        lambda _contents, _filename: ([dataframe], [[None] * len(header)]),
    )
    monkeypatch.setattr(data_processing, "fit_single_diode", lambda _df: fit)
    monkeypatch.setattr(data_processing.time, "sleep", lambda _seconds: None)

    _, stored, _ = data_processing.update_output_extern(
        ["data:application/octet-stream;base64,unused"],
        ["sample.xlsx"],
        None,
    )

    assert len(stored["data"]["sample.xlsx"]) == 1
    assert stored["fits"]["sample.xlsx"] == [fit]


def test_parameter_table_still_shows_fit_when_read_values_are_missing():
    data_store = _data_store()
    data_store["parameters"]["IV Measurement_sample.xlsx"] = None

    rows = prepare_parameter_table_data(
        data_store,
        [["IV Measurement_sample.xlsx"]],
        [{"index": "IV Measurement_sample.xlsx"}],
        [[0]],
        [{"index": "IV Measurement_sample.xlsx"}],
    )

    assert len(rows) == 1
    assert rows[0]["Rp Fit [kOhm]"] == 1.5
    assert rows[0]["Rs Fit [Ohm]"] == 1.8


def test_graph_overlay_can_be_toggled_and_tracks_axis_flips():
    data_store = _data_store()
    common_arguments = (
        [[0]],
        "auto",
        None,
        None,
        None,
        None,
    )
    ids = [{"type": "dataset-checklist", "index": "IV Measurement_sample.xlsx"}]

    visible = update_graph_extern(
        *common_arguments, False, False, True, data_store, ids
    )
    hidden = update_graph_extern(
        *common_arguments, False, False, False, data_store, ids
    )
    flipped = update_graph_extern(
        *common_arguments, True, True, True, data_store, ids
    )

    assert len(visible.data) == 2
    assert visible.data[0].name == "sample - Datensatz 1"
    assert visible.data[1].name == "sample - Datensatz 1 - Fit"
    assert visible.data[1].line.dash == "dash"
    assert visible.data[0].line.color == visible.data[1].line.color
    assert len(hidden.data) == 1
    assert list(flipped.data[1].x) == [100.0, -0.0, -500.0]
    assert list(flipped.data[1].y) == [-35.1, -34.1, -4.9]
