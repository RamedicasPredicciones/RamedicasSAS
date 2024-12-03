import pandas as pd
import streamlit as st
import io
import requests
import cv2
from streamlit_webrtc import VideoTransformerBase, webrtc_streamer

# Función para cargar los datos desde Google Sheets
@st.cache_data
def cargar_base():
    url = "https://docs.google.com/spreadsheets/d/1Gk-EUifL3fODSc5kJ52gsNsxY9-hC1j4/export?format=xlsx"
    try:
        response = requests.get(url)
        response.raise_for_status()
        base = pd.read_excel(io.BytesIO(response.content), sheet_name="TP's GHG")
        base.columns = base.columns.str.lower().str.strip()
        return base
    except Exception as e:
        st.error(f"Error al cargar la base de datos: {e}")
        return None

# Clase para procesar video y detectar códigos de barras
class BarcodeReader(VideoTransformerBase):
    def transform(self, frame):
        img = frame.to_ndarray(format="bgr24")
        detector = cv2.QRCodeDetector()
        data, _, _ = detector.detectAndDecode(img)
        if data:  # Si se detecta un código de barras
            st.session_state['barcode'] = data
            cv2.putText(img, f"Codigo: {data}", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        return img

# Función para guardar los datos en un archivo Excel
def convertir_a_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Consulta")
    output.seek(0)
    return output

# Configuración de la app
st.title("Consulta Automática de Artículos")

base_df = cargar_base()

if "consultas" not in st.session_state:
    st.session_state.consultas = []

# Activar la cámara para escanear el código de barras
st.subheader("Escanea el código de barras")
webrtc_streamer(
    key="barcode-reader",
    video_transformer_factory=BarcodeReader,
    media_stream_constraints={"video": True, "audio": False}
)

# Detectar y procesar automáticamente el código
if 'barcode' in st.session_state and st.session_state['barcode']:
    codigo = st.session_state['barcode']

    # Buscar automáticamente en la base de datos
    if base_df is not None:
        search_results = base_df[base_df['codarticulo'].str.contains(codigo, case=False, na=False)]
        if not search_results.empty:
            st.success("Código detectado. Detalles del artículo:")
            st.write(search_results.head(1))  # Mostrar el primer resultado

            # Seleccionar lote
            lotes = search_results['lote'].dropna().unique().tolist()
            lotes.append('Otro')
            lote_seleccionado = st.selectbox('Seleccione un lote', lotes)

            # Campo para un nuevo lote si es necesario
            if lote_seleccionado == 'Otro':
                nuevo_lote = st.text_input('Ingrese el nuevo número de lote:')
            else:
                nuevo_lote = lote_seleccionado

            # Campo opcional para la cantidad
            cantidad = st.text_input('Ingrese la cantidad (opcional):')

            # Botón para guardar
            if st.button("Guardar entrada"):
                if not nuevo_lote:
                    st.error("Debe ingresar un número de lote válido.")
                else:
                    consulta_data = {
                        'codarticulo': codigo,
                        'articulo': search_results.iloc[0]['articulo'] if 'articulo' in search_results.columns else None,
                        'lote': nuevo_lote,
                        'codbarras': search_results.iloc[0]['codbarras'] if 'codbarras' in search_results.columns else None,
                        'presentacion': search_results.iloc[0]['presentacion'] if 'presentacion' in search_results.columns else None,
                        'vencimiento': search_results.iloc[0]['vencimiento'] if 'vencimiento' in search_results.columns else None,
                        'cantidad': cantidad if cantidad else None
                    }
                    st.session_state.consultas.append(consulta_data)
                    st.success("Entrada guardada correctamente.")
        else:
            st.error("Código no encontrado en la base.")
    else:
        st.error("Error al cargar la base de datos.")

# Mostrar las entradas guardadas
if st.session_state.consultas:
    st.write("Entradas guardadas:")
    consultas_df = pd.DataFrame(st.session_state.consultas)
    st.dataframe(consultas_df)

    # Botón para descargar las consultas
    consultas_excel = convertir_a_excel(consultas_df)
    st.download_button(
        label="Descargar Excel",
        data=consultas_excel,
        file_name="consultas_guardadas.xlsx",
        mime="application/vnd.ms-excel"
    )
else:
    st.warning("No hay entradas guardadas.")
