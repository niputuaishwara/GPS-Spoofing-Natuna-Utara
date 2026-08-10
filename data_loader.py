import pandas as pd
import io
import re
from typing import Tuple

# ─────────────────────────────────────────────────────────────
# Security Constraints — STRIDE: DoS & Tampering Prevention
# ─────────────────────────────────────────────────────────────
MAX_FILE_SIZE_MB  = 10       # Max upload size (DoS prevention)
MAX_ROWS          = 2000     # Max records per dataset (DoS prevention)
MIN_ROWS          = 2        # Minimum rows for meaningful analysis
ALLOWED_EXTENSIONS = {'.csv', '.xlsx', '.xls'}

REQUIRED_COLUMNS = {"timestamp", "latitude", "longitude", "sog", "cog"}

COLUMN_ALIASES = {
    "time": "timestamp", "datetime": "timestamp", "date_time": "timestamp",
    "utc": "timestamp", "utc_time": "timestamp",
    "lat": "latitude", "lat_deg": "latitude",
    "lon": "longitude", "lng": "longitude", "long": "longitude", "lon_deg": "longitude",
    "speed": "sog", "speed_over_ground": "sog", "spd": "sog", "knots": "sog",
    "course": "cog", "course_over_ground": "cog", "heading": "cog",
    "hdg": "cog", "bearing": "cog",
}

# Valid coordinate ranges
LAT_MIN, LAT_MAX = -90.0,  90.0
LON_MIN, LON_MAX = -180.0, 180.0
SOG_MIN, SOG_MAX = 0.0,    100.0   # knots — beyond 100 is physically impossible for vessels


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names: lowercase, strip whitespace, apply aliases."""
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    df = df.rename(columns=COLUMN_ALIASES)
    return df


def validate_columns(df: pd.DataFrame) -> Tuple[bool, list]:
    """Check that all required columns are present."""
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    return len(missing) == 0, missing


def sanitize_filename(filename: str) -> str:
    """Strip dangerous characters from filename (path traversal prevention)."""
    basename = re.sub(r'[\\/:*?"<>|]', '_', filename)
    return basename[:128]  # limit length


def validate_data_ranges(df: pd.DataFrame) -> Tuple[pd.DataFrame, list]:
    """
    Validate that coordinate and speed values are within physically valid ranges.
    Returns cleaned DataFrame and list of warnings.
    STRIDE Tampering: detects manipulated/injected GPS coordinates.
    """
    warnings = []
    original_len = len(df)

    # Filter invalid latitudes
    invalid_lat = ~df['latitude'].between(LAT_MIN, LAT_MAX)
    if invalid_lat.any():
        cnt = invalid_lat.sum()
        warnings.append(f"⚠️ {cnt} baris dihapus: latitude di luar rentang [{LAT_MIN}, {LAT_MAX}]")
        df = df[~invalid_lat]

    # Filter invalid longitudes
    invalid_lon = ~df['longitude'].between(LON_MIN, LON_MAX)
    if invalid_lon.any():
        cnt = invalid_lon.sum()
        warnings.append(f"⚠️ {cnt} baris dihapus: longitude di luar rentang [{LON_MIN}, {LON_MAX}]")
        df = df[~invalid_lon]

    # Filter invalid SOG (negative or impossibly high)
    invalid_sog = ~df['sog'].between(SOG_MIN, SOG_MAX)
    if invalid_sog.any():
        cnt = invalid_sog.sum()
        warnings.append(f"⚠️ {cnt} baris dihapus: SOG di luar rentang [{SOG_MIN}, {SOG_MAX}] knots")
        df = df[~invalid_sog]

    removed = original_len - len(df)
    if removed > 0:
        warnings.append(f"Total {removed} baris tidak valid dihapus dari {original_len} baris asli.")

    return df, warnings


def load_dataset(filepath: str) -> pd.DataFrame:
    """Load a dataset from a local filepath (used by simulation)."""
    try:
        df = pd.read_csv(filepath)
        df = normalize_columns(df)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df
    except Exception as e:
        print(f"Error loading dataset {filepath}: {e}")
        return pd.DataFrame()


def load_from_upload(uploaded_file) -> Tuple[pd.DataFrame, bool, list, str]:
    """
    Securely load and validate an uploaded GPS dataset file.

    Security controls:
    - File size limit (DoS prevention)
    - Extension whitelist (Tampering prevention)
    - Filename sanitization (Path traversal prevention)
    - Schema validation (Tampering detection)
    - Coordinate range validation (Injection detection)
    - Row count limits (DoS prevention)
    - Missing value handling

    Returns:
        (DataFrame, is_valid, missing_columns, error_message)
    """
    try:
        # ── 1. Filename Sanitization ──────────────────────────
        safe_name = sanitize_filename(uploaded_file.name)
        ext = '.' + safe_name.rsplit('.', 1)[-1].lower() if '.' in safe_name else ''

        # ── 2. Extension Whitelist Check ──────────────────────
        if ext not in ALLOWED_EXTENSIONS:
            return pd.DataFrame(), False, [], \
                f"Format tidak diizinkan: '{ext}'. Hanya {', '.join(ALLOWED_EXTENSIONS)} yang diterima."

        # ── 3. File Size Limit (DoS Prevention) ───────────────
        file_size_mb = uploaded_file.size / (1024 * 1024)
        if file_size_mb > MAX_FILE_SIZE_MB:
            return pd.DataFrame(), False, [], \
                f"File terlalu besar: {file_size_mb:.1f}MB. Maksimum {MAX_FILE_SIZE_MB}MB."

        # ── 4. Read File ──────────────────────────────────────
        if ext == '.csv':
            content = uploaded_file.read()
            df = None
            for sep in [",", ";", "\t"]:
                try:
                    tmp = pd.read_csv(io.BytesIO(content), sep=sep)
                    if len(tmp.columns) >= 4:
                        df = tmp
                        break
                except Exception:
                    continue
            if df is None:
                return pd.DataFrame(), False, [], "Tidak bisa membaca file CSV. Pastikan format valid."

        elif ext in ('.xlsx', '.xls'):
            df = pd.read_excel(uploaded_file)
        else:
            return pd.DataFrame(), False, [], "Format tidak didukung."

        # ── 5. Empty File Check ───────────────────────────────
        if df is None or df.empty:
            return pd.DataFrame(), False, [], "File kosong atau tidak dapat dibaca."

        # ── 6. Column Normalization & Validation ──────────────
        df = normalize_columns(df)
        is_valid, missing = validate_columns(df)
        if not is_valid:
            return df, False, missing, ""

        # ── 7. Type Coercion & Missing Value Handling ─────────
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        for col in ["latitude", "longitude", "sog", "cog"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df.dropna(subset=["timestamp", "latitude", "longitude", "sog", "cog"])

        # ── 8. Minimum Rows Check ─────────────────────────────
        if len(df) < MIN_ROWS:
            return pd.DataFrame(), False, [], \
                f"Dataset terlalu sedikit: {len(df)} baris. Minimum {MIN_ROWS} baris diperlukan."

        # ── 9. Row Count Limit (DoS Prevention) ───────────────
        if len(df) > MAX_ROWS:
            df = df.head(MAX_ROWS)
            # Will show warning in caller via metadata
            df.attrs['truncated'] = True
            df.attrs['truncated_to'] = MAX_ROWS

        # ── 10. Coordinate Range Validation ───────────────────
        df, range_warnings = validate_data_ranges(df)
        if len(df) < MIN_ROWS:
            return pd.DataFrame(), False, [], \
                "Setelah validasi koordinat, data tidak cukup untuk dianalisis."

        # ── 11. Sort & Reset Index ────────────────────────────
        df = df.sort_values("timestamp").reset_index(drop=True)

        # Attach warnings as metadata
        df.attrs['warnings'] = range_warnings

        return df, True, [], ""

    except Exception as e:
        return pd.DataFrame(), False, [], f"Error saat memproses file: {str(e)}"
