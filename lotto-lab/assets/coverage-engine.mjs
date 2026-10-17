import {comb,outcomeCount,prizeSpectrum} from './scientific-math.mjs';

// Desindexar una combinación directamente sin listar millones de resultados.
export function unrankCombination(n,k,index){
  let rank=BigInt(index);
  if(rank<0n||rank>=comb(n,k))throw RangeError('Índice fuera de rango');
  const result=[];let from=1;
  for(let i=0;i<k;i++){
    let chosen=false;
    for(let v=from;v<=n-(k-i)+1;v++){
      const ways=comb(n-v,k-i-1);
      if(rank<ways){result.push(v);from=v+1;chosen=true;break}
      rank-=ways;
    }
    if(!chosen)throw Error('No se puede desindexar la combinación');
  }
  return result;
}
export function coverageTarget(game,basisPoints=8000){
  if(!Number.isSafeInteger(basisPoints)||basisPoints<1||basisPoints>10000)
    throw RangeError('Objetivo porcentual inválido');
  const total=outcomeCount(game);
  const tickets=(total*BigInt(basisPoints)+9999n)/10000n;
  return {total,tickets,basisPoints};
}
// Número de ensayos por sorteo independientes para alcanzar cierta probabilidad de ALGÚN premio.
export function drawsForAnyPrize(game,key,basisPoints=8000){
  const prize=prizeSpectrum(game,key);
  if(prize.anyPrize===null||!prize.winningWays)return null;
  const p=Number(prize.winningWays)/Number(prize.total);
  return Math.ceil(Math.log1p(-basisPoints/10000)/Math.log1p(-p));
}

export function unrankTicket(game,index){
  const total=outcomeCount(game),r=BigInt(index);
  if(r<0n||r>=total)throw RangeError('Combinación inexistente');
  if(game.kind==='digits'||game.k===1&&!game.bonus)return {main:[Number(r)],bonus:null};
  const b=BigInt(game.bonus||1);
  return {main:unrankCombination(game.n,game.k,r/b),bonus:game.bonus?Number(r%b)+1:null};
}
export function rankCombination(n,k,values){
  if(!Array.isArray(values)||values.length!==k)throw RangeError('Selección inválida');
  let rank=0n,from=1;
  for(let i=0;i<k;i++){
    const v=values[i];
    if(!Number.isInteger(v)||v<from||v>n-(k-i)+1)throw RangeError('Números no válidos');
    for(let x=from;x<v;x++)rank+=comb(n-x,k-i-1);
    from=v+1;
  }
  return rank;
}
export function rankTicket(game,ticket){
  const {main,bonus}=ticket;
  if(game.kind==='digits'||game.k===1&&!game.bonus){
    if(!Array.isArray(main)||main.length!==1||!Number.isSafeInteger(main[0])||
      main[0]<0||main[0]>=game.n||bonus!==null)throw RangeError('Dígitos inválidos');
    return BigInt(main[0]);
  }
  if(game.bonus&&(!Number.isInteger(bonus)||bonus<1||bonus>game.bonus))throw RangeError('Bola especial inválida');
  if(!game.bonus&&bonus!==null)throw RangeError('Bola especial no esperada');
  return rankCombination(game.n,game.k,main)*BigInt(game.bonus||1)+
    (game.bonus?BigInt(bonus-1):0n);
}
function hash32(seed){
  let h=2166136261;for(const char of String(seed))h=Math.imul(h^char.charCodeAt(0),16777619);
  return BigInt(h>>>0);
}
function gcd(a,b){while(b){const x=a%b;a=b;b=x}return a}
export function uniqueSample(game,count=5,seed='LOTTOLAB'){
  if(!Number.isSafeInteger(count)||count<1||count>100)throw RangeError('Límite: 1-100 combinaciones');
  const total=outcomeCount(game);
  if(BigInt(count)>total)throw RangeError('Demasiadas combinaciones');
  const offset=hash32(seed+'offset')%total;
  let step=hash32(seed+'step')%total;
  if(!step)step=1n;
  while(gcd(step,total)!==1n)step=step+1n===total?1n:step+1n;
  return Array.from({length:count},(_,i)=>{
    const index=(offset+BigInt(i)*step)%total;
    return {...unrankTicket(game,index),index};
  });
}
