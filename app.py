import streamlit as st
import requests

# Configuración de página simulando el modo oscuro
st.set_page_config(page_title="Inteligencia Geoespacial SIACON", page_icon="🌱", layout="wide")

# Estilos CSS para replicar el diseño oscuro
st.markdown("""
<style>
    .stApp { background-color: #0b1325; color: #e2e8f0; }
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown { color: #e2e8f0 !important; }
    .main-title { color: #ffffff !important; font-size: 26px; font-weight: 700; margin-bottom: 2px; }
    .subtitle { color: #8b9bb4 !important; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 25px; }
    .nav-pills { font-size: 14px; color: #8b9bb4; margin-bottom: 30px; display: flex; gap: 20px; }
    .nav-pill-active { background-color: #d4af37; color: #000; padding: 4px 16px; border-radius: 20px; font-weight: 600; }
    .stSelectbox > div > div, .stMultiSelect > div > div, .stTextInput > div > div { background-color: #1e293b; color: white; border: 1px solid #334155; }
    .analisis-box { background-color: #1e293b; padding: 20px; border-radius: 8px; border-left: 5px solid #2E7D32; margin-top: 10px; font-size: 15px;}
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

st.markdown('<div class="main-title">🌱 Inteligencia Geoespacial SIACON</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Generador de Reportes Agroclimáticos, Estadísticos y Cartográficos.</div>', unsafe_allow_html=True)

# 1. Primera fila de filtros (Estructura de 5 columnas basada en la imagen)
st.markdown("<h4 style='color: #d4af37 !important;'>1. Definición del Objetivo</h4>", unsafe_allow_html=True)
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    cultivo = st.text_input("🌾 CULTIVO Y VARIEDAD", placeholder="Ej: Maíz grano blanco...")
with c2:
    lugar = st.text_input("📍 ESTADO O COBERTURA", placeholder="Ej: Nacional, Sinaloa...")
with c3:
    ciclos = st.multiselect("🌤️ CICLO", ["Otoño-Invierno", "Primavera-Verano", "Perennes"])
with c4:
    variables = st.multiselect(
        "📊 VARIABLES",
        [
            "Superficie sembrada", "Superficie cosechada", "Superficie siniestrada",
            "Producción", "Rendimiento", "Valor de la producción", "Precio medio rural",
            "Índice de siniestralidad"
        ],
        default=["Producción", "Superficie sembrada"]
    )
with c5:
    anios = st.multiselect("📅 AÑOS A CONSULTAR", [str(y) for y in range(2015, 2026)], default=["2018", "2025"])

# 2. Segunda fila de parámetros
st.markdown("<h4 style='color: #d4af37 !important; margin-top: 20px;'>2. Parámetros y Cartografía</h4>", unsafe_allow_html=True)
c6, c7, c8, c9, c10 = st.columns(5)
with c6:
    modalidades = st.multiselect("💧 MODALIDAD", ["Riego", "Temporal"])
with c7:
    nivel = st.selectbox("🌐 NIVEL", ["Municipal", "Estatal", "Nacional"])
with c8:
    st.write("") # Espaciador para alinear el checkbox
    generar_mapa = st.checkbox("🗺️ GENERAR MAPA", value=True)
with c9:
    anios_mapa = st.multiselect(
        "📅 AÑOS MAPA", [str(y) for y in range(2015, 2026)],
        default=["2022", "2025"], disabled=not generar_mapa
    )
with c10:
    tipo_etiqueta = st.selectbox(
        "🏷️ ETIQUETAS",
        ["Ambos (Número y Nombre)", "Solo Nombre", "Solo Número", "Ninguno"],
        disabled=not generar_mapa
    )

st.markdown("---")
API_URL = "https://siacon-api-2m6lhlkauq-uc.a.run.app/consulta"
BASE_FILE_URL = "https://siacon-api-2m6lhlkauq-uc.a.run.app/archivos/"

if st.button("🚀 Ejecutar Análisis Multidimensional", type="primary", use_container_width=True):
    if not lugar or not cultivo:
        st.error("⚠️ Llena 'Estado/Cobertura' y 'Cultivo'.")
    elif not variables or not anios:
        st.error("⚠️ Selecciona al menos un Año y una Variable.")
    else:
        # Traducción de etiquetas
        etiqueta_final = {
            "Ambos (Número y Nombre)": "ambos", "Solo Nombre": "nombre",
            "Solo Número": "numero", "Ninguno": "ninguno"
        }[tipo_etiqueta]

        anios_int = sorted([int(a) for a in anios])
        rango_anios_txt = (
            f"del año {anios_int[0]} al {anios_int[-1]}" if len(anios_int) >= 2 else f"del año {anios_int[0]}"
        )

        # Construcción del prompt usando las variables originales 
        prompt_construido = (
            f"Genera un reporte de {', '.join(variables).lower()} del {cultivo} "
            f"en cobertura {lugar} a nivel {nivel.lower()}"
        )
        if modalidades:
            prompt_construido += f", modalidad {', '.join(modalidades).lower()}"
        if ciclos:
            prompt_construido += f", ciclo {', '.join(ciclos).lower()}"
        prompt_construido += f" {rango_anios_txt}. Exporta a excel e incluye la generación de gráficas correspondientes."

        if generar_mapa and anios_mapa:
            prompt_construido += (
                f" Además genera un mapa comparativo por municipio de producción de los años {', '.join(anios_mapa)}, "
                f"configura ranking_anios en [{', '.join(anios_mapa)}] y etiqueta_mapa exactamente como '{etiqueta_final}'."
            )
        prompt_construido += " INSTRUCCIÓN ESTRICTA: Transcribe palabra por palabra el 'Análisis Agroclimático' generado."

        with st.spinner("🧠 Procesando datos, cruzando sequía, siniestralidad, GDD y dibujando mapas..."):
            try:
                respuesta = requests.post(API_URL, json={"pregunta": prompt_construido}, timeout=600)
                datos = respuesta.json()
                
                if datos.get("ok"):
                    st.success("✅ ¡Análisis Completado!")
                    archivos = datos.get("archivos", [])
                    texto_respuesta = datos.get("respuesta", "Análisis completado.")
                    
                    # Separar archivos: Gráficas vs Mapas vs Documentos
                    documentos = [f for f in archivos if f.lower().endswith((".xlsx", ".txt"))]
                    imagenes = [f for f in archivos if f.lower().endswith((".jpg", ".png"))]
                    
                    # El backend nombra los mapas iniciando con "Mapa_" 
                    imagenes_mapas = [img for img in imagenes if "mapa" in img.lower()]
                    imagenes_graficas = [img for img in imagenes if "mapa" not in img.lower()]

                    # ==========================================
                    # PRIORIDAD 1 y 2: DATOS, INTELIGENCIA Y GRÁFICAS
                    # ==========================================
                    res_col1, res_col2 = st.columns([1, 1.2])

                    with res_col1:
                        st.markdown("### 📥 Descargar Entregables")
                        for doc in documentos:
                            nombre_doc = doc.split("/")[-1]
                            icono = "📊" if nombre_doc.lower().endswith(".xlsx") else "📄"
                            st.markdown(f"{icono} **[{nombre_doc}]({BASE_FILE_URL}{doc})**")
                            
                        # Si hay gráficas (no mapas), se muestran aquí arriba
                        if imagenes_graficas:
                            st.markdown("### 📈 Gráficas Analíticas")
                            for graf in imagenes_graficas:
                                st.image(f"{BASE_FILE_URL}{graf}", use_container_width=True)

                    with res_col2:
                        st.markdown("### 🧠 Reporte de Inteligencia")
                        if "ANÁLISIS AGROCLIMÁTICO Y ESTRATÉGICO" in texto_respuesta:
                            analisis_limpio = texto_respuesta.split("ANÁLISIS AGROCLIMÁTICO Y ESTRATÉGICO")[-1].strip("=\n ")
                            st.markdown(f'<div class="analisis-box">{analisis_limpio}</div>', unsafe_allow_html=True)
                        else:
                            st.info(texto_respuesta)

                    # ==========================================
                    # PRIORIDAD 3: MAPAS HASTA EL FINAL
                    # ==========================================
                    if imagenes_mapas:
                        st.markdown("---")
                        st.markdown("<h2 style='text-align: center;'>🗺️ Cartografía Comparativa</h2>", unsafe_allow_html=True)
                        for mapa in imagenes_mapas:
                            mapa_url = f"{BASE_FILE_URL}{mapa}"
                            st.image(mapa_url, use_container_width=True)
                            st.markdown(f"<div style='text-align: center;'><a href='{mapa_url}' target='_blank'>⬇️ Abrir / Descargar Mapa en Alta Resolución</a></div>", unsafe_allow_html=True)

                else:
                    st.error(f"❌ Error en el motor: {datos.get('respuesta', 'Desconocido')}")
            except Exception as e:
                st.error(f"❌ Error de conexión: {e}")