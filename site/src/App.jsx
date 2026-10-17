import React,{useMemo,useRef,useState} from "react";
import {DEMO_MARKER,sources,claims,links,compilationHistory,nodes,nodeById,sourceOf} from "./demo-data.mjs";

const initialFilters={evidence:true,related:true,conflict:true,model:true};
const keys=[
  ["evidence","Evidence pointers"],["related","Related concepts"],
  ["conflict","Possible contradictions"],["model","Model proposals / reviews"]
];
const phases=[
  ["INGEST","Preserve source bytes","The real engine snapshots input documents without editing the originals."],
  ["EXTRACT","Create candidate claims","Each extracted candidate keeps its source reference and line number. Extraction is not verification."],
  ["CONNECT","Propose relationships","Cross-source links are candidates produced by heuristics or optionally a local model."],
  ["GOVERN","Record review decisions","A person can accept or reject a useful relationship without verifying either claim."],
  ["RECALL","Explore with receipts","The graph preserves lineage and displays provenance for human inspection."]
];
const group=e=>e.id.startsWith("model-")?"model":e.kind==="EVIDENCED_BY"?"evidence":e.kind==="POSSIBLE_CONTRADICTION"?"conflict":"related";
const caption=s=>({TRACEABLE:"EVIDENCE POINTER",CANDIDATE:"UNVERIFIED CANDIDATE",PROPOSED:"MODEL PROPOSAL",ACCEPTED_CONNECTION:"HUMAN ACCEPTED CONNECTION",REJECTED_CONNECTION:"HUMAN REJECTED CONNECTION"})[s]||s;
const color=(e,s)=>{
 if(s==="ACCEPTED_CONNECTION")return "#66e4bb";
 if(s==="REJECTED_CONNECTION")return "#e88095";
 return {evidence:"#417489",related:"#74dfcf",conflict:"#edb069",model:"#ba9eea"}[group(e)];
};
function ButtonIcon({name}){
 const glyph={external:"↗",search:"⌕",arrow:"→",reset:"↺",check:"✓",source:"▤"}[name]||"◇";
 return <span className="glyph" aria-hidden="true">{glyph}</span>;
}
function Mark({children,tone="neutral"}){return <span className={"mark "+tone}>{children}</span>}
function Metrics(){
 const values=[
  [String(sources.length).padStart(2,"0"),"Fictional sources","No real files"],
  [String(claims.length).padStart(2,"0"),"Candidate claims","Never verified"],
  ["01","Potential conflict","Not adjudicated"],
  ["03","Simulated AI links","Demo only"]
 ];
 return <section className="metrics">{values.map(([v,name,sub])=><div className="metric" key={name}><div className="metric-value">{v}</div><strong>{name}</strong><small>{sub}</small></div>)}</section>
}
function Graph({filters,query,selected,choose,decisions}){
 const [viewport,setViewport]=useState({x:-5,y:-5,w:1210,h:675});
 const ref=useRef(null);
 const needle=query.trim().toLowerCase();
 const matches=new Set(nodes.filter(n=>!needle||[n.label,n.id,n.name,n.text,n.code].filter(Boolean).some(x=>String(x).toLowerCase().includes(needle))).map(n=>n.id));
 function start(e){
   if(e.target.closest("[data-pick]"))return;
   ref.current={x:e.clientX,y:e.clientY,view:viewport};
   e.currentTarget.setPointerCapture(e.pointerId);
 }
 function move(e){
   if(!ref.current)return;
   const rect=e.currentTarget.getBoundingClientRect(),d=ref.current;
   setViewport({...d.view,x:d.view.x-(e.clientX-d.x)*d.view.w/rect.width,y:d.view.y-(e.clientY-d.y)*d.view.h/rect.height});
 }
 function wheel(e){
   e.preventDefault();
   setViewport(v=>{
    const w=Math.max(380,Math.min(2200,v.w*(e.deltaY>0?1.12:.88)));
    const h=w*675/1210;
    return {x:v.x+(v.w-w)/2,y:v.y+(v.h-h)/2,w,h};
   });
 }
 function pick(e,kind,id){e.stopPropagation();choose({kind,id})}
 return <div className="graph-stage">
  <div className="graph-caption"><i className="pulse"/> PHIGRAPH / SIMULATION-001 <span>OFFLINE FIXTURE</span></div>
  <button className="viewport-reset" onClick={()=>setViewport({x:-5,y:-5,w:1210,h:675})}><ButtonIcon name="reset"/> Reset view</button>
  <svg className="graph-svg" viewBox={[viewport.x,viewport.y,viewport.w,viewport.h].join(" ")} onWheel={wheel} onPointerDown={start} onPointerMove={move} onPointerUp={()=>ref.current=null} onPointerCancel={()=>ref.current=null} aria-label="Interactive graph of fictional source records and claim candidates">
    <defs><pattern id="dots" width="32" height="32" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1" fill="#497087" opacity=".28"/></pattern><radialGradient id="radiance"><stop stopColor="#2d8d87" stopOpacity=".14"/><stop offset="1" stopColor="#0b1825" stopOpacity="0"/></radialGradient></defs>
    <rect x="-2000" y="-2000" width="5200" height="5200" fill="url(#dots)"/>
    <circle cx="570" cy="330" r="440" fill="url(#radiance)"/>
    {links.filter(e=>filters[group(e)]).map((e,i)=>{
      const from=nodeById(e.from),to=nodeById(e.to);
      const status=decisions[e.id]||e.status;
      const curve=group(e)==="evidence"?0:(i%2?35:-35);
      const d="M "+from.x+" "+from.y+" Q "+((from.x+to.x)/2+curve)+" "+((from.y+to.y)/2-curve)+" "+to.x+" "+to.y;
      const highlighted=selected?.id===e.id||selected?.id===e.from||selected?.id===e.to;
      const faded=needle&&!matches.has(e.from)&&!matches.has(e.to);
      return <g key={e.id} role="button" tabIndex="0" data-pick="edge" aria-label={"Inspect "+e.kind+" relationship"} opacity={faded?.12:1} onClick={evt=>pick(evt,"edge",e.id)} onKeyDown={evt=>{if(evt.key==="Enter"){evt.preventDefault();pick(evt,"edge",e.id)}}}>
        <path d={d} fill="none" stroke={color(e,status)} strokeWidth={highlighted?3.7:group(e)==="evidence"?1.4:2.5} strokeOpacity={highlighted?1:group(e)==="evidence"?.4:.75} strokeDasharray={status==="PROPOSED"?"8 7":status==="REJECTED_CONNECTION"?"3 6":undefined}/>
        <path d={d} fill="none" stroke="transparent" strokeWidth="17"/>
      </g>;
    })}
    {nodes.map(n=>{
      const isSource=n.kind==="SOURCE",selectedNode=selected?.kind==="node"&&selected.id===n.id;
      const paint=isSource?n.color:"#a0e7da";
      return <g key={n.id} role="button" tabIndex="0" data-pick="node" aria-label={"Inspect "+n.kind+" "+n.label} transform={"translate("+n.x+" "+n.y+")"} opacity={needle&&!matches.has(n.id)?.16:1} onClick={e=>pick(e,"node",n.id)} onKeyDown={e=>{if(e.key==="Enter"){e.preventDefault();pick(e,"node",n.id)}}}>
       <circle r={isSource?39:24} fill={paint} opacity=".065"/>
       <circle r={isSource?27:15} fill="#0a1e2b" stroke={paint} strokeWidth={selectedNode?4:isSource?2.5:1.8}/>
       {isSource?<text y="7" textAnchor="middle" fontSize="23" fill={paint}>Φ</text>:<circle r="5.8" fill={paint}/>}
       <text y={isSource?50:37} fontSize={isSource?"15":"12.5"} fontWeight={isSource?"700":"500"} textAnchor="middle" fill={isSource?"#e9f5f8":"#bdd2dc"} paintOrder="stroke" strokeWidth="4" stroke="#091824">{n.label.length>21?n.label.slice(0,19)+"…":n.label}</text>
       {isSource&&<text y="65" fontSize="10" textAnchor="middle" fill="#7191a5" letterSpacing="1.2">{n.code}</text>}
      </g>
    })}
  </svg>
  <div className="legend"><span><i className="legend-dot source"/>Source</span><span><i className="legend-dot claim"/>Claim</span><span><i className="legend-dot conflict"/>Conflict</span><span><i className="legend-dot proposal"/>AI proposal</span><em>SCROLL TO ZOOM · DRAG TO PAN</em></div>
 </div>;
}
function Inspector({selection,onSelect,decisions,onDecide}){
 if(!selection)return <div className="blank-inspector"><span className="blank-phi">Φ</span><h3>Follow the connection.</h3><p>Choose a source, claim, or relationship to reveal its origin, evidence trail, and review status.</p><div>Every link has a history.<br/>Every hypothesis deserves a check.</div></div>;
 if(selection.kind==="node"){
   const item=nodeById(selection.id);if(!item)return null;
   const src=item.kind==="SOURCE"?item:sourceOf(item);
   const edges=links.filter(e=>e.from===item.id||e.to===item.id);
   return <div className="inspector-body">
    <div className="eyebrow">{item.kind==="SOURCE"?"SOURCE RECORD":"CANDIDATE CLAIM"} · {item.id}</div>
    <h3>{item.kind==="SOURCE"?item.name:item.text}</h3>
    <Mark tone={item.kind==="SOURCE"?"blue":"lilac"}>{item.kind==="SOURCE"?"SIMULATED SOURCE":"INFERRED · NOT VERIFIED"}</Mark>
    <div className="inspector-block"><span className="field-name">PROVENANCE RECORD</span><p className="quote">{item.kind==="SOURCE"?item.excerpt:item.text}</p>
     <dl><dt>Origin</dt><dd>SIMULATED</dd><dt>Fixture ID</dt><dd>{src.code}</dd><dt>Evidence line</dt><dd>{item.kind==="CLAIM"?item.line:"Illustrative file"}</dd><dt>Truth status</dt><dd>NOT VERIFIED</dd></dl></div>
    {item.kind==="CLAIM"&&<button className="jump" onClick={()=>onSelect({kind:"node",id:src.id})}>View source <ButtonIcon name="arrow"/></button>}
    <div className="inspector-block"><span className="field-name">CONNECTED RECORDS ({edges.length})</span>
      {edges.map(e=><button className="linked" key={e.id} onClick={()=>onSelect({kind:"edge",id:e.id})}><i style={{background:color(e,decisions[e.id]||e.status)}}/><span><strong>{e.kind.replaceAll("_"," ")}</strong><small>{nodeById(e.from===item.id?e.to:e.from)?.label}</small></span><ButtonIcon name="arrow"/></button>)}</div>
    <div className="inspector-bottom">SYNTHETIC TRACE · {src.code}</div>
   </div>;
 }
 const e=links.find(x=>x.id===selection.id);if(!e)return null;
 const status=decisions[e.id]||e.status;
 return <div className="inspector-body">
   <div className="eyebrow">RELATIONSHIP RECORD · {e.id}</div>
   <h3>{e.kind.replaceAll("_"," ")}</h3>
   <Mark tone={status==="ACCEPTED_CONNECTION"?"mint":status==="REJECTED_CONNECTION"?"red":e.kind==="POSSIBLE_CONTRADICTION"?"amber":"lilac"}>{caption(status)}</Mark>
   <p className="safety-hint">A relationship review does not verify either source claim.</p>
   <div className="inspector-block"><span className="field-name">CONNECTED CANDIDATES</span>
    {[e.from,e.to].map((id,i)=><button className="link-target" key={id} onClick={()=>onSelect({kind:"node",id})}><span>{i===0?"A":"B"}</span>{nodeById(id)?.label}<ButtonIcon name="arrow"/></button>)}</div>
   <div className="inspector-block"><span className="field-name">EXPLANATION</span><p className="quote">{e.rationale}</p><p className="subtle">Basis: {e.basis}</p></div>
   {group(e)==="model"&&<div className="review-box"><span className="field-name">HUMAN REVIEW SIMULATOR</span><p>Try accepting or rejecting this connection. Your choice lasts only until page reset or reload.</p>
    <div className="review-buttons"><button className="accept" onClick={()=>onDecide(e.id,"ACCEPTED_CONNECTION")}>✓ Accept</button><button className="reject" onClick={()=>onDecide(e.id,"REJECTED_CONNECTION")}>× Reject</button></div>
    {(decisions[e.id]||e.reviewNote)&&<small>{decisions[e.id]?"Temporary UI decision. No real review ledger was edited.":e.reviewNote}</small>}</div>}
   <div className="inspector-bottom">DEMO LINK / NOT VERIFIED</div>
 </div>;
}
function Ledger({actions}){
 const all=[...compilationHistory,...actions].reverse();
 return <section className="secondary-view"><div className="section-heading"><div><div className="eyebrow">03 / COMPILATION RECEIPTS</div><h2>How a connection gets its history.</h2><p>Illustrative compilation timeline, plus any temporary actions you took in this browser. These are not cryptographic receipts.</p></div><Mark tone="blue">SIMULATED LEDGER</Mark></div>
  <div className="ledger-box"><div className="ledger-top"><span><i className="pulse"/> ACTIVITY STREAM / FIXTURE-001</span><span>{all.length} SYNTHETIC EVENTS</span></div>
   {all.map(row=><div key={row.id} className="ledger-event"><div className="timeline-mark"><i/><b/></div><div className="event-content"><div><strong>{row.name}</strong><small>{row.time}</small></div><p>{row.desc}</p><span>{row.id} / {row.kind}</span></div></div>)}</div>
  <div className="principle-cards"><article><b>01</b><h3>Evidence stays intact.</h3><p>The real compiler keeps content-addressed source snapshots rather than rewriting input documents.</p></article><article><b>02</b><h3>Inference stays inference.</h3><p>Model output starts as a proposal, not a privileged instruction or verified statement.</p></article><article><b>03</b><h3>Decisions leave records.</h3><p>Actual local human reviews use an append-only, hash-linked history independent of this demo.</p></article></div>
 </section>;
}
function Protocol(){
 const [step,setStep]=useState(0);
 return <section className="secondary-view"><div className="section-heading"><div><div className="eyebrow">04 / TRUST PROTOCOL</div><h2>Knowledge should carry its receipt.</h2><p>Explore the governed compilation pipeline. This is a design walkthrough, not proof that these projects are already integrated.</p></div><Mark tone="mint">LEDGER ABOVE EGO</Mark></div>
  <div className="protocol-grid"><div className="protocol-menu">{phases.map((phase,i)=><button key={phase[0]} onClick={()=>setStep(i)} className={i===step?"active":""}><span>{String(i+1).padStart(2,"0")}</span><strong>{phase[0]}</strong><small>{phase[1]}</small><ButtonIcon name="arrow"/></button>)}</div>
   <div className="protocol-detail"><div className="eyebrow">PROTOCOL PHASE {String(step+1).padStart(2,"0")} / 05</div><div className="phase-mark">Φ<span>{String(step+1).padStart(2,"0")}</span></div><h3>{phases[step][0]}</h3><p>{phases[step][2]}</p><div className="protocol-note"><i className="pulse"/> NO AUTOMATIC TRUTH PROMOTION</div><div className="phase-actions"><button onClick={()=>setStep((step+4)%5)}>← Previous</button><button onClick={()=>setStep((step+1)%5)}>Next phase →</button></div></div></div>
  <div className="core-rule"><span>FOUNDATIONAL PRINCIPLE</span>Knowledge may evolve. Evidence must remain traceable. Human authority stays intact.</div>
 </section>;
}
export default function App(){
 const [tab,setTab]=useState("explorer");
 const [query,setQuery]=useState("");
 const [filters,setFilters]=useState(initialFilters);
 const [selection,setSelection]=useState(null);
 const [decisions,setDecisions]=useState({});
 const [actions,setActions]=useState([]);
 const visible=useMemo(()=>links.filter(e=>filters[group(e)]).length,[filters]);
 function review(id,status){
  setDecisions(old=>({...old,[id]:status}));
  setActions(old=>[...old,{id:"SESSION-"+String(old.length+1).padStart(3,"0"),time:"SIMULATED",name:status==="ACCEPTED_CONNECTION"?"Demo connection accepted":"Demo connection rejected",desc:id+" was reviewed in temporary browser state; no real ledger was modified.",kind:"LOCAL UI"}]);
 }
 function reset(){setQuery("");setFilters(initialFilters);setSelection(null);setDecisions({});setActions([])}
 return <div className="app">
  <header className="topbar"><a className="brand" href="./" aria-label="PhiCompile home"><span className="brand-symbol">Φ</span><span><strong>Compile<span className="mint-dot">.</span></strong><small>KNOWLEDGE ENGINE</small></span></a>
   <nav>{[["explorer","Knowledge graph"],["ledger","Compilation ledger"],["protocol","Trust protocol"]].map(([id,label],i)=><button key={id} onClick={()=>setTab(id)} className={tab===id?"active":""}><small>0{i+1}</small>{label}</button>)}</nav>
   <a href="https://github.com/MichaelWave369/PhiCompile" className="source-link" target="_blank" rel="noreferrer">SOURCE CODE <ButtonIcon name="external"/></a></header>
  <div className="synthetic-banner"><span>PUBLIC FIELD LAB</span><strong>{DEMO_MARKER.replaceAll("_"," ")}</strong><span>NO PRIVATE DATA · NO BACKEND CONNECTION</span></div>
  <main>
   <section className="hero">
    <div className="hero-copy"><div className="eyebrow"><i className="pulse"/> KNOWLEDGE COMPILATION / 001</div><h1>Memory stores.<br/><em>Understanding connects.</em></h1><p>Step inside ΦCompile. Explore how raw notes become source-linked claims, relationship candidates, and reviewable connections. Every item here is fictional, created solely to demonstrate the architecture.</p><div className="hero-tags"><span>LOCAL-FIRST CORE</span><span>EVIDENCE GOVERNED</span><span>HUMAN IN CONTROL</span></div></div>
    <div className="hero-emblem"><div className="rings"><div className="r1"/><div className="r2"/><div className="r3"/><span>Φ</span><i/><b/></div><div><i className="pulse"/> FIELD SYSTEM / DEMO READY <small>SIMULATION ENVIRONMENT</small></div></div>
   </section>
   <Metrics/>
   {tab==="explorer"&&<section className="work-section"><div className="section-heading"><div><div className="eyebrow">02 / INTERCONNECTED KNOWLEDGE</div><h2>The field of relationships.</h2><p>Explore fictional sources and candidate assertions. Select a node or connection to inspect its lineage.</p></div><button className="reset-demo" onClick={reset}><ButtonIcon name="reset"/> Reset simulation</button></div>
    <div className="workbench">
     <aside className="controls"><div className="aside-head">EXPLORER CONTROLS <span>001</span></div><label className="search-box"><ButtonIcon name="search"/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Find a concept…" aria-label="Search knowledge graph"/></label>
      <div className="aside-label">RELATIONSHIP TYPES</div><div className="filter-options">{keys.map(([k,label])=><label key={k}><input type="checkbox" checked={filters[k]} onChange={e=>setFilters(old=>({...old,[k]:e.target.checked}))}/><i className={"filter-marker "+k}/>{label}</label>)}</div>
      <div className="aside-label">SOURCE INDEX <small>{sources.length.toString().padStart(2,"0")}</small></div>
      <div className="source-list">{sources.map((src,i)=><button key={src.id} onClick={()=>setSelection({kind:"node",id:src.id})} className={selection?.id===src.id?"selected":""}><small>{String(i+1).padStart(2,"0")}</small><span>{src.name}</span><i style={{background:src.color}}/></button>)}</div>
      <p className="control-note">All project notes here are fictional.<br/>Nothing was imported from any repository.</p>
     </aside>
     <Graph filters={filters} query={query} selected={selection} choose={setSelection} decisions={decisions}/>
     <aside className="inspector"><div className="inspector-head"><span><i className="pulse"/> EVIDENCE INSPECTOR</span><span>READ ONLY</span></div><Inspector selection={selection} onSelect={setSelection} decisions={decisions} onDecide={review}/></aside>
    </div>
    <div className="workbench-footer"><span><strong>FIELD LOG</strong> / {visible} visible connections · {actions.length} temporary review actions</span><span>GRAPH ID: SYNTHETIC / NOT VERIFIED</span></div>
   </section>}
   {tab==="ledger"&&<Ledger actions={actions}/>}
   {tab==="protocol"&&<Protocol/>}
   <section className="bottom-callout"><div className="callout-phi">Φ</div><div><div className="eyebrow">THE REAL ENGINE IS SEPARATE</div><h2>Private knowledge stays on your machine.</h2><p>The public React lab is synthetic. Actual ingestion, Ollama review suggestions, human decisions, and local ΦGraph exports run separately through the private Python vault.</p></div><a href="https://github.com/MichaelWave369/PhiCompile#quick-start" target="_blank" rel="noreferrer">EXPLORE THE ENGINE →</a></section>
  </main>
  <footer><span>ΦCOMPILE / OPEN-SOURCE RESEARCH TOOL</span><span>BUILD OUTWARD · CIRCLE BACK · COMPILE FORWARD</span><span>LEDGER ABOVE EGO · 2026</span></footer>
 </div>;
}
