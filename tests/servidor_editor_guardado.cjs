// Servidor de prueba aislado. No acepta escrituras ni expone otros archivos.
const http=require('node:http'),fs=require('node:fs'),path=require('node:path');
const routes={'/':path.join(__dirname,'fixture_editor_guardado.html'),
 '/editor/index.html':path.join(__dirname,'../ui/planeacion_papel_component/index.html')};
http.createServer((req,res)=>{const file=routes[req.url.split('?')[0]];if(!file){res.writeHead(404);res.end();return}
 res.writeHead(200,{'Content-Type':'text/html; charset=utf-8','Cache-Control':'no-store'});res.end(fs.readFileSync(file));
}).listen(8603,'127.0.0.1',()=>console.log('Prueba ficticia en http://127.0.0.1:8603/'));
