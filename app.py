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

st.markdown('<div class="main-title">🌱 Inteligencia Geoespacial SIACON</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Dashboard Dinámico y Generador de Reportes Agroclimáticos.</div>', unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. CONEXIÓN DIRECTA A SUPABASE (CACHÉ AUTOMÁTICA)
# -----------------------------------------------------------------------------
# Requiere tener instalado: pip install psycopg2-binary SQLAlchemy
conn = st.connection("supabase", type="sql", ttl=3600) # ttl=3600 guarda en caché por 1 hora

# -----------------------------------------------------------------------------
# 3. FILTROS DE INTERFAZ
# -----------------------------------------------------------------------------
st.markdown("<h4 style='color: #d4af37 !important;'>1. Definición del Objetivo</h4>", unsafe_allow_html=True)
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    cultivo_input = st.text_input("🌾 CULTIVO", placeholder="Ej: Maíz grano")
with c2:
    estado_input = st.text_input("📍 ESTADO (Opcional)", placeholder="Ej: Sinaloa")
with c3:
    ciclos = st.multiselect("🌤️ CICLO", ["Otoño-Invierno", "Primavera-Verano", "Perennes"])
with c4:
    metrica_seleccionada = st.selectbox(
        "📊 MÉTRICA",
        ["Producción", "Superficie sembrada", "Superficie cosechada", "Superficie siniestrada", "Rendimiento", "Valor de la producción"]
    )
with c5:
    anios = st.slider("📅 RANGO DE AÑOS", 2015, 2025, (2018, 2025))

# Diccionario para mapear la métrica visual a la columna real de la base de datos
columnas_metricas = {
    "Producción": "volumenproduccion",
    "Superficie sembrada": "sembrada",
    "Superficie cosechada": "cosechada",
    "Superficie siniestrada": "siniestrada",
    "Rendimiento": "rendimiento",
    "Valor de la producción": "valorproduccion"
}
columna_sql = columnas_metricas[metrica_seleccionada]

# -----------------------------------------------------------------------------
# 4. CAPA DE VISUALIZACIÓN INMEDIATA (SQL DIRECTO)
# -----------------------------------------------------------------------------
if cultivo_input:
    # Construcción dinámica de la consulta SQL hacia las tablas de Supabase
    query = f"""
    SELECT 
        a.anio, 
        e.nomestado as estado,
        SUM(a.{columna_sql}) as valor
    FROM agro_cierre_estatal a
    JOIN cat_cultivo c ON a.idcultivo = c.idcultivo
    JOIN cat_estado e ON a.idestado = e.idestado
    WHERE c.nomcultivo ILIKE :cultivo
    AND a.anio BETWEEN :anio_inicio AND :anio_fin
    """
    params = {
        "cultivo": f"%{cultivo_input}%",
        "anio_inicio": anios[0],
        "anio_fin": anios[1]
    }
    
    if estado_input and estado_input.lower() not in ["nacional", "todo mexico"]:
        query += " AND e.nomestado ILIKE :estado"
        params["estado"] = f"%{estado_input}%"
        
    query += " GROUP BY a.anio, e.nomestado ORDER BY a.anio"

    try:
        # Ejecución ultrarrápida contra Supabase
        df = conn.query(query, params=params)
        
        if not df.empty:
            # Renderizado interactivo con Plotly
            st.markdown(f"### 📈 Evolución de {metrica_seleccionada}")
            
            # Si hay un estado específico, coloreamos por estado, si no, mostramos el total nacional en la gráfica
            if not estado_input or estado_input.lower() in ["nacional", "todo mexico"]:
                df_plot = df.groupby("anio")["valor"].sum().reset_index()
                fig = px.line(df_plot, x="anio", y="valor", markers=True)
            else:
                fig = px.line(df, x="anio", y="valor", color="estado", markers=True)
                
            fig.update_layout(
                template="plotly_dark",
                plot_bgcolor="#0b1325", paper_bgcolor="#0b1325",
                font=dict(color="#8b9bb4"), title_font=dict(size=18, color="#ffffff"),
                xaxis_title="Año (Ciclo Agrícola)", yaxis_title=metrica_seleccionada,
                margin=dict(l=40, r=40, t=20, b=40)
            )
            fig.update_traces(line=dict(width=3), marker=dict(size=8))
            
            # Se muestra instantáneamente sin invocar al agente
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No se encontraron registros para los filtros seleccionados.")
    except Exception as e:
        st.warning(f"Error consultando la base de datos: {e}")

st.markdown("---")

# -----------------------------------------------------------------------------
# 5. CAPA DE INTELIGENCIA Y CARTOGRAFÍA (LLM Y CONTENEDOR EN CLOUD RUN)
# -----------------------------------------------------------------------------
st.markdown("<h4 style='color: #d4af37 !important;'>Generación de Entregables (Agente SIACON)</h4>", unsafe_allow_html=True)
st.caption("Utiliza este módulo solo cuando requieras cruzar coordenadas de sequía, descargar matrices completas en Excel y generar la cartografía verde de alto contraste.")

API_URL = "https://siacon-api-2m6lhlkauq-uc.a.run.app/consulta"
BASE_FILE_URL = "https://siacon-api-2m6lhlkauq-uc.a.run.app/archivos/"

if st.button("🧠 Ejecutar Análisis Profundo (IA, GDD y Mapas)", type="primary"):
    if not cultivo_input:
        st.error("⚠️ Define al menos el 'Cultivo' en la parte superior.")
    else:
        # Construimos un prompt natural para el LLM basado en los mismos filtros
        rango_txt = f"del año {anios[0]} al {anios[1]}"
        cobertura = estado_input if estado_input else "Nacional"
        prompt_agente = f"Genera un reporte de {metrica_seleccionada.lower()} del cultivo {cultivo_input} en cobertura {cobertura}. {rango_txt}."
        if ciclos: prompt_agente += f" Ciclos: {', '.join(ciclos)}."
        prompt_agente += " Exporta a excel, genera el mapa comparativo del último año y devuelve el Análisis Agroclimático con GDD."
        
        with st.spinner("🧠 El Agente SIACON está analizando el clima, sequía y dibujando el shapefile..."):
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
                                    label=f"⬇️ {nombre_doc}",
                                    data=doc_bytes,
                                    file_name=nombre_doc,
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    use_container_width=True
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