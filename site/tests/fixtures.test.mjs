import {test} from "node:test";
import assert from "node:assert/strict";
import {DEMO_MARKER,sources,claims,links,compilationHistory,nodes} from "../src/demo-data.mjs";

test("public demo consists only of explicit synthetic fixtures",()=>{
 assert.equal(DEMO_MARKER,"SYNTHETIC_FIXTURE_ONLY");
 assert.equal(sources.length,6);
 assert.equal(claims.length,9);
 assert.ok(compilationHistory.every(e=>e.id.startsWith("DEMO-EVT-")));
 assert.ok(sources.every(s=>s.code.startsWith("FIX-")));
 assert.ok(!JSON.stringify({sources,claims,links}).includes("microneesia79@gmail.com"));
});
test("no orphan claims or relationships",()=>{
 const ids=new Set(nodes.map(n=>n.id));
 const sourceIds=new Set(sources.map(s=>s.id));
 assert.equal(ids.size,nodes.length);
 for(const claim of claims){
  assert.ok(sourceIds.has(claim.sourceId),claim.id);
  assert.ok(Number.isInteger(claim.line)&&claim.line>=1);
 }
 for(const edge of links){
  assert.ok(ids.has(edge.from),edge.id);
  assert.ok(ids.has(edge.to),edge.id);
 }
 assert.equal(new Set(links.map(l=>l.id)).size,links.length);
});
test("simulated review never claims VERIFIED",()=>{
 assert.ok(claims.every(c=>!c.status || c.status==="INFERRED"));
 assert.ok(!links.some(l=>l.status==="VERIFIED"));
 assert.deepEqual(new Set(links.filter(l=>l.id.startsWith("model-")).map(l=>l.status)),
   new Set(["PROPOSED","ACCEPTED_CONNECTION","REJECTED_CONNECTION"]));
 assert.ok(links.some(l=>l.kind==="POSSIBLE_CONTRADICTION"));
});
test("each fixture claim has exact evidence pointer",()=>{
 for(const c of claims){
  const matches=links.filter(l=>l.kind==="EVIDENCED_BY"&&l.from===c.id&&l.to===c.sourceId);
  assert.equal(matches.length,1,c.id);
 }
});
