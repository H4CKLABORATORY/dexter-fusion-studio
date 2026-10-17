export const GAMES={
  powerball:{label:'Powerball',main:69,bonus:26,k:5,price:2,ruleFrom:'2015-10-07',dataset:'data/powerball.json',color:'#7da9fa'},
  megamillions:{label:'Mega Millions',main:70,bonus:24,k:5,price:5,ruleFrom:'2025-04-08',dataset:'data/megamillions.json',color:'#f7bc65'}
};
export function choose(n,k){
  if(!Number.isInteger(n)||!Number.isInteger(k)||n<0||k<0||k>n)throw new RangeError('Valores combinatorios incorrectos');
  k=Math.min(k,n-k);let v=1n;
  for(let i=1;i<=k;i++)v=v*BigInt(n-k+i)/BigInt(i);
  return v;
}
export function totalCombos(game){const g=typeof game==='string'?GAMES[game]:game; if(!g)throw Error('Juego desconocido');return choose(g.main,g.k)*BigInt(g.bonus)}
export function exactJackpotChance(game,tickets=1){
  const total=totalCombos(game),t=BigInt(tickets);
  if(t<=0n)throw RangeError('Cantidad de boletos positiva');
  return Number(t>total?total:t)/Number(total); // Solo combinaciones distintas en UN sorteo.
}
export function normalizeRows(payload,game){
  const g=GAMES[game];if(!g||!payload||payload.game!==game||!Array.isArray(payload.rows))throw Error('Archivo histórico incorrecto');
  const seen=new Set(),rows=[];
  for(const input of payload.rows){
    if(!Array.isArray(input)||input.length!==7||typeof input[0]!=='string')continue;
    const date=input[0];if(!/^\d{4}-\d{2}-\d{2}$/.test(date)||seen.has(date))continue;
    const main=input.slice(1,6),extra=input[6];
    // Archivo completo: permite límites anteriores más altos (Mega Millions pasó por varios sistemas).
    if(!main.every(v=>Number.isInteger(v)&&v>=1&&v<=75)||new Set(main).size!==5||!Number.isInteger(extra)||extra<1||extra>52)continue;
    rows.push({date,main:[...main].sort((a,b)=>a-b),bonus:extra});seen.add(date);
  }
  rows.sort((a,b)=>b.date.localeCompare(a.date));
  if(!rows.length)throw Error('Sin sorteos válidos');
  return rows;
}
export function currentRegime(rows,game){const g=GAMES[game];return rows.filter(r=>r.date>=g.ruleFrom&&r.main.every(x=>x<=g.main)&&r.bonus<=g.bonus)}
export function stats(rows,game){
  const g=GAMES[game];if(!g)throw Error('Juego inválido');
  const counts=Array(g.main+1).fill(0),bonuses=Array(g.bonus+1).fill(0);let oddCount=0,sum=0;
  const pairs=new Map();
  for(const row of rows){
    row.main.forEach(n=>{counts[n]++;sum+=n;if(n%2)oddCount++});bonuses[row.bonus]++;
    for(let i=0;i<row.main.length;i++)for(let j=i+1;j<row.main.length;j++){
      const key=`${row.main[i]}-${row.main[j]}`;pairs.set(key,(pairs.get(key)||0)+1);
    }
  }
  const main=Array.from({length:g.main},(_,i)=>({number:i+1,count:counts[i+1]}));
  const bonus=Array.from({length:g.bonus},(_,i)=>({number:i+1,count:bonuses[i+1]}));
  return {n:rows.length,hot:[...main].sort((a,b)=>b.count-a.count||a.number-b.number),
    cold:[...main].sort((a,b)=>a.count-b.count||a.number-b.number),
    bonus:[...bonus].sort((a,b)=>b.count-a.count||a.number-b.number),
    pairs:[...pairs].map(([pair,count])=>({pair,count})).sort((a,b)=>b.count-a.count||a.pair.localeCompare(b.pair)),
    oddPercent:rows.length?100*oddCount/(rows.length*5):0,avgMainSum:rows.length?sum/rows.length:0};
}
export function secureInt(max){
  if(!globalThis.crypto?.getRandomValues)throw Error('Tu navegador no admite un generador seguro.');
  if(!Number.isInteger(max)||max<1||max>2**32-1)throw RangeError('Máximo incorrecto');
  const range=0x100000000, limit=range-(range%max),u=new Uint32Array(1);
  do{globalThis.crypto.getRandomValues(u)}while(u[0]>=limit);
  return u[0]%max;
}
export function randomTicket(game,rand=secureInt){
  const g=GAMES[game];if(!g)throw Error('Juego desconocido');
  const pool=Array.from({length:g.main},(_,i)=>i+1);
  for(let i=0;i<g.k;i++){let j=i+rand(g.main-i);[pool[i],pool[j]]=[pool[j],pool[i]];}
  return {main:pool.slice(0,g.k).sort((a,b)=>a-b),bonus:rand(g.bonus)+1};
}
export function overlaps(ticket,draw){const set=new Set(draw.main);return {main:ticket.main.filter(n=>set.has(n)).length,bonus:ticket.bonus===draw.bonus};}
// Walk-forward validation: never looks at future results when selecting numbers.
export function backtest(rows,game,{minimumTrain=30,evaluations=120}={}){
  const g=GAMES[game];if(!g)throw Error('Juego desconocido');
  const sequence=[...rows].sort((a,b)=>a.date.localeCompare(b.date));
  const count=Math.min(evaluations,sequence.length-minimumTrain);
  if(count<20)throw Error('Necesitamos al menos 50 sorteos del mismo régimen para evaluar estrategias.');
  const start=sequence.length-count,frequency=Array(g.main+1).fill(0),special=Array(g.bonus+1).fill(0);
  for(const row of sequence.slice(0,start)){row.main.forEach(x=>frequency[x]++);special[row.bonus]++;}
  let hitHot=0,hitUniform=0,bHot=0,bUniform=0;
  for(let i=start;i<sequence.length;i++){
    const rankings=Array.from({length:g.main},(_,j)=>j+1).sort((a,b)=>frequency[b]-frequency[a]||a-b);
    const hot={main:rankings.slice(0,5),bonus:Array.from({length:g.bonus},(_,j)=>j+1).sort((a,b)=>special[b]-special[a]||a-b)[0]};
    const actual=sequence[i];
    const h=overlaps(hot,actual);hitHot+=h.main;bHot+=Number(h.bonus);
    // Baseline matemático exacto: E[aciertos principales]=k*k/N y P[bonus]=1/B.
    hitUniform+=g.k*g.k/g.main;bUniform+=1/g.bonus;
    actual.main.forEach(x=>frequency[x]++);special[actual.bonus]++;
  }
  return {n:count,hotAverage:hitHot/count,randomExpected:hitUniform/count,
          hotBonusRate:bHot/count,randomBonusExpected:bUniform/count,
          warning:'Muestra retrospectiva; una ventaja aparente NO prueba capacidad predictiva.'};
}
export function oddsLabel(total){return '1 entre '+total.toLocaleString('es-ES')}
export function csvForRows(rows){return ['fecha,n1,n2,n3,n4,n5,bola_especial',...rows.map(r=>[r.date,...r.main,r.bonus].join(','))].join('\n')+'\n'}