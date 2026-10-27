import streamlit as st
import requests
import re

# Configuración de página simulando el modo oscuro
st.set_page_config(page_title="Panel de Avance Agrícola", page_icon="📈", layout="wide")

# Estilos CSS para replicar el diseño oscuro, tipografía y colores de la imagen
st.markdown("""
<style>
    /* Fondo principal estilo dashboard oscuro */
    .stApp { background-color: #0b1325; color: #e2e8f0; }
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown { color: #e2e8f0 !important; }
    
    /* Encabezados y títulos */
    .main-title { color: #ffffff !important; font-size: 26px; font-weight: 700; margin-bottom: 2px; }
    .subtitle { color: #8b9bb4 !important; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 25px; }
    
    /* Pestañas de navegación superiores */
    .nav-pills { font-size: 14px; color: #8b9bb4; margin-bottom: 30px; display: flex; gap: 20px; }
    .nav-pill-active { background-color: #d4af37; color: #000; padding: 4px 16px; border-radius: 20px; font-weight: 600; }
    
    /* Ajustes a los inputs para hacerlos oscuros */
    .stSelectbox > div > div { background-color: #1e293b; color: white; border: 1px solid #334155; }
    .summary-text { color: #8b9bb4 !important; font-size: 13px; margin-top: 5px; }
    
    /* Cajas de métricas para el Análisis Ejecutivo */
    .analisis-box { background-color: #1e293b; padding: 20px; border-radius: 8px; border-left: 5px solid #2E7D32; margin-top: 20px; font-size: 15px;}
</style>
""", unsafe_allow_html=True)

# Navegación superior simulada
st.markdown('''
<div class="nav-pills">
    <span>Precios</span>
    <span>Exportaciones agrícolas</span>
    <span class="nav-pill-active">Avance agrícola</span>
    <span>Producción agrícola</span>
</div>
''', unsafe_allow_html=True)

st.markdown('<div class="main-title">Panel de Avance Agrícola (SIACON Agent)</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">SIAP-SADER AVANCE DE SIEMBRAS Y COSECHAS · MÉXICO · FUENTE OFICIAL</div>', unsafe_allow_html=True)

# Cuadrícula idéntica a la imagen para los parámetros
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    cultivo = st.selectbox("CULTIVO", ["Maíz grano", "Frijol", "Trigo grano", "Sorgo grano", "Arroz palay"])
with col2:
    region = st.selectbox("REGIÓN", ["Nacional", "Sinaloa", "Sonora", "Michoacán", "Jalisco", "Zacatecas"])
with col3:
    ciclo = st.selectbox("CICLO", ["Todos los ciclos", "Otoño-Invierno", "Primavera-Verano", "Perennes"])
with col4:
    # Mapeo a las métricas del diccionario de agente_siacon.py
    metrica = st.selectbox("MÉTRICA", [
        "Producción (t)", 
        "Superficie sembrada (ha)", 
        "Superficie cosechada (ha)", 
        "Superficie siniestrada (ha)",
        "Rendimiento (t/ha)",
        "Valor de la producción ($)"
    ])
with col5:
    vista = st.radio("VISTA temporal", ["Anual (Tendencia)", "Acumulado"], horizontal=True, index=0)

# Unidades 
st.write("<span style='font-size: 14px; font-weight: 600; color: #8b9bb4; text-transform: uppercase;'>Unidades</span>", unsafe_allow_html=True)
unidades = st.radio("UNIDADES", ["Imperial", "Métrico"], horizontal=True, index=1, label_visibility="collapsed")

# Mapeo inverso de la métrica visual a la clave de SIACON
metrica_key = {
    "Producción (t)": "produccion",
    "Superficie sembrada (ha)": "sembrada",
    "Superficie cosechada (ha)": "cosechada",
    "Superficie siniestrada (ha)": "siniestrada",
    "Rendimiento (t/ha)": "rendimiento",
    "Valor de la producción ($)": "valorproduccion"
}[metrica]

st.markdown("---")

# Backend endpoints
API_URL = "https://siacon-api-2m6lhlkauq-uc.a.run.app/consulta"
BASE_FILE_URL = "https://siacon-api-2m6lhlkauq-uc.a.run.app/archivos/"

@st.cache_data(show_spinner=False)
def descargar_binario(url: str):
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    return r.content

if st.button("🚀 Ejecutar Análisis SIACON", type="primary", use_container_width=True):
    
    # Construcción estricta del prompt para disparar generar_reporte del agente
    cobertura_str = "nacional (sin filtrar estado y con mapa_ambito='nacional')" if region == "Nacional" else f"estado='{region}'"
    ciclo_str = "" if ciclo == "Todos los ciclos" else f"ciclo=['{ciclo}'], "
    
    prompt_construido = (
        f"Genera un reporte completo para el cultivo=['{cultivo}'], {ciclo_str}cobertura {cobertura_str}. "
        f"Años del 2022 al 2025. "
        f"Usa la métrica principal '{metrica_key}'. "
        f"Genera mapas (etiqueta_mapa='ambos') para los años 2024 y 2025. "
        f"Devuelve el análisis ejecutivo textual que incluya GDD, Sequía y Siniestralidad."
    )

    with st.spinner("🧠 El agente SIACON está consultando la BD, calculando Sequía/GDD y dibujando mapas..."):
        try:
            respuesta = requests.post(API_URL, json={"pregunta": prompt_construido}, timeout=600)
            datos = respuesta.json()
            
            if datos.get("ok"):
                st.success("✅ ¡Datos obtenidos de la BD SIACON!")
                archivos = datos.get("archivos", [])
                texto_respuesta = datos.get("respuesta", "")
                
                # Layout de resultados
                res_col1, res_col2 = st.columns([1.5, 1])

                with res_col1:
                    # Mostrar las gráficas y mapas (con la paleta verde YlGn)
                    visualizaciones = [f for f in archivos if f.lower().endswith((".jpg", ".png"))]
                    if visualizaciones:
                        st.markdown(f"### 🗺️ Mapas de {metrica.split('(')[0].strip()}")
                        for idx, vis in enumerate(visualizaciones):
                            vis_url = f"{BASE_FILE_URL}{vis}"
                            st.image(vis_url, use_container_width=True)
                            nombre_vis = vis.split("/")[-1]
                            st.markdown(f"👉 **[Descargar Imagen en HD]({vis_url})**")
                    else:
                        st.info("El agente no devolvió archivos de imagen en esta consulta.")

                with res_col2:
                    st.markdown("### 📄 Entregables SIACON")
                    # Archivos Excel y Textos crudos
                    documentos = [f for f in archivos if f.lower().endswith((".xlsx", ".txt"))]
                    for doc in documentos:
                        nombre_doc = doc.split("/")[-1]
                        if ".xlsx" in nombre_doc:
                            st.markdown(f"📊 **[Descargar Excel Completo (Matrices)]({BASE_FILE_URL}{doc})**")
                            st.caption("Incluye Resumen Histórico, Radiografía, Top Municipal y Datos Crudos.")
                        else:
                            st.markdown(f"📄 **[Descargar Reporte en Texto]({BASE_FILE_URL}{doc})**")
                    
                    st.markdown("<br>### 🧠 Análisis Agroclimático", unsafe_allow_html=True)
                    # Extracción del análisis ejecutivo (Sequía, GDD, etc.)
                    if "ANÁLISIS AGROCLIMÁTICO Y ESTRATÉGICO" in texto_respuesta:
                        analisis_limpio = texto_respuesta.split("ANÁLISIS AGROCLIMÁTICO Y ESTRATÉGICO")[-1].strip("=\n ")
                        st.markdown(f'<div class="analisis-box">{analisis_limpio}</div>', unsafe_allow_html=True)
                    else:
                        st.info(texto_respuesta)

            else:
                st.error(f"❌ Error devuelto por el agente: {datos.get('respuesta', 'Desconocido')}")
        except Exception as e:
            st.error(f"❌ Error de conexión al servicio Run: {e}")

st.markdown("<br><p style='color: #64748b; font-size: 11px; text-align: center;'>Datos generados y cruzados con Open-Meteo (GDD) y Monitor de Sequía (D0-D4) por el Agente SIACON NextGen.</p>", unsafe_allow_html=True)