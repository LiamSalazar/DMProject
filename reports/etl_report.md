# Informe ETL

## Archivos detectados
- pobreza: datasets\enigh_16_20.csv
- infraestructura: datasets\infraestructura.csv
- fgj: datasets\carpetasFGJ_acumulado_2025_01.csv

## Filas
- pobreza: originales=842342, finales=22219
- infraestructura: originales=1814, finales=1814
- fgj: originales=2098743, finales=2024266, robos=610306

## Temporalidad FGJ
- Rango antes de limpieza: [222, 2025]
- Rango despues de limpieza: [2016, 2025]
- Confirmacion: FGJ filtrado a 2016-2025.

## Panel principal
- Años: [2016, 2018, 2020]
- Filas: 48
- Confirmacion: 16 alcaldias por año comun validado.

## Infraestructura
- Confirmacion: snapshot 2022, no medicion anual.
- Temporalidad: static_snapshot_2022

## Robos patrimoniales
- Confirmacion: hechos y archivos robbery_only no contienen OTRO.
- Target calculado solo desde los seis subtipos patrimoniales.

## Registros eliminados
- pobreza: {'fuera_de_cdmx': 820123, 'alcaldia_o_anio_no_validos': 0}
- infraestructura: {}
- fgj: {'alcaldia_no_valida': 42482, 'anio_o_mes_no_parseable': 559, 'fuera_rango_proyecto_2016_2025': 32599}

## Nulos relevantes
- Sin nulos relevantes en modeling_panel.

## Variables agregadas
- Sociales: promedios ponderados `_wmean` por alcaldia-anio.
- Infraestructura: sumas para conteos/volumen y promedios para porcentajes/rankings.
- FGJ general: total_delitos_fgj, total_robos_patrimoniales y share anual.
- Robos: agregados mensuales por subtipo y target anual.

## Salidas dimensionales
- Dimensiones: {'dim_alcaldia': 16, 'dim_tiempo': 119, 'dim_delito_subtipo': 6, 'dim_variable_social': 12, 'dim_variable_infraestructura': 21, 'dim_fuente_datos': 5, 'dim_colonia': 1814}
- Hechos: {'fact_delitos_generales_alcaldia_anio': 160, 'fact_robos_patrimoniales_alcaldia_mes_subtipo': 10362, 'fact_robos_patrimoniales_alcaldia_anio': 160, 'fact_pobreza_alcaldia_anio': 48, 'fact_infraestructura_alcaldia': 16, 'fact_infraestructura_colonia': 1814, 'fact_panel_analitico_alcaldia_anio': 48}

## Validaciones aprobadas
- Existe CSV data/processed/clean/pobreza_clean.csv
- CSV UTF-8 data/processed/clean/pobreza_clean.csv
- Columnas snake_case en data/processed/clean/pobreza_clean.csv
- Existe CSV data/processed/clean/infraestructura_clean.csv
- CSV UTF-8 data/processed/clean/infraestructura_clean.csv
- Columnas snake_case en data/processed/clean/infraestructura_clean.csv
- Existe CSV data/processed/clean/fgj_clean.csv
- CSV UTF-8 data/processed/clean/fgj_clean.csv
- Columnas snake_case en data/processed/clean/fgj_clean.csv
- Existe CSV data/processed/analytics/pobreza_alcaldia_anio.csv
- CSV UTF-8 data/processed/analytics/pobreza_alcaldia_anio.csv
- Columnas snake_case en data/processed/analytics/pobreza_alcaldia_anio.csv
- Existe CSV data/processed/analytics/infraestructura_alcaldia.csv
- CSV UTF-8 data/processed/analytics/infraestructura_alcaldia.csv
- Columnas snake_case en data/processed/analytics/infraestructura_alcaldia.csv
- Existe CSV data/processed/analytics/delitos_alcaldia_anio.csv
- CSV UTF-8 data/processed/analytics/delitos_alcaldia_anio.csv
- Columnas snake_case en data/processed/analytics/delitos_alcaldia_anio.csv
- Existe CSV data/processed/robbery_only/fgj_robos_patrimoniales_clean.csv
- CSV UTF-8 data/processed/robbery_only/fgj_robos_patrimoniales_clean.csv
- Columnas snake_case en data/processed/robbery_only/fgj_robos_patrimoniales_clean.csv
- Existe CSV data/processed/robbery_only/robos_patrimoniales_alcaldia_mes_subtipo.csv
- CSV UTF-8 data/processed/robbery_only/robos_patrimoniales_alcaldia_mes_subtipo.csv
- Columnas snake_case en data/processed/robbery_only/robos_patrimoniales_alcaldia_mes_subtipo.csv
- Existe CSV data/processed/robbery_only/robos_patrimoniales_alcaldia_anio.csv
- CSV UTF-8 data/processed/robbery_only/robos_patrimoniales_alcaldia_anio.csv
- Columnas snake_case en data/processed/robbery_only/robos_patrimoniales_alcaldia_anio.csv
- Existe CSV data/processed/analytics/panel_alcaldia_anio.csv
- CSV UTF-8 data/processed/analytics/panel_alcaldia_anio.csv
- Columnas snake_case en data/processed/analytics/panel_alcaldia_anio.csv
- Existe CSV data/processed/analytics/modeling_panel.csv
- CSV UTF-8 data/processed/analytics/modeling_panel.csv
- Columnas snake_case en data/processed/analytics/modeling_panel.csv
- Existe CSV data/processed/analytics/feature_catalog.csv
- CSV UTF-8 data/processed/analytics/feature_catalog.csv
- Columnas snake_case en data/processed/analytics/feature_catalog.csv
- Existe CSV dimensional_schema/dim_alcaldia.csv
- CSV UTF-8 dimensional_schema/dim_alcaldia.csv
- Columnas snake_case en dimensional_schema/dim_alcaldia.csv
- Existe CSV dimensional_schema/dim_tiempo.csv
- CSV UTF-8 dimensional_schema/dim_tiempo.csv
- Columnas snake_case en dimensional_schema/dim_tiempo.csv
- Existe CSV dimensional_schema/dim_colonia.csv
- CSV UTF-8 dimensional_schema/dim_colonia.csv
- Columnas snake_case en dimensional_schema/dim_colonia.csv
- Existe CSV dimensional_schema/dim_delito_subtipo.csv
- CSV UTF-8 dimensional_schema/dim_delito_subtipo.csv
- Columnas snake_case en dimensional_schema/dim_delito_subtipo.csv
- Existe CSV dimensional_schema/dim_variable_social.csv
- CSV UTF-8 dimensional_schema/dim_variable_social.csv
- Columnas snake_case en dimensional_schema/dim_variable_social.csv
- Existe CSV dimensional_schema/dim_variable_infraestructura.csv
- CSV UTF-8 dimensional_schema/dim_variable_infraestructura.csv
- Columnas snake_case en dimensional_schema/dim_variable_infraestructura.csv
- Existe CSV dimensional_schema/dim_fuente_datos.csv
- CSV UTF-8 dimensional_schema/dim_fuente_datos.csv
- Columnas snake_case en dimensional_schema/dim_fuente_datos.csv
- Existe CSV dimensional_schema/fact_delitos_generales_alcaldia_anio.csv
- CSV UTF-8 dimensional_schema/fact_delitos_generales_alcaldia_anio.csv
- Columnas snake_case en dimensional_schema/fact_delitos_generales_alcaldia_anio.csv
- Existe CSV dimensional_schema/fact_robos_patrimoniales_alcaldia_mes_subtipo.csv
- CSV UTF-8 dimensional_schema/fact_robos_patrimoniales_alcaldia_mes_subtipo.csv
- Columnas snake_case en dimensional_schema/fact_robos_patrimoniales_alcaldia_mes_subtipo.csv
- Existe CSV dimensional_schema/fact_robos_patrimoniales_alcaldia_anio.csv
- CSV UTF-8 dimensional_schema/fact_robos_patrimoniales_alcaldia_anio.csv
- Columnas snake_case en dimensional_schema/fact_robos_patrimoniales_alcaldia_anio.csv
- Existe CSV dimensional_schema/fact_pobreza_alcaldia_anio.csv
- CSV UTF-8 dimensional_schema/fact_pobreza_alcaldia_anio.csv
- Columnas snake_case en dimensional_schema/fact_pobreza_alcaldia_anio.csv
- Existe CSV dimensional_schema/fact_infraestructura_alcaldia.csv
- CSV UTF-8 dimensional_schema/fact_infraestructura_alcaldia.csv
- Columnas snake_case en dimensional_schema/fact_infraestructura_alcaldia.csv
- Existe CSV dimensional_schema/fact_infraestructura_colonia.csv
- CSV UTF-8 dimensional_schema/fact_infraestructura_colonia.csv
- Columnas snake_case en dimensional_schema/fact_infraestructura_colonia.csv
- Existe CSV dimensional_schema/fact_panel_analitico_alcaldia_anio.csv
- CSV UTF-8 dimensional_schema/fact_panel_analitico_alcaldia_anio.csv
- Columnas snake_case en dimensional_schema/fact_panel_analitico_alcaldia_anio.csv
- Existe SQL sql/00_create_database_notes.md
- Existe SQL sql/01_create_schemas.sql
- Existe SQL sql/02_create_clean_tables.sql
- Existe SQL sql/03_create_analytics_tables.sql
- Existe SQL sql/04_create_dimensional_schema.sql
- Existe SQL sql/05_create_indexes_and_constraints.sql
- Existe SQL sql/06_copy_clean_csv.sql
- Existe SQL sql/07_copy_analytics_csv.sql
- Existe SQL sql/08_copy_dimensional_csv.sql
- Existe SQL sql/09_validation_queries.sql
- Existe SQL sql/10_drop_all.sql
- FGJ limpio general solo tiene años 2016-2025
- FGJ limpio general sin alcaldias fuera de catalogo
- FGJ robos patrimoniales solo tiene años 2016-2025
- fgj_robos_patrimoniales_clean solo tiene is_robo_patrimonial = 1
- fgj_robos_patrimoniales_clean no contiene OTRO
- dim_alcaldia tiene 16 alcaldias
- dim_alcaldia coincide con catalogo canonico
- alcaldia_id sin nulos
- dim_delito_subtipo contiene solo los 6 subtipos patrimoniales
- dim_delito_subtipo no contiene OTRO
- robos_patrimoniales mensual no contiene OTRO
- robos_patrimoniales anual no contiene columna OTRO
- target_robos_patrimoniales_total es numerico
- target_robos_patrimoniales_total no se calcula con OTRO
- fact_infra_alcaldia.snapshot_tiempo_id = 202200
- fact_infra_alcaldia.infraestructura_actualizacion_anio = 2022
- fact_infra_alcaldia.infraestructura_es_snapshot = true
- fact_infra_alcaldia.infraestructura_temporalidad = static_snapshot_2022
- fact_infra_colonia.snapshot_tiempo_id = 202200
- fact_infra_colonia.infraestructura_actualizacion_anio = 2022
- fact_infra_colonia.infraestructura_es_snapshot = true
- fact_infra_colonia.infraestructura_temporalidad = static_snapshot_2022
- Sin duplicados en clave natural dim_alcaldia
- Sin duplicados en clave natural dim_tiempo
- Sin duplicados en clave natural dim_colonia
- Sin duplicados en clave natural dim_delito_subtipo
- Sin duplicados en clave natural dim_variable_social
- Sin duplicados en clave natural dim_variable_infraestructura
- Sin duplicados en clave natural dim_fuente_datos
- Sin duplicados en grano fact_delitos_generales
- Sin duplicados en grano fact_robos_mes
- Sin duplicados en grano fact_robos_anio
- Sin duplicados en grano fact_pobreza
- Sin duplicados en grano fact_infra_alcaldia
- Sin duplicados en grano fact_infra_colonia
- Sin duplicados en grano fact_panel
- Llaves fact_delitos_generales.alcaldia_id existen en dimension
- Llaves fact_robos_mes.alcaldia_id existen en dimension
- Llaves fact_robos_anio.alcaldia_id existen en dimension
- Llaves fact_pobreza.alcaldia_id existen en dimension
- Llaves fact_infra_alcaldia.alcaldia_id existen en dimension
- Llaves fact_infra_colonia.alcaldia_id existen en dimension
- Llaves fact_panel.alcaldia_id existen en dimension
- Llaves fact_delitos_generales.tiempo_id existen en dimension
- Llaves fact_robos_mes.tiempo_id existen en dimension
- Llaves fact_robos_anio.tiempo_id existen en dimension
- Llaves fact_pobreza.tiempo_id existen en dimension
- Llaves fact_panel.tiempo_id existen en dimension
- Llaves fact_infra_alcaldia.snapshot_tiempo_id existen en dimension
- Llaves fact_infra_colonia.snapshot_tiempo_id existen en dimension
- Llaves delito_subtipo_id existen en dimension
- Llaves colonia_id existen en dimension
- fact_panel tiene 16 alcaldias por cada anio comun
- Panel tiene 48 filas para 2016, 2018 y 2020
- panel sin alcaldias fuera de catalogo
- modeling sin alcaldias fuera de catalogo
- fact_panel sin alcaldias fuera de catalogo
- feature_catalog clasifica roles esperados
- feature_catalog marca infraestructura como static_snapshot_2022
- Variables derivadas del target no recomendadas para modelado
- Panel final sin columnas completamente vacias
- CREATE TABLE incluye columnas de data/processed/clean/pobreza_clean.csv
- COPY referencia data/processed/clean/pobreza_clean.csv
- CREATE TABLE incluye columnas de data/processed/clean/infraestructura_clean.csv
- COPY referencia data/processed/clean/infraestructura_clean.csv
- CREATE TABLE incluye columnas de data/processed/clean/fgj_clean.csv
- COPY referencia data/processed/clean/fgj_clean.csv
- CREATE TABLE incluye columnas de data/processed/analytics/pobreza_alcaldia_anio.csv
- COPY referencia data/processed/analytics/pobreza_alcaldia_anio.csv
- CREATE TABLE incluye columnas de data/processed/analytics/infraestructura_alcaldia.csv
- COPY referencia data/processed/analytics/infraestructura_alcaldia.csv
- CREATE TABLE incluye columnas de data/processed/analytics/delitos_alcaldia_anio.csv
- COPY referencia data/processed/analytics/delitos_alcaldia_anio.csv
- CREATE TABLE incluye columnas de data/processed/robbery_only/fgj_robos_patrimoniales_clean.csv
- COPY referencia data/processed/robbery_only/fgj_robos_patrimoniales_clean.csv
- CREATE TABLE incluye columnas de data/processed/robbery_only/robos_patrimoniales_alcaldia_mes_subtipo.csv
- COPY referencia data/processed/robbery_only/robos_patrimoniales_alcaldia_mes_subtipo.csv
- CREATE TABLE incluye columnas de data/processed/robbery_only/robos_patrimoniales_alcaldia_anio.csv
- COPY referencia data/processed/robbery_only/robos_patrimoniales_alcaldia_anio.csv
- CREATE TABLE incluye columnas de data/processed/analytics/panel_alcaldia_anio.csv
- COPY referencia data/processed/analytics/panel_alcaldia_anio.csv
- CREATE TABLE incluye columnas de data/processed/analytics/modeling_panel.csv
- COPY referencia data/processed/analytics/modeling_panel.csv
- CREATE TABLE incluye columnas de data/processed/analytics/feature_catalog.csv
- COPY referencia data/processed/analytics/feature_catalog.csv
- CREATE TABLE incluye columnas de dimensional_schema/dim_alcaldia.csv
- COPY referencia dimensional_schema/dim_alcaldia.csv
- CREATE TABLE incluye columnas de dimensional_schema/dim_tiempo.csv
- COPY referencia dimensional_schema/dim_tiempo.csv
- CREATE TABLE incluye columnas de dimensional_schema/dim_colonia.csv
- COPY referencia dimensional_schema/dim_colonia.csv
- CREATE TABLE incluye columnas de dimensional_schema/dim_delito_subtipo.csv
- COPY referencia dimensional_schema/dim_delito_subtipo.csv
- CREATE TABLE incluye columnas de dimensional_schema/dim_variable_social.csv
- COPY referencia dimensional_schema/dim_variable_social.csv
- CREATE TABLE incluye columnas de dimensional_schema/dim_variable_infraestructura.csv
- COPY referencia dimensional_schema/dim_variable_infraestructura.csv
- CREATE TABLE incluye columnas de dimensional_schema/dim_fuente_datos.csv
- COPY referencia dimensional_schema/dim_fuente_datos.csv
- CREATE TABLE incluye columnas de dimensional_schema/fact_delitos_generales_alcaldia_anio.csv
- COPY referencia dimensional_schema/fact_delitos_generales_alcaldia_anio.csv
- CREATE TABLE incluye columnas de dimensional_schema/fact_robos_patrimoniales_alcaldia_mes_subtipo.csv
- COPY referencia dimensional_schema/fact_robos_patrimoniales_alcaldia_mes_subtipo.csv
- CREATE TABLE incluye columnas de dimensional_schema/fact_robos_patrimoniales_alcaldia_anio.csv
- COPY referencia dimensional_schema/fact_robos_patrimoniales_alcaldia_anio.csv
- CREATE TABLE incluye columnas de dimensional_schema/fact_pobreza_alcaldia_anio.csv
- COPY referencia dimensional_schema/fact_pobreza_alcaldia_anio.csv
- CREATE TABLE incluye columnas de dimensional_schema/fact_infraestructura_alcaldia.csv
- COPY referencia dimensional_schema/fact_infraestructura_alcaldia.csv
- CREATE TABLE incluye columnas de dimensional_schema/fact_infraestructura_colonia.csv
- COPY referencia dimensional_schema/fact_infraestructura_colonia.csv
- CREATE TABLE incluye columnas de dimensional_schema/fact_panel_analitico_alcaldia_anio.csv
- COPY referencia dimensional_schema/fact_panel_analitico_alcaldia_anio.csv
- README.md existe
- README incluye carga futura en PostgreSQL
- README incluye comandos psql
- README explica diferencia entre FGJ general y robos patrimoniales
- README explica infraestructura snapshot 2022
- dimensional_schema/README.md existe
- dimensional_schema/README.md incluye diagrama ER Mermaid

## Advertencias
- FGJ tiene 1 registros con coordenadas fuera del rango aproximado CDMX; se reportan, no se eliminan.

## Limitaciones metodologicas
- Infraestructura es snapshot 2022 y no debe interpretarse como medicion anual.
- El panel principal depende de los anios comunes entre pobreza y FGJ.
- El analisis no demuestra causalidad; permite explorar relaciones, patrones y asociaciones.
- El modelado predictivo debe interpretarse con cautela por el tamano reducido del panel.
- No se inventan tasas poblacionales; no se incluye tasa por 100k al no haber denominador poblacional defendible.
