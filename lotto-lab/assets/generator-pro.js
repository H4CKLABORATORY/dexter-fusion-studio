/* LOTTO LAB DEXTER — generador determinista, probabilidades verificables.
   No se afirma ventaja predictiva: un sorteo justo es independiente del historial. */
const specs = Object.freeze({
  powerball:{name:'Powerball',n:69,k:5,bonus:26,start:'2015-10-07',source:'data/powerball.json',web:'https://www.powerball.com/',price:'$2'},
  megamillions:{name:'Mega Millions',n:70,k:5,bonus:24,start:'2025-04-08',source:'data/megamillions.json',web:'https://www.megamillions.com/',price:'$5'},
  chica:{name:'La Chica · Honduras',n:100,k:1,bonus:0,start:null,source:null,web:'https://www.pani.gob.hn/',price:'Consultar PANI'}
});
// Semilla fija e interna, no editable por visitantes ni predictiva.
const INTERNAL_SEED='LOTTO-LAB-DEXTER-2.0';
const $p = id=>document.getElementById(id);
let selected='powerball',generation=0,verified=[],loading=0,lastNumbers=[];
let fetched={};
const nf=n=>Number(n).toLocaleString('es-ES');
const pct=n=>(n*100).toLocaleString('es-ES',{minimumFractionDigits:2,maximumFractionDigits:6})+' %';
function pickHash(s){
  let h=2166136261;for(let i=0;i<s.length;i++){h=Math.imul(h^s.charCodeAt(i),16777619);}
  h ^= h>>>16; h=Math.imul(h,0x7feb352d);h ^= h>>>15;h=Math.imul(h,0x846ca68b);return(h^(h>>>16))>>>0;
}
function chooseBig(n,k){let t=1n;for(let i=1;i<=k;i++)t=t*BigInt(n-k+i)/BigInt(i);return t}
function totalOutcomes(g){return chooseBig(g.n,g.k)*BigInt(g.bonus||1);}
function theoretical(g){return g.k/g.n;}
function parseFav(g){
  const raw=$p('proFavorites').value.trim();if(!raw)return [];
  const nums=raw.split(/[,\s;]+/).filter(Boolean).map(v=>Number(v));
  const min=g.bonus?1:0,max=g.bonus?g.n:99;
  if(nums.some(v=>!Number.isInteger(v)||v<min||v>max)||new Set(nums).size!==nums.length||nums.length>g.k)
    throw Error('Escribe hasta '+g.k+' números diferentes entre '+String(min).padStart(2,'0')+' y '+max+'.');
  return nums;
}
function historicalFrequency(g){
  const hits=new Uint32Array(g.n+(g.bonus?1:0));
  for(const row of verified){for(const v of row.main)if(v>=1&&v<=g.n)hits[v]++;}
  return hits;
}
function createTicket(){
  const g=specs[selected],style=$p('proStyle').value,seed=INTERNAL_SEED;
  const favorites=parseFav(g);
  if((style==='hot'||style==='cold')&&!verified.length)throw Error('Este modo requiere historial verificado; espera la descarga o selecciona otro modo.');
  const counts=historicalFrequency(g);
  const values=Array.from({length:g.n},(_,i)=>g.bonus?i+1:i);
  const ranked=values.map(v=>{
    const tie=pickHash([seed,selected,style,generation,v].join('|'))/4294967296;
    const frequency=counts[v];
    const score=style==='hot'?-frequency+tie*.001:style==='cold'?frequency+tie*.001:tie;
    return {v,score};
  }).sort((a,b)=>a.score-b.score||a.v-b.v).map(x=>x.v);
  let pool=ranked;
  if(style==='even')pool=ranked.filter(x=>x%2===0);
  if(style==='odd')pool=ranked.filter(x=>x%2===1);
  if(style==='low')pool=ranked.filter(x=>g.bonus?x<=Math.floor(g.n/2):x<50);
  if(style==='high')pool=ranked.filter(x=>g.bonus?x>Math.floor(g.n/2):x>=50);
  const chosen=[...favorites];
  if(style==='balanced'&&g.k===5){
    const even=ranked.filter(x=>x%2===0&&!chosen.includes(x));
    const odd=ranked.filter(x=>x%2!==0&&!chosen.includes(x));
    const target=pickHash(seed+'|'+generation)%2?2:3;
    for(const [list,need] of [[even,target],[odd,5-target]]){
      const have=chosen.filter(x=>list===even?x%2===0:x%2===1).length;
      chosen.push(...list.slice(0,Math.max(0,need-have)));
    }
  }
  for(const v of pool)if(chosen.length<g.k&&!chosen.includes(v))chosen.push(v);
  for(const v of ranked)if(chosen.length<g.k&&!chosen.includes(v))chosen.push(v);
  if(chosen.length!==g.k)throw Error('No fue posible completar una combinación válida.');
  chosen.sort((a,b)=>a-b);
  // Bola especial en otro bombo: elección determinista, NO basada en el futuro.
  const bonus=g.bonus?1+(pickHash([seed,selected,'especial',generation].join('|'))%g.bonus):null;
  generation++;
  return {main:chosen,bonus};
}
function outputTicket(t){
  const g=specs[selected];const div=$p('proTicket');div.replaceChildren();
  for(const value of t.main){const x=document.createElement('span');x.className='ticket-ball'+(selected==='chica'?' chica':'');x.textContent=String(value).padStart(2,'0');div.append(x)}
  if(t.bonus){const x=document.createElement('span');x.className='ticket-ball bonus';x.textContent=String(t.bonus).padStart(2,'0');x.title='Bola especial';div.append(x)}
  lastNumbers=t.main.concat(t.bonus?[t.bonus]:[]);
  $p('proTicketCount').textContent='Combinación #'+nf(generation);
  $p('proCopy').disabled=false;
  const b=g.bonus?' · especial '+String(t.bonus).padStart(2,'0'):'';
  $p('proTicketNote').textContent='Selección por regla «'+$p('proStyle').selectedOptions[0].textContent+'»'+b+'. Este método NO incrementa la probabilidad del próximo sorteo.';
  renderProbabilities();
}
function histRows(payload,g){
  if(!payload||!Array.isArray(payload.rows)||payload.game!==selected)return [];
  const seen=new Set();
  const rows=[];
  for(const row of payload.rows){
    if(!Array.isArray(row)||row.length!==7||typeof row[0]!=='string'||row[0]<g.start||seen.has(row[0]))continue;
    const main=row.slice(1,6),bonus=row[6];
    if(!main.every(n=>Number.isInteger(n)&&n>=1&&n<=g.n)||new Set(main).size!==5||!Number.isInteger(bonus)||bonus<1||bonus>g.bonus)continue;
    seen.add(row[0]);rows.push({date:row[0],main,bonus});
  }
  return rows;
}
async function loadVerified(){
  const g=specs[selected],stamp=++loading;verified=[];
  if(!g.source){
    $p('proHistoryStatus').textContent='PANI: historial digital completo sin fuente verificable integrada. No se fabrican resultados.';
    renderProbabilities();return;
  }
  $p('proHistoryStatus').textContent='Sincronizando biblioteca oficial '+g.name+'…';
  try{
    const key=selected;
    if(!fetched[key]){
      const r=await fetch(g.source,{cache:'no-cache'});if(!r.ok)throw Error('HTTP '+r.status);
      const obj=await r.json();fetched[key]=obj;
    }
    if(stamp!==loading)return;
    verified=histRows(fetched[key],g);
    if(fetched[key].count&&verified.length>fetched[key].count)throw Error('Archivo inconsistente');
    $p('proHistoryStatus').textContent=nf(verified.length)+' sorteos verificados con reglas vigentes, extraídos de un archivo que incluye sorteos anteriores. Fecha más reciente disponible: '+(verified.map(r=>r.date).sort().at(-1)||'—')+'.';
  }catch(e){
    if(stamp!==loading)return;
    $p('proHistoryStatus').textContent='Historial no disponible: '+e.message+'. Se conservan solo probabilidades matemáticas exactas.';
  }
  renderProbabilities();
}
function wilson(h,n){
  if(!n)return null;
  const z=1.96,p=h/n,d=1+z*z/n,m=(p+z*z/(2*n))/d,delta=z*Math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d;
  return [Math.max(0,m-delta),Math.min(1,m+delta)];
}
function renderProbabilities(){
  const g=specs[selected],total=totalOutcomes(g),individual=theoretical(g),count=verified.length;
  $p('proOdds').textContent='1 en '+nf(total);
  $p('proPerNumber').textContent=pct(individual);
  $p('proPerNumberLabel').textContent=g.k===1?'De que salga un número de 00 a 99':'De que salga una bola principal específica';
  $p('proModel').textContent=g.k===1?'100 números posibles · un número ganador · modelo uniforme':g.k+' de '+g.n+' + 1 especial de '+g.bonus+' · combinatoria exacta';
  const chips=$p('proProbGrid');chips.replaceChildren();
  const counts=historicalFrequency(g);
  const denominator=g.k?count:0;
  const chosen=new Set(lastNumbers.slice(0,g.k));
  const percentTheo=pct(individual);
  for(let i=g.bonus?1:0;i<=(g.bonus?g.n:99);i++){
    const item=document.createElement('div');item.className='prob-chip'+(chosen.has(i)?' favored':'');
    const n=document.createElement('strong');n.textContent=String(i).padStart(2,'0');
    const theoreticalText=document.createElement('span');theoreticalText.textContent=percentTheo+' teórico';
    const sample=document.createElement('small');
    sample.textContent=denominator?pct(counts[i]/denominator)+' histórico':'Sin archivo histórico';
    item.append(n,theoreticalText,sample);
    if(denominator){
      const ci=wilson(counts[i],denominator);
      item.title='Frecuencia observada: '+counts[i]+'/'+denominator+' sorteos. Intervalo descriptivo 95 %: '+pct(ci[0])+' – '+pct(ci[1])+'. No es un pronóstico.';
    }
    chips.append(item);
  }
  $p('proSpecialOdds').textContent=g.bonus?pct(1/g.bonus):'No hay bola especial';
  $p('proEntropy').textContent=Math.log2(Number(total)).toFixed(2)+' bits';
  const mode=$p('proStyle').value;
  $p('proModeNote').textContent=(mode==='hot'||mode==='cold')
    ?'Ordena números usando frecuencias históricas de las reglas vigentes. La ventaja predictiva NO está demostrada; cada bola conserva la misma probabilidad teórica.'
    :'Las probabilidades mostradas son del sorteo, NO la probabilidad que asigna tu filtro a cada boleto. Cambiar paridad, fechas o categorías no mejora las probabilidades de acertar.';
}
function updateGame(){
  selected=$p('proGame').value;generation=0;lastNumbers=[];
  const g=specs[selected];$p('proTicket').innerHTML='<span class="ticket-empty">Tu combinación aparecerá aquí.</span>';
  $p('proTicketCount').textContent='LISTO PARA GENERAR';
  $p('proCopy').disabled=true;
  $p('proFavorites').placeholder=g.k===1?'Ej. 07':'Ej. 7, 13, 28';
  $p('proFavorites').value='';
  $p('proPrice').textContent=g.price;
  $p('proOfficial').href=g.web;
  $p('proOfficial').textContent=g.bonus?'Consultar premio acumulado ↗':'Información oficial PANI ↗';
  $p('proTicketNote').textContent=g.k===1?'La Chica: número de dos cifras (00–99), cálculo bajo equiprobabilidad.':'Prueba un criterio matemático de selección. Los resultados dependen del método elegido.';
  renderProbabilities();loadVerified();
}
$p('proGame').addEventListener('change',updateGame);
$p('proStyle').addEventListener('change',renderProbabilities);
$p('proGenerate').addEventListener('click',()=>{
  try{const t=createTicket();outputTicket(t);}
  catch(e){$p('proTicketNote').textContent=e.message;$p('proTicketNote').style.color='#ffcaac';return;}
  $p('proTicketNote').style.color='';
});
$p('proCopy').addEventListener('click',async()=>{
  if(!lastNumbers.length)return;
  const g=specs[selected];
  const text=lastNumbers.slice(0,g.k).map(v=>String(v).padStart(2,'0')).join(' ') +(g.bonus?' | '+String(lastNumbers.at(-1)).padStart(2,'0'):'');
  try{await navigator.clipboard.writeText(text);$p('proTicketNote').textContent='Copiado: '+text;}catch{$p('proTicketNote').textContent='Selecciona y copia: '+text;}
});
updateGame();