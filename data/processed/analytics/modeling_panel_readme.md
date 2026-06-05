# modeling_panel.csv

`modeling_panel.csv` tiene grano alcaldia-anio y queda listo para modelado exploratorio. No contiene escalamiento, `StandardScaler` ni imputacion silenciosa.

El target principal es `target_robos_patrimoniales_total`, calculado solo desde `data/processed/robbery_only/fgj_robos_patrimoniales_clean.csv`.

Columnas con `share_` y `target_robos_log1p` son derivadas del target o de conteos del mismo anio. Estan documentadas en `feature_catalog.csv` como `derived_analysis` o `target`, y no se recomiendan como predictores.

Infraestructura se interpreta como `static_snapshot_2022`; no es una medicion anual.
