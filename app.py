# Modificado para agregar el nuevo lote al DataFrame
if lote_seleccionado == 'Otro':
    nuevo_lote = st.text_input('Ingrese el nuevo número de lote:')
else:
    nuevo_lote = lote_seleccionado

# Guardar la selección y datos en el archivo Excel
if st.button('Guardar consulta'):
    if not nuevo_lote:  # Verificar si el nuevo lote está vacío
        st.error("Debe ingresar un número de lote válido.")
    else:
        selected_data = search_results[search_results['numlote'] == nuevo_lote] if lote_seleccionado != 'Otro' else search_results.copy()
        
        # Si el lote es 'Otro', asignar el nuevo lote
        if lote_seleccionado == 'Otro':
            selected_data['numlote'] = nuevo_lote  # Asignar el nuevo lote al DataFrame

        # Asegurarse de que las columnas necesarias estén presentes
        required_columns = ['codart', 'numlote', 'cantidad', 'cod_barras', 'nomart', 'presentacion', 'fechavencelote']
        missing_columns = [col for col in required_columns if col not in selected_data.columns]
        if missing_columns:
            st.error(f"Faltan las siguientes columnas: {', '.join(missing_columns)}")
        else:
            # Si las columnas están presentes, procesar los datos
            selected_data = selected_data[required_columns].copy()
            selected_data['cantidad'] = cantidad

            # Crear archivo Excel en memoria
            consultas_excel = convertir_a_excel(selected_data)

            # Proveer opción de descarga
            st.success("Consulta guardada con éxito!")
            st.download_button(
                label="Descargar Excel con la consulta guardada",
                data=consultas_excel,
                file_name='consulta_guardada.xlsx',
                mime="application/vnd.ms-excel"
            )

