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
with col_lugar:
    lugar = st.text_input("📍 Estado o Cobertura", placeholder="Ej: Nacional, Sinaloa...")
with col_cultivo:
    cultivo = st.text_input("🌾 Cultivo y Variedad", placeholder="Ej: Maíz grano blanco...")

st.markdown('<div class="siacon-header">2. Parámetros Agrícolas</div>', unsafe_allow_html=True)
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    ciclos = st.multiselect("🌤️ Ciclo", ["Otoño-Invierno", "Primavera-Verano", "Perennes"])
with c2:
    modalidades = st.multiselect("💧 Modalidad", ["Riego", "Temporal"])
with c3:
    anios = st.multiselect("📅 Años a consultar", [str(y) for y in range(2015, 2026)], default=["2018", "2025"])
with c4:
    variables = st.multiselect(
        "📊 Variables a exportar",
        [
            "Superficie sembrada",
            "Superficie cosechada",
            "Superficie siniestrada",
            "Producción",
            "Rendimiento",
            "Valor de la producción",
            "Precio medio rural",
            "Índice de siniestralidad",
        ],
        default=["Producción", "Superficie sembrada"],
    )
with c5:
    nivel = st.selectbox("🌐 Nivel de Agrupación", ["Municipal", "Estatal", "Nacional"])

st.markdown('<div class="siacon-header">3. Módulo de Cartografía (GIS)</div>', unsafe_allow_html=True)
col_map1, col_map2, col_map3 = st.columns([1, 2, 2])
with col_map1:
    generar_mapa = st.checkbox("🗺️ Generar Mapa Comparativo", value=True)
with col_map2:
    anios_mapa = st.multiselect(
        "📅 Años a renderizar",
        [str(y) for y in range(2015, 2026)],
        default=["2022", "2025"],
        disabled=not generar_mapa,
    )
with col_map3:
    tipo_etiqueta = st.selectbox(
        "🏷️ Etiquetas de Ranking",
        ["Ambos (Número y Nombre)", "Solo Nombre", "Solo Número", "Ninguno"],
        disabled=not generar_mapa,
    )

st.markdown("---")
API_URL = "https://siacon-api-2m6lhlkauq-uc.a.run.app/consulta"
BASE_FILE_URL = "https://siacon-api-2m6lhlkauq-uc.a.run.app/archivos/"


@st.cache_data(show_spinner=False)
def descargar_binario(url: str):
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    return r.content


if st.button("🚀 Ejecutar Análisis Multidimensional", type="primary", use_container_width=True):
    if not lugar or not cultivo:
        st.error("⚠️ Llena 'Estado/Cobertura' y 'Cultivo'.")
    elif not variables or not anios:
        st.error("⚠️ Selecciona al menos un Año y una Variable.")
    else:
        etiqueta_final = {
            "Ambos (Número y Nombre)": "ambos",
            "Solo Nombre": "nombre",
            "Solo Número": "numero",
            "Ninguno": "ninguno",
        }[tipo_etiqueta]

        anios_int = sorted([int(a) for a in anios])
        rango_anios_txt = (
            f"del año {anios_int[0]} al {anios_int[-1]}"
            if len(anios_int) >= 2
            else f"del año {anios_int[0]}"
        )

        prompt_construido = (
            f"Genera un reporte de {', '.join(variables).lower()} del {cultivo} "
            f"en cobertura {lugar} a nivel {nivel.lower()}"
        )
        if modalidades:
            prompt_construido += f", modalidad {', '.join(modalidades).lower()}"
        if ciclos:
            prompt_construido += f", ciclo {', '.join(ciclos).lower()}"
        prompt_construido += f" {rango_anios_txt}. Exporta a excel."

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
                    res_col1, res_col2 = st.columns([1.5, 1])

                    with res_col1:
                        mapas = [f for f in archivos if f.lower().endswith((".jpg", ".png"))]
                        if mapas:
                            st.markdown("### 🗺️ Mapas Generados")
                            for idx, mapa in enumerate(mapas):
                                mapa_url = f"{BASE_FILE_URL}{mapa}"
                                nombre_mapa = mapa.split("/")[-1]
                                st.image(mapa_url, use_container_width=True)
                                try:
                                    img_bytes = descargar_binario(mapa_url)
                                    mime_type = "image/png" if nombre_mapa.lower().endswith(".png") else "image/jpeg"
                                    st.download_button(
                                        label=f"🗺️ Descargar Mapa ({nombre_mapa})",
                                        data=img_bytes,
                                        file_name=nombre_mapa,
                                        mime=mime_type,
                                        key=f"dl_map_{idx}_{nombre_mapa}",
                                        use_container_width=True,
                                    )
                                except Exception:
                                    st.markdown(f"👉 **[Abrir / Guardar Mapa ({nombre_mapa})]({mapa_url})**")

                    with res_col2:
                        st.markdown("### 📄 Reporte de Inteligencia")
                        st.info(datos.get("respuesta", "Análisis completado."))
                        documentos = [f for f in archivos if f.lower().endswith((".xlsx", ".txt", ".jpg", ".png"))]
                        if documentos:
                            st.markdown("### 📥 Descargar Entregables")
                            for doc in documentos:
                                nombre_doc = doc.split("/")[-1]
                                icono = "🗺️" if nombre_doc.lower().endswith((".jpg", ".png")) else ("📊" if nombre_doc.lower().endswith(".xlsx") else "📄")
                                st.markdown(f"{icono} **[{nombre_doc}]({BASE_FILE_URL}{doc})**")
                else:
                    st.error(f"❌ Error en el motor: {datos.get('respuesta', 'Desconocido')}")
            except Exception as e:
                st.error(f"❌ Error de conexión: {e}")