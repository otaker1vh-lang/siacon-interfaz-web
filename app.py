import streamlit as st
import requests

st.set_page_config(page_title="SIACON NextGen", page_icon="🌱", layout="wide")

st.markdown("""
<style>
    .siacon-header {
        background-color: #1A4D2E; color: white; padding: 8px 15px;
        border-radius: 6px; font-size: 18px; font-weight: 600;
        margin-top: 20px; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .main-title { color: #1A4D2E; font-weight: 800; margin-bottom: -10px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-title">🌱 Inteligencia Geoespacial SIACON</h1>', unsafe_allow_html=True)
st.markdown("Generador de Reportes Agroclimáticos, Estadísticos y Cartográficos.")

st.markdown('<div class="siacon-header">1. Definición del Objetivo</div>', unsafe_allow_html=True)
col_lugar, col_cultivo = st.columns(2)
with col_lugar: lugar = st.text_input("📍 Estado o Cobertura", placeholder="Ej: Nacional, Sinaloa...")
with col_cultivo: cultivo = st.text_input("🌾 Cultivo y Variedad", placeholder="Ej: Maíz grano blanco...")

st.markdown('<div class="siacon-header">2. Parámetros Agrícolas</div>', unsafe_allow_html=True)
c1, c2, c3, c4, c5 = st.columns(5)
with c1: ciclos = st.multiselect("🌤️ Ciclo", ["Otoño-Invierno", "Primavera-Verano", "Perennes"])
with c2: modalidades = st.multiselect("💧 Modalidad", ["Riego", "Temporal"])
with c3: anios = st.multiselect("📅 Años a consultar", [str(y) for y in range(2015, 2026)], default=["2018", "2025"])
with c4: variables = st.multiselect("📊 Variables a exportar", ["Superficie sembrada", "Superficie cosechada", "Superficie siniestrada", "Producción", "Rendimiento", "Valor de la producción", "Precio medio rural"], default=["Producción", "Superficie sembrada"])
with c5: nivel = st.selectbox("🌐 Nivel de Agrupación", ["Municipal", "Estatal", "Nacional"])

st.markdown('<div class="siacon-header">3. Módulo de Cartografía (GIS)</div>', unsafe_allow_html=True)
col_map1, col_map2, col_map3 = st.columns([1, 2, 2])
with col_map1: generar_mapa = st.checkbox("🗺️ Generar Mapa Comparativo", value=True)
with col_map2: anios_mapa = st.multiselect("📅 Años a renderizar", [str(y) for y in range(2015, 2026)], default=["2022", "2025"], disabled=not generar_mapa)
with col_map3: tipo_etiqueta = st.selectbox("🏷️ Etiquetas de Ranking", ["Ambos (Número y Nombre)", "Solo Nombre", "Solo Número", "Ninguno"], disabled=not generar_mapa)

st.markdown("---")
API_URL = "https://siacon-api-2m6lhlkauq-uc.a.run.app/consulta"
BASE_FILE_URL = "https://siacon-api-2m6lhlkauq-uc.a.run.app/archivos/"

if st.button("🚀 Ejecutar Análisis Multidimensional", type="primary", use_container_width=True):
    if not lugar or not cultivo: st.error("⚠️ Llena 'Estado/Cobertura' y 'Cultivo'.")
    elif not variables or not anios: st.error("⚠️ Selecciona un Año y Variable.")
    else:
        etiqueta_final = {"Ambos (Número y Nombre)": "ambos", "Solo Nombre": "nombre", "Solo Número": "numero", "Ninguno": "ninguno"}[tipo_etiqueta]
        prompt_construido = f"Genera un reporte de {', '.join(variables).lower()} del {cultivo} en {lugar} a nivel {nivel.lower()}"
        if modalidades: prompt_construido += f", modalidad {', '.join(modalidades).lower()}"
        if ciclos: prompt_construido += f", ciclo {', '.join(ciclos).lower()}"
        prompt_construido += f" de los años {', '.join(anios)}. Exporta a excel."
        if generar_mapa and anios_mapa: prompt_construido += f" Además genera un mapa comparativo por municipio de producción de los años {', '.join(anios_mapa)}, configura la etiqueta_mapa exactamente como '{etiqueta_final}'."
        prompt_construido += " INSTRUCCIÓN ESTRICTA: Transcribe palabra por palabra el 'Análisis Agroclimático' generado."

        with st.spinner("🧠 Procesando datos, cruzando sequía, siniestralidad, GDD y dibujando mapas..."):
            try:
                respuesta = requests.post(API_URL, json={"pregunta": prompt_construido}, timeout=120)
                datos = respuesta.json()
                if datos.get("ok"):
                    st.success("✅ ¡Análisis Completado!")
                    archivos = datos.get("archivos", [])
                    res_col1, res_col2 = st.columns([1.5, 1])
                    with res_col1:
                        mapas = [f for f in archivos if f.endswith(('.jpg', '.png'))]
                        if mapas:
                            st.markdown("### 🗺️ Mapas Generados")
                            for mapa in mapas: st.image(f"{BASE_FILE_URL}{mapa}", use_container_width=True)
                    with res_col2:
                        st.markdown("### 📄 Reporte de Inteligencia")
                        # 🟢 LECTURA DIRECTA DE LA RESPUESTA (Sin descargas problemáticas)
                        st.info(datos.get("respuesta", "Análisis completado."))
                        documentos = [f for f in archivos if f.endswith(('.xlsx', '.txt'))]
                        if documentos:
                            st.markdown("### 📥 Descargar Entregables")
                            for doc in documentos: st.markdown(f"👉 **[{doc.split('/')[-1]}]({BASE_FILE_URL}{doc})**")
                else: st.error(f"❌ Error en el motor: {datos.get('respuesta', 'Desconocido')}")
            except Exception as e: st.error(f"❌ Error de conexión: {e}")