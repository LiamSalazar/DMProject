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
    FGJ_YEAR_MAX,
    FGJ_YEAR_MIN,
    INFRA_FEATURES,
    INFRA_SNAPSHOT_TIME_ID,
    INFRA_SNAPSHOT_YEAR,
    INFRA_TEMPORALITY,
    REPORTS_DIR,
    ROBBERY_ONLY_DIR,
    ROBO_PATRIMONIAL_SUBTIPOS,
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
        ANALYTICS_DIR / "delitos_alcaldia_anio.csv",
        ROBBERY_ONLY_DIR / "fgj_robos_patrimoniales_clean.csv",
        ROBBERY_ONLY_DIR / "robos_patrimoniales_alcaldia_mes_subtipo.csv",
        ROBBERY_ONLY_DIR / "robos_patrimoniales_alcaldia_anio.csv",
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
        DIMENSIONAL_DIR / "fact_delitos_generales_alcaldia_anio.csv",
        DIMENSIONAL_DIR / "fact_robos_patrimoniales_alcaldia_mes_subtipo.csv",
        DIMENSIONAL_DIR / "fact_robos_patrimoniales_alcaldia_anio.csv",
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


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


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


def has_duplicate(df: pd.DataFrame, columns: list[str]) -> bool:
    return df.duplicated(subset=columns).any()


def assert_fk(v: Validator, fact: pd.DataFrame, dim: pd.DataFrame, fact_col: str, dim_col: str, name: str) -> None:
    missing = set(fact[fact_col].dropna().astype(int)) - set(dim[dim_col].dropna().astype(int))
    v.check(not missing, f"Llaves {name} existen en dimension")


def validate_files(v: Validator) -> None:
    for paths in EXPECTED_CSV.values():
        for path in paths:
            v.check(path.exists(), f"Existe CSV {rel(path)}")
            if path.exists():
                v.check(csv_is_utf8(path), f"CSV UTF-8 {rel(path)}")
                bad = [col for col in csv_header(path) if not is_snake_case(col)]
                v.check(not bad, f"Columnas snake_case en {rel(path)}")
    for path in EXPECTED_SQL:
        v.check(path.exists(), f"Existe SQL {rel(path)}")


def validate_chunked_fgj(v: Validator) -> dict:
    clean_path = CLEAN_DIR / "fgj_clean.csv"
    robbery_path = ROBBERY_ONLY_DIR / "fgj_robos_patrimoniales_clean.csv"
    clean_years_outside = 0
    clean_alcaldias_outside: set[str] = set()
    coord_outside = 0
    for chunk in pd.read_csv(
        clean_path,
        encoding="utf-8",
        na_values=[r"\N"],
        usecols=["anio_hecho_clean", "alcaldia_key", "latitud", "longitud"],
        chunksize=500_000,
    ):
        years = pd.to_numeric(chunk["anio_hecho_clean"], errors="coerce")
        clean_years_outside += int((years.notna() & ~years.between(FGJ_YEAR_MIN, FGJ_YEAR_MAX)).sum())
        clean_alcaldias_outside.update(set(chunk["alcaldia_key"].dropna()) - set(CANONICAL_ALCALDIAS))
        lat = pd.to_numeric(chunk["latitud"], errors="coerce")
        lon = pd.to_numeric(chunk["longitud"], errors="coerce")
        coord_valid = lat.notna() & lon.notna()
        coord_outside += int((coord_valid & ~(lat.between(19.0, 19.7) & lon.between(-99.4, -98.8))).sum())

    robbery_bad_is = 0
    robbery_otro = 0
    robbery_years_outside = 0
    for chunk in pd.read_csv(
        robbery_path,
        encoding="utf-8",
        na_values=[r"\N"],
        usecols=["anio_hecho_clean", "is_robo_patrimonial", "subtipo_robo_patrimonial"],
        chunksize=500_000,
    ):
        years = pd.to_numeric(chunk["anio_hecho_clean"], errors="coerce")
        robbery_years_outside += int((years.notna() & ~years.between(FGJ_YEAR_MIN, FGJ_YEAR_MAX)).sum())
        robbery_bad_is += int((pd.to_numeric(chunk["is_robo_patrimonial"], errors="coerce") != 1).sum())
        robbery_otro += int(chunk["subtipo_robo_patrimonial"].eq("OTRO").sum())

    v.check(clean_years_outside == 0, "FGJ limpio general solo tiene años 2016-2025")
    v.check(not clean_alcaldias_outside, "FGJ limpio general sin alcaldias fuera de catalogo")
    v.check(robbery_years_outside == 0, "FGJ robos patrimoniales solo tiene años 2016-2025")
    v.check(robbery_bad_is == 0, "fgj_robos_patrimoniales_clean solo tiene is_robo_patrimonial = 1")
    v.check(robbery_otro == 0, "fgj_robos_patrimoniales_clean no contiene OTRO")
    if coord_outside:
        v.warnings.append(
            f"FGJ tiene {coord_outside} registros con coordenadas fuera del rango aproximado CDMX; se reportan, no se eliminan."
        )
    else:
        v.passed.append("Coordenadas FGJ dentro de rango aproximado CDMX")
    return {"coord_outside": coord_outside}


def validate_data(v: Validator) -> dict[str, pd.DataFrame]:
    frames = {
        "dim_alcaldia": read_output_csv(DIMENSIONAL_DIR / "dim_alcaldia.csv"),
        "dim_tiempo": read_output_csv(DIMENSIONAL_DIR / "dim_tiempo.csv"),
        "dim_colonia": read_output_csv(DIMENSIONAL_DIR / "dim_colonia.csv"),
        "dim_delito_subtipo": read_output_csv(DIMENSIONAL_DIR / "dim_delito_subtipo.csv"),
        "dim_fuente_datos": read_output_csv(DIMENSIONAL_DIR / "dim_fuente_datos.csv"),
        "dim_variable_social": read_output_csv(DIMENSIONAL_DIR / "dim_variable_social.csv"),
        "dim_variable_infraestructura": read_output_csv(DIMENSIONAL_DIR / "dim_variable_infraestructura.csv"),
        "fact_delitos_generales": read_output_csv(DIMENSIONAL_DIR / "fact_delitos_generales_alcaldia_anio.csv"),
        "fact_robos_mes": read_output_csv(DIMENSIONAL_DIR / "fact_robos_patrimoniales_alcaldia_mes_subtipo.csv"),
        "fact_robos_anio": read_output_csv(DIMENSIONAL_DIR / "fact_robos_patrimoniales_alcaldia_anio.csv"),
        "fact_pobreza": read_output_csv(DIMENSIONAL_DIR / "fact_pobreza_alcaldia_anio.csv"),
        "fact_infra_alcaldia": read_output_csv(DIMENSIONAL_DIR / "fact_infraestructura_alcaldia.csv"),
        "fact_infra_colonia": read_output_csv(DIMENSIONAL_DIR / "fact_infraestructura_colonia.csv"),
        "fact_panel": read_output_csv(DIMENSIONAL_DIR / "fact_panel_analitico_alcaldia_anio.csv"),
        "panel": read_output_csv(ANALYTICS_DIR / "panel_alcaldia_anio.csv"),
        "modeling": read_output_csv(ANALYTICS_DIR / "modeling_panel.csv"),
        "feature_catalog": read_output_csv(ANALYTICS_DIR / "feature_catalog.csv"),
        "robos_mes": read_output_csv(ROBBERY_ONLY_DIR / "robos_patrimoniales_alcaldia_mes_subtipo.csv"),
        "robos_anio": read_output_csv(ROBBERY_ONLY_DIR / "robos_patrimoniales_alcaldia_anio.csv"),
        "delitos_generales": read_output_csv(ANALYTICS_DIR / "delitos_alcaldia_anio.csv"),
    }

    dim_alcaldia = frames["dim_alcaldia"]
    v.check(len(dim_alcaldia) == 16, "dim_alcaldia tiene 16 alcaldias")
    v.check(set(dim_alcaldia["alcaldia_key"]) == set(CANONICAL_ALCALDIAS), "dim_alcaldia coincide con catalogo canonico")
    v.check(dim_alcaldia["alcaldia_id"].notna().all(), "alcaldia_id sin nulos")

    dim_subtipo = frames["dim_delito_subtipo"]
    v.check(
        set(dim_subtipo["subtipo_robo_patrimonial"]) == set(ROBO_PATRIMONIAL_SUBTIPOS)
        and len(dim_subtipo) == 6,
        "dim_delito_subtipo contiene solo los 6 subtipos patrimoniales",
    )
    v.check(not dim_subtipo["subtipo_robo_patrimonial"].eq("OTRO").any(), "dim_delito_subtipo no contiene OTRO")

    v.check(not frames["robos_mes"]["subtipo_robo_patrimonial"].eq("OTRO").any(), "robos_patrimoniales mensual no contiene OTRO")
    v.check(not frames["robos_anio"].columns.str.contains("otro", case=False).any(), "robos_patrimoniales anual no contiene columna OTRO")

    subtype_sum = frames["fact_robos_anio"][
        [
            "robo_a_transeunte",
            "robo_a_negocio",
            "robo_a_casa_habitacion",
            "robo_de_vehiculo",
            "robo_de_accesorios_auto",
            "robo_del_interior_de_vehiculo",
        ]
    ].sum(axis=1)
    target = pd.to_numeric(frames["fact_robos_anio"]["target_robos_patrimoniales_total"], errors="coerce")
    v.check(target.notna().all(), "target_robos_patrimoniales_total es numerico")
    v.check(target.eq(subtype_sum).all(), "target_robos_patrimoniales_total no se calcula con OTRO")

    for name in ["fact_infra_alcaldia", "fact_infra_colonia"]:
        frame = frames[name]
        v.check(frame["snapshot_tiempo_id"].eq(INFRA_SNAPSHOT_TIME_ID).all(), f"{name}.snapshot_tiempo_id = 202200")
        v.check(frame["infraestructura_actualizacion_anio"].eq(INFRA_SNAPSHOT_YEAR).all(), f"{name}.infraestructura_actualizacion_anio = 2022")
        v.check(frame["infraestructura_es_snapshot"].astype(str).str.lower().isin(["true", "1"]).all(), f"{name}.infraestructura_es_snapshot = true")
        v.check(frame["infraestructura_temporalidad"].eq(INFRA_TEMPORALITY).all(), f"{name}.infraestructura_temporalidad = static_snapshot_2022")

    natural_keys = {
        "dim_alcaldia": ["alcaldia_key"],
        "dim_tiempo": ["tiempo_id"],
        "dim_colonia": ["alcaldia_id", "colonia_key", "cve_col"],
        "dim_delito_subtipo": ["subtipo_robo_patrimonial"],
        "dim_variable_social": ["variable_nombre"],
        "dim_variable_infraestructura": ["variable_nombre"],
        "dim_fuente_datos": ["fuente_nombre"],
    }
    for name, cols in natural_keys.items():
        v.check(not has_duplicate(frames[name], cols), f"Sin duplicados en clave natural {name}")

    fact_grains = {
        "fact_delitos_generales": ["alcaldia_id", "tiempo_id"],
        "fact_robos_mes": ["alcaldia_id", "tiempo_id", "delito_subtipo_id"],
        "fact_robos_anio": ["alcaldia_id", "tiempo_id"],
        "fact_pobreza": ["alcaldia_id", "tiempo_id"],
        "fact_infra_alcaldia": ["alcaldia_id", "snapshot_tiempo_id"],
        "fact_infra_colonia": ["colonia_id", "snapshot_tiempo_id"],
        "fact_panel": ["alcaldia_id", "tiempo_id"],
    }
    for name, cols in fact_grains.items():
        v.check(not has_duplicate(frames[name], cols), f"Sin duplicados en grano {name}")

    for name in ["fact_delitos_generales", "fact_robos_mes", "fact_robos_anio", "fact_pobreza", "fact_infra_alcaldia", "fact_infra_colonia", "fact_panel"]:
        assert_fk(v, frames[name], frames["dim_alcaldia"], "alcaldia_id", "alcaldia_id", f"{name}.alcaldia_id")
    for name in ["fact_delitos_generales", "fact_robos_mes", "fact_robos_anio", "fact_pobreza", "fact_panel"]:
        assert_fk(v, frames[name], frames["dim_tiempo"], "tiempo_id", "tiempo_id", f"{name}.tiempo_id")
    for name in ["fact_infra_alcaldia", "fact_infra_colonia"]:
        assert_fk(v, frames[name], frames["dim_tiempo"], "snapshot_tiempo_id", "tiempo_id", f"{name}.snapshot_tiempo_id")
    assert_fk(v, frames["fact_robos_mes"], frames["dim_delito_subtipo"], "delito_subtipo_id", "delito_subtipo_id", "delito_subtipo_id")
    assert_fk(v, frames["fact_infra_colonia"], frames["dim_colonia"], "colonia_id", "colonia_id", "colonia_id")

    panel_counts = frames["fact_panel"].groupby("anio")["alcaldia_id"].nunique()
    v.check(panel_counts.eq(16).all(), "fact_panel tiene 16 alcaldias por cada anio comun")
    panel_years = sorted(frames["fact_panel"]["anio"].dropna().astype(int).unique().tolist())
    if panel_years == [2016, 2018, 2020]:
        v.check(len(frames["fact_panel"]) == 48, "Panel tiene 48 filas para 2016, 2018 y 2020")

    for frame_name in ["panel", "modeling", "fact_panel"]:
        frame = frames[frame_name]
        if "alcaldia_key" in frame.columns:
            outside = set(frame["alcaldia_key"].dropna()) - set(CANONICAL_ALCALDIAS)
            v.check(not outside, f"{frame_name} sin alcaldias fuera de catalogo")

    catalog = frames["feature_catalog"]
    required_roles = {"id", "target", "feature", "control", "derived_analysis"}
    v.check(required_roles.issubset(set(catalog["feature_role"])), "feature_catalog clasifica roles esperados")
    infra_catalog = catalog[catalog["feature_name"].isin(INFRA_FEATURES)]
    v.check(not infra_catalog.empty and infra_catalog["temporal_behavior"].eq(INFRA_TEMPORALITY).all(), "feature_catalog marca infraestructura como static_snapshot_2022")
    derived_catalog = catalog[catalog["feature_role"].eq("derived_analysis")]
    v.check(
        not derived_catalog.empty and derived_catalog["recommended_for_modeling"].astype(str).str.lower().isin(["false", "0"]).all(),
        "Variables derivadas del target no recomendadas para modelado",
    )

    null_counts = frames["modeling"].isna().sum()
    high_null = null_counts[null_counts > 0]
    if not high_null.empty:
        v.warnings.append(f"Nulos no criticos en modeling_panel: {high_null.to_dict()}")
    v.check(not frames["panel"].isna().all().any(), "Panel final sin columnas completamente vacias")
    return frames


def validate_sql(v: Validator) -> None:
    for group, paths in EXPECTED_CSV.items():
        create_text = CREATE_SQL_BY_GROUP[group].read_text(encoding="utf-8").lower()
        copy_text = COPY_SQL_BY_GROUP[group].read_text(encoding="utf-8")
        for path in paths:
            header = csv_header(path)
            missing_cols = [col for col in header if f"    {col} " not in create_text]
            v.check(not missing_cols, f"CREATE TABLE incluye columnas de {rel(path)}")
            v.check(rel(path) in copy_text, f"COPY referencia {rel(path)}")

    readme = ROOT / "README.md"
    dim_readme = DIMENSIONAL_DIR / "README.md"
    v.check(readme.exists(), "README.md existe")
    if readme.exists():
        text = readme.read_text(encoding="utf-8")
        v.check("Carga futura en PostgreSQL" in text, "README incluye carga futura en PostgreSQL")
        v.check("\\i sql/01_create_schemas.sql" in text, "README incluye comandos psql")
        v.check("FGJ general vs robos patrimoniales" in text, "README explica diferencia entre FGJ general y robos patrimoniales")
        v.check("snapshot estructural 2022" in text, "README explica infraestructura snapshot 2022")
    v.check(dim_readme.exists(), "dimensional_schema/README.md existe")
    if dim_readme.exists():
        v.check("erDiagram" in dim_readme.read_text(encoding="utf-8"), "dimensional_schema/README.md incluye diagrama ER Mermaid")


def write_report(v: Validator, frames: dict[str, pd.DataFrame]) -> None:
    metadata = load_metadata()
    source_results = metadata.get("source_results", {})
    analytics_panel = metadata.get("analytics_panel", {})
    dimensional_outputs = metadata.get("dimensional_outputs", {})
    fgj = source_results.get("fgj", {})

    lines = ["# Informe ETL", "", "## Archivos detectados"]
    for dataset, result in source_results.items():
        lines.append(f"- {dataset}: {result.get('source', 'no disponible')}")

    lines.extend(["", "## Filas"])
    for dataset, result in source_results.items():
        extra = f", robos={result.get('robbery_rows')}" if dataset == "fgj" else ""
        lines.append(f"- {dataset}: originales={result.get('original_rows')}, finales={result.get('clean_rows')}{extra}")

    lines.extend(["", "## Temporalidad FGJ"])
    lines.append(f"- Rango antes de limpieza: {fgj.get('raw_year_range', [])}")
    lines.append(f"- Rango despues de limpieza: {fgj.get('clean_year_range', [])}")
    lines.append(f"- Confirmacion: FGJ filtrado a {FGJ_YEAR_MIN}-{FGJ_YEAR_MAX}.")

    lines.extend(["", "## Panel principal"])
    lines.append(f"- Años: {analytics_panel.get('panel_years', [])}")
    lines.append(f"- Filas: {analytics_panel.get('panel_rows')}")
    lines.append("- Confirmacion: 16 alcaldias por año comun validado.")

    lines.extend(["", "## Infraestructura"])
    lines.append("- Confirmacion: snapshot 2022, no medicion anual.")
    lines.append(f"- Temporalidad: {INFRA_TEMPORALITY}")

    lines.extend(["", "## Robos patrimoniales"])
    lines.append("- Confirmacion: hechos y archivos robbery_only no contienen OTRO.")
    lines.append("- Target calculado solo desde los seis subtipos patrimoniales.")

    lines.extend(["", "## Registros eliminados"])
    for dataset, result in source_results.items():
        lines.append(f"- {dataset}: {result.get('dropped_rows', {})}")

    nulls = analytics_panel.get("nulls", {})
    lines.extend(["", "## Nulos relevantes"])
    lines.append("- Sin nulos relevantes en modeling_panel." if not nulls else f"- {nulls}")

    lines.extend(["", "## Variables agregadas"])
    lines.append("- Sociales: promedios ponderados `_wmean` por alcaldia-anio.")
    lines.append("- Infraestructura: sumas para conteos/volumen y promedios para porcentajes/rankings.")
    lines.append("- FGJ general: total_delitos_fgj, total_robos_patrimoniales y share anual.")
    lines.append("- Robos: agregados mensuales por subtipo y target anual.")

    lines.extend(["", "## Salidas dimensionales"])
    lines.append(f"- Dimensiones: {dimensional_outputs.get('dimensions', {})}")
    lines.append(f"- Hechos: {dimensional_outputs.get('facts', {})}")

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
            "## Limitaciones metodologicas",
            "- Infraestructura es snapshot 2022 y no debe interpretarse como medicion anual.",
            "- El panel principal depende de los anios comunes entre pobreza y FGJ.",
            "- El analisis no demuestra causalidad; permite explorar relaciones, patrones y asociaciones.",
            "- El modelado predictivo debe interpretarse con cautela por el tamano reducido del panel.",
            "- No se inventan tasas poblacionales; no se incluye tasa por 100k al no haber denominador poblacional defendible.",
        ]
    )
    (REPORTS_DIR / "etl_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    validator = Validator()
    validate_files(validator)
    frames: dict[str, pd.DataFrame] = {}
    if not validator.critical:
        validate_chunked_fgj(validator)
        frames = validate_data(validator)
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
