/**
 * LOTTO LAB — emulador educativo reproducible de reglas, NO sorteo oficial.
 * Cada sorteo virtual se hace con RNG criptográfico + rechazo sin sesgo módulo.
 * Un histórico se muestra como REPRODUCCIÓN, no como sorteo nuevo.
 */
import {GAME_TIERS} from './scientific-math.mjs';

export function uniformInt(max,source){
  if(!Number.isSafeInteger(max)||max<1||max>0x100000000)throw RangeError('Límite aleatorio inválido');
  const rng=source||(()=>{
    if(!globalThis.crypto?.getRandomValues)throw Error('El navegador requiere crypto.getRandomValues');
    const bytes=new Uint32Array(1);globalThis.crypto.getRandomValues(bytes);return bytes[0];
  });
  const limit=Math.floor(0x100000000/max)*max;
  for(let attempts=0;attempts<100000;attempts++){
    const v=rng();
    if(!Number.isSafeInteger(v)||v<0||v>=0x100000000)throw RangeError('Fuente aleatoria inválida');
    if(v<limit)return v%max;
  }
  throw Error('Fuente aleatoria defectuosa: demasiados rechazos');
}
export function validDraw(game,ticket){
  if(!game||!ticket||!Array.isArray(ticket.main))return false;
  if(game.kind==='digits'){
    return ticket.main.length===1&&Number.isInteger(ticket.main[0])&&
      ticket.main[0]>=0&&ticket.main[0]<game.n&&ticket.bonus==null;
  }
  const low=game.k===1&&!game.bonus?0:1;
  const high=game.k===1&&!game.bonus?game.n-1:game.n;
  return ticket.main.length===game.k&&new Set(ticket.main).size===game.k&&
    ticket.main.every(x=>Number.isInteger(x)&&x>=low&&x<=high)&&
    (game.bonus?Number.isInteger(ticket.bonus)&&ticket.bonus>=1&&ticket.bonus<=game.bonus:ticket.bonus==null);
}
export function fairDraw(game,random=uniformInt){
  if(!game||!Number.isSafeInteger(game.n)||!Number.isSafeInteger(game.k)||game.n<1||game.k<1||game.k>game.n)
    throw RangeError('Reglas de la lotería inválidas');
  if(game.kind==='digits'||game.k===1&&!game.bonus){
    const draw={main:[random(game.n)],bonus:null};
    if(!validDraw(game,draw))throw Error('Sorteo fuera de rango');
    return draw;
  }
  // Fisher-Yates parcial uniforme: exactamente k elementos sin reemplazo.
  const range=Array.from({length:game.n},(_,i)=>i+1);
  const main=[];
  for(let i=0;i<game.k;i++){
    const j=i+random(game.n-i);
    if(!Number.isSafeInteger(j)||j<i||j>=game.n)throw Error('RNG devolvió posición inválida');
    [range[i],range[j]]=[range[j],range[i]];
    main.push(range[i]);
  }
  main.sort((a,b)=>a-b);
  const bonus=game.bonus?1+random(game.bonus):null;
  const ticket={main,bonus};
  if(!validDraw(game,ticket))throw Error('Sorteo inválido');
  return ticket;
}
export function matchDraw(game,ticket,draw,key=''){
  if(!validDraw(game,ticket)||!validDraw(game,draw))throw RangeError('Boleto o sorteo no corresponden a las reglas');
  if(game.kind==='digits'){
    const t=String(ticket.main[0]).padStart(game.width,'0');
    const d=String(draw.main[0]).padStart(game.width,'0');
    const mainHits=[...t].filter((v,i)=>v===d[i]).length;
    return {mainHits,bonusHit:null,exact:mainHits===game.width,
      tier:mainHits===game.width?'Orden exacto':'Sin acierto exacto',prizeVerified:false};
  }
  const chosen=new Set(ticket.main);
  const mainHits=draw.main.filter(x=>chosen.has(x)).length;
  const bonusHit=game.bonus?ticket.bonus===draw.bonus:null;
  const exact=mainHits===game.k&&(!game.bonus||bonusHit);
  const category=GAME_TIERS[key]?.[mainHits+'|'+Number(bonusHit===true)];
  return {mainHits,bonusHit,exact,tier:category?.label||(exact?'Combinación completa':'Sin categoría verificada'),
    prizeVerified:Boolean(category),prizeLabel:category?.prize??null};
}
export function parseUserTicket(game,text){
  const input=String(text||'').trim();
  if(game.kind==='digits'||game.k===1&&!game.bonus){
    const width=game.width||2;
    if(!new RegExp('^[0-9]{1,'+width+'}$').test(input))throw Error('Escribe entre 1 y '+width+' dígitos (admite ceros iniciales)');
    const result={main:[Number(input)],bonus:null};
    if(!validDraw(game,result))throw Error('Número fuera de rango');
    return result;
  }
  const parts=input.split('|');
  if(parts.length>(game.bonus?2:1))throw Error('Formato inválido; usa una barra | antes de la bola especial');
  const main=parts[0].split(/[\s,;]+/).filter(Boolean).map(Number);
  const special=game.bonus?Number(parts[1]?.trim()):null;
  if(main.length!==game.k||main.some(n=>!Number.isInteger(n))||
    (game.bonus&&(!parts[1]||!Number.isInteger(special))))
    throw Error('Escribe '+game.k+' números'+(game.bonus?' y la especial después de |':''));
  const result={main:main.slice().sort((a,b)=>a-b),bonus:special};
  if(!validDraw(game,result))throw Error('Números repetidos, fuera de rango o bola especial inválida');
  return result;
}
export function chooseHistorical(rows,game,random=uniformInt){
  if(!Array.isArray(rows)||!rows.length)throw Error('No hay historial oficial comparable en este juego');
  const eligible=rows.filter(row=>validDraw(game,row));
  if(!eligible.length)throw Error('No hay sorteos válidos de las reglas actuales');
  const item=eligible[random(eligible.length)];
  return {main:item.main.slice().sort((a,b)=>a-b),bonus:item.bonus??null,
    date:item.date||'sin fecha',period:item.period||null};
}
export function simulateMany(game,ticket,key,trialCount=1000,random=uniformInt){
  if(!validDraw(game,ticket))throw Error('Introduce un boleto válido');
  if(!Number.isInteger(trialCount)||trialCount<1||trialCount>10000)throw RangeError('Cantidad inválida de simulaciones');
  const buckets=new Uint32Array(game.kind==='digits'?game.width+1:game.k+1);
  let exact=0,secondary=0,prizeCount=0,mainHitSum=0;
  for(let i=0;i<trialCount;i++){
    const sample=fairDraw(game,random);
    const match=matchDraw(game,ticket,sample,key);
    buckets[match.mainHits]++;
    mainHitSum+=match.mainHits;
    if(match.exact)exact++;
    if(match.prizeVerified)prizeCount++;
    if(!match.exact&&match.mainHits>0)secondary++;
  }
  return {draws:trialCount,exact,anyKnownPrize:prizeCount,secondary,meanHits:mainHitSum/trialCount,
    buckets:Array.from(buckets),fairBaseline:game.kind==='digits'?game.width/10:
      game.k===1&&!game.bonus?1/game.n:game.k*game.k/game.n};
}
export function assessHistorical(rows,game,ticket,key=''){
  if(!validDraw(game,ticket))throw RangeError('Boleto inválido');
  if(!Array.isArray(rows)||!rows.length)throw Error('Este juego todavía no tiene historial verificado');
  let compared=0,exact=0,anyKnownPrize=0,high=0,bonusHits=0,latestExact=null;
  for(const row of rows){
    if(!validDraw(game,row))continue;
    const match=matchDraw(game,ticket,row,key);
    compared++;if(match.exact){exact++;if(!latestExact||row.date>latestExact)latestExact=row.date}
    if(match.prizeVerified)anyKnownPrize++;
    high=Math.max(high,match.mainHits);
    if(match.bonusHit)bonusHits++;
  }
  if(!compared)throw Error('Historial incompatible con las reglas del juego');
  return {compared,exact,anyKnownPrize,highestMainMatches:high,bonusHits,latestExact};
}
/** Fuentes de tendencias: tres ventanas independientes sin presentarlas como pronóstico. */
export function rollingStats(rows,game,windows=[50,200,500]){
  if(game.kind==='digits')return [];
  const eligible=(rows||[]).filter(row=>validDraw(game,row)).slice().sort((a,b)=>
    ((b.date||'')+'|'+(b.period||'')).localeCompare((a.date||'')+'|'+(a.period||'')));
  return windows.map(window=>{
    const sample=eligible.slice(0,window),count=new Uint32Array(game.n+1);
    for(const row of sample)for(const ball of row.main)count[ball]++;
    const expected=sample.length*game.k/game.n;
    const ranking=Array.from({length:game.n},(_,i)=>({number:i+1,count:count[i+1]}))
      .sort((a,b)=>b.count-a.count||a.number-b.number);
    let odd=0,low=0;
    for(const row of sample)for(const ball of row.main){
      if(ball%2)odd++;
      if(ball<=Math.floor(game.n/2))low++;
    }
    return {window,draws:sample.length,expectedPerNumber:expected,top:ranking.slice(0,5),
      cold:ranking.slice(-5).reverse(),oddPercent:sample.length?odd/(sample.length*game.k):null,
      lowPercent:sample.length?low/(sample.length*game.k):null};
  });
}
