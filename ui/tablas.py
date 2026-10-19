"""Tabla accesible y paginación explícita sin scripts ni datos ocultos."""
import math
from html import escape
import streamlit as st


def tabla_paginada(frame,key,columnas=None):
    query=st.text_input('Buscar en la tabla',key=key+'_buscar',placeholder='Escribe para filtrar…')
    if st.session_state.get(key+'_filtro_anterior')!=query:
        st.session_state[key+'_pagina']=1;st.session_state[key+'_filtro_anterior']=query
    if query:
        from utils.text import normalizar_texto
        tokens=normalizar_texto(query).split()
        frame=frame.loc[frame.fillna('').astype(str).apply(lambda r:all(t in normalizar_texto(' '.join(r)) for t in tokens),axis=1)]
    c1,c2=st.columns([1,2])
    cantidad=c1.selectbox('Filas por página',[10,25,50],index=1,key=key+'_tamano')
    paginas=max(1,math.ceil(len(frame)/cantidad))
    if st.session_state.get(key+'_pagina',1)>paginas:st.session_state[key+'_pagina']=1
    pagina=c2.number_input('Página',min_value=1,max_value=paginas,step=1,key=key+'_pagina')
    inicio=(int(pagina)-1)*cantidad
    st.caption(f'{len(frame)} resultados · página {pagina} de {paginas}')
    pagina_frame=frame.iloc[inicio:inicio+cantidad].fillna('')
    cabecera=''.join('<th scope="col">'+escape(str(c))+'</th>' for c in pagina_frame.columns)
    filas=''.join('<tr>'+''.join('<td>'+escape(str(v))+'</td>' for v in row)+'</tr>' for row in pagina_frame.itertuples(index=False,name=None))
    if not filas:filas='<tr><td colspan="'+str(max(1,len(pagina_frame.columns)))+'">No hay resultados para esta búsqueda.</td></tr>'
    st.html('<div class="usaer-table-wrap" role="region" aria-label="Resultados de la consulta" tabindex="0"><table class="usaer-data-table"><thead><tr>'+cabecera+'</tr></thead><tbody>'+filas+'</tbody></table></div>')
    seguro=frame.map(lambda v:"'"+v if isinstance(v,str) and v.lstrip().startswith(('=','+','-','@')) else v)
    st.download_button('Descargar resultados de esta consulta',seguro.to_csv(index=False).encode('utf-8-sig'),file_name='consulta.csv',mime='text/csv',key=key+'_csv')
