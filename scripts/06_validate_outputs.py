from __future__ import annotations

import csv
import sys
from pathlib import Path

import pandas as pd

from etl_common import (
    ANALYTICS_DIR,
    CANONICAL_ALCALDIAS,
    CLEAN_DIR,
    DIMENSIONAL_DIR,
    INFRA_FEATURES,
    INFRA_SNAPSHOT_TIME_ID,
    INFRA_SNAPSHOT_YEAR,
    METADATA_PATH,
    REPORTS_DIR,
    ROOT,
    SQL_DIR,
    is_snake_case,
    load_metadata,
    read_output_csv,
)


EXPECTED_CSV = {
    "clean": [
        CLEAN_DIR / "pobreza_clean.csv",
        CLEAN_DIR / "infraestructura_clean.csv",
        CLEAN_DIR / "fgj_clean.csv",
    ],
    "analytics": [
        ANALYTICS_DIR / "pobreza_alcaldia_anio.csv",
        ANALYTICS_DIR / "infraestructura_alcaldia.csv",
        ANALYTICS_DIR / "delitos_alcaldia_mes_subtipo.csv",
        ANALYTICS_DIR / "delitos_alcaldia_anio.csv",
        ANALYTICS_DIR / "panel_alcaldia_anio.csv",
        ANALYTICS_DIR / "modeling_panel.csv",
        ANALYTICS_DIR / "feature_catalog.csv",
    ],
    "dimensional": [
        DIMENSIONAL_DIR / "dim_alcaldia.csv",
        DIMENSIONAL_DIR / "dim_tiempo.csv",
        DIMENSIONAL_DIR / "dim_colonia.csv",
        DIMENSIONAL_DIR / "dim_delito_subtipo.csv",
        DIMENSIONAL_DIR / "dim_variable_social.csv",
        DIMENSIONAL_DIR / "dim_variable_infraestructura.csv",
        DIMENSIONAL_DIR / "dim_fuente_datos.csv",
        DIMENSIONAL_DIR / "fact_delitos_alcaldia_mes_subtipo.csv",
        DIMENSIONAL_DIR / "fact_delitos_alcaldia_anio.csv",
        DIMENSIONAL_DIR / "fact_pobreza_alcaldia_anio.csv",
        DIMENSIONAL_DIR / "fact_infraestructura_alcaldia.csv",
        DIMENSIONAL_DIR / "fact_infraestructura_colonia.csv",
        DIMENSIONAL_DIR / "fact_panel_analitico_alcaldia_anio.csv",
    ],
}

EXPECTED_SQL = [
    SQL_DIR / "00_create_database_notes.md",
    SQL_DIR / "01_create_schemas.sql",
    SQL_DIR / "02_create_clean_tables.sql",
    SQL_DIR / "03_create_analytics_tables.sql",
    SQL_DIR / "04_create_dimensional_schema.sql",
    SQL_DIR / "05_create_indexes_and_constraints.sql",
    SQL_DIR / "06_copy_clean_csv.sql",
    SQL_DIR / "07_copy_analytics_csv.sql",
    SQL_DIR / "08_copy_dimensional_csv.sql",
    SQL_DIR / "09_validation_queries.sql",
    SQL_DIR / "10_drop_all.sql",
]

CREATE_SQL_BY_GROUP = {
    "clean": SQL_DIR / "02_create_clean_tables.sql",
    "analytics": SQL_DIR / "03_create_analytics_tables.sql",
    "dimensional": SQL_DIR / "04_create_dimensional_schema.sql",
}
COPY_SQL_BY_GROUP = {
    "clean": SQL_DIR / "06_copy_clean_csv.sql",
    "analytics": SQL_DIR / "07_copy_analytics_csv.sql",
    "dimensional": SQL_DIR / "08_copy_dimensional_csv.sql",
}


class Validator:
    def __init__(self) -> None:
        self.passed: list[str] = []
        self.warnings: list[str] = []
        self.critical: list[str] = []

    def check(self, condition: bool, message: str, critical: bool = True) -> None:
        if condition:
            self.passed.append(message)
        elif critical:
            self.critical.append(message)
        else:
            self.warnings.append(message)


def csv_header(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return next(csv.reader(handle))


def csv_is_utf8(path: Path) -> bool:
    try:
        with path.open("r", encoding="utf-8") as handle:
            for _ in iter(lambda: handle.read(1024 * 1024), ""):
                pass
        return True
    except UnicodeDecodeError:
        return False


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def has_duplicate(df: pd.DataFrame, columns: list[str]) -> bool:
    return df.duplicated(subset=columns).any()


def assert_fk(v: Validator, fact: pd.DataFrame, dim: pd.DataFrame, fact_col: str, dim_col: str, name: str):
    missing = set(fact[fact_col].dropna().astype(int)) - set(dim[dim_col].dropna().astype(int))
    v.check(not missing, f"Llaves {name} existen en dimension")


def validate_files(v: Validator) -> None:
    all_csv = [path for paths in EXPECTED_CSV.values() for path in paths]
    for path in all_csv:
        v.check(path.exists(), f"Existe CSV {rel(path)}")
        if path.exists():
            v.check(csv_is_utf8(path), f"CSV UTF-8 {rel(path)}")
            header = csv_header(path)
            bad = [col for col in header if not is_snake_case(col)]
            v.check(not bad, f"Columnas snake_case en {rel(path)}")
    for path in EXPECTED_SQL:
        v.check(path.exists(), f"Existe SQL {rel(path)}")


def validate_data(v: Validator) -> dict[str, pd.DataFrame]:
    frames = {
        "dim_alcaldia": read_output_csv(DIMENSIONAL_DIR / "dim_alcaldia.csv"),
        "dim_tiempo": read_output_csv(DIMENSIONAL_DIR / "dim_tiempo.csv"),
        "dim_colonia": read_output_csv(DIMENSIONAL_DIR / "dim_colonia.csv"),
        "dim_delito_subtipo": read_output_csv(DIMENSIONAL_DIR / "dim_delito_subtipo.csv"),
        "dim_fuente_datos": read_output_csv(DIMENSIONAL_DIR / "dim_fuente_datos.csv"),
        "fact_delitos_mes": read_output_csv(DIMENSIONAL_DIR / "fact_delitos_alcaldia_mes_subtipo.csv"),
        "fact_delitos_anio": read_output_csv(DIMENSIONAL_DIR / "fact_delitos_alcaldia_anio.csv"),
        "fact_pobreza": read_output_csv(DIMENSIONAL_DIR / "fact_pobreza_alcaldia_anio.csv"),
        "fact_infra_alcaldia": read_output_csv(DIMENSIONAL_DIR / "fact_infraestructura_alcaldia.csv"),
        "fact_infra_colonia": read_output_csv(DIMENSIONAL_DIR / "fact_infraestructura_colonia.csv"),
        "fact_panel": read_output_csv(DIMENSIONAL_DIR / "fact_panel_analitico_alcaldia_anio.csv"),
        "panel": read_output_csv(ANALYTICS_DIR / "panel_alcaldia_anio.csv"),
        "modeling": read_output_csv(ANALYTICS_DIR / "modeling_panel.csv"),
        "feature_catalog": read_output_csv(ANALYTICS_DIR / "feature_catalog.csv"),
    }

    dim_alcaldia = frames["dim_alcaldia"]
    v.check(len(dim_alcaldia) == 16, "dim_alcaldia tiene 16 alcaldias")
    v.check(
        set(dim_alcaldia["alcaldia_key"]) == set(CANONICAL_ALCALDIAS),
        "dim_alcaldia coincide con catalogo canonico",
    )
    v.check(dim_alcaldia["alcaldia_id"].notna().all(), "alcaldia_id sin nulos")

    for name, frame in frames.items():
        if name.startswith("fact_") and "alcaldia_id" in frame.columns:
            v.check(frame["alcaldia_id"].notna().all(), f"{name}.alcaldia_id sin nulos")
        if name.startswith("fact_") and "tiempo_id" in frame.columns:
            v.check(frame["tiempo_id"].notna().all(), f"{name}.tiempo_id sin nulos")

    for name in ["fact_infra_alcaldia", "fact_infra_colonia"]:
        frame = frames[name]
        v.check(
            frame["snapshot_tiempo_id"].eq(INFRA_SNAPSHOT_TIME_ID).all(),
            f"{name}.snapshot_tiempo_id = 202200",
        )
        v.check(
            frame["infraestructura_actualizacion_anio"].eq(INFRA_SNAPSHOT_YEAR).all(),
            f"{name}.infraestructura_actualizacion_anio = 2022",
        )
        v.check(
            frame["infraestructura_es_snapshot"].astype(str).str.lower().isin(["true", "1"]).all(),
            f"{name}.infraestructura_es_snapshot = true",
        )

    assert_fk(v, frames["dim_colonia"], frames["dim_alcaldia"], "alcaldia_id", "alcaldia_id", "dim_colonia.alcaldia_id")
    for name in ["fact_delitos_mes", "fact_delitos_anio", "fact_pobreza", "fact_infra_alcaldia", "fact_infra_colonia", "fact_panel"]:
        assert_fk(v, frames[name], frames["dim_alcaldia"], "alcaldia_id", "alcaldia_id", f"{name}.alcaldia_id")
    for name in ["fact_delitos_mes", "fact_delitos_anio", "fact_pobreza", "fact_panel"]:
        assert_fk(v, frames[name], frames["dim_tiempo"], "tiempo_id", "tiempo_id", f"{name}.tiempo_id")
    for name in ["fact_infra_alcaldia", "fact_infra_colonia"]:
        assert_fk(v, frames[name], frames["dim_tiempo"], "snapshot_tiempo_id", "tiempo_id", f"{name}.snapshot_tiempo_id")
    assert_fk(v, frames["fact_delitos_mes"], frames["dim_delito_subtipo"], "delito_subtipo_id", "delito_subtipo_id", "delito_subtipo_id")
    assert_fk(v, frames["fact_infra_colonia"], frames["dim_colonia"], "colonia_id", "colonia_id", "colonia_id")

    natural_keys = {
        "dim_alcaldia": ["alcaldia_key"],
        "dim_tiempo": ["tiempo_id"],
        "dim_colonia": ["alcaldia_id", "colonia_key", "cve_col"],
        "dim_delito_subtipo": ["subtipo_robo_patrimonial"],
        "dim_fuente_datos": ["fuente_nombre"],
    }
    for name, cols in natural_keys.items():
        v.check(not has_duplicate(frames[name], cols), f"Sin duplicados en clave natural {name}")

    fact_grains = {
        "fact_delitos_mes": ["alcaldia_id", "tiempo_id", "delito_subtipo_id"],
        "fact_delitos_anio": ["alcaldia_id", "tiempo_id"],
        "fact_pobreza": ["alcaldia_id", "tiempo_id"],
        "fact_infra_alcaldia": ["alcaldia_id", "snapshot_tiempo_id"],
        "fact_infra_colonia": ["colonia_id", "snapshot_tiempo_id"],
        "fact_panel": ["alcaldia_id", "tiempo_id"],
    }
    for name, cols in fact_grains.items():
        v.check(not has_duplicate(frames[name], cols), f"Sin duplicados en grano {name}")

    panel_counts = frames["fact_panel"].groupby("anio")["alcaldia_id"].nunique()
    v.check(panel_counts.eq(16).all(), "fact_panel tiene 16 alcaldias por cada anio comun")

    panel = frames["panel"]
    v.check("target_robos_patrimoniales_total" in panel.columns, "Panel tiene target")
    if "target_robos_patrimoniales_total" in panel.columns:
        target = pd.to_numeric(panel["target_robos_patrimoniales_total"], errors="coerce")
        v.check(target.notna().all(), "Target es numerico")
    v.check(not panel.isna().all().any(), "Panel final sin columnas completamente vacias")

    modeling = frames["modeling"]
    required_modeling = {
        "alcaldia_id",
        "tiempo_id",
        "alcaldia_key",
        "alcaldia_nombre",
        "anio",
        "target_robos_patrimoniales_total",
    }
    v.check(required_modeling.issubset(modeling.columns), "modeling_panel contiene ids y target")

    catalog = frames["feature_catalog"]
    required_roles = {"id", "target", "feature", "control", "metadata"}
    v.check(
        required_roles.intersection(set(catalog["feature_role"])) >= {"id", "target", "feature", "control"},
        "feature_catalog clasifica ids, target, features y controles",
    )
    infra_catalog = catalog[catalog["feature_name"].isin(INFRA_FEATURES)]
    v.check(
        not infra_catalog.empty
        and infra_catalog["temporal_behavior"].eq("static_snapshot_2022").all(),
        "feature_catalog marca infraestructura como static_snapshot_2022",
    )

    for frame_name in ["panel", "modeling", "fact_panel"]:
        frame = frames[frame_name]
        if "alcaldia_key" in frame.columns:
            outside = set(frame["alcaldia_key"].dropna()) - set(CANONICAL_ALCALDIAS)
            v.check(not outside, f"{frame_name} sin alcaldias fuera de catalogo")

    numeric_checks = [
        (frames["modeling"], "target_robos_patrimoniales_total"),
        (frames["modeling"], "mmip_wmean"),
        (frames["modeling"], "mercados_total"),
        (frames["fact_delitos_anio"], "total_delitos_fgj"),
    ]
    for frame, col in numeric_checks:
        if col in frame.columns:
            values = pd.to_numeric(frame[col], errors="coerce")
            v.check(values.notna().all(), f"Columna numerica valida: {col}")

    return frames


def validate_fgj_coordinates(v: Validator) -> None:
    path = CLEAN_DIR / "fgj_clean.csv"
    if not path.exists():
        return
    years_outside = 0
    coord_outside = 0
    outside_alcaldias: set[str] = set()
    for chunk in pd.read_csv(
        path,
        encoding="utf-8",
        na_values=[r"\N"],
        usecols=["anio_hecho_clean", "latitud", "longitud", "alcaldia_key"],
        chunksize=500_000,
    ):
        years = pd.to_numeric(chunk["anio_hecho_clean"], errors="coerce")
        years_outside += int((years.notna() & ~years.between(2000, 2030)).sum())
        lat = pd.to_numeric(chunk["latitud"], errors="coerce")
        lon = pd.to_numeric(chunk["longitud"], errors="coerce")
        coord_valid = lat.notna() & lon.notna()
        coord_outside += int((coord_valid & ~(lat.between(19.0, 19.7) & lon.between(-99.4, -98.8))).sum())
        outside_alcaldias.update(set(chunk["alcaldia_key"].dropna()) - set(CANONICAL_ALCALDIAS))
    v.check(not outside_alcaldias, "fgj_clean sin alcaldias fuera de catalogo")
    v.check(years_outside == 0, "FGJ sin anios fuera de rango razonable")
    if coord_outside == 0:
        v.passed.append("Coordenadas FGJ dentro de rango aproximado CDMX")
    else:
        v.warnings.append(
            f"FGJ tiene {coord_outside} registros con coordenadas fuera del rango aproximado CDMX; se reportan, no se eliminan."
        )


def validate_sql(v: Validator) -> None:
    for group, paths in EXPECTED_CSV.items():
        create_text = CREATE_SQL_BY_GROUP[group].read_text(encoding="utf-8").lower()
        copy_text = COPY_SQL_BY_GROUP[group].read_text(encoding="utf-8")
        for path in paths:
            header = csv_header(path)
            missing_cols = [
                col for col in header if f"    {col} " not in create_text and f"    {col}\n" not in create_text
            ]
            v.check(not missing_cols, f"CREATE TABLE incluye columnas de {rel(path)}")
            v.check(rel(path) in copy_text, f"COPY referencia {rel(path)}")

    readme = ROOT / "README.md"
    dim_readme = DIMENSIONAL_DIR / "README.md"
    v.check(readme.exists(), "README.md existe")
    if readme.exists():
        text = readme.read_text(encoding="utf-8")
        v.check("Carga futura en PostgreSQL" in text, "README incluye carga futura en PostgreSQL")
        v.check("\\i sql/01_create_schemas.sql" in text, "README incluye comandos psql")
    v.check(dim_readme.exists(), "dimensional_schema/README.md existe")
    if dim_readme.exists():
        text = dim_readme.read_text(encoding="utf-8")
        v.check("erDiagram" in text, "dimensional_schema/README.md incluye diagrama ER Mermaid")


def write_report(v: Validator, frames: dict[str, pd.DataFrame]) -> None:
    metadata = load_metadata()
    source_results = metadata.get("source_results", {})
    analytics_panel = metadata.get("analytics_panel", {})
    dimensional_outputs = metadata.get("dimensional_outputs", {})

    lines = [
        "# Informe ETL",
        "",
        "## Archivos detectados",
    ]
    for dataset, result in source_results.items():
        lines.append(f"- {dataset}: {result.get('source', 'no disponible')}")

    lines.extend(["", "## Filas"])
    for dataset, result in source_results.items():
        lines.append(
            f"- {dataset}: originales={result.get('original_rows')}, finales={result.get('clean_rows')}"
        )

    lines.extend(["", "## Columnas principales"])
    for dataset, result in source_results.items():
        cols = result.get("columns_analytics") or result.get("columns_analytics_annual") or []
        lines.append(f"- {dataset}: {', '.join(cols[:18])}")

    lines.extend(["", "## Años y alcaldias"])
    lines.append(f"- Panel: {analytics_panel.get('panel_years', [])}")
    for dataset, result in source_results.items():
        lines.append(
            f"- {dataset}: anios={result.get('years', [])}, alcaldias={len(result.get('alcaldias', []))}"
        )

    lines.extend(["", "## Registros eliminados"])
    for dataset, result in source_results.items():
        lines.append(f"- {dataset}: {result.get('dropped_rows', {})}")

    nulls = analytics_panel.get("nulls", {})
    lines.extend(["", "## Nulos relevantes"])
    lines.append("- Sin nulos relevantes en modeling_panel." if not nulls else f"- {nulls}")

    lines.extend(["", "## Variables agregadas"])
    lines.append("- Sociales: promedios ponderados `_wmean` por alcaldia-anio.")
    lines.append("- Infraestructura: sumas para conteos/volumen y promedios para porcentajes/rankings.")
    lines.append("- FGJ: total anual, total mensual por subtipo y target de robos patrimoniales.")

    lines.extend(["", "## Salidas dimensionales"])
    dims = dimensional_outputs.get("dimensions", {})
    facts = dimensional_outputs.get("facts", {})
    lines.append(f"- Dimensiones: {dims}")
    lines.append(f"- Hechos: {facts}")

    lines.extend(["", "## Validaciones aprobadas"])
    for item in v.passed:
        lines.append(f"- {item}")

    lines.extend(["", "## Advertencias"])
    if v.warnings:
        for item in v.warnings:
            lines.append(f"- {item}")
    else:
        lines.append("- Sin advertencias no criticas.")

    lines.extend(
        [
            "",
            "## Limitaciones",
            "- Infraestructura es snapshot 2022 y no debe interpretarse como medicion anual.",
            "- El panel principal depende de los anios comunes entre pobreza y FGJ.",
            "- El analisis no demuestra causalidad; permite explorar relaciones, patrones y asociaciones.",
            "- El modelado predictivo debe interpretarse con cautela por el tamano reducido del panel.",
        ]
    )
    (REPORTS_DIR / "etl_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    validator = Validator()
    validate_files(validator)
    frames: dict[str, pd.DataFrame] = {}
    if not validator.critical:
        frames = validate_data(validator)
        validate_fgj_coordinates(validator)
        validate_sql(validator)
    write_report(validator, frames)

    if validator.critical:
        print("Validaciones criticas fallaron:")
        for item in validator.critical:
            print(f"- {item}")
        sys.exit(1)
    print("Validaciones completadas.")


if __name__ == "__main__":
    main()
