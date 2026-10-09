import React, {useEffect, useRef, useState} from 'react';
import {createRoot} from 'react-dom/client';
import type {Config, Part, Session, State} from './types';
import './styles.css';

const SUBJECTS = [{id:'basic_math',label:'Basic math'},{id:'algebra',label:'Algebra'},{id:'geometry',label:'Geometry'},{id:'calculus',label:'Calculus'},{id:'statistics',label:'Statistics'},{id:'computer_science',label:'Computer science'}];
const ROOMS = ['The Foyer','The Library','The Secret Study','The Final Door'];
const formatTime = (seconds:number) => `${Math.floor(seconds/60).toString().padStart(2,'0')}:${(seconds%60).toString().padStart(2,'0')}`;
const requestId = () => typeof crypto.randomUUID==='function' ? crypto.randomUUID() : Array.from(crypto.getRandomValues(new Uint8Array(16)),b=>b.toString(16).padStart(2,'0')).join('');
function savedSession(key:string): Session|null {try {return JSON.parse(sessionStorage.getItem(key)||'null');} catch {return null;}}

function Icon({name='key',size=22}:{name?:string;size?:number}) {
  const paths:Record<string,React.ReactNode> = {
    key:<><circle cx="8" cy="8" r="5"/><path d="m12 12 9 9m-4-4 3-3m-6 0 3-3"/></>,
    arrow:<><path d="M4 12h16m-6-6 6 6-6 6"/></>,
    users:<><circle cx="9" cy="7" r="3"/><path d="M3 21v-3a6 6 0 0 1 12 0v3m1-17a3 3 0 0 1 0 6m2 5a5 5 0 0 1 3 5"/></>,
    clock:<><circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 2"/></>,
    lock:<><rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V6a4 4 0 0 1 8 0v4m-4 5v2"/></>,
    check:<path d="m5 12 4 4L20 5"/>,
    chat:<><path d="M21 11a8 8 0 0 1-8 8H5l-4 3V11a10 10 0 0 1 20 0Z"/><path d="M7 9h8m-8 4h5"/></>,
    math:<><path d="m2 13 4 6 4-15h12M15 8l6 8m0-8-6 8"/></>,
    book:<><path d="M12 6c-4-3-8-3-10-2v15c3-1 7 0 10 2 3-2 7-3 10-2V4c-2-1-6-1-10 2Zm0 0v15"/></>,
    exit:<><path d="M10 4H4v16h6m3-8h9m-4-4 4 4-4 4"/></>,
    copy:<><rect x="8" y="8" width="12" height="13" rx="2"/><path d="M16 8V3H3v13h5"/></>,
    bulb:<><path d="M8 17c0-4-3-4-3-8a7 7 0 0 1 14 0c0 4-3 4-3 8Zm1 3h6m-5 3h4"/></>,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]||paths.key}</svg>;
}

function MansionArt() {
 return <svg className="mansion-art" viewBox="0 0 600 450" fill="none" aria-hidden="true">
  <defs><linearGradient id="sky" x2="0" y2="1"><stop stopColor="#123636"/><stop offset="1" stopColor="#254343"/></linearGradient><pattern id="grain" width="12" height="12" patternUnits="userSpaceOnUse"><circle cx="3" cy="3" r=".5" fill="#f0d8a1" opacity=".15"/></pattern></defs>
  <rect width="600" height="450" fill="url(#sky)"/><rect width="600" height="450" fill="url(#grain)"/>
  <circle cx="446" cy="86" r="37" fill="#e6d4ab" opacity=".8"/><circle cx="461" cy="72" r="35" fill="#153838"/>
  {[ [73,79],[160,52],[327,52],[514,174],[66,188],[548,63],[378,145] ].map(([x,y],i)=><g key={i} stroke="#d2c297" opacity=".6"><path d={`M${x-3} ${y}h6M${x} ${y-3}v6`}/></g>)}
  <path d="M0 402Q140 370 300 396Q440 370 600 402V450H0Z" fill="#102c2d"/>
  <g stroke="#c8ba96" strokeWidth="1.4"><path d="M153 369V238L125 238 190 178 246 225M447 369V238h28l-65-60-56 47" fill="#243e3b"/>
   <path d="M222 370V182l78-78 78 78v188Z" fill="#25433e"/><path d="M206 187l94-94 94 94M237 178l63-64 63 64"/><path d="M245 154v-35h16v20m74 0v-35h16v50"/>
   <path d="M141 260h91m136 0h91M141 350h91m136 0h91M237 205h126M237 313h126" opacity=".6"/>
   <path d="M273 370v-71a27 27 0 0 1 54 0v71" fill="#102c2d"/><path d="M281 370v-69a19 19 0 0 1 38 0v69M300 280v90"/><circle cx="310" cy="331" r="2" fill="#dbc695"/>
   <path d="M281 203v-21a19 19 0 0 1 38 0v21Z" fill="#d9bd75" opacity=".8"/><path d="M300 163v40M281 187h38" stroke="#304638"/>
   {[169,393].map(x=><g key={x}><path d={`M${x} 299v-24a15 15 0 0 1 30 0v24Z`} fill="#c8ad74" opacity=".75"/><path d={`M${x+15} 260v39M${x} 280h30`} stroke="#344b3e"/><rect x={x} y="318" width="30" height="29" rx="1" fill="#d5bd82" opacity=".5"/><path d={`M${x+15} 318v29M${x} 332h30`} stroke="#344b3e"/></g>)}
   <path d="M137 370h326m-203 0h80m-86 9h92m-100 10h108m-120 12h132"/>
  </g><g stroke="#93a596" opacity=".6"><path d="M91 392V236m0 41-25-23m25 49 26-34m-26 69-37-31m37 49 29-35M510 392V225m0 60 30-29m-30 62-26-36m26 67 38-34"/><path d="M52 389q-14-56-34-29m530 34q17-66 37-26"/></g>
  <path d="M300 402 260 450h81l-41-48" fill="#d7c6a0" opacity=".12"/>
 </svg>;
}

function MathParts({parts}:{parts?:Part[]}) {
 return <div className="math-question">{parts?.map((p,i)=>p.mathml ? <span key={i} className="math-fragment" dangerouslySetInnerHTML={{__html:p.mathml}}/> : <span key={i}>{p.text}</span>)}</div>;
}

function App() {
 const [session,setSession] = useState<Session|null>(()=>savedSession('lastkey.session'));
 const [state,setState] = useState<State|null>(null);
 const [connection,setConnection] = useState<'connecting'|'online'|'offline'|'replaced'|'expired'>('connecting');
 const [error,setError] = useState('');
 const [busy,setBusy] = useState(false);
 const [subjects,setSubjects] = useState(SUBJECTS);
 const [showRules,setShowRules] = useState(false);
 const socket = useRef<WebSocket|null>(null);
 const pending = useRef(new Map<string,string>());
 const [sending,setSending] = useState(false);
 useEffect(()=>{fetch('/api/subjects').then(r=>r.json()).then(data=>{if(Array.isArray(data))setSubjects(data);}).catch(()=>{});},[]);
 useEffect(()=>{
  if (!session) return;
  let stopped = false, attempts = 0, timer:ReturnType<typeof setTimeout>;
  function connect() {
   if(stopped)return;
   setConnection('connecting');
   const ws = new WebSocket(`${location.protocol==='https:'?'wss':'ws'}://${location.host}/ws/${session!.code}`);
   socket.current = ws;
   ws.onopen=()=>{attempts=0; ws.send(JSON.stringify({token:session!.token}));};
   ws.onmessage=(event)=>{
    const data=JSON.parse(event.data);
    if(data.type==='state') {setState(data.state);setConnection('online');}
    else if(data.type==='error') {setError(data.message); if(data.request_id)pending.current.delete(data.request_id);}
    else if(data.type==='ack') {const type=pending.current.get(data.request_id);pending.current.delete(data.request_id);if(type==='answer')window.dispatchEvent(new Event('lastkey.answer'));}
    setSending(pending.current.size>0);
   };
   ws.onclose=(event)=>{
    if(stopped)return;
    pending.current.clear(); setSending(false);
    if(event.code===4001){setConnection('replaced');return;}
    if(event.code===1008){setConnection('expired');setError('This room or reconnect token is no longer available.');return;}
    setConnection('offline');
    timer=setTimeout(connect,Math.min(1000*2**attempts++,15000));
   };
   ws.onerror=()=>ws.close();
  }
  connect();
  const heartbeat=setInterval(()=>{if(socket.current?.readyState===WebSocket.OPEN)socket.current.send(JSON.stringify({type:'ping'}));},15000);
  return ()=>{stopped=true;clearTimeout(timer);clearInterval(heartbeat);socket.current?.close();pending.current.clear();};
 },[session]);
 function enter(s:Session){sessionStorage.setItem('lastkey.session',JSON.stringify(s));localStorage.setItem('lastkey.last-session',JSON.stringify(s));setError('');setState(null);setSession(s);}
 function leave(){sessionStorage.removeItem('lastkey.session');setSession(null);setState(null);setError('');}
 function send(type:string,extra:Record<string,unknown>={}) {
  if(socket.current?.readyState!==WebSocket.OPEN || connection!=='online'){setError('Wait for the connection to return.');return;}
  const request_id=requestId();pending.current.set(request_id,type);setSending(true);setError('');
  socket.current.send(JSON.stringify({type,request_id,...extra}));
 }
 async function join(name:string,code?:string) {
  setBusy(true);setError('');
  try {
   const r=await fetch(code?`/api/rooms/${encodeURIComponent(code.toUpperCase())}/join`:'/api/rooms',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})});
   const result=await r.json();
   if(!r.ok)throw new Error(typeof result.detail==='string'?result.detail:'Please check your name and room code.');
   enter(result);
  }catch(e){setError(e instanceof Error?e.message:'Unable to reach the game server.');}finally{setBusy(false);}
 }
 const connected=connection==='online';
 return <>
  <header className="site-header"><button className="brand" onClick={()=>{if(!session)setShowRules(false);}} aria-label="The Last Key"><span className="brand-icon"><Icon size={25}/></span><span>THE LAST KEY<small>A COLLECTIVE ESCAPE</small></span></button><div className="header-right">{session?<><span className={`connection ${connected?'live':''}`}><i/>{connection==='replaced'?'Open in another tab':connection==='expired'?'Room unavailable':connected?'Connected':connection==='connecting'?'Connecting…':'Reconnecting…'}</span><button className="text-button" onClick={leave}><Icon name="exit" size={17}/>Exit room</button></>:<><span className="header-note">A little mystery. A lot of teamwork.</span><button className="text-button" onClick={()=>setShowRules(true)}>How to play <span>↗</span></button></>}</div></header>
  {error&&<div className="error-toast" role="alert"><span>{error}</span><button onClick={()=>setError('')} aria-label="Dismiss error">×</button></div>}
  {!session?<Home join={join} busy={busy} resume={enter} showRules={()=>setShowRules(true)}/> : !state ? <main className="loading-screen"><span className="brand-icon"><Icon size={34}/></span><h1>Opening the door…</h1><p>{connection==='expired'?'This room has expired.':connection==='replaced'?'Your session is open in another tab.':'Connecting to your team.'}</p>{['expired','replaced'].includes(connection)&&<button className="primary" onClick={leave}>Return home</button>}</main> : <main className="room-layout"><div className="room-main"><div className="room-top"><div><span className="eyebrow">{state.status==='lobby'?'YOUR TEAM’S STARTING POINT':state.config.game==='math'?'A COLLECTIVE CHALLENGE':'BLACKTHORN MANOR'}</span><h1>{state.status==='lobby'?'The gathering room':state.status==='playing'?(state.config.game==='math'?'The equation room':ROOMS[state.current?.room||0]):state.status==='won'?'Together, you did it.':'A mystery left unsolved.'}</h1></div><RoomCode code={state.code}/></div>
   {state.status==='lobby'?<Lobby state={state} subjects={subjects} send={send} disabled={!connected||sending}/>:state.status==='playing'?<Game state={state} send={send} disabled={!connected||sending}/>:<Results state={state} send={send} disabled={!connected||sending}/>}
  </div><aside className="team-sidebar"><Team state={state} send={send} disabled={!connected||sending}/><Chat state={state} send={send} disabled={!connected}/></aside></main>}
  <footer className="site-footer"><span>THE LAST KEY</span><span>Some doors only open together.</span><button onClick={()=>setShowRules(true)}>Game rules</button></footer>
  {showRules&&<Rules close={()=>setShowRules(false)}/>}
 </>;
}

function Home({join,busy,resume,showRules}:{join:(name:string,code?:string)=>void;busy:boolean;resume:(s:Session)=>void;showRules:()=>void}) {
 const [tab,setTab]=useState<'create'|'join'>('create');
 const [name,setName]=useState('');
 const [code,setCode]=useState(()=>new URLSearchParams(location.search).get('room')||'');
 const [last]=useState<Session|null>(()=>{try{return JSON.parse(localStorage.getItem('lastkey.last-session')||'null');}catch{return null;}});
 useEffect(()=>{if(code)setTab('join');},[]);
 return <main className="home"><div className="home-intro"><div className="eyebrow"><span className="little-line"/> YOUR NEXT GAME NIGHT, UNLOCKED</div><h1>A room full<br/>of secrets.<br/><em>A team with<br className="small-break"/> the answers.</em></h1><p>Step into a curious mansion or put your minds to the test. Different devices. One shared adventure.</p><div className="hero-facts"><span><Icon name="users" size={19}/>2–8 players</span><span><Icon name="clock" size={19}/>15–20 minutes</span><span><Icon name="lock" size={17}/>No sign-up</span></div><button className="story-link" onClick={showRules}>A peek behind the door <span>↗</span></button></div>
  <div className="entry-card"><div className="art-panel"><div className="art-label"><span>01 / THE MANSION</span><span>EST. 1893</span></div><MansionArt/><div className="art-caption"><span className="diamond">✧</span> EVERY CLUE NEEDS A SECOND PAIR OF EYES</div></div><div className="entry-form"><div className="tabs" role="tablist" aria-label="Enter a game"><button role="tab" aria-selected={tab==='create'} className={tab==='create'?'selected':''} onClick={()=>setTab('create')}>Create a room</button><button role="tab" aria-selected={tab==='join'} className={tab==='join'?'selected':''} onClick={()=>setTab('join')}>Join a room</button></div><form onSubmit={e=>{e.preventDefault();join(name,tab==='join'?code:undefined);}}><label htmlFor="name">WHAT SHOULD WE CALL YOU?</label><input id="name" maxLength={24} placeholder="Your display name" value={name} onChange={e=>setName(e.target.value)} required autoComplete="nickname"/>{tab==='join'&&<><label htmlFor="code">YOUR INVITATION CODE</label><input id="code" className="code-input" maxLength={6} minLength={6} pattern="[A-Za-z2-9]{6}" placeholder="ABC123" value={code} onChange={e=>setCode(e.target.value.toUpperCase().replace(/[^A-Z2-9]/g,''))} required autoComplete="off"/></>}<button className="primary" disabled={busy||!name.trim()||(tab==='join'&&code.length!==6)}>{busy?'Opening the door…':tab==='create'?'Begin your adventure':'Meet your team'}<Icon name="arrow" size={19}/></button></form><p className="form-note">{tab==='create'?'You’ll get a code to invite your favorite minds.':'A shared code. A shared mission. A way out together.'}</p>{last&&<button className="resume-button" onClick={()=>resume(last)}>Reconnect to room {last.code} ↗</button>}</div></div>
  <section className="mode-overview"><div className="overview-heading"><span className="eyebrow">TWO WAYS TO FIND YOUR WAY</span><p>Pick your adventure in the lobby.</p></div><div className="mode-description"><span className="mode-icon"><Icon name="key" size={25}/></span><div><h3>Mansion Escape <span>THE ORIGINAL</span></h3><p>Trade secret clues. Decode curious mechanisms. Find the last key.</p></div></div><div className="mode-description"><span className="mode-icon"><Icon name="math" size={25}/></span><div><h3>Math Mode <span>MINDS TOGETHER</span></h3><p>From algebra to calculus. Ten questions. One collective breakthrough.</p></div></div></section>
 </main>;
}

function RoomCode({code}:{code:string}) {
 const [copied,setCopied]=useState(false);
 async function copy(){try{await navigator.clipboard.writeText(`${location.origin}/?room=${code}`);setCopied(true);setTimeout(()=>setCopied(false),2000);}catch{window.prompt('Copy this invitation link',`${location.origin}/?room=${code}`);}}
 return <button className="room-code" onClick={copy} aria-label={`Room code ${code}. Copy invitation link.`}><span>ROOM CODE</span><strong>{code}</strong><Icon name={copied?'check':'copy'} size={18}/><small>{copied?'Link copied':'Invite your team'}</small></button>;
}

function Lobby({state,subjects,send,disabled}:{state:State;subjects:typeof SUBJECTS;send:(t:string,e?:Record<string,unknown>)=>void;disabled:boolean}) {
 const host=state.host===state.you;
 const me=state.players.find(p=>p.id===state.you)!;
 const ready=state.players.length>=2&&state.players.every(p=>p.online&&p.ready);
 function configure(config:Partial<Config>){send('configure',{config:{...state.config,...config}});}
 return <><div className="section-label"><span>01</span> CHOOSE YOUR ADVENTURE { !host&&<small>Your host sets the course</small>}</div><div className="mode-options"><button className={`mode-option ${state.config.game==='mansion'?'active':''}`} disabled={!host||disabled} onClick={()=>configure({game:'mansion'})}><Icon name="key" size={31}/><span className="radio-dot"/><h2>Mansion Escape</h2><p>A mysterious house. Scattered clues.<br/>An exit you can only find together.</p><span className="option-tag">3 ROOMS · 7 PUZZLES</span></button><button className={`mode-option ${state.config.game==='math'?'active':''}`} disabled={!host||disabled} onClick={()=>configure({game:'math'})}><Icon name="math" size={31}/><span className="radio-dot"/><h2>Math Mode</h2><p>One question, many minds.<br/>Solve your way to a shared victory.</p><span className="option-tag">6 SUBJECTS · 10 QUESTIONS</span></button></div>
 {state.config.game==='math'&&<div className="subject-section"><label htmlFor="subject">YOUR FIELD OF DISCOVERY</label><select id="subject" value={state.config.subject} disabled={!host||disabled} onChange={e=>configure({subject:e.target.value})}>{subjects.map(s=><option key={s.id} value={s.id}>{s.label}</option>)}</select><p>Typed answers with a live math preview. Questions are verified before the clock starts.</p></div>}
 <div className="section-label"><span>02</span> SET YOUR PACE</div><div className="pace-options">{[{id:'relaxed',title:'Take your time',desc:'No clock. Just curiosity.',icon:'book'},{id:'timed',title:'A little suspense',desc:'20 minutes to find a way.',icon:'clock'},{id:'pressure',title:'Under pressure',desc:'12 minutes. Five mistakes.',icon:'bulb'}].map(p=><button key={p.id} className={`pace-option ${state.config.pace===p.id?'active':''}`} disabled={!host||disabled} onClick={()=>configure({pace:p.id as Config['pace']})}><Icon name={p.icon}/><strong>{p.title}</strong><span>{p.desc}</span></button>)}</div>
 <div className="lobby-bottom"><div><h3>Good mysteries need good company.</h3><p>{state.players.length<2?'Invite at least one teammate to begin.':ready?'Everyone is ready. Let the mystery unfold.':'Everyone needs to mark themselves ready.'}</p></div><div className="lobby-actions"><button className={me.ready?'secondary ready-button':'secondary'} disabled={disabled} onClick={()=>send('ready',{ready:!me.ready})}>{me.ready?<><Icon name="check" size={17}/>Ready</>:'I’m ready'}</button>{host&&<button className="primary" disabled={disabled||!ready} onClick={()=>send('start')}>Start adventure <Icon name="arrow" size={18}/></button>}</div></div><p className="quiet-note">Changing settings resets readiness so everyone agrees on the adventure.</p></>;
}

function Team({state,send,disabled}:{state:State;send:(t:string,e?:Record<string,unknown>)=>void;disabled:boolean}) {
 return <section className="team-section"><div className="sidebar-heading"><h2>Your fellow minds</h2><span>{state.players.length}/8</span></div><div className="players">{state.players.map((p,i)=><div className="player" key={p.id}><span className={`avatar avatar-${i%4}`}>{p.name.slice(0,1).toUpperCase()}<i className={p.online?'online':''}/></span><div><strong>{p.name}{p.id===state.you&&<small> (you)</small>}</strong><span>{p.id===state.host?'Room host':p.online?'Teammate':'Reconnecting'}</span></div>{state.status==='lobby'&&<span className={`player-status ${p.ready?'ready':''}`}>{p.ready?<Icon name="check" size={17}/>:p.online?'Here':'Away'}</span>}{state.status==='lobby'&&state.host===state.you&&!p.online&&p.id!==state.you&&<button className="remove-player" disabled={disabled} aria-label={`Remove absent player ${p.name}`} onClick={()=>send('kick',{player_id:p.id})}>×</button>}</div>)}</div>{state.status==='lobby'&&state.players.length<8&&<div className="empty-seat"><span>+</span>Room for {8-state.players.length} more curious minds</div>}</section>;
}

function Chat({state,send,disabled}:{state:State;send:(t:string,e?:Record<string,unknown>)=>void;disabled:boolean}) {
 const [text,setText]=useState('');
 const list=useRef<HTMLDivElement>(null);
 useEffect(()=>{list.current?.scrollTo({top:list.current.scrollHeight,behavior:'smooth'});},[state.chat.length]);
 return <section className="chat-section"><div className="sidebar-heading"><h2><Icon name="chat" size={18}/>The conversation</h2><span className="live-label">LIVE</span></div><div className="chat-list" ref={list} role="log" aria-label="Team conversation" aria-live="polite">{!state.chat.length?<div className="chat-empty"><Icon name="chat" size={30}/><h3>Start with a hello.</h3><p>Share ideas, trade clues, and connect the dots here.</p></div>:state.chat.map(m=><div className={`chat-message ${m.player_id===state.you?'mine':''}`} key={m.id}><div><strong>{m.name}</strong><time>{new Date(m.time*1000).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})}</time></div><p>{m.text}</p></div>)}</div><form className="chat-input" onSubmit={e=>{e.preventDefault();if(text.trim()){send('chat',{text});setText('');}}}><input aria-label="Message your team" maxLength={500} placeholder="A thought, a clue, a hello…" value={text} onChange={e=>setText(e.target.value)} disabled={disabled}/><button disabled={disabled||!text.trim()} aria-label="Send message"><Icon name="arrow" size={19}/></button></form><p className="chat-note">The best clue is a conversation.</p></section>;
}

function Game({state,send,disabled}:{state:State;send:(t:string,e?:Record<string,unknown>)=>void;disabled:boolean}) {
 const [answer,setAnswer]=useState('');
 const q=state.current!;
 const input=useRef<HTMLInputElement>(null);
 const isMath=state.config.game==='math';
 const [preview,setPreview]=useState<string|null>(null);
 useEffect(()=>{
  let active=true;
  if(!isMath||!answer){setPreview(null);return;}
  import('./math').then(({previewMath})=>{if(active)setPreview(previewMath(answer));});
  return()=>{active=false;};
 },[answer,isMath]);
 useEffect(()=>{setAnswer('');},[q.id]);
 useEffect(()=>{const clear=()=>setAnswer('');window.addEventListener('lastkey.answer',clear);return()=>window.removeEventListener('lastkey.answer',clear);},[]);
 function insert(symbol:string){const el=input.current;const start=el?.selectionStart??answer.length,end=el?.selectionEnd??start;setAnswer(answer.slice(0,start)+symbol+answer.slice(end));requestAnimationFrame(()=>{el?.focus();el?.setSelectionRange(start+symbol.length,start+symbol.length);});}
 return <><div className="game-stats"><div><span>TEAM SCORE</span><strong>{state.score.toLocaleString()}<small> pts</small></strong></div><div><span>{state.remaining===null?'ELAPSED':'TIME REMAINING'}</span><strong className={state.remaining!==null&&state.remaining<60?'urgent':''}>{formatTime(state.remaining??state.elapsed)}</strong></div><div><span>{state.config.pace==='pressure'?'MISTAKES / LIMIT':'MISTAKES'}</span><strong>{state.mistakes}{state.config.pace==='pressure'&&<small> / 5</small>}</strong></div></div><div className="progress-line"><span>{isMath?'QUESTION':'PUZZLE'} {state.index+1} OF {state.total}</span><div><i style={{width:`${state.index/state.total*100}%`}}/></div><span>{Math.round(state.index/state.total*100)}%</span></div>
 <section className="puzzle-card"><div className="puzzle-heading"><span className="puzzle-mark"><Icon name={isMath?'math':'lock'} size={30}/></span><div><span className="eyebrow">{isMath?SUBJECTS.find(s=>s.id===state.config.subject)?.label:ROOMS[q.room||0]}</span><h2>{q.title}</h2></div></div>{isMath?<><MathParts parts={q.parts}/><p className="answer-instruction">{q.instruction}</p></>:<><p className="puzzle-story">{q.story}</p><div className="private-clues"><div className="clue-title"><Icon name="book" size={17}/><span>FOR YOUR EYES ONLY</span></div>{q.clues?.length?q.clues.map((clue,i)=><p key={i}>{clue}</p>):<p>Your teammates hold this puzzle’s clues. Ask what they see, then help connect the pieces.</p>}<small>Share what you see in the conversation. Other players have different clues.</small></div></>}
 <form className="answer-form" onSubmit={e=>{e.preventDefault();send('answer',{puzzle_id:q.id,answer});}}><label htmlFor="answer">{isMath?'YOUR ANSWER':'UNLOCK THE MECHANISM'}</label><div className="answer-row"><input ref={input} id="answer" value={answer} onChange={e=>setAnswer(e.target.value)} maxLength={160} placeholder={isMath?'Try 1/2, 2x^2, or sqrt(9)':q.format} autoComplete="off" spellCheck={false} disabled={disabled||state.paused||!!state.cooldown}/><button className="primary" disabled={disabled||state.paused||!!state.cooldown||!answer.trim()}>{state.cooldown?`Wait ${state.cooldown}s`:'Submit'}<Icon name="arrow" size={18}/></button></div>{isMath&&<><div className="symbol-buttons" aria-label="Math symbols">{['x','^','/','(',')','sqrt(','pi','*'].map(s=><button key={s} type="button" onClick={()=>insert(s)} disabled={disabled}>{s==='sqrt('?'√':s==='pi'?'π':s==='*'?'×':s}</button>)}</div><div className="answer-preview"><span>NOTATION PREVIEW</span>{preview?<div dangerouslySetInnerHTML={{__html:preview}}/>:<p>{answer?'Check your notation; the server will validate before grading.':'Your expression appears here as you type.'}</p>}</div></>}<p className="submission-note">Anyone can submit. Agree with your team first. Incorrect answers cost 10 points.</p></form>
 {!isMath&&<div className="hint-area">{q.revealed?.map((h,i)=><div className="revealed-hint" key={i}><Icon name="bulb" size={18}/><p>{h}</p></div>)}{(q.revealed?.length||0)<2&&<button className="text-button" disabled={disabled||q.votes?.includes(state.you)} onClick={()=>send('hint',{puzzle_id:q.id,hint_index:q.revealed?.length||0})}><Icon name="bulb" size={17}/>{q.votes?.includes(state.you)?'Your hint vote is in':'Vote to reveal a hint'} <span>{q.votes?.length||0}/{Math.floor(state.players.length/2)+1} votes · −25 pts</span></button>}</div>}
 </section>{!isMath&&!!state.keys.length&&<section className="keys-section"><span className="eyebrow">RECOVERED KEY TEETH</span><div>{state.keys.map(k=><span key={k.number}><Icon size={17}/><small>#{k.number}</small><strong>{k.digit}</strong></span>)}</div></section>}{state.paused&&<p role="status">The game is paused until a teammate reconnects.</p>}</>;
}

function Results({state,send,disabled}:{state:State;send:(t:string,e?:Record<string,unknown>)=>void;disabled:boolean}) {
 return <><section className="result-card"><span className="result-emblem"><Icon name={state.status==='won'?'key':'clock'} size={48}/></span><span className="eyebrow">{state.status==='won'?'THE DOOR IS OPEN':'UNTIL NEXT TIME'}</span><h2>{state.reason}</h2><p>{state.status==='won'?'A shared adventure. A victory for every mind in the room.':'Every clue brings you closer. Gather your team and try again.'}</p><div className="final-score">{state.score.toLocaleString()}<small>TEAM POINTS</small></div><div className="result-facts"><span>{formatTime(state.elapsed)} elapsed</span><span>{state.index}/{state.total} solved</span><span>{state.mistakes} mistakes</span><span>{state.hints_used} hints</span>{!!state.bonus&&<span>+{state.bonus} time bonus</span>}</div><p className="mode-result">{state.config.game==='math'?SUBJECTS.find(s=>s.id===state.config.subject)?.label:'Mansion Escape'} · {state.config.pace==='pressure'?'High Pressure':state.config.pace==='timed'?'Timed':'Relaxed'}</p>{state.host===state.you?<button className="primary" onClick={()=>send('replay')} disabled={disabled}>Gather for another adventure<Icon name="arrow" size={19}/></button>:<p>Your host can take the team back to the lobby.</p>}</section><section className="results-list"><h3>Your journey, revealed</h3>{state.results.map((r,i)=><div className="result-question" key={i}><span className={r.solved?'solved':'unsolved'}>{r.solved?<Icon name="check" size={17}/>:<Icon name="lock" size={17}/>}</span><div><strong>{i+1}. {r.title}</strong>{r.parts&&<MathParts parts={r.parts}/>} {r.answer!==undefined&&<p>Correct answer: <code>{r.answer}</code></p>}</div></div>)}</section></>;
}

function Rules({close}:{close:()=>void}) {
 const button=useRef<HTMLButtonElement>(null);
 useEffect(()=>{button.current?.focus();const escape=(e:KeyboardEvent)=>{if(e.key==='Escape')close();};document.addEventListener('keydown',escape);return()=>document.removeEventListener('keydown',escape);},[close]);
 return <div className="modal-backdrop" onClick={close}><section className="rules-modal" role="dialog" aria-modal="true" aria-labelledby="rules-title" onClick={e=>e.stopPropagation()}><button ref={button} className="close-modal" onClick={close} aria-label="Close rules">×</button><span className="eyebrow">A FEW HOUSE RULES</span><h2 id="rules-title">Some doors only<br/><em>open together.</em></h2><p>Invite 2–8 players by room code. Each person joins on their own phone, tablet, or computer. Your host chooses the game and everyone marks themselves ready.</p><h3>Two adventures</h3><p><strong>Mansion Escape:</strong> Trade private clues through three rooms and six mechanisms. Solve a seventh, final puzzle to escape. Each mechanism awards 100 points; escaping awards 400.</p><p><strong>Math Mode:</strong> Choose your subject and solve ten shared questions. Type numbers, fractions, or expressions with a live MathML preview. Each correct answer awards 100 points. No hints in this mode.</p><h3>Your pace</h3><p><strong>Relaxed:</strong> No deadline. <strong>Timed:</strong> 20 minutes. <strong>High Pressure:</strong> 12 minutes; the fifth wrong answer ends the game.</p><h3>Make every answer count</h3><p>Wrong answers cost 10 points and start a five-second team cooldown. Unreadable math input gets feedback without a penalty. Mansion hints require a majority vote (both players in a two-player team); each costs 25 points, with two available per puzzle.</p><p>Win a timed game to earn one bonus point per full ten seconds left. Scores never go below zero. Disconnect? Return to your original tab to rejoin. The clock pauses if everyone disconnects.</p><button className="primary" onClick={close}>Got it. Let’s find a way.<Icon name="arrow" size={18}/></button></section></div>;
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>);
