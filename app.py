import streamlit as st
import requests

# 1. Configuración de la página (Modo Amplio para parecer Dashboard)
st.set_page_config(
    page_title="SIACON NextGen",
    page_icon="🌱",
    layout="wide"
)

# --- ESTILOS CSS PERSONALIZADOS (Estética SIACON Moderna) ---
st.markdown("""
<style>
    .siacon-header {
        background-color: #1A4D2E; /* Verde institucional */
        color: white;
        padding: 8px 15px;
        border-radius: 6px;
        font-size: 18px;
        font-weight: 600;
        margin-top: 20px;
        margin-bottom: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .main-title {
        color: #1A4D2E;
        font-weight: 800;
        margin-bottom: -10px;
    }
</style>
""", unsafe_allow_html=True)

# 2. Encabezado
st.markdown('<h1 class="main-title">🌱 Inteligencia Geoespacial SIACON</h1>', unsafe_allow_html=True)
st.markdown("Generador de Reportes Agroclimáticos, Estadísticos y Cartográficos.")

# ==========================================
# SECCIÓN 1: BÚSQUEDA PRINCIPAL
# ==========================================
st.markdown('<div class="siacon-header">1. Definición del Objetivo</div>', unsafe_allow_html=True)
col_lugar, col_cultivo = st.columns(2)

with col_lugar:
    lugar = st.text_input("📍 Estado o Cobertura", placeholder="Ej: Nacional, Sinaloa, Michoacán y Oaxaca...")
with col_cultivo:
    cultivo = st.text_input("🌾 Cultivo y Variedad", placeholder="Ej: Maíz grano blanco, Ajonjolí, Limón persa...")

# ==========================================
# SECCIÓN 2: FILTROS ESTADÍSTICOS (5 Contenedores)
# ==========================================
st.markdown('<div class="siacon-header">2. Parámetros Agrícolas</div>', unsafe_allow_html=True)

c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    ciclos = st.multiselect("🌤️ Ciclo", ["Otoño-Invierno", "Primavera-Verano", "Perennes"])
with c2:
    modalidades = st.multiselect("💧 Modalidad", ["Riego", "Temporal"])
with c3:
    lista_anios = [str(y) for y in range(2015, 2026)]
    anios = st.multiselect("📅 Años a consultar", lista_anios, default=["2018", "2025"])
with c4:
    variables = st.multiselect(
        "📊 Variables a exportar", 
        ["Superficie sembrada", "Superficie cosechada", "Superficie siniestrada", 
         "Producción", "Rendimiento", "Valor de la producción", "Precio medio rural"],
        default=["Producción", "Superficie sembrada"]
    )
with c5:
    nivel = st.selectbox("🌐 Nivel de Agrupación", ["Municipal", "Estatal", "Nacional"])

# ==========================================
# SECCIÓN 3: CARTOGRAFÍA Y ETIQUETAS
# ==========================================
st.markdown('<div class="siacon-header">3. Módulo de Cartografía (GIS)</div>', unsafe_allow_html=True)

col_map1, col_map2, col_map3 = st.columns([1, 2, 2])
with col_map1:
    generar_mapa = st.checkbox("🗺️ Generar Mapa Comparativo", value=True)
with col_map2:
    anios_mapa = st.multiselect(
        "📅 Años a renderizar en el mapa (Máx 3)", 
        lista_anios, 
        default=["2022", "2025"], 
        disabled=not generar_mapa
    )
with col_map3:
    tipo_etiqueta = st.selectbox(
        "🏷️ Etiquetas de Ranking en el Mapa",
        ["Ambos (Número y Nombre)", "Solo Nombre", "Solo Número", "Ninguno"],
        disabled=not generar_mapa
    )

st.markdown("---")

# URLs de tu API en Cloud Run
API_URL = "https://siacon-api-2m6lhlkauq-uc.a.run.app/consulta"
BASE_FILE_URL = "https://siacon-api-2m6lhlkauq-uc.a.run.app/archivos/"

# ==========================================
# CONSTRUCCIÓN DEL PROMPT Y EJECUCIÓN
# ==========================================
if st.button("🚀 Ejecutar Análisis Multidimensional", type="primary", use_container_width=True):
    
    if not lugar or not cultivo:
        st.error("⚠️ Por favor, llena los campos de 'Estado/Cobertura' y 'Cultivo'.")
    elif not variables or not anios:
        st.error("⚠️ Debes seleccionar al menos un Año y una Variable.")
    else:
        # 1. Diccionario para traducir la etiqueta visual a la palabra que espera el backend
        mapa_etiquetas = {
            "Ambos (Número y Nombre)": "ambos",
            "Solo Nombre": "nombre",
            "Solo Número": "numero",
            "Ninguno": "ninguno"
        }
        etiqueta_final = mapa_etiquetas[tipo_etiqueta]

        # 2. Armar la consulta base
        prompt_construido = f"Genera un reporte de {', '.join(variables).lower()} del {cultivo} en {lugar} a nivel {nivel.lower()}"
        if modalidades: prompt_construido += f", modalidad {', '.join(modalidades).lower()}"
        if ciclos: prompt_construido += f", ciclo {', '.join(ciclos).lower()}"
        prompt_construido += f" de los años {', '.join(anios)}. Exporta a excel."
        
        # 3. Instrucción del mapa
        if generar_mapa and anios_mapa:
            prompt_construido += f" Además genera un mapa comparativo por municipio de producción de los años {', '.join(anios_mapa)}, configura la etiqueta_mapa exactamente como '{etiqueta_final}'."

        # 4. TRUCO DE INGENIERÍA DE PROMPTS: Obligar a la IA a imprimir el clima
        prompt_construido += " INSTRUCCIÓN ESTRICTA: Al darme la respuesta final, es OBLIGATORIO que transcribas palabra por palabra todo el 'Análisis Agroclimático', 'Sequía', 'GDD' y la 'Tabla Resumen Súper Fácil' que genere la herramienta."

        with st.expander("👁️ Ver instrucción técnica que se envía al cerebro (Backend)", expanded=False):
            st.code(prompt_construido, language="text")

        # --- ENVÍO A LA API ---
        with st.spinner("🧠 El agente está procesando la base de datos, cruzando sequía, GDD y dibujando mapas. Esto tomará unos segundos..."):
            try:
                respuesta = requests.post(API_URL, json={"pregunta": prompt_construido})
                datos = respuesta.json()
                
                if datos.get("ok"):
                    st.success("✅ ¡Análisis Completado Exitosamente!")
                    
                    archivos = datos.get("archivos", [])
                    mapas = [f for f in archivos if f.endswith(('.jpg', '.png'))]
                    documentos = [f for f in archivos if f.endswith(('.xlsx', '.txt'))]
                    
                    res_col1, res_col2 = st.columns([1.5, 1])
                    
                    with res_col1:
                        if mapas:
                            st.markdown("### 🗺️ Mapas Generados")
                            for mapa in mapas:
                                st.image(f"{BASE_FILE_URL}{mapa}", use_container_width=True)
                    
                    with res_col2:
                        st.markdown("### 📄 Reporte de Inteligencia")
                        # Imprimir la respuesta que ahora sí vendrá completa
                        st.info(datos["respuesta"])
                        
                        if documentos:
                            st.markdown("### 📥 Descargar Entregables")
                            for doc in documentos:
                                nombre_limpio = doc.split("/")[-1]
                                url_descarga = f"{BASE_FILE_URL}{doc}"
                                st.markdown(f"👉 **[{nombre_limpio}]({url_descarga})**")
                                
                else:
                    st.error(f"❌ Ocurrió un error en el motor: {datos.get('respuesta', 'Error Desconocido')}")
                    
            except Exception as e:
                st.error(f"❌ Error de conexión con Cloud Run: {e}")