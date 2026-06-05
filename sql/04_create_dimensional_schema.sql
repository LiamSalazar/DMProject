-- Ejecutar desde PostgreSQL despues de crear la base de datos.
-- Tablas en esquema dw.

CREATE TABLE IF NOT EXISTS dw.dim_alcaldia (
    alcaldia_id integer,
    alcaldia_key text,
    alcaldia_nombre text,
    municipio_enigh integer,
    cve_ent integer,
    entidad_nombre text
);

CREATE TABLE IF NOT EXISTS dw.dim_tiempo (
    tiempo_id integer,
    anio integer,
    mes integer,
    mes_nombre text,
    trimestre integer,
    granularidad text
);

CREATE TABLE IF NOT EXISTS dw.dim_colonia (
    colonia_id integer,
    alcaldia_id integer,
    colonia_key text,
    colonia_nombre text,
    cve_col text
);

CREATE TABLE IF NOT EXISTS dw.dim_delito_subtipo (
    delito_subtipo_id integer,
    subtipo_robo_patrimonial text,
    descripcion text,
    es_robo_patrimonial boolean
);

CREATE TABLE IF NOT EXISTS dw.dim_variable_social (
    variable_social_id integer,
    variable_nombre text,
    variable_origen text,
    descripcion text,
    metodo_agregacion text,
    rango_esperado text,
    recomendada_modelado boolean
);

CREATE TABLE IF NOT EXISTS dw.dim_variable_infraestructura (
    variable_infraestructura_id integer,
    variable_nombre text,
    variable_origen text,
    descripcion text,
    metodo_agregacion text,
    actualizacion_anio bigint,
    temporalidad text,
    recomendada_modelado boolean
);

CREATE TABLE IF NOT EXISTS dw.dim_fuente_datos (
    fuente_datos_id integer,
    fuente_nombre text,
    fuente_tipo text,
    archivo_origen text,
    carpeta_origen text,
    cobertura_temporal text,
    granularidad_original text,
    granularidad_final text,
    notas_uso text
);

CREATE TABLE IF NOT EXISTS dw.fact_delitos_alcaldia_mes_subtipo (
    alcaldia_id integer,
    tiempo_id integer,
    delito_subtipo_id integer,
    fuente_datos_id integer,
    total_delitos bigint,
    registros_con_coordenadas integer,
    latitud_promedio double precision,
    longitud_promedio double precision
);

CREATE TABLE IF NOT EXISTS dw.fact_delitos_alcaldia_anio (
    alcaldia_id integer,
    tiempo_id integer,
    fuente_datos_id integer,
    total_delitos_fgj bigint,
    total_robos_patrimoniales bigint,
    robo_a_transeunte bigint,
    robo_a_negocio bigint,
    robo_a_casa_habitacion bigint,
    robo_de_vehiculo bigint,
    robo_de_accesorios_auto bigint,
    robo_del_interior_de_vehiculo bigint
);

CREATE TABLE IF NOT EXISTS dw.fact_pobreza_alcaldia_anio (
    alcaldia_id integer,
    tiempo_id integer,
    fuente_datos_id integer,
    n_registros_sociales integer,
    factor_sum bigint,
    mmip_wmean double precision,
    rei_wmean double precision,
    nbi_wmean double precision,
    ccevj_wmean double precision,
    cbdj_wmean double precision,
    csj_wmean double precision,
    ctelj_wmean double precision,
    cenj_wmean double precision,
    ett_wmean double precision,
    casi_wmean double precision,
    cassi_wmean double precision,
    cyt_wmean double precision
);

CREATE TABLE IF NOT EXISTS dw.fact_infraestructura_alcaldia (
    alcaldia_id integer,
    snapshot_tiempo_id integer,
    fuente_datos_id integer,
    infraestructura_actualizacion_anio integer,
    infraestructura_es_snapshot boolean,
    infraestructura_uso_recomendado text,
    colonias_count bigint,
    ba1_noeqsa_sum bigint,
    ba8_nomerc_sum bigint,
    ba8_noloca_sum bigint,
    ba9_no_gua_sum bigint,
    ba3_noeqed_sum bigint,
    resid_ton_sum bigint,
    alump_sum_total bigint,
    alump_mean_avg double precision,
    p_porcelec_avg double precision,
    p_aguapot_avg double precision,
    r_val_dren_avg double precision
);

CREATE TABLE IF NOT EXISTS dw.fact_infraestructura_colonia (
    colonia_id integer,
    alcaldia_id integer,
    snapshot_tiempo_id integer,
    fuente_datos_id integer,
    infraestructura_actualizacion_anio integer,
    infraestructura_es_snapshot boolean,
    infraestructura_uso_recomendado text,
    cve_col text,
    ba1_noeqsa bigint,
    ba8_nomerc bigint,
    ba8_noloca bigint,
    ba9_no_gua bigint,
    ba3_noeqed bigint,
    resid_ton double precision,
    alump_sum bigint,
    alump_mean double precision,
    p_porcelec double precision,
    p_aguapot double precision,
    r_val_dren bigint
);

CREATE TABLE IF NOT EXISTS dw.fact_panel_analitico_alcaldia_anio (
    alcaldia_id integer,
    tiempo_id integer,
    fuente_datos_id integer,
    target_robos_patrimoniales_total bigint,
    total_delitos_fgj bigint,
    n_registros_sociales integer,
    factor_sum bigint,
    mmip_wmean double precision,
    rei_wmean double precision,
    nbi_wmean double precision,
    ccevj_wmean double precision,
    cbdj_wmean double precision,
    csj_wmean double precision,
    ctelj_wmean double precision,
    cenj_wmean double precision,
    ett_wmean double precision,
    casi_wmean double precision,
    cassi_wmean double precision,
    cyt_wmean double precision,
    mercados_total bigint,
    locales_total bigint,
    iluminacion_total bigint,
    iluminacion_promedio double precision,
    residuos_ton_total bigint,
    equipamiento_salud_total bigint,
    equipamiento_educativo_total bigint,
    agua_potable_promedio double precision,
    electricidad_promedio double precision,
    drenaje_promedio double precision,
    infraestructura_actualizacion_anio integer,
    infraestructura_es_snapshot boolean,
    infraestructura_uso_recomendado text,
    anio integer,
    alcaldia_key text,
    alcaldia_nombre text
);

