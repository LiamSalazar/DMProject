from __future__ import annotations

import numpy as np
import pandas as pd

from etl_common import (
    ALCALDIA_ID,
    ALCALDIA_NAME,
    ALCALDIA_TO_MUNICIPIO_CODE,
    ANALYTICS_DIR,
    CANONICAL_ALCALDIAS,
    CLEAN_DIR,
    DIMENSIONAL_DIR,
    INFRA_FEATURES,
    INFRA_SNAPSHOT_TIME_ID,
    INFRA_SNAPSHOT_YEAR,
    INFRA_TEMPORALITY,
    INFRA_USE_RECOMMENDED,
    MONTH_NAMES,
    ROBBERY_ONLY_DIR,
    ROBO_PATRIMONIAL_SUBTIPOS,
    ROBO_SUBTIPO_COLUMNS,
    ROOT,
    SOCIAL_FEATURES,
    SOCIAL_VARIABLES,
    ensure_dirs,
    load_metadata,
    load_mmip_dictionary,
    read_output_csv,
    update_metadata,
    write_csv,
)


FUENTE_IDS = {
    "pobreza_mmip": 1,
    "infraestructura": 2,
    "fgj_general": 3,
    "fgj_robos_patrimoniales": 4,
    "panel_integrado_etl": 5,
}
DELITO_SUBTIPO_ID = {
    subtipo: idx for idx, subtipo in enumerate(ROBO_PATRIMONIAL_SUBTIPOS, start=1)
}


def _safe_read(path):
    return read_output_csv(path) if path.exists() else pd.DataFrame()


def build_dim_alcaldia() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "alcaldia_id": ALCALDIA_ID[key],
                "alcaldia_key": key,
                "alcaldia_nombre": ALCALDIA_NAME[key],
                "municipio_enigh": ALCALDIA_TO_MUNICIPIO_CODE.get(key),
                "cve_ent": 9,
                "entidad_nombre": "Ciudad De Mexico",
            }
            for key in CANONICAL_ALCALDIAS
        ]
    )


def build_dim_tiempo(*frames: pd.DataFrame) -> pd.DataFrame:
    tiempo_ids: set[int] = {INFRA_SNAPSHOT_TIME_ID}
    for frame in frames:
        if frame.empty:
            continue
        if "tiempo_id" in frame.columns:
            tiempo_ids.update(int(x) for x in pd.to_numeric(frame["tiempo_id"], errors="coerce").dropna())
        elif "anio" in frame.columns:
            tiempo_ids.update(int(x) * 100 for x in pd.to_numeric(frame["anio"], errors="coerce").dropna())
    rows = []
    for tid in sorted(tiempo_ids):
        anio = tid // 100
        mes = tid % 100
        if mes == 0:
            mes_nombre = "anual"
            trimestre = 0
            granularidad = "anual_snapshot" if tid == INFRA_SNAPSHOT_TIME_ID else "anual"
        else:
            mes_nombre = MONTH_NAMES.get(mes)
            trimestre = int(np.ceil(mes / 3))
            granularidad = "mensual"
        rows.append(
            {
                "tiempo_id": tid,
                "anio": anio,
                "mes": mes,
                "mes_nombre": mes_nombre,
                "trimestre": trimestre,
                "granularidad": granularidad,
            }
        )
    return pd.DataFrame(rows)


def build_dim_colonia(infra_clean: pd.DataFrame) -> pd.DataFrame:
    if infra_clean.empty:
        return pd.DataFrame(
            columns=["colonia_id", "alcaldia_id", "colonia_key", "colonia_nombre", "cve_col"]
        )
    dim = (
        infra_clean[["alcaldia_id", "colonia_key", "colonia_nombre", "cve_col"]]
        .dropna(subset=["alcaldia_id", "colonia_key"])
        .drop_duplicates()
        .sort_values(["alcaldia_id", "colonia_key", "cve_col"])
        .reset_index(drop=True)
    )
    dim.insert(0, "colonia_id", range(1, len(dim) + 1))
    return dim


def build_dim_delito_subtipo() -> pd.DataFrame:
    descriptions = {
        "ROBO_A_TRANSEUNTE": "Robo a transeunte o pasajero clasificado desde delito.",
        "ROBO_A_NEGOCIO": "Robo a negocio clasificado desde delito.",
        "ROBO_A_CASA_HABITACION": "Robo a casa habitacion clasificado desde delito.",
        "ROBO_DE_VEHICULO": "Robo de vehiculo clasificado desde delito.",
        "ROBO_DE_ACCESORIOS_AUTO": "Robo de accesorios de auto clasificado desde delito.",
        "ROBO_DEL_INTERIOR_DE_VEHICULO": "Robo de objetos del interior de vehiculo.",
    }
    return pd.DataFrame(
        [
            {
                "delito_subtipo_id": DELITO_SUBTIPO_ID[subtipo],
                "subtipo_robo_patrimonial": subtipo,
                "descripcion": descriptions[subtipo],
                "es_robo_patrimonial": True,
            }
            for subtipo in ROBO_PATRIMONIAL_SUBTIPOS
        ]
    )


def build_dim_variable_social() -> pd.DataFrame:
    dictionary = load_mmip_dictionary()
    rows = []
    for idx, variable in enumerate(SOCIAL_VARIABLES, start=1):
        rows.append(
            {
                "variable_social_id": idx,
                "variable_nombre": f"{variable}_wmean",
                "variable_origen": variable,
                "descripcion": dictionary.get(variable)
                or f"Variable social {variable} agregada por promedio ponderado.",
                "metodo_agregacion": "promedio ponderado por factor",
                "rango_esperado": "revisar segun diccionario MMIP",
                "recomendada_modelado": True,
            }
        )
    return pd.DataFrame(rows)


def build_dim_variable_infraestructura() -> pd.DataFrame:
    variable_specs = [
        ("ba1_noeqsa_sum", "ba1_noeqsa", "suma"),
        ("ba8_nomerc_sum", "ba8_nomerc", "suma"),
        ("ba8_noloca_sum", "ba8_noloca", "suma"),
        ("ba9_no_gua_sum", "ba9_no_gua", "suma"),
        ("ba3_noeqed_sum", "ba3_noeqed", "suma"),
        ("resid_ton_sum", "resid_ton", "suma"),
        ("alump_sum_total", "alump_sum", "suma"),
        ("alump_mean_avg", "alump_mean", "promedio"),
        ("p_porcelec_avg", "p_porcelec", "promedio"),
        ("p_aguapot_avg", "p_aguapot", "promedio"),
        ("r_val_dren_avg", "r_val_dren", "promedio"),
        ("mercados_total", "ba8_nomerc", "suma"),
        ("locales_total", "ba8_noloca", "suma"),
        ("iluminacion_total", "alump_sum", "suma"),
        ("iluminacion_promedio", "alump_mean", "promedio"),
        ("residuos_ton_total", "resid_ton", "suma"),
        ("equipamiento_salud_total", "ba1_noeqsa", "suma"),
        ("equipamiento_educativo_total", "ba3_noeqed", "suma"),
        ("agua_potable_promedio", "p_aguapot", "promedio"),
        ("electricidad_promedio", "p_porcelec", "promedio"),
        ("drenaje_promedio", "r_val_dren", "promedio"),
    ]
    return pd.DataFrame(
        [
            {
                "variable_infraestructura_id": idx,
                "variable_nombre": name,
                "variable_origen": origin,
                "descripcion": f"Indicador de infraestructura {name} desde snapshot 2022.",
                "metodo_agregacion": method,
                "actualizacion_anio": INFRA_SNAPSHOT_YEAR,
                "temporalidad": INFRA_TEMPORALITY,
                "recomendada_modelado": name in INFRA_FEATURES,
            }
            for idx, (name, origin, method) in enumerate(variable_specs, start=1)
        ]
    )


def build_dim_fuente_datos() -> pd.DataFrame:
    metadata = load_metadata()
    detected = metadata.get("detected_files", {})
    return pd.DataFrame(
        [
            {
                "fuente_datos_id": FUENTE_IDS["pobreza_mmip"],
                "fuente_nombre": "Pobreza ENIGH MMIP",
                "fuente_tipo": "csv",
                "archivo_origen": detected.get("pobreza", "datasets/enigh_16_20.csv"),
                "carpeta_origen": "datasets",
                "cobertura_temporal": "2016, 2018, 2020 si estan disponibles",
                "granularidad_original": "persona u hogar",
                "granularidad_final": "alcaldia-anio",
                "notas_uso": "Promedios ponderados por factor.",
            },
            {
                "fuente_datos_id": FUENTE_IDS["infraestructura"],
                "fuente_nombre": "Infraestructura urbana",
                "fuente_tipo": "csv",
                "archivo_origen": detected.get("infraestructura", "datasets/infraestructura.csv"),
                "carpeta_origen": "datasets",
                "cobertura_temporal": "snapshot 2022",
                "granularidad_original": "colonia",
                "granularidad_final": "colonia y alcaldia",
                "notas_uso": INFRA_USE_RECOMMENDED,
            },
            {
                "fuente_datos_id": FUENTE_IDS["fgj_general"],
                "fuente_nombre": "FGJ delitos generales",
                "fuente_tipo": "csv",
                "archivo_origen": detected.get("fgj", "datasets/carpetasFGJ_acumulado_2025_01.csv"),
                "carpeta_origen": "datasets",
                "cobertura_temporal": "2016-2025",
                "granularidad_original": "carpeta de investigacion",
                "granularidad_final": "alcaldia-anio",
                "notas_uso": "Control anual de delitos generales FGJ.",
            },
            {
                "fuente_datos_id": FUENTE_IDS["fgj_robos_patrimoniales"],
                "fuente_nombre": "FGJ robos patrimoniales",
                "fuente_tipo": "csv derivado",
                "archivo_origen": "data/processed/robbery_only/fgj_robos_patrimoniales_clean.csv",
                "carpeta_origen": "data/processed/robbery_only",
                "cobertura_temporal": "2016-2025",
                "granularidad_original": "carpeta de investigacion",
                "granularidad_final": "alcaldia-mes-subtipo y alcaldia-anio",
                "notas_uso": "Solo seis subtipos patrimoniales; no incluye OTRO.",
            },
            {
                "fuente_datos_id": FUENTE_IDS["panel_integrado_etl"],
                "fuente_nombre": "Panel integrado ETL",
                "fuente_tipo": "derivado",
                "archivo_origen": "data/processed/analytics/panel_alcaldia_anio.csv",
                "carpeta_origen": "data/processed/analytics",
                "cobertura_temporal": "anios comunes entre pobreza y FGJ",
                "granularidad_original": "alcaldia-anio",
                "granularidad_final": "alcaldia-anio",
                "notas_uso": "No afirma causalidad; usar para exploracion, BI y modelos base.",
            },
        ]
    )


def build_facts(
    dim_colonia: pd.DataFrame,
    delitos_generales: pd.DataFrame,
    robos_mes: pd.DataFrame,
    robos_anio: pd.DataFrame,
    pobreza: pd.DataFrame,
    infraestructura: pd.DataFrame,
    infra_clean: pd.DataFrame,
    panel: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    fact_delitos_generales = delitos_generales.copy()
    fact_delitos_generales["fuente_datos_id"] = FUENTE_IDS["fgj_general"]
    fact_delitos_generales = fact_delitos_generales[
        [
            "alcaldia_id",
            "tiempo_id",
            "fuente_datos_id",
            "total_delitos_fgj",
            "total_robos_patrimoniales",
            "total_no_robos_patrimoniales",
            "share_robos_patrimoniales_sobre_total_delitos",
        ]
    ]

    fact_robos_mes = robos_mes.copy()
    fact_robos_mes["delito_subtipo_id"] = fact_robos_mes["subtipo_robo_patrimonial"].map(DELITO_SUBTIPO_ID)
    fact_robos_mes["fuente_datos_id"] = FUENTE_IDS["fgj_robos_patrimoniales"]
    fact_robos_mes = fact_robos_mes[
        [
            "alcaldia_id",
            "tiempo_id",
            "delito_subtipo_id",
            "fuente_datos_id",
            "total_robos_patrimoniales",
            "registros_con_coordenadas",
            "latitud_promedio",
            "longitud_promedio",
        ]
    ]

    fact_robos_anio = robos_anio.copy()
    fact_robos_anio["fuente_datos_id"] = FUENTE_IDS["fgj_robos_patrimoniales"]
    fact_robos_anio = fact_robos_anio[
        [
            "alcaldia_id",
            "tiempo_id",
            "fuente_datos_id",
            "target_robos_patrimoniales_total",
            "robo_a_transeunte",
            "robo_a_negocio",
            "robo_a_casa_habitacion",
            "robo_de_vehiculo",
            "robo_de_accesorios_auto",
            "robo_del_interior_de_vehiculo",
            "target_robos_log1p",
        ]
    ]

    fact_pobreza = pobreza.copy()
    fact_pobreza["fuente_datos_id"] = FUENTE_IDS["pobreza_mmip"]
    fact_pobreza = fact_pobreza[
        [
            "alcaldia_id",
            "tiempo_id",
            "fuente_datos_id",
            "n_registros_sociales",
            "factor_sum",
            *SOCIAL_FEATURES,
        ]
    ]

    fact_infra_alcaldia = infraestructura.copy()
    fact_infra_alcaldia["snapshot_tiempo_id"] = INFRA_SNAPSHOT_TIME_ID
    fact_infra_alcaldia["fuente_datos_id"] = FUENTE_IDS["infraestructura"]
    expected_infra_alcaldia = [
        "alcaldia_id",
        "snapshot_tiempo_id",
        "fuente_datos_id",
        "infraestructura_actualizacion_anio",
        "infraestructura_es_snapshot",
        "infraestructura_temporalidad",
        "colonias_count",
        "ba1_noeqsa_sum",
        "ba8_nomerc_sum",
        "ba8_noloca_sum",
        "ba9_no_gua_sum",
        "ba3_noeqed_sum",
        "resid_ton_sum",
        "alump_sum_total",
        "alump_mean_avg",
        "p_porcelec_avg",
        "p_aguapot_avg",
        "r_val_dren_avg",
    ]
    for col in expected_infra_alcaldia:
        if col not in fact_infra_alcaldia.columns:
            fact_infra_alcaldia[col] = np.nan
    fact_infra_alcaldia = fact_infra_alcaldia[expected_infra_alcaldia]

    fact_infra_colonia = infra_clean.copy()
    join_cols = ["alcaldia_id", "colonia_key", "cve_col"]
    fact_infra_colonia = fact_infra_colonia.merge(
        dim_colonia[join_cols + ["colonia_id"]],
        on=join_cols,
        how="left",
    )
    fact_infra_colonia["snapshot_tiempo_id"] = INFRA_SNAPSHOT_TIME_ID
    fact_infra_colonia["fuente_datos_id"] = FUENTE_IDS["infraestructura"]
    expected_infra_colonia = [
        "colonia_id",
        "alcaldia_id",
        "snapshot_tiempo_id",
        "fuente_datos_id",
        "infraestructura_actualizacion_anio",
        "infraestructura_es_snapshot",
        "infraestructura_temporalidad",
        "cve_col",
        "ba1_noeqsa",
        "ba8_nomerc",
        "ba8_noloca",
        "ba9_no_gua",
        "ba3_noeqed",
        "resid_ton",
        "alump_sum",
        "alump_mean",
        "p_porcelec",
        "p_aguapot",
        "r_val_dren",
    ]
    for col in expected_infra_colonia:
        if col not in fact_infra_colonia.columns:
            fact_infra_colonia[col] = np.nan
    fact_infra_colonia = fact_infra_colonia[expected_infra_colonia]

    fact_panel = panel.copy()
    fact_panel["fuente_datos_id"] = FUENTE_IDS["panel_integrado_etl"]
    panel_cols = [
        "alcaldia_id",
        "tiempo_id",
        "fuente_datos_id",
        "target_robos_patrimoniales_total",
        "target_robos_log1p",
        "share_robos_patrimoniales_sobre_total_delitos",
        "total_delitos_fgj",
        "n_registros_sociales",
        "factor_sum",
        *SOCIAL_FEATURES,
        *INFRA_FEATURES,
        "infraestructura_actualizacion_anio",
        "infraestructura_es_snapshot",
        "infraestructura_temporalidad",
        "anio",
        "alcaldia_key",
        "alcaldia_nombre",
    ]
    for col in panel_cols:
        if col not in fact_panel.columns:
            fact_panel[col] = np.nan
    fact_panel = fact_panel[panel_cols]

    return {
        "fact_delitos_generales_alcaldia_anio": fact_delitos_generales,
        "fact_robos_patrimoniales_alcaldia_mes_subtipo": fact_robos_mes,
        "fact_robos_patrimoniales_alcaldia_anio": fact_robos_anio,
        "fact_pobreza_alcaldia_anio": fact_pobreza,
        "fact_infraestructura_alcaldia": fact_infra_alcaldia,
        "fact_infraestructura_colonia": fact_infra_colonia,
        "fact_panel_analitico_alcaldia_anio": fact_panel,
    }


def write_dimensional_readme() -> None:
    text = """# Esquema dimensional

El modelo usa una constelacion de hechos: pobreza, infraestructura, delitos generales, robos patrimoniales y panel analitico se guardan como hechos separados conectados por dimensiones compartidas.

## Dimensiones

- `dim_alcaldia`: 16 alcaldias canonicas.
- `dim_tiempo`: anios `YYYY00`, meses `YYYYMM` y snapshot `202200`.
- `dim_colonia`: colonias de infraestructura.
- `dim_delito_subtipo`: solo los seis subtipos patrimoniales, sin `OTRO`.
- `dim_variable_social`, `dim_variable_infraestructura`, `dim_fuente_datos`: trazabilidad.

## Hechos y grano

- `fact_delitos_generales_alcaldia_anio`: una fila por alcaldia-anio.
- `fact_robos_patrimoniales_alcaldia_mes_subtipo`: una fila por alcaldia-mes-subtipo.
- `fact_robos_patrimoniales_alcaldia_anio`: una fila por alcaldia-anio.
- `fact_pobreza_alcaldia_anio`: una fila por alcaldia-anio.
- `fact_infraestructura_alcaldia`: una fila por alcaldia, snapshot 2022.
- `fact_infraestructura_colonia`: una fila por colonia, snapshot 2022.
- `fact_panel_analitico_alcaldia_anio`: una fila por alcaldia-anio.

Las dimensiones tienen primary keys surrogate enteras. Los hechos usan `alcaldia_id`, `tiempo_id`, `snapshot_tiempo_id`, `colonia_id`, `delito_subtipo_id` y `fuente_datos_id` como llaves foraneas.

Infraestructura debe interpretarse como snapshot estructural 2022: `infraestructura_actualizacion_anio = 2022`, `infraestructura_es_snapshot = true`, `infraestructura_temporalidad = static_snapshot_2022`. No es medicion anual.

Para BI territorial usa hechos anuales; para robos mensuales usa `fact_robos_patrimoniales_alcaldia_mes_subtipo`; para reconstruir el panel une `fact_panel_analitico_alcaldia_anio` con `dim_alcaldia` y `dim_tiempo`. No afirmar causalidad y revisar el tamano pequeno del panel antes de modelar.

## Diagrama ER

```mermaid
erDiagram
dim_alcaldia ||--o{ dim_colonia : alcaldia_id
dim_alcaldia ||--o{ fact_delitos_generales_alcaldia_anio : alcaldia_id
dim_tiempo ||--o{ fact_delitos_generales_alcaldia_anio : tiempo_id
dim_fuente_datos ||--o{ fact_delitos_generales_alcaldia_anio : fuente_datos_id
dim_alcaldia ||--o{ fact_robos_patrimoniales_alcaldia_mes_subtipo : alcaldia_id
dim_tiempo ||--o{ fact_robos_patrimoniales_alcaldia_mes_subtipo : tiempo_id
dim_delito_subtipo ||--o{ fact_robos_patrimoniales_alcaldia_mes_subtipo : delito_subtipo_id
dim_fuente_datos ||--o{ fact_robos_patrimoniales_alcaldia_mes_subtipo : fuente_datos_id
dim_alcaldia ||--o{ fact_robos_patrimoniales_alcaldia_anio : alcaldia_id
dim_tiempo ||--o{ fact_robos_patrimoniales_alcaldia_anio : tiempo_id
dim_fuente_datos ||--o{ fact_robos_patrimoniales_alcaldia_anio : fuente_datos_id
dim_alcaldia ||--o{ fact_pobreza_alcaldia_anio : alcaldia_id
dim_tiempo ||--o{ fact_pobreza_alcaldia_anio : tiempo_id
dim_fuente_datos ||--o{ fact_pobreza_alcaldia_anio : fuente_datos_id
dim_alcaldia ||--o{ fact_infraestructura_alcaldia : alcaldia_id
dim_tiempo ||--o{ fact_infraestructura_alcaldia : snapshot_tiempo_id
dim_fuente_datos ||--o{ fact_infraestructura_alcaldia : fuente_datos_id
dim_colonia ||--o{ fact_infraestructura_colonia : colonia_id
dim_alcaldia ||--o{ fact_infraestructura_colonia : alcaldia_id
dim_tiempo ||--o{ fact_infraestructura_colonia : snapshot_tiempo_id
dim_fuente_datos ||--o{ fact_infraestructura_colonia : fuente_datos_id
dim_alcaldia ||--o{ fact_panel_analitico_alcaldia_anio : alcaldia_id
dim_tiempo ||--o{ fact_panel_analitico_alcaldia_anio : tiempo_id
dim_fuente_datos ||--o{ fact_panel_analitico_alcaldia_anio : fuente_datos_id
```

## Carga futura en PostgreSQL

Ejecutar desde la raiz del proyecto:

```sql
\\i sql/01_create_schemas.sql
\\i sql/02_create_clean_tables.sql
\\i sql/03_create_analytics_tables.sql
\\i sql/04_create_dimensional_schema.sql
\\i sql/05_create_indexes_and_constraints.sql
\\i sql/06_copy_clean_csv.sql
\\i sql/07_copy_analytics_csv.sql
\\i sql/08_copy_dimensional_csv.sql
\\i sql/09_validation_queries.sql
```
"""
    (DIMENSIONAL_DIR / "README.md").write_text(text, encoding="utf-8")


def main() -> None:
    ensure_dirs()
    for old_csv in DIMENSIONAL_DIR.glob("*.csv"):
        old_csv.unlink()

    pobreza = _safe_read(ANALYTICS_DIR / "pobreza_alcaldia_anio.csv")
    infraestructura = _safe_read(ANALYTICS_DIR / "infraestructura_alcaldia.csv")
    delitos_generales = _safe_read(ANALYTICS_DIR / "delitos_alcaldia_anio.csv")
    robos_mes = _safe_read(ROBBERY_ONLY_DIR / "robos_patrimoniales_alcaldia_mes_subtipo.csv")
    robos_anio = _safe_read(ROBBERY_ONLY_DIR / "robos_patrimoniales_alcaldia_anio.csv")
    panel = _safe_read(ANALYTICS_DIR / "panel_alcaldia_anio.csv")
    infra_clean = _safe_read(CLEAN_DIR / "infraestructura_clean.csv")

    dims = {
        "dim_alcaldia": build_dim_alcaldia(),
        "dim_tiempo": build_dim_tiempo(pobreza, delitos_generales, robos_mes, robos_anio, panel),
        "dim_delito_subtipo": build_dim_delito_subtipo(),
        "dim_variable_social": build_dim_variable_social(),
        "dim_variable_infraestructura": build_dim_variable_infraestructura(),
        "dim_fuente_datos": build_dim_fuente_datos(),
    }
    dims["dim_colonia"] = build_dim_colonia(infra_clean)

    facts = build_facts(
        dims["dim_colonia"],
        delitos_generales,
        robos_mes,
        robos_anio,
        pobreza,
        infraestructura,
        infra_clean,
        panel,
    )

    for name, frame in {**dims, **facts}.items():
        write_csv(frame, DIMENSIONAL_DIR / f"{name}.csv")

    write_dimensional_readme()
    update_metadata(
        dimensional_outputs={
            "dimensions": {name: int(len(frame)) for name, frame in dims.items()},
            "facts": {name: int(len(frame)) for name, frame in facts.items()},
            "path": str(DIMENSIONAL_DIR.relative_to(ROOT)),
        }
    )
    print("Esquema dimensional completado.")


if __name__ == "__main__":
    main()
