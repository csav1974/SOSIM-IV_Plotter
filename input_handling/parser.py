import pylightxl
import base64
import io

def read_input(contents):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    # In-memory BytesIO-Objekt erstellen
    file_io = io.BytesIO(decoded)

    # Excel-Datei mit pylightxl aus dem BytesIO-Objekt lesen
    db = pylightxl.readxl(fn=file_io)
    # Annahme: Daten sind im ersten Tabellenblatt
    sheet_name = db.ws_names[0]
    sheet = db.ws(ws=sheet_name)
    
    return list(sheet.rows)