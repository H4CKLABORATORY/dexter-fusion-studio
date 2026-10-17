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
