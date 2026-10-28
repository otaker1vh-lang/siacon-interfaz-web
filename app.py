import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import json
import io

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN Y ESTILOS
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Dashboard SIACON", page_icon="🌱", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0b1325; color: #e2e8f0; }
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown { color: #e2e8f0 !important; }
    .main-title { color: #ffffff !important; font-size: 26px; font-weight: 700; margin-bottom: 2px; }
    .subtitle { color: #8b9bb4 !important; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 25px; }
    
    .stSelectbox > div > div, .stMultiSelect > div > div, .stTextInput > div > div { background-color: #1e293b !important; border: 1px solid #334155 !important; }
    input[type="text"] { color: #ffffff !important; -webkit-text-fill-color: #ffffff !important; }
    .stSelectbox div[data-baseweb="select"] div, .stMultiSelect div[data-baseweb="select"] div { color: #ffffff !important; }
    .stMultiSelect span[data-baseweb="tag"] { background-color: #2E7D32 !important; color: #ffffff !important; }
    .stMultiSelect span[data-baseweb="tag"] span { color: #ffffff !important; }
    div[role="listbox"] { background-color: #1e293b !important; }
    div[role="option"] { color: #ffffff !important; }
    
    /* Botón Mapa Personalizado */
    button[kind="secondary"] {
        background-color: #0f766e !important;
        color: white !important;
        border: 1px solid #0f766e !important;
    }
    button[kind="secondary"]:hover {
        background-color: #0d9488 !important;
        border: 1px solid #0d9488 !important;
    }
    
    .analisis-box { background-color: #1e293b; padding: 20px; border-radius: 8px; border-left: 5px solid #2E7D32; margin-top: 10px; font-size: 15px;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🌱 Dashboard SIACON</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Generador de Reportes.</div>', unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. CONEXIÓN Y CARGA DE CATÁLOGOS DESDE SUPABASE
# -----------------------------------------------------------------------------
conn = st.connection("supabase", type="sql", ttl=3600)

@st.cache_data(ttl=86400, show_spinner=False)
def cargar_catalogos():
    try:
        estados = ["Todos"] + conn.query("SELECT DISTINCT nomestado FROM cat_estado ORDER BY nomestado")["nomestado"].tolist()
        cultivos = ["Todos"] + conn.query("SELECT DISTINCT nomcultivo FROM cat_cultivo ORDER BY nomcultivo")["nomcultivo"].tolist()
        variedades = ["Todas"] + conn.query("SELECT DISTINCT nomvariedad FROM cat_variedad ORDER BY nomvariedad")["nomvariedad"].tolist()
        ciclos_db = conn.query("SELECT DISTINCT nomciclo FROM cat_ciclo ORDER BY nomciclo")["nomciclo"].tolist()
        modalidades_db = conn.query("SELECT DISTINCT nommodalidad FROM cat_modalidad ORDER BY nommodalidad")["nommodalidad"].tolist()
        return estados, cultivos, variedades, ciclos_db, modalidades_db
    except Exception:
        return (
            ["Todos", "Sinaloa", "Sonora", "Michoacán", "Jalisco", "Zacatecas"], 
            ["Todos", "Maíz grano", "Frijol", "Sorgo grano", "Trigo grano"], 
            ["Todas", "Blanco", "Amarillo"],
            ["Otoño-Invierno", "Primavera-Verano", "Perennes"],
            ["Riego", "Temporal"]
        )

lista_estados, lista_cultivos, lista_variedades, lista_ciclos_db, lista_modalidades_db = cargar_catalogos()

@st.cache_data(show_spinner=False)
def cargar_mapas_geojson():
    def procesar_geojson(geojson_data):
        for i, feature in enumerate(geojson_data.get('features', [])):
            feature['id'] = str(i)
            geom = feature.get('geometry')
            if not geom: continue
            g_type = geom.get('type')
            coords = geom.get('coordinates', [])
            if g_type == 'Polygon':
                geom['coordinates'] = [anillo[::-1] for anillo in coords]
            elif g_type == 'MultiPolygon':
                geom['coordinates'] = [[anillo[::-1] for anillo in poli] for poli in coords]
        return geojson_data

    try:
        with open("geo_estados.json", "r", encoding="utf-8") as f:
            geo_estados = procesar_geojson(json.load(f))
        with open("geo_municipios.json", "r", encoding="utf-8") as f:
            geo_municipios = procesar_geojson(json.load(f))
        return geo_estados, geo_municipios
    except Exception as e:
        st.error(f"Error técnico detallado: {e}")
        return None, None

geo_estados_data, geo_municipios_data = cargar_mapas_geojson()

columnas_metricas = {
    "Producción": "volumenproduccion", 
    "Superficie sembrada": "sembrada", 
    "Superficie cosechada": "cosechada",
    "Superficie siniestrada": "siniestrada", 
    "Rendimiento": "rendimiento", 
    "Valor de la producción": "valorproduccion",
    "Precio medio rural": "preciomediorural",
    "Índice de siniestralidad": "indice_siniestralidad"
}

unidades_metricas = {
    "Producción": "ton", 
    "Superficie sembrada": "ha", 
    "Superficie cosechada": "ha",
    "Superficie siniestrada": "ha", 
    "Rendimiento": "ton/ha", 
    "Valor de la producción": "miles de pesos",
    "Precio medio rural": "$/ton",
    "Índice de siniestralidad": "%"
}

# -----------------------------------------------------------------------------
# 3. SECCIÓN 1: FILTROS E INTERFAZ
# -----------------------------------------------------------------------------
st.markdown("<h4 style='color: #d4af37 !important;'>1. Parámetros</h4>", unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
with c1:
    cultivo_input = st.selectbox("🌾 CULTIVO", lista_cultivos, index=lista_cultivos.index("Maíz grano") if "Maíz grano" in lista_cultivos else 0)
with c2:
    variedad_input = st.selectbox("🌱 VARIEDAD", lista_variedades)
with c3:
    estado_input = st.selectbox("📍 ESTADO", lista_estados)
with c4:
    municipio_input = st.text_input("🏘️ MUNICIPIO", placeholder="Ej: Ahome, Guasave...")

c5, c6, c7, c8 = st.columns(4)
with c5:
    ciclos = st.multiselect("🌤️ CICLO", lista_ciclos_db, default=[])
with c6:
    modalidades = st.multiselect("💧 MODALIDAD", lista_modalidades_db, default=[])
with c7:
    metricas_seleccionadas = st.multiselect("📊 MÉTRICA(S) [1 o 2 recomendadas]", list(columnas_metricas.keys()), default=["Producción"])
with c8:
    anios = st.slider("📅 RANGO DE AÑOS", 2015, 2025, (2018, 2025))

st.markdown("---")

datos_disponibles = False

# -----------------------------------------------------------------------------
# 4. CAPA DE VISUALIZACIÓN INMEDIATA (DASHBOARD)
# -----------------------------------------------------------------------------
if not metricas_seleccionadas:
    st.warning("⚠️ Selecciona al menos una métrica para visualizar los datos.")
elif len(metricas_seleccionadas) > 2:
    st.warning("⚠️ Para una mejor visualización, se recomienda seleccionar un máximo de 2 métricas simultáneas.")
elif cultivo_input:
    select_metrics = []
    for m_label in metricas_seleccionadas:
        col_db = columnas_metricas[m_label]
        if col_db in ['rendimiento', 'preciomediorural', 'indice_siniestralidad']:
            select_metrics.append(f"AVG(a.{col_db}) as {col_db}")
        else:
            select_metrics.append(f"SUM(a.{col_db}) as {col_db}")
    
    metrics_sql = ", ".join(select_metrics)

    query = f"""
    SELECT 
        a.anio, 
        COALESCE(e.nomestado, 'Nacional') as estado,
        COALESCE(m.nommunicipio, 'General') as municipio,
        {metrics_sql}
    FROM agro_cierre_municipal a
    LEFT JOIN cat_cultivo c ON a.idcultivo = c.idcultivo
    LEFT JOIN cat_estado e ON a.idestado = e.idestado
    LEFT JOIN cat_municipio m ON a.idestado = m.idestado AND a.idmunicipio = m.idmunicipio
    LEFT JOIN cat_variedad v ON a.idcultivo = v.idcultivo AND a.idvariedad = v.idvariedad
    LEFT JOIN cat_ciclo ci ON a.idciclo = ci.idciclo
    LEFT JOIN cat_modalidad mo ON a.idmodalidad = mo.idmodalidad
    WHERE a.anio BETWEEN :anio_inicio AND :anio_fin
    """
    params = {"anio_inicio": anios[0], "anio_fin": anios[1]}
    
    if cultivo_input != "Todos":
        query += " AND c.nomcultivo ILIKE :cultivo"
        params["cultivo"] = f"%{cultivo_input}%"
    if variedad_input != "Todas":
        query += " AND v.nomvariedad ILIKE :variedad"
        params["variedad"] = f"%{variedad_input}%"
    if estado_input != "Todos" and estado_input.lower() not in ["nacional"]:
        query += " AND e.nomestado ILIKE :estado"
        params["estado"] = f"%{estado_input}%"
    if municipio_input:
        query += " AND m.nommunicipio ILIKE :municipio"
        params["municipio"] = f"%{municipio_input}%"
        
    if ciclos:
        ciclo_conditions = []
        for idx, cic in enumerate(ciclos):
            key = f"ciclo_{idx}"
            ciclo_conditions.append(f"ci.nomciclo ILIKE :{key}")
            params[key] = f"%{cic}%"
        query += f" AND ({' OR '.join(ciclo_conditions)})"
        
    if modalidades:
        mod_conditions = []
        for idx, mod in enumerate(modalidades):
            key = f"mod_{idx}"
            mod_conditions.append(f"mo.nommodalidad ILIKE :{key}")
            params[key] = f"%{mod}%"
        query += f" AND ({' OR '.join(mod_conditions)})"
        
    query += " GROUP BY a.anio, e.nomestado, m.nommunicipio ORDER BY a.anio"

    try:
        df = conn.query(query, params=params)
        
        if not df.empty:
            datos_disponibles = True 
            cols_to_plot = []
            for m_label in metricas_seleccionadas:
                col_db = columnas_metricas[m_label]
                df[m_label] = pd.to_numeric(df[col_db], errors='coerce').fillna(0)
                cols_to_plot.append(m_label)
            
            ultimo_anio = df["anio"].max()
            
            g_col1, g_col2 = st.columns([2, 1])
            
            with g_col1:
                st.markdown(f"### 📈 Evolución Temporal")
                df_plot_line = df.groupby("anio")[cols_to_plot].sum().reset_index()
                
                if len(cols_to_plot) == 2:
                    fig_line = make_subplots(specs=[[{"secondary_y": True}]])
                    fig_line.add_trace(
                        go.Scatter(x=df_plot_line["anio"], y=df_plot_line[cols_to_plot[0]], name=cols_to_plot[0], mode="lines+markers", line=dict(width=3, color="#d4af37")),
                        secondary_y=False,
                    )
                    fig_line.add_trace(
                        go.Scatter(x=df_plot_line["anio"], y=df_plot_line[cols_to_plot[1]], name=cols_to_plot[1], mode="lines+markers", line=dict(width=3, color="#00ACC1")),
                        secondary_y=True,
                    )
                    fig_line.update_yaxes(title_text=f"<b>{cols_to_plot[0]}</b>", secondary_y=False, title_font=dict(color="#d4af37"))
                    fig_line.update_yaxes(title_text=f"<b>{cols_to_plot[1]}</b>", secondary_y=True, title_font=dict(color="#00ACC1"))
                else:
                    fig_line = px.line(df_plot_line, x="anio", y=cols_to_plot[0], markers=True)
                    fig_line.update_traces(line=dict(width=3, color="#d4af37"))
                
                fig_line.update_layout(
                    template="plotly_dark", plot_bgcolor="#0b1325", paper_bgcolor="#0b1325",
                    hovermode="x unified", font=dict(color="#8b9bb4"),
                    xaxis_title="Año", margin=dict(l=20, r=20, t=20, b=20)
                )
                st.plotly_chart(fig_line, use_container_width=True)
                
            with g_col2:
                # CORRECCIÓN: Bucle para generar un gráfico por CADA métrica seleccionada y ordenar de mayor a menor
                for metrica_activa in cols_to_plot:
                    unidad = unidades_metricas.get(metrica_activa, "")
                    st.markdown(f"### 📊 Top {metrica_activa} ({unidad}) - {ultimo_anio}")
                    
                    df_last = df[df["anio"] == ultimo_anio]
                    agrupacion = "municipio" if estado_input != "Todos" else "estado"
                    
                    df_bar = (
                        df_last.groupby(agrupacion, as_index=False)[metrica_activa]
                        .sum()
                        .sort_values(metrica_activa, ascending=False)
                        .head(10)
                    )

                    escala_top = [
                        [0.00, "#86cfa5"],
                        [0.50, "#269b63"],
                        [1.00, "#f2c14e"],
                    ]
                    max_bar = float(df_bar[metrica_activa].max()) if not df_bar.empty else 0.0
                    fig_bar = px.bar(
                        df_bar, x=metrica_activa, y=agrupacion, orientation="h",
                        color=metrica_activa, color_continuous_scale=escala_top,
                        range_color=(0, max_bar if max_bar > 0 else 1),
                        text=metrica_activa
                    )
                    fig_bar.update_traces(
                        texttemplate="%{text:,.2f}", textposition="outside",
                        cliponaxis=False, marker_line_width=0,
                        hovertemplate="%{y}<br>%{x:,.2f}<extra></extra>"
                    )
                    fig_bar.update_layout(
                        template="plotly_dark", plot_bgcolor="#0b1325", paper_bgcolor="#0b1325",
                        xaxis_title="", yaxis_title="", showlegend=False,
                        coloraxis_showscale=False,
                        margin=dict(l=10, r=65, t=15, b=20),
                        yaxis=dict(autorange="reversed"), # Coloca el #1 en la parte superior
                        height=280 if len(cols_to_plot) > 1 else 450
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)
                
            st.markdown("### 📋 Resumen Detallado por Variable y Variación Anual")
            df_resumen = df.groupby("anio")[cols_to_plot].sum().reset_index().sort_values("anio")
            
            cols_metric_cards = st.columns(len(cols_to_plot))
            for idx, m_label in enumerate(cols_to_plot):
                with cols_metric_cards[idx]:
                    with st.container(border=True):
                        st.markdown(f"#### 📊 {m_label.upper()}")
                        st.markdown("---")
                        
                        val_anterior = None
                        for _, row in df_resumen.iterrows():
                            val_actual = row[m_label]
                            anio_actual = int(row["anio"])
                            
                            if val_anterior is not None and val_anterior != 0:
                                var_pct = ((val_actual - val_anterior) / abs(val_anterior)) * 100
                                if var_pct > 0:
                                    badge = f"<span style='color: #4ade80; font-weight: 600; margin-left: 6px;'>▲ +{var_pct:.1f}%</span>"
                                elif var_pct < 0:
                                    badge = f"<span style='color: #f87171; font-weight: 600; margin-left: 6px;'>▼ {var_pct:.1f}%</span>"
                                else:
                                    badge = "<span style='color: #94a3b8; font-weight: 600; margin-left: 6px;'>0.0%</span>"
                            else:
                                badge = "<span style='color: #94a3b8; font-weight: 600; margin-left: 6px;'>Base</span>"
                                
                            val_anterior = val_actual
                            
                            fila_html = f"""
                            <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; font-size: 14px;'>
                                <span style='color: #8b9bb4; font-weight: bold;'>Año {anio_actual}:</span>
                                <div style='text-align: right;'>
                                    <span style='color: #ffffff; font-weight: bold;'>{val_actual:,.2f}</span>{badge}
                                </div>
                            </div>
                            """
                            st.markdown(fila_html, unsafe_allow_html=True)
                
        else:
            st.info("No se encontraron registros en la Base de Datos para esta combinación exacta de filtros.")
    except Exception as e:
        st.warning(f"Error consultando la base de datos: {e}")

st.markdown("---")

# -----------------------------------------------------------------------------
# 5. SECCIÓN 2: MAPAS Y GENERACIÓN DE INTELIGENCIA
# -----------------------------------------------------------------------------
st.markdown("<h4 style='color: #d4af37 !important;'>2. Mapa y Reporte</h4>", unsafe_allow_html=True)
st.caption("Genera mapas y análisis.")

c9, c10, c11, c12 = st.columns(4)
with c9:
    nivel = st.selectbox("🌐 NIVEL DE MAPEO", ["Municipal", "Estatal"], index=0)
with c10:
    st.write("") 
    generar_mapa = st.checkbox("🗺️ GENERAR MAPA", value=True)
with c11:
    anios_mapa = st.multiselect("📅 AÑOS MAPA", [str(y) for y in range(2015, 2026)], default=["2024"], disabled=not generar_mapa)
with c12:
    tipo_etiqueta = st.selectbox("🏷️ TOP 10 DESTACADOS", ["Mostrar Puntos y Tabla", "Ocultar"], disabled=not generar_mapa)

API_URL = "https://siacon-api-2m6lhlkauq-uc.a.run.app/consulta"
BASE_FILE_URL = "https://siacon-api-2m6lhlkauq-uc.a.run.app/archivos/"

st.write("")

col_btn1, col_btn2 = st.columns(2)
with col_btn1:
    btn_mapa_rapido = st.button("🗺️ Generar Solo Mapa (Rápido)", type="secondary", use_container_width=True)
with col_btn2:
    btn_ia_completo = st.button("🚀 Análisis (Excel)", type="primary", use_container_width=True)

# ----------------- MAPA INTERACTIVO (MOTOR NATIVO SIN MAPBOX) -----------------
if btn_mapa_rapido:
    if not generar_mapa or not anios_mapa:
        st.error("⚠️ Activa 'Generar Mapa' y selecciona al menos un año.")
    elif not datos_disponibles:
        st.error("⚠️ No hay datos disponibles para dibujar el mapa. Verifica tus filtros en la Sección 1.")
    elif geo_estados_data is None or geo_municipios_data is None:
        st.error("⚠️ No se encontraron los archivos GeoJSON en el repositorio.")
    else:
        with st.spinner("🗺️ Renderizando mapas..."):
            st.markdown("---")
            
            for anio_mapa_str in sorted(anios_mapa):
                anio_mapa = int(anio_mapa_str)
                df_mapa_anio = df[df['anio'] == anio_mapa]
                
                if df_mapa_anio.empty:
                    st.warning(f"No hay datos registrados para el año {anio_mapa} con estos filtros.")
                    continue
                    
                for metrica_activa in metricas_seleccionadas:
                    with st.container():
                        unidad = unidades_metricas.get(metrica_activa, "")
                        titulo_mapa = f"🗺️ Distribución de {metrica_activa} ({unidad}) - {anio_mapa}"
                        
                        st.markdown(f"<h3 style='text-align: center; color: #e2e8f0; margin-bottom: 20px;'>{titulo_mapa}</h3>", unsafe_allow_html=True)
                        
                        geojson_usar = geo_estados_data if nivel == "Estatal" else geo_municipios_data
                        columna_df = "estado" if nivel == "Estatal" else "municipio"
                        
                        df_agrupado = df_mapa_anio.groupby(columna_df)[metrica_activa].sum().reset_index()
                        df_agrupado = df_agrupado[~df_agrupado[columna_df].isin(["Nacional", "General"])]
                        
                        geo_records = []
                        for f in geojson_usar['features']:
                            geo_records.append({"id": f['id'], columna_df: f['properties'].get('NOMGEO', '')})
                        df_all = pd.DataFrame(geo_records)
                        
                        df_plot_map = pd.merge(df_all, df_agrupado, on=columna_df, how='left').fillna({metrica_activa: 0})
                        
                        # Escala robusta para colores
                        valores_positivos = pd.to_numeric(
                            df_plot_map[metrica_activa], errors="coerce"
                        ).fillna(0)
                        valores_positivos = valores_positivos[valores_positivos > 0]
                        limite_color = (
                            float(valores_positivos.quantile(0.98))
                            if not valores_positivos.empty else 1.0
                        )
                        limite_color = max(limite_color, 1e-9)

                        try:
                            fig_mapa = px.choropleth(
                                df_plot_map,
                                geojson=geojson_usar,
                                locations='id', 
                                color=metrica_activa,
                                color_continuous_scale=[
                                    [0.00, "#f1f5f9"],
                                    [0.10, "#d9f0a3"],
                                    [0.25, "#addd8e"],
                                    [0.45, "#78c679"],
                                    [0.65, "#41ab5d"],
                                    [0.82, "#238443"],
                                    [1.00, "#005a32"],
                                ],
                                range_color=(0, limite_color),
                                hover_name=columna_df,
                                hover_data={metrica_activa: ':,.2f', 'id': False}
                            )
                            
                            df_top = pd.DataFrame()
                            if tipo_etiqueta != "Ocultar":
                                # CORRECCIÓN: Evitar municipios duplicados en la tabla por coincidencia de nombre (ej. Cuauhtémoc)
                                df_top = df_plot_map[df_plot_map[metrica_activa] > 0].sort_values(metrica_activa, ascending=False).drop_duplicates(subset=[columna_df]).head(10)
                                lats, lons, texts = [], [], []
                                
                                for _, row in df_top.iterrows():
                                    val_num = row[metrica_activa]
                                    txt = f"{row[columna_df]}: {val_num:,.2f} {unidad}"
                                        
                                    for f in geojson_usar['features']:
                                        if f['id'] == row['id']:
                                            geom = f['geometry']
                                            coords = []
                                            if geom['type'] == 'Polygon':
                                                coords = geom['coordinates'][0]
                                            elif geom['type'] == 'MultiPolygon':
                                                coords = geom['coordinates'][0][0]
                                                
                                            if coords:
                                                lons_p = [c[0] for c in coords]
                                                lats_p = [c[1] for c in coords]
                                                lons.append(sum(lons_p)/len(lons_p))
                                                lats.append(sum(lats_p)/len(lats_p))
                                                texts.append(txt)
                                            break
                                            
                                if lats and lons:
                                    fig_mapa.add_scattergeo(
                                        lon=lons, lat=lats, 
                                        hovertext=texts,
                                        mode="markers",
                                        marker=dict(size=5, color="#ef4444", line=dict(width=1, color="#ffffff")),
                                        name="Top 10"
                                    )
                            
                            fig_mapa.update_geos(
                                fitbounds="locations", 
                                visible=False, 
                                projection_type="mercator",
                                bgcolor='rgba(0,0,0,0)'
                            )
                            
                            fig_mapa.update_layout(
                                height=550,
                                margin={"r":0, "t":0, "l":0, "b":0},
                                paper_bgcolor="#0b1325",
                                plot_bgcolor="#0b1325",
                                geo=dict(bgcolor='rgba(0,0,0,0)')
                            )
                            
                            map_col, table_col = st.columns([4.5, 1.5])
                            
                            with map_col:
                                st.plotly_chart(fig_mapa, use_container_width=True)
                                
                                buffer = io.StringIO()
                                fig_mapa.write_html(buffer, include_plotlyjs='cdn')
                                html_bytes = buffer.getvalue().encode('utf-8')
                                
                                st.download_button(
                                    label=f"⬇️ Descargar Mapa de {metrica_activa} ({anio_mapa})",
                                    data=html_bytes,
                                    file_name=f"mapa_{metrica_activa.lower().replace(' ', '_')}_{anio_mapa}.html",
                                    mime="text/html",
                                    key=f"descarga_mapa_{metrica_activa}_{anio_mapa}",
                                    use_container_width=True
                                )
                                
                            with table_col:
                                if tipo_etiqueta != "Ocultar" and not df_top.empty:
                                    st.markdown(f"#### 🏆 Top 10 {columna_df.capitalize()}")
                                    
                                    df_top_table = df_top[[columna_df, metrica_activa]].copy()
                                    df_top_table = df_top_table.sort_values(
                                        metrica_activa, ascending=False
                                    ).reset_index(drop=True)
                                    df_top_table.insert(0, "Lugar", [f"#{i}" for i in range(1, len(df_top_table) + 1)])
                                    
                                    col_metrica_name = f"{metrica_activa} ({unidad})"
                                    df_top_table.rename(
                                        columns={
                                            columna_df: columna_df.capitalize(),
                                            metrica_activa: col_metrica_name
                                        }, inplace=True
                                    )
                                    
                                    max_top = float(df_top_table[col_metrica_name].max()) if not df_top_table.empty else 0.0
                                    max_top = max(max_top, 1e-9)
                                    
                                    # CORRECCIÓN: Se cambió a un color de texto oscuro para asegurar visibilidad en celdas blancas
                                    st.dataframe(
                                        df_top_table.style
                                        .format({col_metrica_name: "{:,.2f}"})
                                        .bar(subset=[col_metrica_name], color="#238443", vmin=0, vmax=max_top)
                                        .set_properties(
                                            subset=["Lugar"],
                                            **{"color": "#f2c14e", "font-weight": "bold", "text-align": "center"}
                                        )
                                        .set_properties(
                                            subset=[col_metrica_name],
                                            **{"color": "#0b1325", "font-weight": "bold"}
                                        ),
                                        hide_index=True,
                                        use_container_width=True,
                                        height=min(440, 38 * (len(df_top_table) + 1))
                                    )
                                else:
                                    st.write("")
                                    
                        except Exception as e:
                            st.error(f"Error renderizando el mapa geoespacial: {e}")
                        
                        st.markdown("<br><hr>", unsafe_allow_html=True)

# ----------------- ANÁLISIS PROFUNDO (CLOUD RUN) -----------------
if btn_ia_completo:
    if not metricas_seleccionadas:
        st.error("⚠️ Define al menos una 'Métrica' en la Sección 1.")
    else:
        rango_txt = f"del año {anios[0]} al {anios[1]}"
        cobertura = estado_input if estado_input != "Todos" else "Nacional"
        metricas_agente = ", ".join(metricas_seleccionadas)
        
        prompt_agente = f"Genera un reporte de {metricas_agente.lower()} del cultivo {cultivo_input}"
        if variedad_input != "Todas": prompt_agente += f" variedad {variedad_input}"
        prompt_agente += f" en cobertura {cobertura}."
        if municipio_input: prompt_agente += f" Filtra estrictamente por el municipio {municipio_input}."
        if ciclos: prompt_agente += f" Ciclos: {', '.join(ciclos)}."
        if modalidades: prompt_agente += f" Modalidad: {', '.join(modalidades)}."
        
        prompt_agente += f" {rango_txt}. Nivel requerido para el reporte: {nivel.lower()}."
        prompt_agente += " Exporta a excel y devuelve el Análisis Agroclimático textual."
        
        with st.spinner("🧠 El Agente SIACON está analizando el clima, sequía y generando el reporte..."):
            try:
                respuesta = requests.post(API_URL, json={"pregunta": prompt_agente}, timeout=900)
                datos = respuesta.json()
                
                if datos.get("ok"):
                    archivos = datos.get("archivos", [])
                    texto_respuesta = datos.get("respuesta", "")
                    
                    documentos = [f for f in archivos if f.lower().endswith((".xlsx", ".txt"))]
                    
                    res_col1, res_col2 = st.columns([1, 1.2])
                    
                    with res_col1:
                        st.markdown("### 📥 Descargar Matrices de Excel")
                        for doc in documentos:
                            nombre_doc = doc.split("/")[-1]
                            if ".xlsx" in nombre_doc:
                                doc_bytes = requests.get(f"{BASE_FILE_URL}{doc}").content
                                st.download_button(
                                    label=f"⬇️ {nombre_doc}", data=doc_bytes, file_name=nombre_doc,
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True
                                )
                                
                    with res_col2:
                        st.markdown("### 🧠 Reporte Agroclimático Ejecutivo")
                        if "ANÁLISIS AGROCLIMÁTICO Y ESTRATÉGICO" in texto_respuesta:
                            analisis_limpio = texto_respuesta.split("ANÁLISIS AGROCLIMÁTICO Y ESTRATÉGICO")[-1].strip("=\n ")
                            st.markdown(f'<div class="analisis-box">{analisis_limpio}</div>', unsafe_allow_html=True)
                        else:
                            st.info(texto_respuesta)

                else:
                    st.error(f"❌ Error del agente: {datos.get('error', 'Desconocido')}")
            except requests.exceptions.ReadTimeout:
                st.error("❌ El servidor tardó demasiado en responder (Timeout). Intenta reducir el rango de años.")
            except Exception as e:
                st.error(f"❌ Error de conexión al contenedor: {e}")