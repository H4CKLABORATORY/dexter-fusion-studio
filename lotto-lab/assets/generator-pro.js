/* LOTTO LAB DEXTER — generador determinista, probabilidades verificables.
   No se afirma ventaja predictiva: un sorteo justo es independiente del historial. */
const specs = Object.freeze({
  // Nacionales: matriz y precios vigentes documentados en sitios de las loterías.
  powerball:{name:'Powerball',n:69,k:5,bonus:26,start:'2015-10-07',source:'data/powerball.json',web:'https://www.powerball.com/',price:'$2'},
  megamillions:{name:'Mega Millions',n:70,k:5,bonus:24,start:'2025-04-08',source:'data/megamillions.json',web:'https://www.megamillions.com/',price:'$5'},
  // Estatales: solo reglas específicas contrastadas. Sin historial integrado salvo NY Take 5.
  mdpick3:{name:'Maryland Pick 3 · exacto',n:1000,k:1,bonus:0,kind:'digits',width:3,start:null,source:null,web:'https://www.mdlottery.com/games/pick-3-pick-4-pick-5/',price:'Consultar MD'},
  mdpick4:{name:'Maryland Pick 4 · exacto',n:10000,k:1,bonus:0,kind:'digits',width:4,start:null,source:null,web:'https://www.mdlottery.com/games/pick-3-pick-4-pick-5/',price:'Consultar MD'},
  mdpick5:{name:'Maryland Pick 5 · exacto',n:100000,k:1,bonus:0,kind:'digits',width:5,start:null,source:null,web:'https://www.mdlottery.com/games/pick-3-pick-4-pick-5/',price:'Consultar MD'},
  vapick3:{name:'Virginia Pick 3 · exacto',n:1000,k:1,bonus:0,kind:'digits',width:3,start:null,source:null,web:'https://www.valottery.com/data/draw-games/pick3',price:'Consultar VA'},
  vacash5:{name:'Virginia Cash 5',n:45,k:5,bonus:0,start:null,source:null,web:'https://www.valottery.com/data/draw-games/cash5',price:'$1'},
  cafantasy5:{name:'California Fantasy 5',n:39,k:5,bonus:0,start:null,source:null,web:'https://www.calottery.com/es-us/draw-games/fantasy-5',price:'$1'},
  nytake5:{name:'Nueva York Take 5',n:39,k:5,bonus:0,start:'1992-01-17',source:'data/nytake5.json',historyFormat:'nytake5',web:'https://nylottery.ny.gov/draw-game?game=take5',price:'Consultar NY'},
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
function theoreticalCoverage(game,distinctTickets){
  const total=totalOutcomes(game),tickets=BigInt(distinctTickets);
  if(tickets<1n||tickets>total)throw new RangeError('Cobertura de boletos inválida');
  return Number(tickets)/Number(total);
}
function renderCoverage(){
  const g=specs[selected],n=Number($p('proCoverage').value),probability=theoreticalCoverage(g,n);
  $p('proCoverageChance').textContent=pct(probability)+(g.kind==='digits'?' de acertar el orden exacto':' de acertar la combinación completa');
  $p('proCoverageOdds').textContent='1 entre '+(Number(totalOutcomes(g))/n).toLocaleString('es-ES',{maximumFractionDigits:2})+' en un sorteo, suponiendo '+n+' boletos válidos distintos.';
}
function parseFav(g){
  const raw=$p('proFavorites').value.trim();if(!raw)return [];
  const nums=raw.split(/[,\s;]+/).filter(Boolean).map(v=>Number(v));
  const min=g.bonus?1:0,max=g.bonus?g.n-1:(g.kind==='digits'?g.n-1:99);
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
  if(g.kind==='digits'){
    // Orden exacto: una secuencia de dígitos, no un conjunto de bolas sin reemplazo.
    let value=favorites.length?favorites[0]:pickHash([seed,selected,style,generation].join('|'))%g.n;
    if(!favorites.length){
      const half=Math.floor(g.n/2);
      if(style==='even')value=Math.floor(value/2)*2;
      if(style==='odd')value=Math.floor(value/2)*2+1;
      if(style==='low')value%=half;
      if(style==='high')value=half+value%(g.n-half);
    }
    generation++;
    return {main:[value],bonus:null};
  }
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
// Animación exclusivamente visual: el boleto calculado NO representa un premio real.
// Los efectos son reproducibles y no alteran los números ni las probabilidades.
function renderTicketReveal(container,t,lottery,sequence){
  const reduceMotion=typeof matchMedia==='function'
    && matchMedia('(prefers-reduced-motion: reduce)').matches;
  const items=[...t.main.map(value=>({value,bonus:false}))];
  if(t.bonus!==null&&t.bonus!==undefined)items.push({value:t.bonus,bonus:true});

  // Una generación nueva reemplaza las bolas y efectos anteriores por completo.
  container.classList.remove('lotto-revealing');
  container.replaceChildren();
  items.forEach(({value,bonus},index)=>{
    const ball=document.createElement('span');
    ball.className='ticket-ball'
      +(bonus?' bonus':'')
      +(lottery==='chica'?' chica':'')
      +(specs[lottery]?.kind==='digits'?' digits':'')
      +(reduceMotion?'':' lotto-ball-reveal');
    ball.textContent=String(value).padStart(lottery in specs && specs[lottery].kind==='digits'?specs[lottery].width:2,'0');
    if(bonus)ball.title='Bola especial';
    if(!reduceMotion)ball.style.setProperty('--ball-delay',(95+index*170)+'ms');
    container.append(ball);
  });
  if(reduceMotion)return;

  // Máximo 15 chispas decorativas y sin sonidos: apto para móviles.
  const sparkCount=lottery==='chica'?8:15;
  const revealDelay=440+(items.length-1)*170;
  const colors=['#ffe28a','#ffffff','#71d7ee','#ffc66c','#8ce8b9'];
  for(let i=0;i<sparkCount;i++){
    const spark=document.createElement('span');
    spark.className='lotto-spark';
    spark.setAttribute('aria-hidden','true');
    const hash=pickHash('visual|'+lottery+'|'+sequence+'|'+i);
    const spreadX=(hash%231)-115;
    const spreadY=(Math.floor(hash/231)%185)-90;
    const rotation=(Math.floor(hash/42735)%481)-240;
    spark.style.setProperty('--spark-x',spreadX+'px');
    spark.style.setProperty('--spark-y',spreadY+'px');
    spark.style.setProperty('--spark-rot',rotation+'deg');
    spark.style.setProperty('--spark-delay',(revealDelay+(i%5)*38)+'ms');
    spark.style.setProperty('--spark-color',colors[i%colors.length]);
    spark.addEventListener('animationend',()=>spark.remove(),{once:true});
    container.append(spark);
  }
  // Reinicia el brillo si el usuario vuelve a generar inmediatamente.
  void container.offsetWidth;
  container.classList.add('lotto-revealing');
}
function outputTicket(t){
  const g=specs[selected];const div=$p('proTicket');
  renderTicketReveal(div,t,selected,generation);
  lastNumbers=t.main.concat(t.bonus?[t.bonus]:[]);
  $p('proTicketCount').textContent='Combinación #'+nf(generation);
  $p('proCopy').disabled=false;
  const b=g.bonus?' · especial '+String(t.bonus).padStart(2,'0'):'';
  $p('proTicketNote').textContent='Combinación calculada y revelada. Selección por regla «'+$p('proStyle').selectedOptions[0].textContent+'»'+b+'. La celebración es visual: no indica un premio ganado ni aumenta la probabilidad del siguiente sorteo.';
  renderProbabilities();
}
function histRows(payload,g){
  if(!payload||!Array.isArray(payload.rows)||payload.game!==selected)return [];
  const seen=new Set(),rows=[];
  for(const row of payload.rows){
    if(payload.schema===3&&g.historyFormat==='nytake5'){
      if(!row||typeof row.date!=='string'||row.date<g.start||!['midday','evening'].includes(row.period)||!Array.isArray(row.main))continue;
      if(row.main.length!==5||new Set(row.main).size!==5||!row.main.every(n=>Number.isInteger(n)&&n>=1&&n<=g.n))continue;
      const key=row.date+'|'+row.period;
      if(seen.has(key))continue;
      seen.add(key);rows.push({date:row.date,period:row.period,main:[...row.main],bonus:null});
      continue;
    }
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
    $p('proHistoryStatus').textContent=selected==='chica'?'PANI: historial digital completo sin fuente verificable integrada. No se fabrican resultados.':'Este juego tiene reglas oficiales comprobadas, pero su historial todavía no está incorporado. No se inventan sorteos.';
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
    if(fetched[key].count&&verified.length<fetched[key].count*.97)throw Error('Archivo histórico incompleto o incompatible');
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
  renderCoverage();
  $p('proPerNumber').textContent=pct(g.kind==='digits'?0.1:individual);
  $p('proPerNumberLabel').textContent=g.kind==='digits'?'Probabilidad de un dígito en una posición':g.k===1?'De que salga un número de 00 a 99':'De que salga una bola principal específica';
  $p('proModel').textContent=g.kind==='digits'?g.width+' dígitos ordenados · 10^'+g.width+' resultados posibles':g.k===1?'100 números posibles · un número ganador · modelo uniforme':g.k+' de '+g.n+(g.bonus?' + 1 especial de '+g.bonus:'')+' · combinatoria exacta';
  const chips=$p('proProbGrid');chips.replaceChildren();
  if(g.kind==='digits'){
    const chosen=lastNumbers[0],digits=chosen===undefined?'':String(chosen).padStart(g.width,'0');
    for(let i=0;i<=9;i++){
      const item=document.createElement('div');item.className='prob-chip'+(digits.includes(String(i))?' favored':'');
      const n=document.createElement('strong');n.textContent=i;
      const text=document.createElement('span');text.textContent='10 % por posición';
      const info=document.createElement('small');info.textContent='Sin historial oficial cargado';
      item.append(n,text,info);chips.append(item);
    }
    $p('proSpecialOdds').textContent='Sin bola especial';
    $p('proEntropy').textContent=Math.log2(g.n).toFixed(2)+' bits';
    $p('proModeNote').textContent='Acierto completo en orden exacto: 1 en '+nf(g.n)+'. Un dígito en una posición: 10 %. No equivale a un sorteo de '+g.n+' bolas distintas.';
    return;
  }
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
  $p('proFavorites').placeholder=g.kind==='digits'?'Ej. '+('0'.repeat(g.width-1))+'7':g.k===1?'Ej. 07':'Ej. 7, 13, 28';
  $p('proFavorites').value='';
  $p('proPrice').textContent=g.price;
  $p('proOfficial').href=g.web;
  $p('proOfficial').textContent=selected==='chica'?'Información oficial PANI ↗':selected==='powerball'||selected==='megamillions'?'Consultar premio acumulado oficial ↗':'Consultar reglas y resultados oficiales ↗';
  $p('proTicketNote').textContent=g.kind==='digits'?'Modalidad de '+g.width+' dígitos: para acertar en orden exacto, cada dígito debe coincidir.':selected==='chica'?'La Chica: número de dos cifras (00–99), cálculo bajo equiprobabilidad.':'Prueba un criterio matemático de selección. Los resultados dependen del método elegido.';
  renderProbabilities();loadVerified();
}
$p('proGame').addEventListener('change',updateGame);
$p('proStyle').addEventListener('change',renderProbabilities);
$p('proCoverage').addEventListener('change',renderCoverage);
$p('proGenerate').addEventListener('click',()=>{
  try{const t=createTicket();outputTicket(t);}
  catch(e){$p('proTicketNote').textContent=e.message;$p('proTicketNote').style.color='#ffcaac';return;}
  $p('proTicketNote').style.color='';
});
$p('proCopy').addEventListener('click',async()=>{
  if(!lastNumbers.length)return;
  const g=specs[selected];
  const text=lastNumbers.slice(0,g.k).map(v=>String(v).padStart(g.kind==='digits'?g.width:2,'0')).join(' ') +(g.bonus?' | '+String(lastNumbers.at(-1)).padStart(2,'0'):'');
  try{await navigator.clipboard.writeText(text);$p('proTicketNote').textContent='Copiado: '+text;}catch{$p('proTicketNote').textContent='Selecciona y copia: '+text;}
});
updateGame();