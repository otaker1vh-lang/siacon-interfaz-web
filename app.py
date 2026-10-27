import streamlit as st
import pandas as pd
import plotly.express as px
import requests

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN Y ESTILOS
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Inteligencia Geoespacial SIACON", page_icon="🌱", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0b1325; color: #e2e8f0; }
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown { color: #e2e8f0 !important; }
    .main-title { color: #ffffff !important; font-size: 26px; font-weight: 700; margin-bottom: 2px; }
    .subtitle { color: #8b9bb4 !important; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 25px; }
    
    /* Corrección Visual para Inputs y Dropdowns */
    .stSelectbox > div > div, .stMultiSelect > div > div, .stTextInput > div > div { background-color: #1e293b !important; border: 1px solid #334155 !important; }
    input[type="text"] { color: #ffffff !important; -webkit-text-fill-color: #ffffff !important; }
    .stSelectbox div[data-baseweb="select"] div, .stMultiSelect div[data-baseweb="select"] div { color: #ffffff !important; }
    .stMultiSelect span[data-baseweb="tag"] { background-color: #2E7D32 !important; color: #ffffff !important; }
    .stMultiSelect span[data-baseweb="tag"] span { color: #ffffff !important; }
    div[role="listbox"] { background-color: #1e293b !important; }
    div[role="option"] { color: #ffffff !important; }
    
    /* Tarjetas KPI */
    .kpi-card { background-color: #1e293b; padding: 20px; border-radius: 8px; border: 1px solid #334155; text-align: center; }
    .kpi-value { font-size: 24px; font-weight: bold; color: #d4af37; }
    .kpi-label { font-size: 12px; color: #8b9bb4; text-transform: uppercase; }
    
    .analisis-box { background-color: #1e293b; padding: 20px; border-radius: 8px; border-left: 5px solid #2E7D32; margin-top: 10px; font-size: 15px;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🌱 Inteligencia Geoespacial SIACON</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Dashboard Dinámico y Generador de Reportes Agroclimáticos.</div>', unsafe_allow_html=True)

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
        return estados, cultivos, variedades
    except Exception:
        # Valores de respaldo seguros en caso de fallo de red
        return (
            ["Todos", "Sinaloa", "Sonora", "Michoacán", "Jalisco", "Zacatecas"], 
            ["Todos", "Maíz grano", "Frijol", "Sorgo grano", "Trigo grano"], 
            ["Todas", "Blanco", "Amarillo"]
        )

lista_estados, lista_cultivos, lista_variedades = cargar_catalogos()

# -----------------------------------------------------------------------------
# 3. FILTROS DE INTERFAZ (Listas Desplegables)
# -----------------------------------------------------------------------------
st.markdown("<h4 style='color: #d4af37 !important;'>1. Definición del Objetivo</h4>", unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)
with c1:
    cultivo_input = st.selectbox("🌾 CULTIVO", lista_cultivos, index=lista_cultivos.index("Maíz grano") if "Maíz grano" in lista_cultivos else 0)
with c2:
    variedad_input = st.selectbox("🌱 VARIEDAD", lista_variedades)
with c3:
    estado_input = st.selectbox("📍 ESTADO", lista_estados)
with c4:
    municipio_input = st.text_input("🏘️ MUNICIPIO", placeholder="Ej: Ahome, Guasave...")

st.markdown("<h4 style='color: #d4af37 !important; margin-top: 15px;'>2. Parámetros Agrícolas y Cartografía</h4>", unsafe_allow_html=True)
c5, c6, c7, c8, c9 = st.columns(5)
with c5:
    ciclos = st.multiselect("🌤️ CICLO", ["Otoño-Invierno", "Primavera-Verano", "Perennes"])
with c6:
    modalidades = st.multiselect("💧 MODALIDAD", ["Riego", "Temporal"])
with c7:
    nivel = st.selectbox("🌐 NIVEL MAPEO", ["Municipal", "Estatal", "Nacional"], index=1)
with c8:
    metrica_seleccionada = st.selectbox("📊 MÉTRICA", ["Producción", "Superficie sembrada", "Superficie cosechada", "Superficie siniestrada", "Rendimiento", "Valor de la producción"])
with c9:
    anios = st.slider("📅 RANGO DE AÑOS", 2015, 2025, (2018, 2025))

c10, c11, c12, _ = st.columns([1, 1, 1, 2])
with c10:
    generar_mapa = st.checkbox("🗺️ GENERAR MAPA", value=True)
with c11:
    anios_mapa = st.multiselect("📅 AÑOS MAPA", [str(y) for y in range(2015, 2026)], default=["2024", "2025"], disabled=not generar_mapa)
with c12:
    tipo_etiqueta = st.selectbox("🏷️ ETIQUETAS", ["Ambos (Número y Nombre)", "Solo Nombre", "Solo Número", "Ninguno"], disabled=not generar_mapa)

columnas_metricas = {
    "Producción": "volumenproduccion", "Superficie sembrada": "sembrada", "Superficie cosechada": "cosechada",
    "Superficie siniestrada": "siniestrada", "Rendimiento": "rendimiento", "Valor de la producción": "valorproduccion"
}
columna_sql = columnas_metricas[metrica_seleccionada]

st.markdown("---")

# -----------------------------------------------------------------------------
# 4. CAPA DE VISUALIZACIÓN INMEDIATA (DASHBOARD)
# -----------------------------------------------------------------------------
if cultivo_input:
    # Se consulta la tabla municipal para poder filtrar por municipio si es necesario
    query = f"""
    SELECT 
        a.anio, 
        e.nomestado as estado,
        m.nommunicipio as municipio,
        SUM(a.{columna_sql}) as valor
    FROM agro_cierre_municipal a
    JOIN cat_cultivo c ON a.idcultivo = c.idcultivo
    JOIN cat_estado e ON a.idestado = e.idestado
    JOIN cat_municipio m ON a.idestado = m.idestado AND a.idmunicipio = m.idmunicipio
    LEFT JOIN cat_variedad v ON a.idcultivo = v.idcultivo AND a.idvariedad = v.idvariedad
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
        
    query += " GROUP BY a.anio, e.nomestado, m.nommunicipio ORDER BY a.anio"

    try:
        df = conn.query(query, params=params)
        
        if not df.empty:
            df["valor"] = pd.to_numeric(df["valor"], errors='coerce').fillna(0)
            
            # --- KPIs ---
            total_global = df["valor"].sum()
            ultimo_anio = df["anio"].max()
            total_ultimo = df[df["anio"] == ultimo_anio]["valor"].sum()
            
            k1, k2, k3 = st.columns(3)
            k1.markdown(f'<div class="kpi-card"><div class="kpi-label">Total Acumulado ({anios[0]}-{anios[1]})</div><div class="kpi-value">{total_global:,.0f}</div></div>', unsafe_allow_html=True)
            k2.markdown(f'<div class="kpi-card"><div class="kpi-label">Registro Año {ultimo_anio}</div><div class="kpi-value">{total_ultimo:,.0f}</div></div>', unsafe_allow_html=True)
            k3.markdown(f'<div class="kpi-card"><div class="kpi-label">Métrica Activa</div><div class="kpi-value" style="font-size:18px; margin-top:5px;">{metrica_seleccionada}</div></div>', unsafe_allow_html=True)
            st.write("")
            
            # --- Gráficas Mejoradas ---
            g_col1, g_col2 = st.columns([2, 1])
            
            with g_col1:
                st.markdown(f"### 📈 Evolución Temporal")
                # Agrupación dependiendo del nivel de visualización
                if municipio_input:
                    df_plot_line = df.groupby(["anio", "municipio"])["valor"].sum().reset_index()
                    fig_line = px.line(df_plot_line, x="anio", y="valor", color="municipio", markers=True)
                elif estado_input != "Todos":
                    df_plot_line = df.groupby(["anio", "estado"])["valor"].sum().reset_index()
                    fig_line = px.line(df_plot_line, x="anio", y="valor", color="estado", markers=True)
                else:
                    df_plot_line = df.groupby("anio")["valor"].sum().reset_index()
                    fig_line = px.area(df_plot_line, x="anio", y="valor", markers=True, color_discrete_sequence=["#d4af37"])
                    fig_line.update_traces(fillcolor='rgba(212, 175, 55, 0.2)')
                    
                fig_line.update_layout(
                    template="plotly_dark", plot_bgcolor="#0b1325", paper_bgcolor="#0b1325",
                    hovermode="x unified", font=dict(color="#8b9bb4"),
                    xaxis_title="Año", yaxis_title=metrica_seleccionada,
                    margin=dict(l=20, r=20, t=20, b=20)
                )
                st.plotly_chart(fig_line, use_container_width=True)
                
            with g_col2:
                st.markdown(f"### 📊 Top Distribución ({ultimo_anio})")
                df_last = df[df["anio"] == ultimo_anio]
                agrupacion = "municipio" if estado_input != "Todos" else "estado"
                df_bar = df_last.groupby(agrupacion)["valor"].sum().reset_index().sort_values("valor", ascending=True).tail(10)
                
                fig_bar = px.bar(df_bar, x="valor", y=agrupacion, orientation='h', color_discrete_sequence=["#2E7D32"])
                fig_bar.update_layout(
                    template="plotly_dark", plot_bgcolor="#0b1325", paper_bgcolor="#0b1325",
                    xaxis_title="", yaxis_title="", margin=dict(l=10, r=20, t=20, b=20)
                )
                st.plotly_chart(fig_bar, use_container_width=True)
                
        else:
            st.info("No se encontraron registros en la Base de Datos para esta combinación exacta de filtros.")
    except Exception as e:
        st.warning(f"Error consultando la base de datos: {e}")

st.markdown("---")

# -----------------------------------------------------------------------------
# 5. CAPA DE INTELIGENCIA (LLM Y CONTENEDOR EN CLOUD RUN)
# -----------------------------------------------------------------------------
st.markdown("<h4 style='color: #d4af37 !important;'>Generación de Entregables (Agente SIACON)</h4>", unsafe_allow_html=True)
API_URL = "https://siacon-api-2m6lhlkauq-uc.a.run.app/consulta"
BASE_FILE_URL = "https://siacon-api-2m6lhlkauq-uc.a.run.app/archivos/"

if st.button("🧠 Ejecutar Análisis Profundo (IA, Sequía y Mapas)", type="primary"):
    rango_txt = f"del año {anios[0]} al {anios[1]}"
    cobertura = estado_input if estado_input != "Todos" else "Nacional"
    
    # Construcción precisa del prompt para el Agente
    prompt_agente = f"Genera un reporte de {metrica_seleccionada.lower()} del cultivo {cultivo_input}"
    if variedad_input != "Todas": prompt_agente += f" variedad {variedad_input}"
    prompt_agente += f" en cobertura {cobertura}."
    if municipio_input: prompt_agente += f" Filtra estrictamente por el municipio {municipio_input}."
    if ciclos: prompt_agente += f" Ciclos: {', '.join(ciclos)}."
    if modalidades: prompt_agente += f" Modalidad: {', '.join(modalidades)}."
    
    prompt_agente += f" {rango_txt}. Nivel requerido: {nivel.lower()}."
    prompt_agente += " Exporta a excel y devuelve el Análisis Agroclimático."
    
    if generar_mapa and anios_mapa:
        etiqueta_final = {"Ambos (Número y Nombre)": "ambos", "Solo Nombre": "nombre", "Solo Número": "numero", "Ninguno": "ninguno"}[tipo_etiqueta]
        prompt_agente += f" Genera mapas comparativos de los años {', '.join(anios_mapa)}, etiqueta_mapa='{etiqueta_final}'."
        
    with st.spinner("🧠 El Agente SIACON está analizando el clima, sequía y procesando la cartografía..."):
        try:
            respuesta = requests.post(API_URL, json={"pregunta": prompt_agente}, timeout=600)
            datos = respuesta.json()
            
            if datos.get("ok"):
                archivos = datos.get("archivos", [])
                texto_respuesta = datos.get("respuesta", "")
                documentos = [f for f in archivos if f.lower().endswith((".xlsx", ".txt"))]
                imagenes_mapas = [f for f in archivos if f.lower().endswith((".jpg", ".png")) and "mapa" in f.lower()]
                
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

                if imagenes_mapas:
                    st.markdown("---")
                    st.markdown("<h2 style='text-align: center;'>🗺️ Cartografía Comparativa</h2>", unsafe_allow_html=True)
                    for mapa in imagenes_mapas:
                        st.image(f"{BASE_FILE_URL}{mapa}", use_container_width=True)

            else:
                st.error(f"❌ Error del agente: {datos.get('error', 'Desconocido')}")
        except Exception as e:
            st.error(f"❌ Error de conexión al contenedor: {e}")