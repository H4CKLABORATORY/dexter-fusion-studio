/**
 * LOTTO LAB DEXTER · números de la suerte del día.
 *
 * Selecciones educativas: muestran números de frecuencia histórica destacada
 * cuando hay datos verificables. No atribuyen ventaja sobre un sorteo justo.
 * Clave diaria UTC + contador local: misma fecha/selección, mismo resultado.
 */
export function dayKeyUTC(now=new Date()){
  if(!(now instanceof Date)||!Number.isFinite(now.getTime()))throw TypeError('Fecha inválida');
  return now.toISOString().slice(0,10);
}
export function dailyHash(text){
  let h=2166136261;
  for(let i=0;i<text.length;i++){h=Math.imul(h^text.charCodeAt(i),16777619);}
  h^=h>>>16;h=Math.imul(h,0x7feb352d);h^=h>>>15;
  h=Math.imul(h,0x846ca68b);return(h^h>>>16)>>>0;
}
function validateGame(game){
  if(!game||!Number.isSafeInteger(game.n)||!Number.isSafeInteger(game.k)||game.k<1||game.k>game.n)
    throw new Error('Matriz del juego inválida');
}
function chooseFrom(values,count,seed){
  // Ordenación reproducible mediante hash de la clave de fecha.
  return values.map(v=>({v,weight:dailyHash(seed+'|'+v)}))
    .sort((a,b)=>a.weight-b.weight||a.v-b.v).slice(0,count).map(x=>x.v).sort((a,b)=>a-b);
}
function observedCounts(rows,game,field){
  const max=field==='bonus'?game.bonus:game.n;
  const counts=new Uint32Array(max+1);
  let valid=0;
  if(!Array.isArray(rows))return {counts,total:0};
  for(const row of rows){
    if(field==='bonus'){
      if(Number.isInteger(row.bonus)&&row.bonus>=1&&row.bonus<=max){
        counts[row.bonus]++;valid++;
      }
      continue;
    }
    if(!Array.isArray(row.main)||row.main.length!==game.k||new Set(row.main).size!==game.k)continue;
    if(!row.main.every(v=>Number.isInteger(v)&&v>=1&&v<=max))continue;
    valid++;
    for(const v of row.main)counts[v]++;
  }
  return {counts,total:valid};
}
function bestCandidates(game,rows,count){
  const min=game.k===1&&!game.bonus?0:1;
  const max=game.k===1&&!game.bonus?game.n-1:game.n;
  const options=Array.from({length:max-min+1},(_,i)=>i+min);
  if(!rows?.length)return {options,history:false};
  const {counts,total}=observedCounts(rows,game,'main');
  if(total<60)return {options,history:false};
  const sorted=options.sort((a,b)=>counts[b]-counts[a]||a-b);
  // Top 35% de frecuencia observada, sin convertirla en una probabilidad futura.
  const poolSize=Math.max(count*3,Math.ceil(sorted.length*.35));
  return {options:sorted.slice(0,poolSize),history:true};
}
export function luckySuggestion(game,key,rows,day,round=0){
  validateGame(game);
  if(typeof key!=='string'||!key||typeof day!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(day))
    throw TypeError('Clave o fecha diaria inválida');
  if(!Number.isInteger(round)||round<0||round>9999)throw RangeError('Número de variante inválido');
  const seed='LOTTO-LAB-LUCKY-v1|'+key+'|'+day+'|'+round;
  const history=Array.isArray(rows)?rows:[];
  if(game.kind==='digits'){
    const number=dailyHash(seed+'|exact-digits')%game.n;
    return {main:[number],bonus:null,date:day,history:false,sample:0,round,method:'rotación matemática del día'};
  }
  const candidates=bestCandidates(game,history,game.k);
  const chosen=chooseFrom(candidates.options,game.k,seed+'|main');
  let bonus=null;
  if(game.bonus){
    const sample=observedCounts(history,game,'bonus');
    let bonusCandidates=Array.from({length:game.bonus},(_,i)=>i+1);
    if(sample.total>=60){
      bonusCandidates.sort((a,b)=>sample.counts[b]-sample.counts[a]||a-b);
      bonusCandidates=bonusCandidates.slice(0,Math.max(6,Math.ceil(game.bonus*.4)));
    }
    bonus=chooseFrom(bonusCandidates,1,seed+'|bonus')[0];
  }
  return {main:chosen,bonus,date:day,history:candidates.history,
    sample:candidates.history?history.length:0,round,
    method:candidates.history?'frecuencias observadas históricas':'selección matemática diaria'};
}
export function validLucky(game,ticket){
  if(!ticket||!Array.isArray(ticket.main)||ticket.main.length!==game.k)return false;
  const min=game.kind==='digits'||game.k===1&&!game.bonus?0:1;
  const max=game.kind==='digits'||game.k===1&&!game.bonus?game.n-1:game.n;
  if(!ticket.main.every(v=>Number.isInteger(v)&&v>=min&&v<=max))return false;
  if(new Set(ticket.main).size!==game.k)return false;
  return game.bonus?Number.isInteger(ticket.bonus)&&ticket.bonus>=1&&ticket.bonus<=game.bonus:ticket.bonus===null;
}
