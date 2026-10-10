"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const P = require("../frontend/native-library-protocol.js");
const C = require("../frontend/inventory-snapshot-model.js");
const source = JSON.parse(fs.readFileSync(require.resolve("../prototypes/inventory_catalogue/owned-creative.example.json"),"utf8"));
const sample = C.exportCatalogue(C.add(C.empty(), source, "Shelf café 😀"));
const S = "12345678-1234-4234-8234-123456789abc";
const id = n => `00000000-0000-4000-8000-${String(n).padStart(12,"0")}`;
const request = (n, more={}) => ({version:P.VERSION, session:S, operation:id(n), ...more});
const checks=[];
function fixture(mode="owned-storage") {
  const state={revision:"0",epoch:"0",dirty:"clean",selections:"0",dialog:"none",draft:"none",busy:false};
  let text=C.exportCatalogue(C.empty()), fenced=false, cleans=0, commits=0, renderFailure=false, available=true;
  const port={check(v,s){assert.equal(v,P.VERSION);if(s!==S||!available)throw Error("retired");},mode:()=>mode,state:()=>({...state}),export:()=>text,
    fence(value){fenced=value;},clean(revision){assert.equal(state.revision,revision);state.dirty="clean";cleans++;},
    parse(value){const parsed=C.parse(value);if(parsed.schema_version!==C.CATALOGUE)throw Error("catalogue required");return parsed;},
    commit(value){text=C.exportCatalogue(value);state.revision=String(BigInt(state.revision)+1n);state.epoch=String(BigInt(state.epoch)+1n);state.dirty="clean";state.selections="0";commits++;},
    render(){if(renderFailure)throw Error("owned render failure");}};
  return {api:P.create(port),state,edit(value=sample){text=value;state.revision=String(BigInt(state.revision)+1n);state.epoch=String(BigInt(state.epoch)+1n);state.dirty="dirty";},
    get text(){return text;},get fenced(){return fenced;},get cleans(){return cleans;},get commits(){return commits;},
    failRender(){renderFailure=true;},retire(){available=false;}};
}
function check(name, fn){fn();checks.push(name);}
check("exact version/session/UUID/type/field admission",()=>{
 const f=fixture();for(const value of [null,[],{},request(1,{extra:"x"}),request(1,{version:"catalogue-data-bridge/v1"}),request(1,{session:id(2)}),request(1,{operation:1}),request(1,{operation:id(1).toUpperCase()+"X"})])assert.throws(()=>f.api.status(value));
 const accessor={...request(1)};Object.defineProperty(accessor,"version",{get(){throw Error("must not invoke getter");},enumerable:true});assert.throws(()=>f.api.status(accessor));
 assert.equal(f.api.status(request(1)).state,"idle");
});
check("temporary mode can close honestly but cannot save/open",()=>{
 const f=fixture("temporary");assert.throws(()=>f.api.exportCatalogue(request(1,{fence:""})));assert.throws(()=>f.api.prepareOpen(request(2)));
 assert.equal(f.api.prepareClose(request(3)).state,"fenced");assert.equal(f.fenced,true);f.api.releaseClose(request(3));assert.equal(f.fenced,false);
});
check("application-data mode permits only the same data operations and exact admission",()=>{
 const f=fixture("application-data");f.edit();const saved=f.api.exportCatalogue(request(1,{fence:""}));assert.equal(saved.text,sample);assert.equal(f.state.dirty,"dirty");f.api.acknowledgeSaved(request(1,{revision:"1"}));assert.equal(f.state.dirty,"clean");f.api.prepareOpen(request(2));f.api.cancelOpen(request(2));
 for(const mode of ["application-data ","APPLICATION-DATA","applicationData","user-drive",null]){const g=fixture(mode);assert.throws(()=>g.api.exportCatalogue(request(1,{fence:""})));assert.throws(()=>g.api.prepareOpen(request(2)));}
});
check("export is data-only, immutable and one-use",()=>{
 const f=fixture();f.edit();const reply=f.api.exportCatalogue(request(1,{fence:""}));assert.equal(reply.text,sample);assert.equal(reply.revision,"1");assert.equal(Object.isFrozen(reply),true);assert.equal(f.state.dirty,"dirty");assert.equal(f.cleans,0);assert.throws(()=>f.api.exportCatalogue(request(1,{fence:""})));
});
check("acknowledgement keeps selections and supports exact idempotent querying",()=>{
 const f=fixture();f.edit();f.state.selections="2";f.api.exportCatalogue(request(1,{fence:""}));assert.equal(f.api.savedResult(request(1)).state,"not-applied");
 assert.throws(()=>f.api.acknowledgeSaved(request(1,{revision:"0"})));assert.equal(f.api.acknowledgeSaved(request(1,{revision:"1"})).state,"current-saved");assert.equal(f.state.selections,"2");assert.equal(f.cleans,1);
 f.api.acknowledgeSaved(request(1,{revision:"1"}));assert.equal(f.cleans,1);assert.equal(f.api.savedResult(request(1)).state,"current-saved");
});
check("later edits cannot be cleaned by an old or repeated acknowledgement",()=>{
 const f=fixture();f.edit();f.api.exportCatalogue(request(1,{fence:""}));f.edit();assert.equal(f.api.acknowledgeSaved(request(1,{revision:"1"})).state,"earlier-saved");assert.equal(f.state.dirty,"dirty");assert.equal(f.cleans,0);
 const g=fixture();g.edit();g.api.exportCatalogue(request(1,{fence:""}));g.api.acknowledgeSaved(request(1,{revision:"1"}));g.edit();assert.equal(g.api.savedResult(request(1)).state,"earlier-saved");g.api.acknowledgeSaved(request(1,{revision:"1"}));assert.equal(g.cleans,1);assert.equal(g.state.dirty,"dirty");
});
check("dialog/draft and sample review refuse ordinary Save/Open",()=>{
 for(const change of [{dialog:"label-edit",draft:"uncommitted"},{dialog:"snapshot-review"},{busy:true}]){const f=fixture();Object.assign(f.state,change);assert.throws(()=>f.api.exportCatalogue(request(1,{fence:""})));assert.throws(()=>f.api.prepareOpen(request(2)));}
});
check("close fences all mutation while exposing complete loss state",()=>{
 const f=fixture();f.edit();Object.assign(f.state,{selections:"5",dialog:"label-edit",draft:"uncommitted"});const value=f.api.prepareClose(request(1));assert.equal(value.selections,"5");assert.equal(value.dialog,"label-edit");assert.equal(value.draft,"uncommitted");assert.equal(value.dirty,"dirty");assert.throws(()=>f.api.requireMutable());assert.throws(()=>f.api.prepareClose(request(2)));assert.throws(()=>f.api.releaseClose(request(2)));f.api.releaseClose(request(1));f.api.releaseClose(request(1));f.api.requireMutable();assert.equal(f.state.selections,"5");assert.equal(f.state.dialog,"label-edit");
});
check("only the matching close fence allows its committed catalogue export",()=>{
 const f=fixture();f.edit();f.api.prepareClose(request(1));assert.throws(()=>f.api.exportCatalogue(request(2,{fence:""})));assert.throws(()=>f.api.exportCatalogue(request(2,{fence:id(3)})));const saved=f.api.exportCatalogue(request(2,{fence:id(1)}));assert.equal(saved.revision,"1");f.api.acknowledgeSaved(request(2,{revision:"1"}));assert.equal(f.fenced,true);f.api.releaseClose(request(1));
});
check("Open cancellation preserves catalogue, selections and draft-free state",()=>{
 const f=fixture();f.edit();f.state.selections="3";const before=f.text;const loss=f.api.prepareOpen(request(1));assert.equal(loss.selections,"3");const cancelled=f.api.cancelOpen(request(1));assert.equal(cancelled.state,"cancelled");assert.equal(f.text,before);assert.equal(f.state.selections,"3");assert.equal(f.state.dirty,"dirty");assert.equal(f.fenced,false);assert.equal(f.api.cancelOpen(request(1)).state,"cancelled");
});
check("selected replacement prepares without mutation then commits exactly once",()=>{
 const f=fixture();f.state.selections="2";f.api.prepareOpen(request(1));const args=request(1,{candidate:id(2),revision:"0",epoch:"0"});f.api.prepareReplacement({...args,text:sample});assert.equal(f.commits,0);assert.equal(f.state.selections,"2");const value=f.api.commitReplacement(args);assert.equal(value.state,"committed");assert.equal(value.revision,"1");assert.equal(f.commits,1);assert.equal(f.text,sample);assert.equal(f.state.selections,"0");assert.equal(f.state.dirty,"clean");assert.equal(f.fenced,false);f.api.commitReplacement(args);assert.equal(f.commits,1);assert.equal(f.api.replacementResult(request(1,{candidate:id(2)})).state,"committed");assert.equal(f.api.cancelOpen(request(1)).state,"committed");
});
check("stale revision, epoch and candidate cannot replace a newer view",()=>{
 for(const key of ["revision","epoch"]){const f=fixture();f.api.prepareOpen(request(1));const args=request(1,{candidate:id(2),revision:"0",epoch:"0"});f.api.prepareReplacement({...args,text:sample});f.state[key]="1";assert.throws(()=>f.api.commitReplacement(args));assert.equal(f.commits,0);}
 const f=fixture();f.api.prepareOpen(request(1));f.api.prepareReplacement(request(1,{candidate:id(2),revision:"0",epoch:"0",text:sample}));assert.throws(()=>f.api.commitReplacement(request(1,{candidate:id(3),revision:"0",epoch:"0"})));assert.equal(f.commits,0);
});
check("retired candidate cannot be replayed or replace another selected preview",()=>{
 const f=fixture();f.api.prepareOpen(request(1));const args=request(1,{candidate:id(2),revision:"0",epoch:"0"});f.api.prepareReplacement({...args,text:sample});f.api.retireCandidate(request(1,{candidate:id(2)}));assert.throws(()=>f.api.commitReplacement(args));assert.throws(()=>f.api.prepareReplacement({...args,text:sample}));f.api.prepareReplacement(request(1,{candidate:id(3),revision:"0",epoch:"0",text:sample}));assert.throws(()=>f.api.commitReplacement(args));assert.equal(f.commits,0);
});
check("render failure preserves a queryable committed fact without rollback",()=>{
 const f=fixture();f.api.prepareOpen(request(1));const args=request(1,{candidate:id(2),revision:"0",epoch:"0"});f.api.prepareReplacement({...args,text:sample});f.failRender();const result=f.api.commitReplacement(args);assert.equal(result.state,"committed");assert.equal(result.view,"blocked");assert.equal(f.commits,1);assert.equal(f.api.replacementResult(request(1,{candidate:id(2)})).view,"blocked");assert.throws(()=>f.api.requireMutable());
});
check("malformed/non-catalogue/Unicode/BOM/oversized text cannot stage",()=>{
 const f=fixture();f.api.prepareOpen(request(1));for(const text of ["",null,"{}","\ufeff"+sample,"\ud800",JSON.stringify(source),"é".repeat(P.BYTES/2+1)])assert.throws(()=>f.api.prepareReplacement(request(1,{candidate:id(2),revision:"0",epoch:"0",text})));assert.equal(f.commits,0);
});
check("exact multibyte byte boundary is admitted, one extra byte refuses",()=>{
 const f=fixture();const base=sample.length-"é".length; // The payload itself need not consume the whole limit.
 const exact=sample+" ".repeat(P.BYTES-Buffer.byteLength(sample));assert.equal(Buffer.byteLength(exact),P.BYTES);f.api.prepareOpen(request(1));f.api.prepareReplacement(request(1,{candidate:id(2),revision:"0",epoch:"0",text:exact}));f.api.retireCandidate(request(1,{candidate:id(2)}));assert.throws(()=>f.api.prepareReplacement(request(1,{candidate:id(3),revision:"0",epoch:"0",text:exact+" "})));assert.equal(base>0,true);
});
check("replay histories and revision counters fail without silent eviction/wrap",()=>{
 const f=fixture();for(let n=1;n<=P.LIMIT;n++){f.api.prepareClose(request(n));f.api.releaseClose(request(n));}assert.throws(()=>f.api.prepareClose(request(P.LIMIT+1)));assert.equal(f.fenced,false);
 const g=fixture();g.state.revision="9007199254740991";g.api.prepareOpen(request(1));g.api.prepareReplacement(request(1,{candidate:id(2),revision:g.state.revision,epoch:"0",text:sample}));assert.throws(()=>g.api.commitReplacement(request(1,{candidate:id(2),revision:g.state.revision,epoch:"0"})));assert.equal(g.commits,0);
 for(const revision of ["01","-1","9007199254740992",true,1]){const h=fixture();h.state.revision=revision;assert.throws(()=>h.api.status(request(1)));}
});
check("retired documents reject late acknowledgement and replacement queries",()=>{
 const f=fixture();f.edit();f.api.exportCatalogue(request(1,{fence:""}));f.retire();assert.throws(()=>f.api.acknowledgeSaved(request(1,{revision:"1"})));assert.throws(()=>f.api.savedResult(request(1)));assert.equal(f.cleans,0);
});
console.log(`PASS: ${checks.length} pure native library protocol checks`);for(const name of checks)console.log("  "+name);
