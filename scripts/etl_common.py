from __future__ import annotations

import csv
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATASETS_DIR = ROOT / "datasets"
DOCUMENTACION_DIR = ROOT / "Documentacion"
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
CLEAN_DIR = PROCESSED_DIR / "clean"
ANALYTICS_DIR = PROCESSED_DIR / "analytics"
DIMENSIONAL_DIR = ROOT / "dimensional_schema"
SQL_DIR = ROOT / "sql"
REPORTS_DIR = ROOT / "reports"
SCRIPTS_DIR = ROOT / "scripts"

METADATA_PATH = REPORTS_DIR / "etl_metadata.json"
RAW_PROFILE_PATH = REPORTS_DIR / "raw_profile.json"

CSV_NULL = r"\N"
CSV_ENCODINGS = ("utf-8", "utf-8-sig", "latin1")
INFRA_SNAPSHOT_YEAR = 2022
INFRA_SNAPSHOT_TIME_ID = 202200
INFRA_USE_RECOMMENDED = (
    "variable estructural contextual; no interpretar como medicion anual"
)

CANONICAL_ALCALDIAS = [
    "AZCAPOTZALCO",
    "ALVARO OBREGON",
    "BENITO JUAREZ",
    "COYOACAN",
    "CUAJIMALPA DE MORELOS",
    "CUAUHTEMOC",
    "GUSTAVO A MADERO",
    "IZTACALCO",
    "IZTAPALAPA",
    "LA MAGDALENA CONTRERAS",
    "MIGUEL HIDALGO",
    "MILPA ALTA",
    "TLAHUAC",
    "TLALPAN",
    "VENUSTIANO CARRANZA",
    "XOCHIMILCO",
]

ALCALDIA_ID = {key: idx for idx, key in enumerate(CANONICAL_ALCALDIAS, start=1)}
ALCALDIA_NAME = {key: key.title() for key in CANONICAL_ALCALDIAS}

MUNICIPIO_CODE_TO_ALCALDIA = {
    2: "AZCAPOTZALCO",
    3: "COYOACAN",
    4: "CUAJIMALPA DE MORELOS",
    5: "GUSTAVO A MADERO",
    6: "IZTACALCO",
    7: "IZTAPALAPA",
    8: "LA MAGDALENA CONTRERAS",
    9: "MILPA ALTA",
    10: "ALVARO OBREGON",
    11: "TLAHUAC",
    12: "TLALPAN",
    13: "XOCHIMILCO",
    14: "BENITO JUAREZ",
    15: "CUAUHTEMOC",
    16: "MIGUEL HIDALGO",
    17: "VENUSTIANO CARRANZA",
}
ALCALDIA_TO_MUNICIPIO_CODE = {
    alcaldia: municipio for municipio, alcaldia in MUNICIPIO_CODE_TO_ALCALDIA.items()
}

SOCIAL_VARIABLES = [
    "mmip",
    "rei",
    "nbi",
    "ccevj",
    "cbdj",
    "csj",
    "ctelj",
    "cenj",
    "ett",
    "casi",
    "cassi",
    "cyt",
]
SOCIAL_FEATURES = [f"{var}_wmean" for var in SOCIAL_VARIABLES]

INFRA_SUM_VARIABLES = [
    "ba1_noeqsa",
    "ba8_nomerc",
    "ba8_noloca",
    "ba9_no_gua",
    "ba3_noeqed",
    "resid_ton",
    "alump_sum",
]
INFRA_AVG_VARIABLES = [
    "p_porcelec",
    "r_valelect",
    "p_aguapot",
    "r_val_dren",
    "epr_pob",
    "r_epr_pob",
    "r_resd_ton",
    "alump_mean",
    "r_alump_su",
    "r_alump_mn",
    "s_ri_6",
    "c_ri_6",
]
INFRA_FEATURES = [
    "mercados_total",
    "locales_total",
    "iluminacion_total",
    "iluminacion_promedio",
    "residuos_ton_total",
    "equipamiento_salud_total",
    "equipamiento_educativo_total",
    "agua_potable_promedio",
    "electricidad_promedio",
    "drenaje_promedio",
]

ROBO_SUBTIPOS = [
    "ROBO_A_TRANSEUNTE",
    "ROBO_A_NEGOCIO",
    "ROBO_A_CASA_HABITACION",
    "ROBO_DE_VEHICULO",
    "ROBO_DE_ACCESORIOS_AUTO",
    "ROBO_DEL_INTERIOR_DE_VEHICULO",
    "OTRO",
]
ROBO_SUBTIPO_COLUMNS = {
    "ROBO_A_TRANSEUNTE": "robo_a_transeunte",
    "ROBO_A_NEGOCIO": "robo_a_negocio",
    "ROBO_A_CASA_HABITACION": "robo_a_casa_habitacion",
    "ROBO_DE_VEHICULO": "robo_de_vehiculo",
    "ROBO_DE_ACCESORIOS_AUTO": "robo_de_accesorios_auto",
    "ROBO_DEL_INTERIOR_DE_VEHICULO": "robo_del_interior_de_vehiculo",
}

MONTH_NAMES = {
    1: "enero",
    2: "febrero",
    3: "marzo",
    4: "abril",
    5: "mayo",
    6: "junio",
    7: "julio",
    8: "agosto",
    9: "septiembre",
    10: "octubre",
    11: "noviembre",
    12: "diciembre",
}
MONTH_NAME_TO_NUM = {
    "ENERO": 1,
    "FEBRERO": 2,
    "MARZO": 3,
    "ABRIL": 4,
    "MAYO": 5,
    "JUNIO": 6,
    "JULIO": 7,
    "AGOSTO": 8,
    "SEPTIEMBRE": 9,
    "SETIEMBRE": 9,
    "OCTUBRE": 10,
    "NOVIEMBRE": 11,
    "DICIEMBRE": 12,
}


def ensure_dirs() -> None:
    for path in [
        DATASETS_DIR,
        DOCUMENTACION_DIR,
        DATA_DIR,
        RAW_DIR,
        PROCESSED_DIR,
        CLEAN_DIR,
        ANALYTICS_DIR,
        DIMENSIONAL_DIR,
        SQL_DIR,
        REPORTS_DIR,
        SCRIPTS_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)


def strip_accents(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value))
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def to_snake_case(value: Any) -> str:
    text = strip_accents(str(value)).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    if not text:
        text = "columna"
    if text[0].isdigit():
        text = f"c_{text}"
    return text


def dedupe_columns(columns: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    result: list[str] = []
    for col in columns:
        base = to_snake_case(col)
        count = seen.get(base, 0)
        result.append(base if count == 0 else f"{base}_{count + 1}")
        seen[base] = count + 1
    return result


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = dedupe_columns([str(c) for c in df.columns])
    return df


def normalize_text_key(value: Any) -> str | None:
    if pd.isna(value):
        return None
    text = strip_accents(str(value)).upper().strip()
    text = text.replace(".", " ")
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


ALCALDIA_VARIATIONS = {
    "GUSTAVO A MADERO": "GUSTAVO A MADERO",
    "GUSTAVO A MADERO CDMX": "GUSTAVO A MADERO",
    "ALVARO OBREGON": "ALVARO OBREGON",
    "BENITO JUAREZ": "BENITO JUAREZ",
    "COYOACAN": "COYOACAN",
    "CUAJIMALPA": "CUAJIMALPA DE MORELOS",
    "CUAJIMALPA DE MORELOS": "CUAJIMALPA DE MORELOS",
    "CUAUHTEMOC": "CUAUHTEMOC",
    "IZTACALCO": "IZTACALCO",
    "IZTAPALAPA": "IZTAPALAPA",
    "MAGDALENA CONTRERAS": "LA MAGDALENA CONTRERAS",
    "LA MAGDALENA CONTRERAS": "LA MAGDALENA CONTRERAS",
    "MIGUEL HIDALGO": "MIGUEL HIDALGO",
    "MILPA ALTA": "MILPA ALTA",
    "TLAHUAC": "TLAHUAC",
    "TLALPAN": "TLALPAN",
    "VENUSTIANO CARRANZA": "VENUSTIANO CARRANZA",
    "XOCHIMILCO": "XOCHIMILCO",
    "AZCAPOTZALCO": "AZCAPOTZALCO",
}


def canonicalize_alcaldia(value: Any) -> str | None:
    if pd.isna(value):
        return None
    if isinstance(value, (int, np.integer)) and int(value) in MUNICIPIO_CODE_TO_ALCALDIA:
        return MUNICIPIO_CODE_TO_ALCALDIA[int(value)]
    if isinstance(value, float) and float(value).is_integer():
        as_int = int(value)
        if as_int in MUNICIPIO_CODE_TO_ALCALDIA:
            return MUNICIPIO_CODE_TO_ALCALDIA[as_int]
    raw = str(value).strip()
    if re.fullmatch(r"\d+(\.0+)?", raw):
        as_int = int(float(raw))
        if as_int in MUNICIPIO_CODE_TO_ALCALDIA:
            return MUNICIPIO_CODE_TO_ALCALDIA[as_int]
    key = normalize_text_key(raw)
    if not key:
        return None
    key = re.sub(r"^(ALCALDIA|DELEGACION)\s+", "", key)
    key = re.sub(r"\s+(ALCALDIA|DELEGACION)$", "", key)
    key = key.replace("GUSTAVO A MADERO", "GUSTAVO A MADERO")
    return ALCALDIA_VARIATIONS.get(key)


def alcaldia_nombre(alcaldia_key: Any) -> str | None:
    key = canonicalize_alcaldia(alcaldia_key)
    return ALCALDIA_NAME.get(key) if key else None


def alcaldia_id(alcaldia_key: Any) -> int | float:
    key = canonicalize_alcaldia(alcaldia_key)
    return ALCALDIA_ID.get(key, np.nan) if key else np.nan


def colonia_key(value: Any) -> str | None:
    return normalize_text_key(value)


def detect_encoding(path: Path) -> str:
    for encoding in CSV_ENCODINGS:
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                handle.readline()
            return encoding
        except UnicodeDecodeError:
            continue
    return "latin1"


def read_csv_robust(path: Path, **kwargs: Any) -> pd.DataFrame:
    last_error: Exception | None = None
    for encoding in CSV_ENCODINGS:
        try:
            return pd.read_csv(path, encoding=encoding, **kwargs)
        except UnicodeDecodeError as exc:
            last_error = exc
    raise RuntimeError(f"No se pudo leer {path} con codificaciones esperadas") from last_error


def iter_csv_robust(path: Path, chunksize: int, **kwargs: Any):
    encoding = detect_encoding(path)
    return pd.read_csv(path, encoding=encoding, chunksize=chunksize, **kwargs)


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8", na_rep=CSV_NULL)


def read_output_csv(path: Path, **kwargs: Any) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8", na_values=[CSV_NULL], keep_default_na=True, **kwargs)


def count_csv_rows(path: Path) -> int:
    with path.open("rb") as handle:
        line_count = sum(block.count(b"\n") for block in iter(lambda: handle.read(1024 * 1024), b""))
    return max(line_count - 1, 0)


def read_csv_header(path: Path) -> list[str]:
    encoding = detect_encoding(path)
    with path.open("r", encoding=encoding, newline="") as handle:
        reader = csv.reader(handle)
        return next(reader)


def coerce_numeric(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def bool_series(value: bool, length: int) -> pd.Series:
    return pd.Series([value] * length, dtype="bool")


def classify_dataset(path: Path) -> str | None:
    columns = set(dedupe_columns(read_csv_header(path)))
    if {"anio_inicio", "delito"}.issubset(columns) and (
        "alcaldia_hecho" in columns or "alcaldia_catalogo" in columns
    ):
        return "fgj"
    if {"mmip", "factor", "entidad", "municipio"}.issubset(columns):
        return "pobreza"
    if {"cve_col", "colonia", "alcaldia"}.issubset(columns) and (
        "ba1_noeqsa" in columns or "alump_sum" in columns
    ):
        return "infraestructura"
    return None


def detect_input_files() -> dict[str, str]:
    files: dict[str, Path] = {}
    candidates = sorted(DATASETS_DIR.glob("*.csv"), key=lambda p: p.stat().st_size, reverse=True)
    for path in candidates:
        dataset = classify_dataset(path)
        if dataset and dataset not in files:
            files[dataset] = path
    required = {"pobreza", "infraestructura", "fgj"}
    missing = sorted(required - set(files))
    if missing:
        raise FileNotFoundError(
            "No se detectaron datasets requeridos en datasets/: " + ", ".join(missing)
        )
    return {key: str(value.relative_to(ROOT)) for key, value in files.items()}


def load_metadata() -> dict[str, Any]:
    if METADATA_PATH.exists():
        return json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    return {}


def save_metadata(metadata: dict[str, Any]) -> None:
    ensure_dirs()
    METADATA_PATH.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def update_metadata(**kwargs: Any) -> dict[str, Any]:
    metadata = load_metadata()
    metadata.update(kwargs)
    save_metadata(metadata)
    return metadata


def project_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return ROOT / path


def time_id(anio: Any, mes: Any = 0) -> int | float:
    try:
        year = int(float(anio))
        month = int(float(mes)) if not pd.isna(mes) else 0
        return year * 100 + month
    except (TypeError, ValueError):
        return np.nan


def parse_month(value: Any) -> int | float:
    if pd.isna(value):
        return np.nan
    if isinstance(value, (int, np.integer)) and 1 <= int(value) <= 12:
        return int(value)
    if isinstance(value, float) and float(value).is_integer() and 1 <= int(value) <= 12:
        return int(value)
    text = normalize_text_key(value)
    if not text:
        return np.nan
    if text.isdigit():
        month = int(text)
        return month if 1 <= month <= 12 else np.nan
    return MONTH_NAME_TO_NUM.get(text, np.nan)


def classify_robo_subtipo(delito_key: Any) -> str:
    text = normalize_text_key(delito_key)
    if not text or "ROBO" not in text:
        return "OTRO"
    if "ACCESORIO" in text and ("AUTO" in text or "VEHICULO" in text):
        return "ROBO_DE_ACCESORIOS_AUTO"
    if "INTERIOR" in text and ("VEHICULO" in text or "AUTO" in text):
        return "ROBO_DEL_INTERIOR_DE_VEHICULO"
    if "OBJETOS DEL INTERIOR" in text and ("VEHICULO" in text or "AUTO" in text):
        return "ROBO_DEL_INTERIOR_DE_VEHICULO"
    if "TRANSEUNTE" in text or "PASAJERO" in text:
        return "ROBO_A_TRANSEUNTE"
    if "NEGOCIO" in text:
        return "ROBO_A_NEGOCIO"
    if "CASA HABITACION" in text:
        return "ROBO_A_CASA_HABITACION"
    if "VEHICULO" in text:
        return "ROBO_DE_VEHICULO"
    return "OTRO"


def load_mmip_dictionary() -> dict[str, str]:
    candidates = sorted(DOCUMENTACION_DIR.glob("*diccionario*mmip*.xlsx"))
    if not candidates:
        return {}
    path = candidates[0]
    try:
        sheets = pd.read_excel(path, sheet_name=None)
    except Exception:
        return {}
    descriptions: dict[str, str] = {}
    for _, frame in sheets.items():
        if frame.empty:
            continue
        frame = normalize_columns(frame.dropna(how="all"))
        if frame.empty:
            continue
        variable_col = next(
            (c for c in frame.columns if c in {"variable", "indicador", "nombre", "campo"}),
            frame.columns[0],
        )
        description_col = next(
            (
                c
                for c in frame.columns
                if c in {"descripcion", "descripcion_indicador", "definicion", "detalle"}
            ),
            frame.columns[1] if len(frame.columns) > 1 else frame.columns[0],
        )
        for _, row in frame[[variable_col, description_col]].dropna(how="all").iterrows():
            var = to_snake_case(row.get(variable_col, ""))
            desc = str(row.get(description_col, "")).strip()
            if var and desc and desc.lower() != "nan":
                descriptions[var] = desc
    return descriptions


def default_social_description(variable: str) -> str:
    defaults = {
        "mmip": "Indicador de pobreza multidimensional MMIP.",
        "rei": "Componente de ingreso o recursos economicos del MMIP.",
        "nbi": "Componente de necesidades basicas insatisfechas.",
        "ccevj": "Componente social MMIP agregado por promedio ponderado.",
        "cbdj": "Componente de bienes durables o condiciones basicas del MMIP.",
        "csj": "Componente de seguridad social del MMIP.",
        "ctelj": "Componente de telefonia o comunicacion del MMIP.",
        "cenj": "Componente de energia del MMIP.",
        "ett": "Componente de tiempo disponible del MMIP.",
        "casi": "Componente de acceso a salud del MMIP.",
        "cassi": "Componente de seguridad social o salud del MMIP.",
        "cyt": "Componente de cultura, educacion o tiempo del MMIP.",
    }
    return defaults.get(variable, f"Variable social {variable} agregada por alcaldia-anio.")


def clean_string_columns(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].map(lambda x: x.strip() if isinstance(x, str) else x)
    return df


def add_alcaldia_fields(df: pd.DataFrame, source_col: str) -> pd.DataFrame:
    df["alcaldia_key"] = df[source_col].map(canonicalize_alcaldia)
    df["alcaldia_nombre"] = df["alcaldia_key"].map(alcaldia_nombre)
    df["alcaldia_id"] = df["alcaldia_key"].map(ALCALDIA_ID)
    return df


def is_snake_case(value: str) -> bool:
    return bool(re.fullmatch(r"[a-z][a-z0-9_]*", value))
