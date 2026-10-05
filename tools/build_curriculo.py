"""Construye catálogo trazable desde tablas originales SEP; no utiliza IA."""
import hashlib
import gzip
import json
from pathlib import Path
import re
import unicodedata
import urllib.request
import pymupdf

CAMPOS=['Lenguajes','Saberes y Pensamiento Científico','Ética, Naturaleza y Sociedades','De lo Humano y lo Comunitario']
def norm(v):return re.sub(r'\s+',' ',''.join(c for c in unicodedata.normalize('NFD',v.lower()) if unicodedata.category(c)!='Mn'))
def limpio(v):return re.sub(r'\s+',' ',re.sub(r'(?<=\w)-\n(?=\w)','',str(v or ''))).strip()

def main():
    records=[];sources=[]
    for fase in (3,4,5):
        url=f'https://educacionbasica.sep.gob.mx/wp-content/uploads/2025/Plan_y_programas_de_estudio_2025/WEB%20FASE%20{fase}-2025.pdf'
        with urllib.request.urlopen(url,timeout=60) as response:
            chunks=[]
            while True:
                chunk=response.read(524288)
                if not chunk:break
                chunks.append(chunk)
            blob=b''.join(chunks)
        pdf=pymupdf.open(stream=blob,filetype='pdf')
        source={'id':f'SEP-F{fase}','titulo':f'Programa Sintético de la Fase {fase}','organismo':'SEP','edicion':'2025','url':url,'sha256':hashlib.sha256(blob).hexdigest(),'uso':'Extractos para consulta educativa no comercial; reconocer la autoría de SEP y conservar la referencia al documento original.'}
        sources.append(source);ultimo={};field=None
        grados={3:(1,2),4:(3,4),5:(5,6)}[fase]
        for page_index,page in enumerate(pdf):
            top=norm(page.get_text()[:350])
            for campo in CAMPOS:
                if norm(campo) in top:field=campo;break
            if not field:continue
            for table in page.find_tables().tables:
                rows=table.extract()
                if table.col_count!=3 or not rows:continue
                header=' '.join(limpio(v) for row in rows[:2] for v in row)
                if 'Contenidos' not in header or 'aprendizaje' not in header:continue
                previous=''
                for row in rows[2:]:
                    content=limpio(row[0]);continuacion=not bool(content)
                    if content:previous=content
                    else:content=previous or ultimo.get(field,'')
                    if not content:continue
                    ultimo[field]=content
                    for column,grade in enumerate(grados,1):
                        pda=limpio(row[column])
                        if not pda:continue
                        key=f'SEP-F{fase}-G{grade}-P{page_index+1}-R{len(records)+1}'
                        records.append({'id':key,'fuente':source['id'],'fase':fase,'grado':grade,'campo':field,'contenido':content,'pda':pda,'pagina_pdf':page_index+1,'continuacion':continuacion})
        print('Fase',fase,'registros acumulados',len(records))
    if len(records)<300:raise RuntimeError('Extracción insuficiente; no publicar un catálogo incompleto sin revisión.')
    output=Path(__file__).resolve().parents[1]/'data'/'curriculo_sep.json'
    output.write_text(json.dumps({'fuentes':sources,'registros':records},ensure_ascii=False,indent=2),encoding='utf-8')
    output.with_suffix('.json.gz').write_bytes(gzip.compress(output.read_bytes(),mtime=0))
    print('Catálogo escrito:',output,'registros',len(records))

if __name__=='__main__':main()
