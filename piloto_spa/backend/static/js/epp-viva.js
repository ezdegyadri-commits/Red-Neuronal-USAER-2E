/* EPP institucional: edición por área con propuestas revisables. */
function EPPVivaView({ onBack, onOpenAlumno }) {
  const h = React.createElement;
  const {useEffect, useState} = React;
  const [padron, setPadron] = useState([]);
  const [lista, setLista] = useState([]);
  const [seleccion, setSeleccion] = useState('');
  const [ciclo, setCiclo] = useState('2026-2027');
  const [doc, setDoc] = useState(null);
  const [area, setArea] = useState('Aprendizaje');
  const [borrador, setBorrador] = useState(null);
  const [evidencia, setEvidencia] = useState([]);
  const [error, setError] = useState('');
  const [estado, setEstado] = useState('');
  const [ocupado, setOcupado] = useState(false);
  const [cambios, setCambios] = useState(false);
  const [asistente, setAsistente] = useState(false);
  const [campo, setCampo] = useState('');
  const [notas, setNotas] = useState('');
  const [archivo, setArchivo] = useState(null);
  const [propuesta, setPropuesta] = useState(null);
  const caja = 'w-full rounded-lg border border-slate-200 p-2 bg-white text-sm';
  const boton = 'rounded-lg px-3 py-2 text-sm font-semibold bg-slate-100 hover:bg-slate-200 disabled:opacity-50';
  const panel = 'bg-white border border-slate-200 rounded-xl p-4 space-y-3';
  const ruta = id => '/api/epp/' + encodeURIComponent(id);
  const consulta = periodo => '?ciclo=' + encodeURIComponent(periodo);
  const accion = (titulo, onClick, disabled = false, key = titulo) =>
    h('button', {key, type:'button', className:boton, onClick, disabled}, titulo);
  const entrada = (titulo, elemento) =>
    h('label', {key:titulo, className:'block space-y-1 text-sm'}, h('span', null, titulo), elemento);
  const option = (value, label) => h('option', {key:value, value}, label);
  const cargarLista = async () => {
    const [docs, alumnos] = await Promise.all([apiRequest('/api/epp'), apiRequest('/api/alumnos')]);
    setLista(docs);
    setPadron(alumnos);
  };
  useEffect(() => {cargarLista().catch(e => setError(e.message));}, []);
  useEffect(() => {
    if (!cambios) return;
    const advertir = e => {e.preventDefault(); e.returnValue = '';};
    window.addEventListener('beforeunload', advertir);
    return () => window.removeEventListener('beforeunload', advertir);
  }, [cambios]);

  function abrirArea(documento, nombre) {
    setArea(nombre);
    setBorrador(documento.partes[nombre].contenido);
    setCampo('');
    setArchivo(null);
    setNotas('');
    setPropuesta(null);
    setAsistente(false);
  }
  async function abrir(id, periodo) {
    if (!id) return;
    setOcupado(true); setError(''); setEstado('');
    try {
      const documento = await apiRequest(ruta(id) + consulta(periodo));
      setDoc(documento);
      abrirArea(documento, documento.editables[0] || 'Aprendizaje');
      setCambios(false);
      setEvidencia([]);
      apiRequest(ruta(documento.alumno) + '/pruebas').then(setEvidencia)
        .catch(() => setEstado('No se pudo consultar el listado de instrumentos históricos.'));
    } catch (e) {setError(e.message);}
    finally {setOcupado(false);}
  }
  const editar = doc?.editables.includes(area);
  const actualizar = valores => {
    if (!editar) return;
    setBorrador(anterior => ({...anterior,...valores}));
    setCambios(true);
    setEstado('');
  };
  async function guardar(revisada) {
    setOcupado(true); setError('');
    const payload = {area, ciclo:doc.ciclo, revision:doc.revision, campos:borrador.campos, revisada};
    for (const k of ['instrumentos','fecha_aplicacion','sintesis']) payload[k] = borrador[k] || '';
    if (area === 'Conclusión') for (const k of ['nee','bap']) payload[k] = borrador[k] || [];
    try {
      const reciente = await apiRequest(ruta(doc.alumno)+'/apartado', {method:'PUT',body:JSON.stringify(payload)});
      setDoc(reciente); setBorrador(reciente.partes[area].contenido); setCambios(false);
      setEstado(revisada ? 'Revisión guardada' : 'Borrador guardado');
    } catch (e) {setError(e.message);}
    finally {setOcupado(false);}
  }
  async function analizar() {
    setOcupado(true); setError(''); setPropuesta(null);
    try {
      const payload = {area, ciclo:doc.ciclo, campo, notas};
      if (archivo && area !== 'Conclusión') {
        if (archivo.size > 3 * 1024 * 1024) throw new Error('El archivo supera 3 MB.');
        const dataUrl = await new Promise((resolve,reject) => {
          const lector = new FileReader();
          lector.onerror = () => reject(new Error('No se pudo leer el archivo.'));
          lector.onload = () => resolve(lector.result);
          lector.readAsDataURL(archivo);
        });
        payload.archivo_nombre = archivo.name;
        payload.archivo_base64 = dataUrl.split(',', 2)[1];
      }
      setPropuesta(await apiRequest(ruta(doc.alumno)+'/propuesta', {method:'POST',body:JSON.stringify(payload)}));
    } catch (e) {setError(e.message);}
    finally {setOcupado(false);}
  }
  function incorporar() {
    const campos = {...borrador.campos};
    const combinar = (a,b) => !b || String(a || '').includes(b) ? a : [a,b].filter(Boolean).join('\n\n');
    if (area !== 'Conclusión') {
      campos[campo] = combinar(campos[campo], propuesta.texto);
      actualizar({campos});
    } else {
      for (const [k,v] of Object.entries(propuesta.campos)) campos[k] = combinar(campos[k],v);
      const unir = (k,clave) => {
        const actual = [...(borrador[k] || [])];
        const textos = new Set(actual.map(r => (r[clave] || '').trim().toLowerCase()));
        for (const row of propuesta[k] || []) {
          const v = (row[clave] || '').trim().toLowerCase();
          if (v && !textos.has(v)) {actual.push(row); textos.add(v);}
        }
        return actual;
      };
      actualizar({campos,nee:unir('nee','NEE'),bap:unir('bap','Tipo de barrera')});
    }
    setAsistente(false); setPropuesta(null);
  }
  function tabla(nombre, columnas, datos, editable) {
    const cambiar = (i,k,v) => actualizar({[nombre]:datos.map((r,n)=>n===i?{...r,[k]:v}:r)});
    return h('div',{key:nombre,className:'overflow-x-auto space-y-2'},
      h('h3',{className:'font-semibold'}, nombre === 'nee' ? 'Necesidades educativas específicas' :
        nombre === 'bap' ? 'Barreras para el aprendizaje y la participación' : nombre),
      h('table',{className:'w-full text-xs text-left'}, h('thead',null,h('tr',null,
        columnas.map(k=>h('th',{key:k,className:'p-2 min-w-28 bg-slate-50'},k)))),
      h('tbody',null,datos.map((r,i)=>h('tr',{key:i},columnas.map(k=>h('td',{key:k,className:'p-1 align-top whitespace-pre-wrap'},
        editable ? h('textarea',{className:caja,rows:2,'aria-label':k+' fila '+(i+1),value:r[k]||'',disabled:ocupado,
          onChange:e=>cambiar(i,k,e.target.value)}) : String(r[k]||''))))))),
      editable && accion('Agregar fila de '+nombre.toUpperCase(),
        ()=>actualizar({[nombre]:[...datos,Object.fromEntries(columnas.map(k=>[k,'']))]}),ocupado));
  }
  const aviso = error && h('p',{role:'alert',className:'text-red-800 bg-red-50 rounded-lg p-2'},error);
  if (!doc) return h('div',{className:'space-y-4'},
    accion('← Volver',onBack),h('h1',{className:'text-2xl font-bold'},'Evaluación Psicopedagógica'),
    aviso,h('form',{className:panel,onSubmit:e=>{e.preventDefault();abrir(seleccion,ciclo);}},
      entrada('Alumno',h('select',{className:caja,value:seleccion,onChange:e=>setSeleccion(e.target.value)},
        option('','Selecciona un alumno'),padron.map(a=>option(a.id,a.nombre_completo+' · '+a.escuela)))),
      entrada('Ciclo escolar',h('input',{className:caja,required:true,pattern:'20[0-9]{2}-20[0-9]{2}',value:ciclo,onChange:e=>setCiclo(e.target.value)})),
      h('button',{className:boton,disabled:ocupado||!seleccion},'Abrir formato vivo')),
    lista.map(d=>h('article',{key:d.id,className:panel},
      h('strong',null,(d.nombre_alumno||d.alumno)+' · '+d.ciclo),
      accion('Abrir EPP',()=>abrir(d.alumno,d.ciclo),ocupado))));

  const parte = doc.partes[area];
  const resumenTablas = ['historia','familia','evaluaciones'].filter(k=>borrador[k]?.length);
  return h('div',{className:'space-y-4'},
    h('div',{className:panel},
      accion('← Volver a la lista',()=>{setDoc(null); cargarLista().catch(e=>setError(e.message));},cambios||ocupado),
      h('h1',{className:'text-xl font-bold'},'EPP · '+doc.nombre_alumno+' · '+doc.ciclo),
      h('div',{className:'flex flex-wrap gap-2'},Object.keys(doc.partes).map(a=>accion(a,()=>abrirArea(doc,a),ocupado||cambios,a))),
      h('p',{className:'text-sm text-slate-500'},[parte.autor,parte.fecha,parte.contenido.validada?'Área revisada':'Borrador',editar?'':'Lectura'].filter(Boolean).join(' · ')),
      h('div',{className:'flex flex-wrap gap-2'},
        editar && accion(area==='Conclusión'?'Generar conclusión, NEE y BAP':'Asistente de redacción',()=>{setAsistente(!asistente);setPropuesta(null);},ocupado),
        editar && accion('Guardar borrador',()=>guardar(false),!cambios||ocupado),
        editar && accion('Marcar como revisado',()=>guardar(true),ocupado),
        accion('Descargar PDF',()=>descargarArchivoAutenticado(ruta(doc.alumno)+'/pdf'+consulta(doc.ciclo),'EPP.pdf'),cambios||ocupado||doc.revision===null),
        accion('Abrir expediente',()=>onOpenAlumno(doc.alumno),cambios||ocupado)),
      estado&&h('p',{role:'status',className:'text-emerald-800'},estado), aviso),
    asistente && h('section',{className:panel},
      area!=='Conclusión' && [
        entrada('Apartado',h('select',{className:caja,value:campo,onChange:e=>{setCampo(e.target.value);setPropuesta(null);}},
          option('','Selecciona el apartado'),Object.keys(borrador.campos).filter(k=>!borrador.no_requeridos?.[k]).map(k=>option(k,k)))),
        entrada('Archivo con evidencia · PDF, DOCX o TXT',h('input',{className:caja,type:'file',accept:'.pdf,.docx,.txt',
          onChange:e=>{setArchivo(e.target.files[0]||null);setPropuesta(null);}})),
        entrada('Observaciones del especialista',h('textarea',{className:caja,rows:3,maxLength:4000,value:notas,onChange:e=>{setNotas(e.target.value);setPropuesta(null);}}))],
      accion(ocupado?'Analizando…':'Generar propuesta',analizar,ocupado||(area!=='Conclusión'&&(!campo||(!archivo&&!notas.trim())))),
      propuesta && h('div',{className:'space-y-2'},
        propuesta.fuente&&h('p',null,'Fuente · '+propuesta.fuente),
        h('p',{className:'whitespace-pre-wrap'},propuesta.texto || Object.values(propuesta.campos||{}).join('\n')),
        !!propuesta.faltantes?.length&&h('p',null,'Áreas sin hallazgos registrados · '+propuesta.faltantes.join(', ')),
        !!propuesta.nee&&h('p',null,'NEE sustentadas · '+propuesta.nee.map(r=>r.NEE).filter(Boolean).join(' · ')),
        !!propuesta.bap&&h('p',null,'BAP sustentadas · '+propuesta.bap.map(r=>r['Tipo de barrera']).filter(Boolean).join(' · ')),
        accion('Añadir al borrador',incorporar,ocupado))),
    h('section',{className:panel},
      h('h2',{className:'font-bold'},area),
      area!=='Conclusión' && [['instrumentos','Instrumentos'],['fecha_aplicacion','Fecha de aplicación'],['sintesis','Síntesis']].map(([k,l])=>
        entrada(l,h('textarea',{className:caja,rows:2,value:borrador[k]||'',readOnly:!editar||ocupado,onChange:e=>actualizar({[k]:e.target.value})}))),
      Object.entries(borrador.campos).map(([k,v])=>entrada(k,h('textarea',{className:caja,rows:3,value:v,
        readOnly:!editar||ocupado||borrador.no_requeridos?.[k],onChange:e=>actualizar({campos:{...borrador.campos,[k]:e.target.value}})}))),
      area==='Conclusión'&&['nee','bap'].map(k=>tabla(k,doc.columnas[k],borrador[k]||[],editar)),
      resumenTablas.map(k=>h('details',{key:k},h('summary',{className:'font-semibold'},
        {historia:'Historia escolar',familia:'Composición familiar',evaluaciones:'Evaluaciones registradas'}[k]),
        borrador[k].map((r,i)=>h('p',{key:i,className:'whitespace-pre-wrap p-2 border-b'},
          Object.entries(r).filter(([a,v])=>v && typeof v==='string' && !['id','archivo_sha256'].includes(a)).map(([a,v])=>a+' · '+v).join('\n'))))),
      evidencia.length>0&&h('details',null,h('summary',{className:'font-semibold'},'Instrumentos históricos'),
        evidencia.map(p=>h('p',{key:p.id},[p.nombre_prueba,p.area,p.fecha,p.observaciones].filter(Boolean).join(' · '))))));
}
