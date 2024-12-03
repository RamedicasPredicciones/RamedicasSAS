import requests
import pandas as pd
import streamlit as st
import io

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

            # Renombrar la columna 'codArt' a 'codart' si es necesario
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

# Función para guardar los datos seleccionados en un archivo Excel en memoria
def convertir_a_excel(df):
    output = io.BytesIO()  # Crea un archivo en memoria
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Consultas")
    output.seek(0)  # Mueve el puntero al inicio del archivo
    return output.getvalue()

# Configuración de la página en Streamlit
st.title("Consulta de Artículos y Lotes")

# Cargar el inventario y los datos completos
inventario_df = cargar_inventario_y_completar()

# Formulario de búsqueda del código de artículo
codigo = st.text_input('Ingrese el código del artículo:')

if codigo:
    # Filtrar el inventario por código de artículo
    search_results = inventario_df[inventario_df['codart'].str.contains(codigo, case=False, na=False)]

    if not search_results.empty:
        # Mostrar los lotes disponibles para el código de artículo ingresado
        lotes = search_results['numlote'].unique().tolist()
        lotes.append('Otro')  # Agregar la opción de "Otro" para escribir un nuevo lote
        lote_seleccionado = st.selectbox('Seleccione un lote', lotes)

        # Si el lote seleccionado es "Otro", permitir escribir uno nuevo
        if lote_seleccionado == 'Otro':
            nuevo_lote = st.text_input('Ingrese el nuevo número de lote:')
        else:
            nuevo_lote = lote_seleccionado

        # Campo para ingresar la cantidad (esto es lo que el usuario ingresa)
        cantidad = st.number_input('Ingrese la cantidad', min_value=1)

        # Guardar la selección y datos en el archivo Excel
        if st.button('Guardar consulta'):
            if not nuevo_lote:  # Verificar si el nuevo lote está vacío
                st.error("Debe ingresar un número de lote válido.")
            else:
                # Comprobar si el lote seleccionado existe en el dataframe
                if nuevo_lote != 'Otro' and nuevo_lote in search_results['numlote'].values:
                    selected_row = search_results[search_results['numlote'] == nuevo_lote].iloc[0]
                elif nuevo_lote == 'Otro' and not search_results.empty:
                    selected_row = search_results.iloc[0]
                else:
                    st.error(f"No se encontró un lote válido para el código '{codigo}'.")
                    selected_row = None

                # Si se encuentra la fila seleccionada, guardar los datos
                if selected_row is not None:
                    # Crear un dataframe con la información ingresada y los datos del inventario
                    consulta_data = {
                        'codart': [codigo],
                        'numlote': [nuevo_lote],  # Usar el lote ingresado por el usuario
                        'cantidad': [cantidad],
                        'cod_barras': [selected_row['cod_barras'] if 'cod_barras' in selected_row else None],
                        'nomart': [selected_row['nomart'] if 'nomart' in selected_row else None],
                        'presentacion': [selected_row['presentacion'] if 'presentacion' in selected_row else None],
                        # Verificar el formato de 'fechavencelote' y convertirlo si es necesario
                        'fechavencelote': [pd.to_datetime(selected_row['fechavencelote'], errors='coerce').strftime('%d/%m/%Y') 
                                           if 'fechavencelote' in selected_row else None]
                    }

                    consulta_df = pd.DataFrame(consulta_data)

                    # Crear archivo Excel en memoria
                    consultas_excel = convertir_a_excel(consulta_df)

                    # Proveer opción de descarga
                    st.success("Consulta guardada con éxito!")
                    st.download_button(
                        label="Descargar Excel con la consulta guardada",
                        data=consultas_excel,
                        file_name='consulta_guardada.xlsx',
                        mime="application/vnd.ms-excel"
                    )
    else:
        st.error("Código de artículo no encontrado en el inventario.")
