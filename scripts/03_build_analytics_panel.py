from __future__ import annotations

import numpy as np
import pandas as pd

from etl_common import (
    ANALYTICS_DIR,
    INFRA_FEATURES,
    INFRA_SNAPSHOT_YEAR,
    INFRA_TEMPORALITY,
    INFRA_USE_RECOMMENDED,
    REPORTS_DIR,
    ROBBERY_ONLY_DIR,
    ROBO_SUBTIPO_COLUMNS,
    SOCIAL_FEATURES,
    clean_string_columns,
    ensure_dirs,
    load_mmip_dictionary,
    load_metadata,
    read_output_csv,
    update_metadata,
    write_csv,
)


TARGET = "target_robos_patrimoniales_total"
DERIVED_ANALYSIS_COLUMNS = [
    "target_robos_log1p",
    "share_robos_patrimoniales_sobre_total_delitos",
    "share_robo_a_transeunte",
    "share_robo_a_negocio",
    "share_robo_a_casa_habitacion",
    "share_robo_de_vehiculo",
    "share_robo_de_accesorios_auto",
    "share_robo_del_interior_de_vehiculo",
]
MODEL_CONTROL_COLUMNS = [
    "total_delitos_fgj",
    "n_registros_sociales",
    "factor_sum",
    "infraestructura_actualizacion_anio",
    "infraestructura_es_snapshot",
    "infraestructura_temporalidad",
]


def _data_type(series: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_integer_dtype(series):
        return "integer"
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    return "text"


def build_feature_catalog(modeling_panel: pd.DataFrame) -> pd.DataFrame:
    dictionary = load_mmip_dictionary()
    rows = []
    for col in modeling_panel.columns:
        notes = ""
        if col == TARGET:
            role = "target"
            source = "fgj_robos_patrimoniales"
            description = "Target principal: total anual de robos patrimoniales clasificados."
            leakage = "target"
            recommended = False
            temporal = "annual"
            notes = "No usar como feature; es la variable objetivo."
        elif col == "target_robos_log1p":
            role = "target"
            source = "fgj_robos_patrimoniales"
            description = "Transformacion log1p del target principal para analisis exploratorio."
            leakage = "target"
            recommended = False
            temporal = "annual"
            notes = "Usar solo como target alternativo, no como predictor."
        elif col in {
            "share_robos_patrimoniales_sobre_total_delitos",
            "share_robo_a_transeunte",
            "share_robo_a_negocio",
            "share_robo_a_casa_habitacion",
            "share_robo_de_vehiculo",
            "share_robo_de_accesorios_auto",
            "share_robo_del_interiorde_vehiculo",
            "share_robo_del_interior_de_vehiculo",
        }:
            role = "derived_analysis"
            source = "fgj_robos_patrimoniales"
            description = "Proporcion derivada de conteos delictivos del mismo anio."
            leakage = "high_same_year_target_derived"
            recommended = False
            temporal = "annual"
            notes = "Variable analitica; no recomendada como predictor por fuga de informacion."
        elif col in {"alcaldia_id", "tiempo_id", "alcaldia_key", "alcaldia_nombre", "anio"}:
            role = "id"
            source = "etl"
            description = "Identificador o llave de la unidad alcaldia-anio."
            leakage = "none"
            recommended = False
            temporal = "metadata" if col != "anio" else "annual"
        elif col in SOCIAL_FEATURES:
            raw = col.replace("_wmean", "")
            role = "feature"
            source = "pobreza_mmip"
            description = dictionary.get(raw) or f"Promedio ponderado por factor de {raw}."
            leakage = "low"
            recommended = True
            temporal = "annual"
        elif col in INFRA_FEATURES:
            role = "feature"
            source = "infraestructura"
            description = f"Indicador urbano agregado por alcaldia desde snapshot {INFRA_SNAPSHOT_YEAR}."
            leakage = "low"
            recommended = True
            temporal = "static_snapshot_2022"
        elif col in MODEL_CONTROL_COLUMNS:
            role = "metadata" if col.startswith("infraestructura_") else "control"
            source = "infraestructura" if col.startswith("infraestructura_") else "fuente"
            description = "Variable de control, trazabilidad o cobertura del panel."
            leakage = "medium_same_year_control" if col == "total_delitos_fgj" else "low"
            recommended = col not in {"total_delitos_fgj"}
            temporal = "static_snapshot_2022" if col.startswith("infraestructura_") else "annual"
            if col == "total_delitos_fgj":
                notes = "Control exploratorio del mismo anio; revisar uso en modelos predictivos."
        else:
            role = "metadata"
            source = "etl"
            description = "Variable auxiliar generada por el ETL."
            leakage = "review"
            recommended = False
            temporal = "metadata"
        rows.append(
            {
                "feature_name": col,
                "source_dataset": source,
                "feature_role": role,
                "data_type": _data_type(modeling_panel[col]),
                "description": description,
                "leakage_risk": leakage,
                "recommended_for_modeling": recommended,
                "temporal_behavior": temporal,
                "notes": notes,
            }
        )
    return pd.DataFrame(rows)


def _add_share_columns(panel: pd.DataFrame) -> pd.DataFrame:
    target = pd.to_numeric(panel[TARGET], errors="coerce").fillna(0)
    total_delitos = pd.to_numeric(panel["total_delitos_fgj"], errors="coerce").replace({0: np.nan})
    panel["share_robos_patrimoniales_sobre_total_delitos"] = target / total_delitos
    subtype_to_share = {
        "robo_a_transeunte": "share_robo_a_transeunte",
        "robo_a_negocio": "share_robo_a_negocio",
        "robo_a_casa_habitacion": "share_robo_a_casa_habitacion",
        "robo_de_vehiculo": "share_robo_de_vehiculo",
        "robo_de_accesorios_auto": "share_robo_de_accesorios_auto",
        "robo_del_interior_de_vehiculo": "share_robo_del_interior_de_vehiculo",
    }
    denominator = target.replace({0: np.nan})
    for subtype_col, share_col in subtype_to_share.items():
        panel[share_col] = pd.to_numeric(panel[subtype_col], errors="coerce").fillna(0) / denominator
    return panel


def write_modeling_readme() -> None:
    text = """# modeling_panel.csv

`modeling_panel.csv` tiene grano alcaldia-anio y queda listo para modelado exploratorio. No contiene escalamiento, `StandardScaler` ni imputacion silenciosa.

El target principal es `target_robos_patrimoniales_total`, calculado solo desde `data/processed/robbery_only/fgj_robos_patrimoniales_clean.csv`.

Columnas con `share_` y `target_robos_log1p` son derivadas del target o de conteos del mismo anio. Estan documentadas en `feature_catalog.csv` como `derived_analysis` o `target`, y no se recomiendan como predictores.

Infraestructura se interpreta como `static_snapshot_2022`; no es una medicion anual.
"""
    (ANALYTICS_DIR / "modeling_panel_readme.md").write_text(text, encoding="utf-8")


def main() -> None:
    ensure_dirs()
    pobreza = clean_string_columns(read_output_csv(ANALYTICS_DIR / "pobreza_alcaldia_anio.csv"))
    delitos_generales = clean_string_columns(read_output_csv(ANALYTICS_DIR / "delitos_alcaldia_anio.csv"))
    robos_anio = clean_string_columns(
        read_output_csv(ROBBERY_ONLY_DIR / "robos_patrimoniales_alcaldia_anio.csv")
    )
    infraestructura = clean_string_columns(read_output_csv(ANALYTICS_DIR / "infraestructura_alcaldia.csv"))

    pobreza_years = set(pd.to_numeric(pobreza["anio"], errors="coerce").dropna().astype(int))
    fgj_years = set(pd.to_numeric(delitos_generales["anio"], errors="coerce").dropna().astype(int))
    common_years = sorted(pobreza_years & fgj_years)
    preferred_years = [2016, 2018, 2020]
    panel_years = preferred_years if set(preferred_years).issubset(common_years) else common_years
    if not panel_years:
        raise RuntimeError("No hay años comunes entre pobreza y FGJ para construir el panel.")

    base = pobreza[pobreza["anio"].astype(int).isin(panel_years)].copy()
    general_cols = [
        "alcaldia_key",
        "anio",
        "total_delitos_fgj",
        "share_robos_patrimoniales_sobre_total_delitos",
    ]
    robbery_cols = [
        "alcaldia_key",
        "anio",
        TARGET,
        *ROBO_SUBTIPO_COLUMNS.values(),
        "target_robos_log1p",
    ]

    panel = base.merge(delitos_generales[general_cols], on=["alcaldia_key", "anio"], how="left")
    panel = panel.merge(robos_anio[robbery_cols], on=["alcaldia_key", "anio"], how="left")
    for col in ["total_delitos_fgj", TARGET, *ROBO_SUBTIPO_COLUMNS.values()]:
        panel[col] = pd.to_numeric(panel.get(col, 0), errors="coerce").fillna(0)
    panel["target_robos_log1p"] = np.log1p(panel[TARGET])
    panel = _add_share_columns(panel)

    infra_cols = [
        "alcaldia_key",
        "colonias_count",
        *INFRA_FEATURES,
        "infraestructura_actualizacion_anio",
        "infraestructura_es_snapshot",
        "infraestructura_temporalidad",
        "infraestructura_uso_recomendado",
    ]
    panel = panel.merge(
        infraestructura[[c for c in infra_cols if c in infraestructura.columns]],
        on="alcaldia_key",
        how="left",
    )
    panel["infraestructura_actualizacion_anio"] = panel[
        "infraestructura_actualizacion_anio"
    ].fillna(INFRA_SNAPSHOT_YEAR)
    panel["infraestructura_es_snapshot"] = panel["infraestructura_es_snapshot"].fillna(True)
    panel["infraestructura_temporalidad"] = panel["infraestructura_temporalidad"].fillna(INFRA_TEMPORALITY)
    panel["infraestructura_uso_recomendado"] = panel[
        "infraestructura_uso_recomendado"
    ].fillna(INFRA_USE_RECOMMENDED)

    panel = panel.sort_values(["anio", "alcaldia_key"])
    write_csv(panel, ANALYTICS_DIR / "panel_alcaldia_anio.csv")

    modeling_columns = [
        "alcaldia_id",
        "tiempo_id",
        "alcaldia_key",
        "alcaldia_nombre",
        "anio",
        TARGET,
        "target_robos_log1p",
        *DERIVED_ANALYSIS_COLUMNS[1:],
        *SOCIAL_FEATURES,
        *INFRA_FEATURES,
        *MODEL_CONTROL_COLUMNS,
    ]
    for col in modeling_columns:
        if col not in panel.columns:
            panel[col] = np.nan
    modeling_panel = panel[modeling_columns].copy()
    write_csv(modeling_panel, ANALYTICS_DIR / "modeling_panel.csv")

    null_report = (
        modeling_panel.isna()
        .sum()
        .reset_index()
        .rename(columns={"index": "column_name", 0: "null_count"})
    )
    null_report["row_count"] = len(modeling_panel)
    null_report["null_pct"] = null_report["null_count"] / max(len(modeling_panel), 1)
    write_csv(null_report, REPORTS_DIR / "modeling_panel_nulls.csv")

    feature_catalog = build_feature_catalog(modeling_panel)
    write_csv(feature_catalog, ANALYTICS_DIR / "feature_catalog.csv")
    write_modeling_readme()

    metadata = load_metadata()
    update_metadata(
        analytics_panel={
            "panel_years": panel_years,
            "common_years_pobreza_fgj": common_years,
            "panel_rows": int(len(panel)),
            "modeling_rows": int(len(modeling_panel)),
            "panel_columns": panel.columns.tolist(),
            "modeling_columns": modeling_panel.columns.tolist(),
            "feature_catalog_rows": int(len(feature_catalog)),
            "nulls": {
                row["column_name"]: int(row["null_count"])
                for _, row in null_report.iterrows()
                if int(row["null_count"]) > 0
            },
        },
        source_results=metadata.get("source_results", {}),
    )
    print("Panel analítico y catálogo de features completados.")


if __name__ == "__main__":
    main()
