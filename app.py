import streamlit as st
import requests

# 1. Configuración de la página
st.set_page_config(
    page_title="Agente SIACON",
    page_icon="🌱",
    layout="centered"
)

# 2. Encabezado y descripción
st.title("🌱 Asistente Agrícola SIACON")
st.markdown("""
Bienvenido al asistente de análisis agrícola. Pregunta por rendimientos, 
superficies o volúmenes de producción a nivel municipal, estatal o nacional.
""")

# 3. Entrada del usuario
pregunta = st.text_area(
    "¿Qué deseas analizar hoy?", 
    placeholder="Ej: Genera un reporte de superficie sembrada de frijol en 2022 y 2025, expórtalo a Excel y genera un mapa..."
)

# URL pública de tu API en Cloud Run
API_URL = "https://siacon-api-2m6lhlkauq-uc.a.run.app/consulta"
BASE_FILE_URL = "https://siacon-api-2m6lhlkauq-uc.a.run.app/archivos/"

# 4. Botón de ejecución
if st.button("Generar Análisis 🚀", type="primary"):
    if not pregunta.strip():
        st.warning("Por favor, escribe una consulta antes de continuar.")
    else:
        # Spinner visual mientras el usuario espera
        with st.spinner("El agente está analizando la base de datos y generando los entregables..."):
            try:
                # Petición a tu API
                respuesta = requests.post(API_URL, json={"pregunta": pregunta})
                datos = respuesta.json()
                
                if datos.get("ok"):
                    st.success("¡Análisis completado!")
                    
                    # Mostrar la respuesta de texto de la IA
                    st.markdown("### Análisis Ejecutivo")
                    st.info(datos["respuesta"])
                    
                    # Separar mapas de documentos
                    archivos = datos.get("archivos", [])
                    mapas = [f for f in archivos if f.endswith(('.jpg', '.png'))]
                    documentos = [f for f in archivos if f.endswith(('.xlsx', '.txt'))]
                    
                    # Renderizar mapas directamente en la pantalla
                    if mapas:
                        st.markdown("### Mapas Generados")
                        for mapa in mapas:
                            st.image(f"{BASE_FILE_URL}{mapa}", use_container_width=True)
                            
                    # Crear botones de descarga para los Excel/Txt
                    if documentos:
                        st.markdown("### Descargas Disponibles")
                        for doc in documentos:
                            nombre_limpio = doc.split("/")[-1]
                            url_descarga = f"{BASE_FILE_URL}{doc}"
                            st.markdown(f"📥 **[{nombre_limpio}]({url_descarga})**")
                            
                else:
                    st.error(f"Ocurrió un error en la consulta: {datos.get('respuesta', 'Desconocido')}")
                    
            except Exception as e:
                st.error(f"Error de conexión con el servidor: {e}")