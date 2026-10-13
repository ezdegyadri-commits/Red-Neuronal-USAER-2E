// PostgreSQL real embebido (WASM), sin servicios externos ni datos educativos.
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
const modulePath=process.env.PGLITE_TEST_MODULE;
if (!modulePath) throw Error('Indica PGLITE_TEST_MODULE con el paquete de pruebas, no credenciales');
const {PGlite}=await import(pathToFileURL(resolve(modulePath)).href);
const db=new PGlite();await db.waitReady;
await db.exec('create role anon;create role authenticated;create role service_role;');
const sql=await readFile(new URL('../deployment/coordinacion_postgres.sql',import.meta.url),'utf8');
await db.exec(sql);await db.exec(sql); // Instalación idempotente, no borrar tablas.
const token=n=>n.toString(16).padStart(32,'0');
const key='a'.repeat(64),digest='b'.repeat(64),firma='c'.repeat(64),revision='d'.repeat(32);
const operar=async (accion,params={})=>{
 const p={clave:'',token:'',revision:'',digest:'',firma:'',tipo:'',...params};
 const r=await db.query('select public.usaer_coord_operar($1,$2,$3,$4,$5,$6,$7,$8) as r',['prueba',accion,p.clave,p.token,p.revision,p.digest,p.firma,p.tipo]);
 return r.rows[0].r;
};
const resultados=await Promise.all(Array.from({length:20},(_,i)=>operar('ADQUIRIR',{clave:key,token:token(i+1)})));
assert.equal(resultados.filter(r=>r.ok).length,1);
const propietario=(await db.query('select token from usaer_coord.operaciones')).rows[0].token;
assert.equal((await operar('LIBERAR',{clave:key,token:token(99)})).ok,false);
assert.equal((await operar('INICIAR',{clave:key,token:propietario,revision,digest,firma})).ok,true);
await db.exec("update usaer_coord.operaciones set creado=clock_timestamp()-interval '1 day'");
assert.equal((await operar('ADQUIRIR',{clave:key,token:token(99)})).ok,false);
assert.equal((await operar('RECUPERAR',{clave:key,token:propietario,revision,digest:firma})).ok,false);
assert.equal((await operar('RECUPERAR',{clave:key,token:propietario,revision,digest})).ok,true);
assert.equal((await operar('ADQUIRIR',{clave:key,token:token(98)})).ok,true);
await db.exec("update usaer_coord.operaciones set creado=clock_timestamp()-interval '3 minutes'");
assert.equal((await operar('ADQUIRIR',{clave:key,token:token(99)})).ok,true);
assert.equal((await operar('INICIAR',{clave:key,token:token(98),revision,digest,firma})).ok,false);
assert.equal((await operar('LIBERAR',{clave:key,token:token(98)})).ok,false);
const distintos=await Promise.all(Array.from({length:20},(_,i)=>operar('ADQUIRIR',{clave:(i+2).toString(16).padStart(64,'0'),token:token(i+1)})));
assert.equal(distintos.filter(r=>r.ok).length,20);
const cuotas=await Promise.all(Array.from({length:80},()=>operar('PRESUPUESTO',{tipo:'escritura'})));
assert.equal(cuotas.filter(r=>r.espera===0).length,45);
assert.equal(cuotas.filter(r=>r.espera>0).length,35);
assert.equal((await operar('PRESUPUESTO',{tipo:'lectura'})).espera,0);
await db.exec("update usaer_coord.cupos set eventos=array[clock_timestamp()-interval '61 seconds'] where tipo='escritura'");
assert.equal((await operar('PRESUPUESTO',{tipo:'escritura'})).espera,0);
for (const role of ['anon','authenticated']) {
 const p=(await db.query("select has_function_privilege($1,'public.usaer_coord_operar(text,text,text,text,text,text,text,text)','execute') as ok",[role])).rows[0];
 assert.equal(p.ok,false);
}
assert.equal((await db.query("select has_function_privilege('service_role','public.usaer_coord_operar(text,text,text,text,text,text,text,text)','execute') as ok")).rows[0].ok,true);
assert.equal((await db.query("select count(*)::int as n from pg_class where relnamespace='usaer_coord'::regnamespace and relrowsecurity")).rows[0].n,2);
const cols=(await db.query("select column_name from information_schema.columns where table_schema='usaer_coord'")).rows.map(r=>r.column_name);
assert.ok(!cols.some(c=>/alumno|nombre|curp|contenido|expediente|evaluacion/.test(c)));
await db.close();
console.log('SQL PostgreSQL: instalación idempotente, 20 solicitudes competidoras, 20 documentos independientes, 80 reservas/45 aceptadas, recuperación, fencing previo y permisos: OK');
