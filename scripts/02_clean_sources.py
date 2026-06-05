from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from etl_common import (
    ALCALDIA_ID,
    ANALYTICS_DIR,
    CANONICAL_ALCALDIAS,
    CLEAN_DIR,
    CSV_NULL,
    INFRA_AVG_VARIABLES,
    INFRA_FEATURES,
    INFRA_SNAPSHOT_YEAR,
    INFRA_USE_RECOMMENDED,
    INFRA_SUM_VARIABLES,
    ROBO_SUBTIPO_COLUMNS,
    ROOT,
    SOCIAL_VARIABLES,
    alcaldia_nombre,
    canonicalize_alcaldia,
    classify_robo_subtipo,
    clean_string_columns,
    colonia_key,
    coerce_numeric,
    detect_encoding,
    detect_input_files,
    ensure_dirs,
    load_metadata,
    normalize_columns,
    normalize_text_key,
    parse_month,
    project_path,
    read_csv_robust,
    time_id,
    update_metadata,
    write_csv,
)


def _path_for(dataset: str) -> Path:
    metadata = load_metadata()
    detected = metadata.get("detected_files") or detect_input_files()
    return project_path(detected[dataset])


def _weighted_mean(group: pd.DataFrame, variable: str, weight_col: str = "factor") -> float:
    valid = group[variable].notna() & group[weight_col].notna()
    if not valid.any():
        return np.nan
    weights = group.loc[valid, weight_col]
    denom = weights.sum()
    if denom == 0 or pd.isna(denom):
        return np.nan
    return float((group.loc[valid, variable] * weights).sum() / denom)


def clean_pobreza() -> dict:
    path = _path_for("pobreza")
    df = read_csv_robust(path, low_memory=False)
    original_rows = len(df)
    df = normalize_columns(df)
    if "ano" in df.columns and "anio" not in df.columns:
        df = df.rename(columns={"ano": "anio"})
    df = clean_string_columns(df)

    for col in ["entidad", "municipio", "anio", "factor", *SOCIAL_VARIABLES]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df[df["entidad"].eq(9)].copy()
    rows_cdmx = len(df)
    df["alcaldia_key"] = df["municipio"].map(canonicalize_alcaldia)
    df["alcaldia_nombre"] = df["alcaldia_key"].map(alcaldia_nombre)
    df["alcaldia_id"] = df["alcaldia_key"].map(ALCALDIA_ID)
    df = df[df["alcaldia_key"].isin(CANONICAL_ALCALDIAS)].copy()
    df["anio"] = pd.to_numeric(df["anio"], errors="coerce").astype("Int64")
    df = df[df["anio"].notna()].copy()
    df["tiempo_id"] = df["anio"].astype(int) * 100

    clean_path = CLEAN_DIR / "pobreza_clean.csv"
    write_csv(df, clean_path)

    rows = []
    group_cols = ["alcaldia_key", "alcaldia_nombre", "anio"]
    for (alcaldia_key, alcaldia_name, anio), group in df.groupby(group_cols, dropna=False):
        row = {
            "alcaldia_key": alcaldia_key,
            "alcaldia_nombre": alcaldia_name,
            "alcaldia_id": ALCALDIA_ID.get(alcaldia_key),
            "anio": int(anio),
            "tiempo_id": int(anio) * 100,
            "n_registros_sociales": int(len(group)),
            "factor_sum": float(group["factor"].sum(skipna=True)),
        }
        for variable in SOCIAL_VARIABLES:
            row[f"{variable}_wmean"] = (
                _weighted_mean(group, variable) if variable in group.columns else np.nan
            )
        rows.append(row)
    pobreza_analytics = pd.DataFrame(rows).sort_values(["anio", "alcaldia_key"])
    pobreza_path = ANALYTICS_DIR / "pobreza_alcaldia_anio.csv"
    write_csv(pobreza_analytics, pobreza_path)

    return {
        "source": str(path.relative_to(ROOT)),
        "original_rows": int(original_rows),
        "cdmx_rows": int(rows_cdmx),
        "clean_rows": int(len(df)),
        "analytics_rows": int(len(pobreza_analytics)),
        "years": sorted([int(x) for x in pobreza_analytics["anio"].dropna().unique()]),
        "alcaldias": sorted(pobreza_analytics["alcaldia_key"].dropna().unique().tolist()),
        "dropped_rows": {
            "fuera_de_cdmx": int(original_rows - rows_cdmx),
            "alcaldia_o_anio_no_validos": int(rows_cdmx - len(df)),
        },
        "columns_clean": df.columns.tolist(),
        "columns_analytics": pobreza_analytics.columns.tolist(),
    }


def clean_infraestructura() -> dict:
    path = _path_for("infraestructura")
    df = read_csv_robust(path, low_memory=False)
    original_rows = len(df)
    df = normalize_columns(df)
    df = clean_string_columns(df)
    df["alcaldia_key"] = df["alcaldia"].map(canonicalize_alcaldia)
    df["alcaldia_nombre"] = df["alcaldia_key"].map(alcaldia_nombre)
    df["alcaldia_id"] = df["alcaldia_key"].map(ALCALDIA_ID)
    df["colonia_key"] = df["colonia"].map(colonia_key)
    df["colonia_nombre"] = df["colonia"].map(
        lambda x: normalize_text_key(x).title() if normalize_text_key(x) else None
    )
    df["infraestructura_actualizacion_anio"] = INFRA_SNAPSHOT_YEAR
    df["infraestructura_es_snapshot"] = True
    df["infraestructura_uso_recomendado"] = INFRA_USE_RECOMMENDED

    numeric_cols = [c for c in [*INFRA_SUM_VARIABLES, *INFRA_AVG_VARIABLES] if c in df.columns]
    df = coerce_numeric(df, numeric_cols)
    df = df[df["alcaldia_key"].isin(CANONICAL_ALCALDIAS)].copy()

    clean_path = CLEAN_DIR / "infraestructura_clean.csv"
    write_csv(df, clean_path)

    rows = []
    for alcaldia_key, group in df.groupby("alcaldia_key", dropna=False):
        row = {
            "alcaldia_key": alcaldia_key,
            "alcaldia_nombre": alcaldia_nombre(alcaldia_key),
            "alcaldia_id": ALCALDIA_ID.get(alcaldia_key),
            "colonias_count": int(group["colonia_key"].nunique(dropna=True)),
            "infraestructura_actualizacion_anio": INFRA_SNAPSHOT_YEAR,
            "infraestructura_es_snapshot": True,
            "infraestructura_uso_recomendado": INFRA_USE_RECOMMENDED,
        }
        for col in INFRA_SUM_VARIABLES:
            if col in group.columns:
                suffix = "total" if col == "alump_sum" else "sum"
                row[f"{col}_{suffix}"] = float(group[col].sum(skipna=True))
        for col in INFRA_AVG_VARIABLES:
            if col in group.columns:
                row[f"{col}_avg"] = float(group[col].mean(skipna=True))

        row["mercados_total"] = row.get("ba8_nomerc_sum", np.nan)
        row["locales_total"] = row.get("ba8_noloca_sum", np.nan)
        row["iluminacion_total"] = row.get("alump_sum_total", np.nan)
        row["iluminacion_promedio"] = row.get("alump_mean_avg", np.nan)
        row["residuos_ton_total"] = row.get("resid_ton_sum", np.nan)
        row["equipamiento_salud_total"] = row.get("ba1_noeqsa_sum", np.nan)
        row["equipamiento_educativo_total"] = row.get("ba3_noeqed_sum", np.nan)
        row["agua_potable_promedio"] = row.get("p_aguapot_avg", np.nan)
        row["electricidad_promedio"] = row.get("p_porcelec_avg", np.nan)
        row["drenaje_promedio"] = row.get("r_val_dren_avg", np.nan)
        rows.append(row)

    infraestructura_analytics = pd.DataFrame(rows).sort_values("alcaldia_key")
    for feature in INFRA_FEATURES:
        if feature not in infraestructura_analytics.columns:
            infraestructura_analytics[feature] = np.nan

    infra_path = ANALYTICS_DIR / "infraestructura_alcaldia.csv"
    write_csv(infraestructura_analytics, infra_path)

    missing = sorted(set(CANONICAL_ALCALDIAS) - set(infraestructura_analytics["alcaldia_key"]))
    return {
        "source": str(path.relative_to(ROOT)),
        "original_rows": int(original_rows),
        "clean_rows": int(len(df)),
        "analytics_rows": int(len(infraestructura_analytics)),
        "alcaldias": sorted(infraestructura_analytics["alcaldia_key"].dropna().unique().tolist()),
        "missing_alcaldias": missing,
        "columns_clean": df.columns.tolist(),
        "columns_analytics": infraestructura_analytics.columns.tolist(),
        "aggregation_notes": {
            "sumadas": INFRA_SUM_VARIABLES,
            "promediadas": INFRA_AVG_VARIABLES,
            "ambiguas": (
                "Variables con prefijos p_, r_, s_ y c_ se trataron como porcentajes, "
                "ranking, valor relativo o promedio y se agregaron por media."
            ),
        },
    }


def _best_alcaldia(chunk: pd.DataFrame) -> pd.Series:
    hecho = chunk.get("alcaldia_hecho", pd.Series([np.nan] * len(chunk), index=chunk.index))
    catalogo = chunk.get("alcaldia_catalogo", pd.Series([np.nan] * len(chunk), index=chunk.index))
    alcaldia_from_hecho = hecho.map(canonicalize_alcaldia)
    alcaldia_from_catalogo = catalogo.map(canonicalize_alcaldia)
    return alcaldia_from_hecho.fillna(alcaldia_from_catalogo)


def clean_fgj(chunksize: int = 250_000) -> dict:
    path = _path_for("fgj")
    output_clean = CLEAN_DIR / "fgj_clean.csv"
    if output_clean.exists():
        output_clean.unlink()

    monthly_parts = []
    annual_parts = []
    original_rows = 0
    final_rows = 0
    invalid_alcaldia_rows = 0
    invalid_year_month_rows = 0
    coord_out_of_range = 0
    coord_valid_total = 0
    coord_missing_total = 0
    header_written = False
    years_seen: set[int] = set()
    alcaldias_seen: set[str] = set()

    encoding = detect_encoding(path)
    for chunk in pd.read_csv(path, encoding=encoding, chunksize=chunksize, low_memory=False):
        original_rows += len(chunk)
        chunk = normalize_columns(chunk)
        chunk = clean_string_columns(chunk)

        alcaldia_key = _best_alcaldia(chunk)
        chunk["alcaldia_key"] = alcaldia_key
        chunk["alcaldia_nombre"] = chunk["alcaldia_key"].map(alcaldia_nombre)

        fecha_hecho = pd.to_datetime(chunk.get("fecha_hecho"), errors="coerce")
        fecha_inicio = pd.to_datetime(chunk.get("fecha_inicio"), errors="coerce")
        anio_numeric = pd.to_numeric(chunk.get("anio_hecho"), errors="coerce")
        anio_from_fecha = fecha_hecho.dt.year
        chunk["anio_hecho_clean"] = anio_numeric.fillna(anio_from_fecha)

        mes_from_fecha = fecha_hecho.dt.month
        mes_from_text = chunk.get("mes_hecho", pd.Series([np.nan] * len(chunk))).map(parse_month)
        chunk["mes_hecho_clean"] = pd.to_numeric(mes_from_fecha.fillna(mes_from_text), errors="coerce")

        chunk["latitud"] = pd.to_numeric(chunk.get("latitud"), errors="coerce")
        chunk["longitud"] = pd.to_numeric(chunk.get("longitud"), errors="coerce")
        coord_valid = chunk["latitud"].notna() & chunk["longitud"].notna()
        coord_valid_total += int(coord_valid.sum())
        coord_missing_total += int((~coord_valid).sum())
        coord_range = (
            chunk["latitud"].between(19.0, 19.7)
            & chunk["longitud"].between(-99.4, -98.8)
        )
        coord_out_of_range += int((coord_valid & ~coord_range).sum())

        chunk["delito"] = chunk.get("delito", pd.Series([np.nan] * len(chunk))).astype("string").str.strip()
        chunk["categoria_delito"] = (
            chunk.get("categoria_delito", pd.Series([np.nan] * len(chunk))).astype("string").str.strip()
        )
        chunk["delito_key"] = chunk["delito"].map(normalize_text_key)
        chunk["subtipo_robo_patrimonial"] = chunk["delito_key"].map(classify_robo_subtipo)
        chunk["is_robo_patrimonial"] = chunk["subtipo_robo_patrimonial"].ne("OTRO").astype(int)
        chunk["fecha_hecho"] = fecha_hecho.dt.strftime("%Y-%m-%d")
        chunk["fecha_inicio"] = fecha_inicio.dt.strftime("%Y-%m-%d")

        invalid_alcaldia_rows += int(chunk["alcaldia_key"].isna().sum())
        valid_year_month = (
            chunk["anio_hecho_clean"].between(2000, 2030)
            & chunk["mes_hecho_clean"].between(1, 12)
        )
        invalid_year_month_rows += int((~valid_year_month).sum())

        valid = chunk[chunk["alcaldia_key"].isin(CANONICAL_ALCALDIAS) & valid_year_month].copy()
        if valid.empty:
            continue

        valid["anio_hecho_clean"] = valid["anio_hecho_clean"].astype(int)
        valid["mes_hecho_clean"] = valid["mes_hecho_clean"].astype(int)
        valid["tiempo_id"] = (
            valid["anio_hecho_clean"].astype(int) * 100 + valid["mes_hecho_clean"].astype(int)
        )
        valid["colonia_hecho"] = valid.get("colonia_hecho", pd.Series([np.nan] * len(valid))).fillna(
            valid.get("colonia_catalogo", pd.Series([np.nan] * len(valid)))
        )
        valid["colonia_key"] = valid["colonia_hecho"].map(colonia_key)

        years_seen.update(int(x) for x in valid["anio_hecho_clean"].dropna().unique())
        alcaldias_seen.update(valid["alcaldia_key"].dropna().unique().tolist())
        final_rows += len(valid)

        valid["coord_valid"] = valid["latitud"].notna() & valid["longitud"].notna()
        valid["latitud_para_promedio"] = valid["latitud"].where(valid["coord_valid"])
        valid["longitud_para_promedio"] = valid["longitud"].where(valid["coord_valid"])

        monthly = (
            valid.groupby(
                [
                    "alcaldia_key",
                    "alcaldia_nombre",
                    "anio_hecho_clean",
                    "mes_hecho_clean",
                    "subtipo_robo_patrimonial",
                ],
                dropna=False,
            )
            .agg(
                total_delitos=("delito", "size"),
                registros_con_coordenadas=("coord_valid", "sum"),
                latitud_sum=("latitud_para_promedio", "sum"),
                longitud_sum=("longitud_para_promedio", "sum"),
            )
            .reset_index()
        )
        monthly_parts.append(monthly)

        annual = (
            valid.groupby(
                ["alcaldia_key", "alcaldia_nombre", "anio_hecho_clean", "subtipo_robo_patrimonial"],
                dropna=False,
            )
            .agg(total_delitos=("delito", "size"), total_robos=("is_robo_patrimonial", "sum"))
            .reset_index()
        )
        annual_parts.append(annual)

        clean_columns = [
            "fecha_hecho",
            "fecha_inicio",
            "anio_hecho_clean",
            "mes_hecho_clean",
            "delito",
            "delito_key",
            "categoria_delito",
            "alcaldia_key",
            "alcaldia_nombre",
            "colonia_key",
            "colonia_hecho",
            "latitud",
            "longitud",
            "subtipo_robo_patrimonial",
            "is_robo_patrimonial",
        ]
        valid[clean_columns].to_csv(
            output_clean,
            mode="a",
            header=not header_written,
            index=False,
            encoding="utf-8",
            na_rep=CSV_NULL,
        )
        header_written = True

    if monthly_parts:
        monthly_all = pd.concat(monthly_parts, ignore_index=True)
        monthly_final = (
            monthly_all.groupby(
                [
                    "alcaldia_key",
                    "alcaldia_nombre",
                    "anio_hecho_clean",
                    "mes_hecho_clean",
                    "subtipo_robo_patrimonial",
                ],
                dropna=False,
            )
            .agg(
                total_delitos=("total_delitos", "sum"),
                registros_con_coordenadas=("registros_con_coordenadas", "sum"),
                latitud_sum=("latitud_sum", "sum"),
                longitud_sum=("longitud_sum", "sum"),
            )
            .reset_index()
        )
        monthly_final["latitud_promedio"] = monthly_final["latitud_sum"] / monthly_final[
            "registros_con_coordenadas"
        ].replace({0: np.nan})
        monthly_final["longitud_promedio"] = monthly_final["longitud_sum"] / monthly_final[
            "registros_con_coordenadas"
        ].replace({0: np.nan})
        monthly_final = monthly_final.drop(columns=["latitud_sum", "longitud_sum"])
        monthly_final = monthly_final.rename(
            columns={"anio_hecho_clean": "anio", "mes_hecho_clean": "mes"}
        )
        monthly_final["tiempo_id"] = monthly_final["anio"].astype(int) * 100 + monthly_final[
            "mes"
        ].astype(int)
        monthly_final["alcaldia_id"] = monthly_final["alcaldia_key"].map(ALCALDIA_ID)
        monthly_final = monthly_final[
            [
                "alcaldia_key",
                "alcaldia_nombre",
                "alcaldia_id",
                "anio",
                "mes",
                "tiempo_id",
                "subtipo_robo_patrimonial",
                "total_delitos",
                "registros_con_coordenadas",
                "latitud_promedio",
                "longitud_promedio",
            ]
        ].sort_values(["anio", "mes", "alcaldia_key", "subtipo_robo_patrimonial"])
    else:
        monthly_final = pd.DataFrame()

    if annual_parts:
        annual_all = pd.concat(annual_parts, ignore_index=True)
        annual_grouped = (
            annual_all.groupby(
                ["alcaldia_key", "alcaldia_nombre", "anio_hecho_clean", "subtipo_robo_patrimonial"],
                dropna=False,
            )
            .agg(total_delitos=("total_delitos", "sum"), total_robos=("total_robos", "sum"))
            .reset_index()
        )
        base = (
            annual_grouped.groupby(["alcaldia_key", "alcaldia_nombre", "anio_hecho_clean"], dropna=False)
            .agg(
                total_delitos_fgj=("total_delitos", "sum"),
                total_robos_patrimoniales=("total_robos", "sum"),
            )
            .reset_index()
        )
        pivot = (
            annual_grouped.pivot_table(
                index=["alcaldia_key", "alcaldia_nombre", "anio_hecho_clean"],
                columns="subtipo_robo_patrimonial",
                values="total_robos",
                aggfunc="sum",
                fill_value=0,
            )
            .reset_index()
        )
        annual_final = base.merge(
            pivot,
            on=["alcaldia_key", "alcaldia_nombre", "anio_hecho_clean"],
            how="left",
        )
        for subtype, col in ROBO_SUBTIPO_COLUMNS.items():
            annual_final[col] = annual_final.get(subtype, 0)
        drop_subtype_cols = [c for c in annual_final.columns if c in ROBO_SUBTIPO_COLUMNS]
        annual_final = annual_final.drop(columns=drop_subtype_cols, errors="ignore")
        annual_final = annual_final.rename(columns={"anio_hecho_clean": "anio"})
        annual_final["target_robos_patrimoniales_total"] = annual_final[
            "total_robos_patrimoniales"
        ]
        annual_final["tiempo_id"] = annual_final["anio"].astype(int) * 100
        annual_final["alcaldia_id"] = annual_final["alcaldia_key"].map(ALCALDIA_ID)
        annual_final = annual_final[
            [
                "alcaldia_key",
                "alcaldia_nombre",
                "alcaldia_id",
                "anio",
                "tiempo_id",
                "total_delitos_fgj",
                "total_robos_patrimoniales",
                "target_robos_patrimoniales_total",
                *ROBO_SUBTIPO_COLUMNS.values(),
            ]
        ].sort_values(["anio", "alcaldia_key"])
    else:
        annual_final = pd.DataFrame()

    write_csv(monthly_final, ANALYTICS_DIR / "delitos_alcaldia_mes_subtipo.csv")
    write_csv(annual_final, ANALYTICS_DIR / "delitos_alcaldia_anio.csv")

    return {
        "source": str(path.relative_to(ROOT)),
        "original_rows": int(original_rows),
        "clean_rows": int(final_rows),
        "analytics_month_rows": int(len(monthly_final)),
        "analytics_annual_rows": int(len(annual_final)),
        "years": sorted(years_seen),
        "alcaldias": sorted(alcaldias_seen),
        "dropped_rows": {
            "alcaldia_no_valida": int(invalid_alcaldia_rows),
            "anio_o_mes_no_valido": int(invalid_year_month_rows),
        },
        "coordinates": {
            "validas": int(coord_valid_total),
            "faltantes": int(coord_missing_total),
            "fuera_rango_aproximado_cdmx": int(coord_out_of_range),
        },
        "columns_clean": [
            "fecha_hecho",
            "fecha_inicio",
            "anio_hecho_clean",
            "mes_hecho_clean",
            "delito",
            "delito_key",
            "categoria_delito",
            "alcaldia_key",
            "alcaldia_nombre",
            "colonia_key",
            "colonia_hecho",
            "latitud",
            "longitud",
            "subtipo_robo_patrimonial",
            "is_robo_patrimonial",
        ],
        "columns_analytics_month": monthly_final.columns.tolist(),
        "columns_analytics_annual": annual_final.columns.tolist(),
    }


def main() -> None:
    ensure_dirs()
    source_results = {
        "pobreza": clean_pobreza(),
        "infraestructura": clean_infraestructura(),
        "fgj": clean_fgj(),
    }
    update_metadata(source_results=source_results)
    print("Limpieza de fuentes completada.")


if __name__ == "__main__":
    main()
