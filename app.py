import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import json

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
    try:
        with open("geo_estados.json", "r", encoding="utf-8") as f:
            geo_estados = json.load(f)
        with open("geo_municipios.json", "r", encoding="utf-8") as f:
            geo_municipios = json.load(f)
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
                metrica_principal = cols_to_plot[0]
                st.markdown(f"### 📊 Top {metrica_principal} ({ultimo_anio})")
                df_last = df[df["anio"] == ultimo_anio]
                agrupacion = "municipio" if estado_input != "Todos" else "estado"
                
                df_bar = df_last.groupby(agrupacion)[metrica_principal].sum().reset_index().sort_values(metrica_principal, ascending=True).tail(10)
                
                fig_bar = px.bar(df_bar, x=metrica_principal, y=agrupacion, orientation='h', color_discrete_sequence=["#2E7D32"])
                fig_bar.update_layout(
                    template="plotly_dark", plot_bgcolor="#0b1325", paper_bgcolor="#0b1325",
                    xaxis_title="", yaxis_title="", margin=dict(l=10, r=20, t=20, b=20)
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
    tipo_etiqueta = st.selectbox("🏷️ ETIQUETAS", ["Ambos (Número y Nombre)", "Solo Nombre", "Solo Número", "Ninguno"], disabled=not generar_mapa)

API_URL = "https://siacon-api-2m6lhlkauq-uc.a.run.app/consulta"
BASE_FILE_URL = "https://siacon-api-2m6lhlkauq-uc.a.run.app/archivos/"

st.write("")

col_btn1, col_btn2 = st.columns(2)
with col_btn1:
    btn_mapa_rapido = st.button("🗺️ Generar Solo Mapa Interactivo (Rápido)", use_container_width=True)
with col_btn2:
    btn_ia_completo = st.button("🚀 Análisis Profundo (IA, Sequía y Excel)", type="primary", use_container_width=True)

# ----------------- MAPA INTERACTIVO (MOTOR NATIVO SIN MAPBOX) -----------------
if btn_mapa_rapido:
    if not generar_mapa or not anios_mapa:
        st.error("⚠️ Activa 'Generar Mapa' y selecciona al menos un año.")
    elif not datos_disponibles:
        st.error("⚠️ No hay datos disponibles para dibujar el mapa. Verifica tus filtros en la Sección 1.")
    elif geo_estados_data is None or geo_municipios_data is None:
        st.error("⚠️ No se encontraron los archivos 'geo_estados.json' o 'geo_municipios.json' en el repositorio.")
    else:
        metrica_activa = metricas_seleccionadas[0]
        anio_mapa = int(anios_mapa[-1])
        
        with st.spinner("🗺️ Renderizando mapa geoespacial nativo..."):
            st.markdown("---")
            st.markdown(f"<h3 style='text-align: center;'>🗺️ Distribución de {metrica_activa} ({anio_mapa})</h3>", unsafe_allow_html=True)
            
            df_mapa = df[df['anio'] == anio_mapa]
            
            if df_mapa.empty:
                st.warning(f"No hay datos registrados específicamente para el año {anio_mapa} con estos filtros.")
            else:
                if nivel == "Estatal":
                    df_plot_map = df_mapa.groupby("estado")[metrica_activa].sum().reset_index()
                    geojson_usar = geo_estados_data
                    llave_geojson = "properties.NOMGEO"
                    columna_df = "estado"
                else:
                    df_plot_map = df_mapa.groupby("municipio")[metrica_activa].sum().reset_index()
                    geojson_usar = geo_municipios_data
                    llave_geojson = "properties.NOMGEO" 
                    columna_df = "municipio"

                try:
                    # Renderizado nativo vectorial (más rápido y sin dependencias externas)
                    fig_mapa = px.choropleth(
                        df_plot_map,
                        geojson=geojson_usar,
                        locations=columna_df,
                        featureidkey=llave_geojson,
                        color=metrica_activa,
                        color_continuous_scale="Viridis",
                        hover_name=columna_df
                    )
                    
                    # Ajuste automático del zoom sobre las geometrías de México
                    fig_mapa.update_geos(fitbounds="locations", visible=False)
                    
                    fig_mapa.update_layout(
                        margin={"r":0, "t":0, "l":0, "b":0},
                        paper_bgcolor="#0b1325",
                        plot_bgcolor="#0b1325"
                    )
                    
                    st.plotly_chart(fig_mapa, use_container_width=True)
                except Exception as e:
                    st.error(f"Error renderizando el mapa geoespacial: {e}")

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