const $ = id => document.getElementById(id);
let selectedRun = null;
async function api(path, body) {
  const response = await fetch(path, {method:body===undefined?'GET':'POST',headers:{'Content-Type':'application/json'},...(body===undefined?{}:{body:JSON.stringify(body)})});
  const value = await response.json();
  if (!response.ok) throw Error(typeof value.detail==='string'?value.detail:JSON.stringify(value.detail));
  return value;
}
function notice(value) { $('notice').textContent=value; }
function render(run) {
  selectedRun = run;
  const active = new Set(run.selected.map(s=>s.component_id));
  document.querySelectorAll('.slot').forEach(el=>el.classList.toggle('active',active.has(el.dataset.id)));
  $('active').textContent=`${active.size} active · tier ${run.tier}`;
  $('metrics').replaceChildren();
  for (const [label,value] of [['Active components',active.size],['Latency (ms)',run.latency_ms.toFixed(2)],['MACs',run.macs],['Cache hits',run.cache_hits]]) {
    const el=document.createElement('div'),strong=document.createElement('strong'),small=document.createElement('small');
    strong.textContent=value;small.textContent=label;el.append(strong,small);$('metrics').append(el);
  }
  $('trace').textContent=JSON.stringify(run,null,2);
  $('perception-status').textContent=run.perception
    ? 'Perception — '+[3,4,5].map(d=>`D${d}: ${run.perception.perceived_outputs[String(d)]===null?'not yet perceptible':'perceptible'}`).join(' · ')
    : 'Historical run: dimensional perception was not evaluated.';
  $('output').textContent=JSON.stringify({perceived_outputs:run.perception?.perceived_outputs??null,
    perception_rule:run.perception?.rule_version??'not evaluated in this historical run',
    raw_probabilities:run.output,semantics:run.output_semantics,meso:run.meso,macro:run.macro},null,2);
  $('replay').disabled=false;
}
async function history() {
  const records=await api('/history');$('history').replaceChildren();
  for(const record of records.filter(r=>r.kind==='execute').reverse()) {
    const b=document.createElement('button');b.type='button';b.textContent=`${record.timestamp.slice(11,19)} · tier ${record.payload.tier} · ${record.id.slice(0,8)}`;
    b.onclick=()=>render({id:record.id,...record.payload});$('history').append(b);
  }
}
async function action(fn) {try{await fn();}catch(e){notice(e.message);}}
$('execution').onsubmit=e=>{e.preventDefault();action(async()=>{const features=$('features').value.split(',').map(v=>Number(v.trim()));if(features.length!==8||features.some(v=>!Number.isFinite(v)))throw Error('Enter exactly eight finite numbers.');const run=await api('/execute',{features,tier:Number($('tier').value)});render(run);notice(`Persisted run ${run.id.slice(0,12)}.`);await history();});};
$('contact').onsubmit=e=>{e.preventDefault();action(async()=>{const result=await api('/events',{actor_ref:'local-owner',modality:$('modality').value,timestamp:new Date().toISOString(),observed_features:JSON.parse($('observed').value),source_ref:$('source').value,uncertainty:.8});const record=await api(`/runs/${result.field_run}`);render({id:record.id,...record.payload});$('output').textContent=JSON.stringify(result,null,2);notice(result.response);await history();});};
$('checkpoint').onclick=()=>action(async()=>{const saved=await api('/checkpoint',{});notice(`Saved checkpoint ${saved.id}.`);});
$('replay').onclick=()=>action(async()=>{const result=await api(`/runs/${selectedRun.id}/replay`,{});notice(result.exact?'Exact replay verified against stored neural outputs.':'Replay mismatch: inspect trace.');});
$('audio-form').onsubmit=e=>{e.preventDefault();action(async()=>{
  const file=$('audio-file').files[0];
  if(!file)throw Error('Choose a PCM WAV file.');
  const response=await fetch('/audio',{method:'POST',headers:{'Content-Type':'audio/wav'},body:file});
  const result=await response.json();
  if(!response.ok)throw Error(result.detail||'Audio analysis failed.');
  const record=await api(`/runs/${result.contact.field_run}`);
  render({id:record.id,...record.payload});
  $('output').textContent=JSON.stringify(result.analysis,null,2);
  const player=document.createElement('audio');player.controls=true;player.src=`/artifacts/${result.source_hash}`;
  const link=document.createElement('a');link.href=`/artifacts/${result.analysis_hash}`;link.textContent='Open measured acoustic evidence';link.target='_blank';link.rel='noopener';
  $('audio-artifacts').replaceChildren(player,link);
  notice('Audio measured and persisted. Meaning remains unresolved.');await history();
});};
await action(async()=>{await api('/health');$('connection').textContent='Connected to local field';for(let d=0;d<5;d++){const section=document.createElement('div');section.className='dimension';const label=document.createElement('span');label.textContent=`Dimension ${d+1} · source semantics unresolved`;const grid=document.createElement('div');grid.className='slots';for(let g=0;g<64;g++){const slot=document.createElement('span');slot.className='slot';slot.dataset.id=`d${d}:g${g}`;slot.textContent=g;slot.title=`Dimension ${d+1}, binary slot ${g}`;grid.append(slot);}section.append(label,grid);$('dimensions').append(section);}const capabilities=await api('/capabilities');for(const [name,status] of Object.entries(capabilities)){const dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=name.replaceAll('_',' ');dd.textContent=status;$('capabilities').append(dt,dd);}await history();});
