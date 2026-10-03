// Test the component protocol without a browser or any personal credential.
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const html=fs.readFileSync('ui/passkey_component/index.html','utf8');
const script=html.match(/<script>([\s\S]*?)<\/script>/)[1];
const callbacks={},sent=[];
const button={disabled:true,textContent:'',addEventListener:(k,f)=>callbacks[k]=f};
const message={textContent:''};
const parent={postMessage:(m,o)=>sent.push([m,o])};
let called;
const context={document:{referrer:'https://red-neuronal-usaer-2e.streamlit.app/~/+/',getElementById:id=>id==='access'?button:message},
 location:{origin:'https://red-neuronal-usaer-2e.streamlit.app'},parent,isSecureContext:true,
 PublicKeyCredential:{isUserVerifyingPlatformAuthenticatorAvailable:async()=>true},
 navigator:{credentials:{get:async args=>{called=args;return {id:'AQ',rawId:new Uint8Array([1]).buffer,type:'public-key',
 response:{clientDataJSON:new Uint8Array([2]).buffer,authenticatorData:new Uint8Array([3]).buffer,signature:new Uint8Array([4]).buffer,userHandle:new Uint8Array([5]).buffer},getClientExtensionResults:()=>({})}}}},
 Uint8Array,structuredClone,URL,atob,btoa};
context.window={PublicKeyCredential:context.PublicKeyCredential,addEventListener:(k,f)=>callbacks[k]=f};
vm.runInNewContext(script,context);
(async()=>{
 await new Promise(r=>setImmediate(r));
 const args={kind:'authenticate',request:'nonce',options:{challenge:'AQ',rpId:context.location.origin.substring(8),userVerification:'required'}};
 callbacks.message({source:parent,origin:'https://evil.example',data:{type:'streamlit:render',args}});
 assert.equal(button.disabled,true);
 callbacks.message({source:parent,origin:context.location.origin,data:{type:'streamlit:render',args}});
 assert.equal(button.disabled,false);
 assert.equal(called,undefined); // No OS prompt until explicit click.
 await callbacks.click();
 assert.equal(new Uint8Array(called.publicKey.challenge)[0],1);
 const result=sent.find(([m])=>m.type==='streamlit:setComponentValue');
 assert.equal(result[0].value.request,'nonce');
 assert.equal(result[0].value.credential.response.signature,'BA');
 assert.equal(result[1],context.location.origin);
 console.log('Component protocol, explicit gesture, binary conversion and origin checks: OK');
})().catch(e=>{console.error(e);process.exitCode=1});
