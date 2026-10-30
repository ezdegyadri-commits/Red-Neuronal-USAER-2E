// Modelo de acuses con datos y reloj ficticios. No emula paquetes ni ancho de banda real.
const assert=require('node:assert/strict'),fs=require('node:fs'),cp=require('node:child_process'),path=require('node:path');
const {fixture,hoja,script}=require('./planeacion_editor_cliente.cjs');
const original=cp.execFileSync('git',['show','9cf45b1:ui/planeacion_papel_component/index.html'],{encoding:'utf8'});
const before=original.match(/<script>([\s\S]*?)<\/script>/)[1];
const profiles=[
 {nombre:'Referencia sintética',rtt_ms:0},
 {nombre:'Latencia configurada 150 ms',rtt_ms:150},
 {nombre:'Latencia configurada 300 ms',rtt_ms:300},
 {nombre:'Latencia configurada 500 ms',rtt_ms:500},
 {nombre:'Descarga 1 Mbps (modelo)',rtt_ms:0,down_bps:1000000},
 {nombre:'Subida 256 Kbps (modelo)',rtt_ms:0,up_bps:256000},
 {nombre:'Combinación (modelo)',rtt_ms:500,down_bps:1000000,up_bps:256000}
];
function action(source,reply) {
 const f=fixture(undefined,undefined,false,source);
 f.render(hoja());f.input('Actividad ficticia para proteger durante una conexión lenta.');
 f.tools.children.find(b=>b.textContent==='Guardar planeación').click();
 const sent=f.events()[0];
 f.tools.children.find(b=>b.textContent==='Descargar').click();
 f.render(hoja(sent.cambios.c0,'recibido'),{recibido_nonce:sent.nonce,guardado:''});
 const released=f.events().some(e=>e.accion==='pdf');
 assert.ok(f.cache.size);
 if(reply)assert.equal(released,true);else assert.equal(released,false);
 if(!reply)f.render(hoja(sent.cambios.c0,'recibido'),{aceptado_nonce:sent.nonce,guardado:'confirmado-ficticio'});
 assert.ok(f.events().some(e=>e.accion==='pdf'));
 return {evento_bytes:Buffer.byteLength(JSON.stringify(sent)),
  respuesta_bytes:Buffer.byteLength(JSON.stringify(hoja(sent.cambios.c0,'recibido'))),
  libera_herramienta_con_recibo:released};
}
const old=action(before,false),now=action(script,true);
const results=profiles.map(profile=>{
 const network=(profile.rtt_ms||0)+(profile.up_bps?now.evento_bytes*8/profile.up_bps*1000:0)+(profile.down_bps?now.respuesta_bytes*8/profile.down_bps*1000:0);
 return {...profile,antes:old.libera_herramienta_con_recibo,despues:now.libera_herramienta_con_recibo,
  demora_transporte_calculada_ms:Math.round(network*100)/100};
});
// Un corte conserva el mismo envío y permite seguir escribiendo.
const f=fixture();f.render(hoja());f.input('Antes del corte');f.tick(4000);
const nonce=f.events()[0].nonce;f.listeners.offline();f.input('Durante el corte');
f.tick(15000);assert.equal(f.events().length,1);f.listeners.online();
assert.equal(f.events().at(-1).nonce,nonce);assert.ok(f.cache.size);
const report={metodo:'Pruebas deterministas del protocolo y cálculos de transmisión. No son tiempos medidos en navegador, Google, Cloud o escuelas.',perdida_de_paquetes:'No simulada',bytes:now,profiles:results,corte_y_reconexion:'Texto conservado y mismo nonce'};
if(process.argv[2])fs.writeFileSync(process.argv[2],JSON.stringify(report,null,2));
console.log('Protocolo: 7 perfiles modelados, corte/reconexión y liberación por recibo aprobados.');
