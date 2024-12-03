import requests
import pandas as pd
import streamlit as st

# Función para cargar y unir los datos del inventario y el maestro de moléculas
@st.cache_data
def cargar_inventario_y_completar():
    url_inventario = "https://apkit.ramedicas.com/api/items/ws-batchsunits?token=3f8857af327d7f1adb005b81a12743bc17fef5c48f228103198100d4b032f556"
    url_maestro_moleculas = "https://docs.google.com/spreadsheets/d/19myWtMrvsor2P_XHiifPgn8YKdTWE39O/export?format=xlsx"
    
    try:
        # Obtener los datos del inventario
        response = requests.get(url_inventario, verify=False)
        if response.status_code == 200:
            data_inventario = response.json()
            inventario_df = pd.DataFrame(data_inventario)
            inventario_df.columns = inventario_df.columns.str.lower().str.strip()

            # Renombrar la columna 'codArt' a 'codart' si no está
            if 'codart' not in inventario_df.columns and 'codart' in inventario_df.columns.str.lower():
                inventario_df.rename(columns={'codArt': 'codart'}, inplace=True)

            # Obtener el archivo maestro de moléculas
            response_maestro = requests.get(url_maestro_moleculas, verify=False)
            if response_maestro.status_code == 200:
                maestro_moleculas = pd.read_excel(response_maestro.content)
                maestro_moleculas.columns = maestro_moleculas.columns.str.lower().str.strip()

                # Unir la base de inventario con el maestro para incluir 'cod_barras'
                inventario_df = inventario_df.merge(
                    maestro_moleculas[['codart', 'cod_barras']], 
                    on='codart', 
                    how='left'
                )
                return inventario_df
            else:
                print(f"Error al obtener el archivo maestro de moléculas: {response_maestro.status_code}")
                return None
        else:
            print(f"Error al obtener datos de la API: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error en la conexión con la API: {e}")
        return None

# Función para guardar los datos seleccionados en un archivo Excel
def save_to_excel(data, file_name='consultas.xlsx'):
    try:
        existing_data = pd.read_excel(file_name)
        combined_data = pd.concat([existing_data, data], ignore_index=True)
        combined_data.to_excel(file_name, index=False)
    except FileNotFoundError:
        data.to_excel(file_name, index=False)

# Configuración de la página en Streamlit
st.title("Consulta de Artículos y Lotes")

# Cargar el inventario y los datos completos
inventario_df = cargar_inventario_y_completar()

# Verificar si las columnas necesarias están en el inventario
required_columns = ['codart', 'numlote', 'cantidad', 'cod_barras', 'nomart', 'presentacion', 'fechavencelote']
missing_columns = [col for col in required_columns if col not in inventario_df.columns]
if missing_columns:
    st.error(f"Faltan las siguientes columnas en el inventario: {', '.join(missing_columns)}")
else:
    # Formulario de búsqueda del código de artículo
    codigo = st.text_input('Ingrese el código del artículo:')

    if codigo:
        # Filtrar el inventario por código de artículo
        search_results = inventario_df[inventario_df['codart'].str.contains(codigo, case=False, na=False)]

        if not search_results.empty:
            # Mostrar los lotes disponibles para el código de artículo ingresado
            lotes = search_results['numlote'].unique().tolist()

            # Añadir una opción para ingresar un nuevo lote
            lotes.append('Otro')

            lote_seleccionado = st.selectbox('Seleccione un lote', lotes)

            # Si el lote seleccionado es 'Otro', permitir ingresar un nuevo número de lote
            if lote_seleccionado == 'Otro':
                nuevo_lote = st.text_input('Ingrese el nuevo número de lote:')
            else:
                nuevo_lote = lote_seleccionado

            # Campo para ingresar la cantidad
            cantidad = st.number_input('Ingrese la cantidad', min_value=1)

            # Guardar la selección y datos en el archivo Excel
            if st.button('Guardar consulta'):
                # Filtrar los datos por el lote seleccionado
                selected_data = search_results[search_results['numlote'] == nuevo_lote]
                selected_data = selected_data[['codart', 'numlote', 'cantidad', 'cod_barras', 'nomart', 'presentacion', 'fechavencelote']].copy()
                selected_data['cantidad'] = cantidad

                # Guardar el archivo
                save_to_excel(selected_data)
                st.success("Consulta guardada con éxito!")

        else:
            st.error("Código de artículo no encontrado en el inventario.")

    # Opción para descargar el archivo con todas las consultas realizadas
    st.download_button(
        label="Descargar Excel con todas las consultas",
        data=open('consultas.xlsx', 'rb').read(),
        file_name='consultas.xlsx',
        mime="application/vnd.ms-excel"
    )
