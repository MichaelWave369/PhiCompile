/** Synthetic, hand-authored scenario. No real source files or ledger entries. */
export const DEMO_MARKER = "SYNTHETIC_FIXTURE_ONLY";
export const sources = [
  { id:"src-nbg", name:"NBG · Provenance Note", code:"FIX-NBG-001", sector:"Governance", color:"#73e8d1", x:165, y:153, excerpt:"Every candidate retains its original source reference.", lineCount:18 },
  { id:"src-brainc", name:"BrainC · Routing Sketch", code:"FIX-BRC-002", sector:"Memory", color:"#88b8ff", x:518, y:118, excerpt:"The routing demonstration uses reviewed link suggestions.", lineCount:12 },
  { id:"src-vessie", name:"Super Φ.Vessel · Draft", code:"FIX-SPV-003", sector:"Orchestration", color:"#c5abff", x:980, y:163, excerpt:"The routing demonstration does not use reviewed link suggestions.", lineCount:14 },
  { id:"src-openblue", name:"OpenBlue · Sample", code:"FIX-OBL-004", sector:"Design", color:"#ffc27d", x:158, y:507, excerpt:"Geometry snapshots could share a future asset manifest.", lineCount:11 },
  { id:"src-pixelforge", name:"PixelForge · Sample", code:"FIX-PXF-005", sector:"Assets", color:"#ff9ec3", x:683, y:539, excerpt:"A test mesh can reuse selected geometry manifest fields.", lineCount:15 },
  { id:"src-antim", name:"Anti-M · Review Notes", code:"FIX-AMT-006", sector:"Verification", color:"#c2e6a4", x:1022, y:529, excerpt:"Review of a relationship does not verify underlying facts.", lineCount:20 },
];
export const claims = [
  {id:"claim-1",sourceId:"src-nbg",line:3,text:"Every candidate relationship should retain a traceable source reference.",x:316,y:223,topic:"Evidence lineage"},
  {id:"claim-2",sourceId:"src-nbg",line:9,text:"A hypothesis stays INFERRED until evidence is independently evaluated.",x:116,y:307,topic:"Provenance"},
  {id:"claim-3",sourceId:"src-brainc",line:4,text:"The routing demonstration uses reviewed link suggestions.",x:525,y:258,topic:"Routing"},
  {id:"claim-4",sourceId:"src-vessie",line:7,text:"A proposal is not permission to run a tool.",x:1029,y:288,topic:"Boundaries"},
  {id:"claim-5",sourceId:"src-openblue",line:6,text:"Geometry snapshots could share a future asset manifest.",x:356,y:453,topic:"Design"},
  {id:"claim-6",sourceId:"src-pixelforge",line:11,text:"A test mesh can reuse selected geometry manifest fields.",x:724,y:414,topic:"Assets"},
  {id:"claim-7",sourceId:"src-antim",line:5,text:"Reviewing a connection does not verify the underlying claims.",x:1007,y:410,topic:"Review"},
  {id:"claim-8",sourceId:"src-vessie",line:10,text:"The routing demonstration does not use reviewed link suggestions.",x:735,y:295,topic:"Routing"},
  {id:"claim-9",sourceId:"src-brainc",line:9,text:"An evidence brief should identify its original source.",x:445,y:380,topic:"Memory"},
];
export const links = [
  ...claims.map((c,i)=>({id:"evidence-"+(i+1),from:c.id,to:c.sourceId,kind:"EVIDENCED_BY",status:"TRACEABLE",basis:"Synthetic source line reference",rationale:"A candidate assertion is linked to an illustrative source line. This is provenance, not factual verification."})),
  {id:"related-1",from:"claim-2",to:"claim-7",kind:"RELATED",status:"CANDIDATE",basis:"Synthetic keyword heuristic",rationale:"Both notes discuss the distinction between review and fact verification."},
  {id:"conflict-1",from:"claim-3",to:"claim-8",kind:"POSSIBLE_CONTRADICTION",status:"CANDIDATE",basis:"Synthetic opposing statements",rationale:"The two illustrative statements disagree about whether a fictional routing demo uses reviewed suggestions."},
  {id:"model-1",from:"claim-5",to:"claim-6",kind:"RELATED",status:"PROPOSED",basis:"Simulated local model",rationale:"Both statements describe a possible shared asset manifest. This suggestion has not been reviewed."},
  {id:"model-2",from:"claim-1",to:"claim-9",kind:"RELATED",status:"ACCEPTED_CONNECTION",basis:"Simulated local model + human review",rationale:"Both statements concern preserving evidence references.",reviewer:"Demo reviewer",reviewNote:"Useful conceptual relationship, not proof of either claim."},
  {id:"model-3",from:"claim-4",to:"claim-7",kind:"RELATED",status:"REJECTED_CONNECTION",basis:"Simulated local model + human review",rationale:"The proposed link conflates execution permission and evidence review.",reviewer:"Demo reviewer",reviewNote:"Scope mismatch. Not useful for this demonstration."},
];
export const compilationHistory=[
 {id:"DEMO-EVT-001",time:"09:14:02",name:"Input registered",desc:"Six fictional source cards added to the demonstration.",kind:"INGEST"},
 {id:"DEMO-EVT-002",time:"09:14:03",name:"Evidence indexed",desc:"Nine hand-authored claims mapped to illustrative source lines.",kind:"TRACE"},
 {id:"DEMO-EVT-003",time:"09:14:04",name:"Connections inferred",desc:"One topical match and one candidate contradiction added.",kind:"LINK"},
 {id:"DEMO-EVT-004",time:"09:14:05",name:"Model proposals staged",desc:"Three invented model suggestion examples attached.",kind:"PROPOSE"},
 {id:"DEMO-EVT-005",time:"09:14:06",name:"Human reviews simulated",desc:"One example accepted, one rejected; neither verifies a claim.",kind:"REVIEW"},
];
export const nodes=[...sources.map(s=>({...s,kind:"SOURCE",label:s.name})),...claims.map(c=>({...c,kind:"CLAIM",label:c.topic}))];
export const sourceOf=(claim)=>sources.find(s=>s.id===claim.sourceId);
export const nodeById=(id)=>nodes.find(n=>n.id===id);
