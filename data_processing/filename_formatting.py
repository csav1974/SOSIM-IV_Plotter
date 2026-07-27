import re
from datetime import datetime


FILENAME_PREFIX = "IV Measurement_"
XLSX_SUFFIX_RE = re.compile(r"\.xlsx$", re.IGNORECASE)
DATETIME_SUFFIX_RE = re.compile(
    r"^(?P<name>.+)_(?P<datetime>\d{2}-\d{2}-\d{2}_\d{4})$"
)


def normalize_filename(filename: str) -> str:
    """Return the filename used in the plot and parameter table."""

    display_name = XLSX_SUFFIX_RE.sub("", str(filename))
    if display_name.startswith(FILENAME_PREFIX):
        display_name = display_name[len(FILENAME_PREFIX):]
    return display_name.strip("_ ")


def split_filename_datetime(filename: str) -> tuple[str, str | None]:
    """Split a valid trailing ``YY-MM-DD_HHMM`` value from a display filename."""

    display_name = normalize_filename(filename)
    match = DATETIME_SUFFIX_RE.fullmatch(display_name)
    if match is None:
        return display_name, None

    datetime_text = match.group("datetime")
    try:
        datetime.strptime(datetime_text, "%y-%m-%d_%H%M")
    except ValueError:
        return display_name, None

    name = match.group("name").rstrip("_ ")
    if not name:
        return display_name, None
    return name, datetime_text
