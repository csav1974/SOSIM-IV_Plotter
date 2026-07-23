# SOSIM I–V Plotter

SOSIM I–V Plotter is a browser-based Dash application for inspecting photovoltaic
current–voltage measurements. It reads one or more instrument-exported Excel
workbooks, plots every detected dataset, displays the measurement parameters, and
fits compatible curves to the single-diode model to estimate series and parallel
resistance.

The application can be run as a self-contained Docker container or directly with
Python 3.10.

## Features

- Upload several measurement workbooks in one browser session.
- Select complete files or individual datasets for plotting.
- Plot measured voltage and current in mV and mA.
- Switch between automatic and manual plot ranges.
- Use the included CIGS and tandem axis presets.
- Flip the voltage and current axes independently.
- Fit each compatible dataset to the single-diode model.
- Show or hide fitted curves without recalculating the measurements.
- Display fitted `Rs` and `Rp` next to the values read from the workbook.
- Calculate `Cell Area [cm²]` from `Isc / Jsc`.
- Select parameter columns and export the visible datasets as CSV.
- Keep uploaded measurements in memory; the application does not require a
  database or persistent host volume.

## Supported input files

The normal application input is the SOSIM instrument-exported `.xlsx` workbook
layout. The importer expects:

- the relevant data in the first worksheet;
- the standard SOSIM parameter and measurement columns;
- voltage in `Voltage [mV]`;
- current in `Current [mA]`; and
- one or more measurement sections separated according to the instrument export
  structure.

The importer preserves the established XLSX processing behavior, including its
current-sign conversion. The ODS workbook under `exampleData/` is a development
reference measurement and is not an additional supported upload format.

Uploads are processed in memory and stored in the browser-side Dash session.
Restarting the container or refreshing the session does not create or recover a
server-side archive of uploaded files.

## Using the application

1. Open the application in a browser.
2. Select one or more `.xlsx` measurement files with **Dateien auswählen**.
3. Use the generated file and dataset checkboxes to choose which curves are shown.
4. Adjust the graph if needed:
   - **x-Flip** reverses the voltage values;
   - **y-Flip** reverses the current values;
   - **Fit-Kurve** shows or hides the fitted overlays;
   - **Automatisch** derives the plot limits from the visible data; and
   - **Manuell** enables custom limits and the CIGS/tandem presets.
5. Use **Fit-Info anzeigen** to open the explanation of the resistance fit.
6. Review the parameter table below the graph.
7. Select the desired download columns and choose **Download Data** to create
   `selected_data.csv`.

## Parameters

The first parameters in the frontend table are ordered as follows:

1. `Voc [mV]`
2. `Isc [mA]`
3. `Jsc [mA/cm²]`
4. `FF [%]`
5. `Eta [%]`
6. `Rp [kOhm]`
7. `Rs [Ohm]`
8. `Rp Fit [kOhm]`
9. `Rs Fit [Ohm]`
10. `Cell Area [cm²]`

The remaining instrument parameters follow these columns in their original
relative order. `Rp` and `Rs` are values read from the workbook; `Rp Fit` and
`Rs Fit` are calculated from the measured curve.

Cell area is calculated with matching mA-based units:

```text
Cell Area [cm²] = Isc [mA] / Jsc [mA/cm²]
```

If either value is missing or invalid, or `Jsc` is zero, the calculated table cell
is left empty.

## Single-diode fitting

The fitter uses the implicit single-diode equation

```text
I = Iph - I0 · (exp((V + I · Rs) / a) - 1) - (V + I · Rs) / Rp
```

where `a` is the effective diode voltage. Calculations are performed internally
in volts and amperes. The explicit current solution is evaluated in a numerically
stable log-space form.

The fitting procedure:

1. removes invalid voltage/current samples;
2. detects and normalizes either supported current convention;
3. estimates initial `Rp` and `Rs` values from local slopes near `V = 0` and
   `I = 0`;
4. applies positive, data-scaled parameter bounds;
5. performs bounded nonlinear least squares with a robust `soft_l1` loss;
6. refines the robust scale from a pilot fit; and
7. transforms the fitted current back to the displayed sign convention.

At least eight valid measurement points are required. A fit whose normalized
error is too large is rejected instead of displaying a misleading overlay. This
can happen when a curve is not described adequately by the single-diode model or
contains a large compliance-limited region.

## Installation with Docker

Docker is the recommended installation method because it supplies Python and all
application dependencies inside the image.

### Prerequisites

Install one of the following:

- Docker Desktop on Windows, macOS, or Linux; or
- Docker Engine with the Docker Compose plugin on Linux.

Confirm that Docker and Compose are available:

```bash
docker --version
docker compose version
```

Copy or clone this complete project directory onto the target machine, then run
the following commands from the directory containing `Dockerfile` and
`compose.yaml`.

### Start with Docker Compose

Build the image and start the application:

```bash
docker compose up --build
```

Open <http://localhost:8050/>. To run in the background, use:

```bash
docker compose up -d --build
```

Check the container and its health status:

```bash
docker compose ps
```

View application logs:

```bash
docker compose logs -f
```

Stop and remove the container and its Compose network:

```bash
docker compose down
```

The built image remains available locally as `sosim-iv-plotter:latest` and can be
started again without rebuilding unless the source or dependency files change.

### Start with plain Docker

Compose is convenient but not required:

```bash
docker build -t sosim-iv-plotter .
docker run --rm -p 8050:8050 sosim-iv-plotter
```

Open <http://localhost:8050/> and stop the foreground container with `Ctrl+C`.

### Access from another computer

The container publishes port 8050 on all host interfaces. From another computer
on the same network, open:

```text
http://HOST_IP_ADDRESS:8050/
```

The host firewall must allow inbound TCP traffic on port 8050. Do not expose the
application directly to an untrusted public network without an appropriate
reverse proxy, authentication, and TLS configuration.

### Use a different host port

If port 8050 is already occupied, keep the container port unchanged and publish a
different host port. With plain Docker:

```bash
docker run --rm -p 8060:8050 sosim-iv-plotter
```

Then open <http://localhost:8060/>. For Compose, change the port mapping in
`compose.yaml` from `8050:8050` to `8060:8050`.

### Rebuild after source changes

```bash
docker compose up --build -d
```

To force a completely clean dependency and source rebuild:

```bash
docker compose build --no-cache
docker compose up -d
```

## Container design

The `Dockerfile`:

- uses the multi-platform `python:3.10-slim-bookworm` base image;
- installs the locked production dependencies from `Pipfile.lock`;
- copies only the runtime application sources;
- runs as the unprivileged `app` user;
- serves the exported Flask server with Gunicorn on `0.0.0.0:8050`; and
- includes an HTTP health check.

Gunicorn runs two threaded workers. No host volume is necessary because workbook
uploads and Dash state are not persisted to disk.

## Local Python installation

Docker is not required for development. Install Python 3.10 and Pipenv, then run:

```bash
pipenv install --dev
pipenv run python app.py
```

Open <http://127.0.0.1:8050/>. The local development entry point binds only to
the local machine and checks that port 8050 is free before starting.

## Tests

Install the development dependencies first, then run:

```bash
pipenv run pytest -q
```

The automated tests cover the diode equation, robust resistance recovery,
current-sign handling, invalid-fit rejection, upload-store integration, graph
overlays, parameter ordering, cell-area calculation, the collapsible fit
information box, and the WSGI server export.

## Project structure

```text
.
├── app.py                              Dash layout, callbacks, table, and WSGI export
├── input_handling/
│   └── parser.py                       Base64/XLSX decoding
├── data_processing/
│   ├── file_processing.py              Workbook sections and DataFrame creation
│   ├── data_processing.py              Upload state, dataset controls, and fit dispatch
│   ├── diode_fitting.py                 Robust single-diode fitting
│   └── graph_processing.py              Measured and fitted Plotly traces
├── tests/                               Numerical and integration tests
├── Pipfile                              Runtime and development dependencies
├── Pipfile.lock                         Reproducible locked dependency versions
├── Dockerfile                           Production container image
├── compose.yaml                         One-command container orchestration
└── .dockerignore                        Docker build-context exclusions
```

### Runtime data flow

1. Dash receives uploaded workbook contents as Base64 data.
2. `input_handling/parser.py` decodes the workbook in memory.
3. `data_processing/file_processing.py` identifies measurement sections and
   converts valid voltage/current cells to pandas DataFrames.
4. `data_processing/data_processing.py` serializes the datasets into the Dash
   store and calculates one fit result per dataset.
5. `data_processing/graph_processing.py` creates measured traces and optional
   dashed fit overlays.
6. `app.py` filters the selected files/datasets, builds the parameter table, and
   prepares selected columns for CSV download.

## Troubleshooting

### Port 8050 is already in use

Publish a different host port as described above, or stop the process/container
currently using port 8050.

### The container does not become healthy

Inspect its status and logs:

```bash
docker compose ps
docker compose logs --tail=100
```

### Dependency or build cache problems

Rebuild without Docker's cache:

```bash
docker compose down
docker compose build --no-cache
docker compose up
```

### A workbook cannot be imported

Confirm that it is an `.xlsx` file using the expected SOSIM export structure.
The application does not treat arbitrary spreadsheets or the development ODS
reference as normal upload formats.

### No fitted curve is displayed

Ensure **Fit-Kurve** is active and that the dataset contains at least eight valid
points. Curves that fail convergence or do not meet the single-diode fit-quality
threshold are intentionally not overlaid.
