/**
 * LOTTO LAB — selección uniforme de varias jugadas únicas.
 * Floyd sampling: O(m) memoria, sin enumerar el espacio de boletos.
 * Crypto RNG y rechazo en BigInt para evitar sesgo de módulo.
 *
 * Uso matemático/educativo: NO genera predicciones ni compra boletos.
 */
import {comb,outcomeCount} from './scientific-math.mjs';
import {unrankTicket,rankTicket} from './coverage-engine.mjs';

export function randomBigIntBelow(limit,getWord){
  if(typeof limit!=='bigint'||limit<=0n)throw RangeError('Límite BigInt positivo requerido');
  if(limit===1n)return 0n;
  const randomWord=getWord||(()=>{
    if(!globalThis.crypto?.getRandomValues)
      throw Error('Se necesita un navegador seguro con crypto.getRandomValues');
    const array=new Uint32Array(1);
    globalThis.crypto.getRandomValues(array);
    return array[0];
  });
  const bits=(limit-1n).toString(2).length;
  const words=Math.ceil(bits/32);
  const mask=(1n<<BigInt(bits))-1n;
  for(let attempts=0;attempts<100000;attempts++){
    let value=0n;
    for(let i=0;i<words;i++){
      const word=randomWord();
      if(!Number.isSafeInteger(word)||word<0||word>0xffffffff)
        throw new RangeError('La fuente aleatoria debe devolver enteros uint32');
      value=(value<<32n)|BigInt(word);
    }
    value&=mask;
    if(value<limit)return value;
  }
  throw Error('La fuente aleatoria no produjo resultados válidos');
}

export function chooseUniqueRanks(total,count,randomBelow=randomBigIntBelow){
  if(typeof total!=='bigint'||total<1n)throw RangeError('Espacio inválido');
  if(!Number.isSafeInteger(count)||count<1||count>100)
    throw RangeError('Elige de 1 a 100 combinaciones');
  if(BigInt(count)>total)throw RangeError('Más boletos que combinaciones posibles');
  const selected=new Set();
  for(let j=total-BigInt(count);j<total;j++){
    const t=randomBelow(j+1n);
    if(typeof t!=='bigint'||t<0n||t>j)throw RangeError('Aleatoriedad fuera de rango');
    selected.add(selected.has(t)?j:t);
  }
  if(selected.size!==count)throw Error('Selección no tiene la cantidad de combinaciones solicitada');
  return [...selected];
}

export function generateUniquePack(game,count,randomBelow=randomBigIntBelow){
  const total=outcomeCount(game);
  const ranks=chooseUniqueRanks(total,count,randomBelow);
  const tickets=ranks.map(rank=>({...unrankTicket(game,rank),rank}));
  // Prueba defensiva de ida y vuelta, sin generar listas gigantes.
  for(const t of tickets){
    if(rankTicket(game,t)!==t.rank)throw Error('Inconsistencia al reconstruir un boleto');
  }
  return {total,count,tickets,coverageNumerator:BigInt(count),coverageDenominator:total};
}

export function packCost(count,unitPrice){
  if(unitPrice==null)return null;
  if(typeof unitPrice!=='number'||!Number.isFinite(unitPrice)||unitPrice<0)
    throw RangeError('Precio no válido');
  if(!Number.isSafeInteger(count)||count<1||count>100)throw RangeError('Cantidad no válida');
  return Math.round(count*unitPrice*100)/100;
}


/**
 * Exact 3+-main-ball union probability when ticket main sets are pairwise
 * disjoint. Proof: 3+ hits on each of two disjoint 5-ball tickets would
 * require >=6 winning main balls, but only 5 exist. The events are disjoint.
 * Does NOT describe every official prize tier or jackpot profitability.
 */
export function disjointThreePlusOdds(game,count){
  if(!game||game.kind||game.k!==5||!Number.isSafeInteger(game.n)||game.n<5)
    throw RangeError('Esta demostración requiere un juego de cinco bolas diferentes');
  if(!Number.isSafeInteger(count)||count<1||count*5>game.n)
    throw RangeError('La cantidad supera los grupos de cinco números sin repetir');
  const denominator=comb(game.n,5);
  let singleWays=0n;
  for(let r=3;r<=5;r++){
    if(game.n-5>=5-r)singleWays+=comb(5,r)*comb(game.n-5,5-r);
  }
  return {
    numerator:singleWays*BigInt(count),denominator,
    threshold:3,mainNumbersPerTicket:5,count
  };
}

/**
 * A strictly disjoint set of 5-number tickets, via partial Fisher–Yates.
 * At most floor(n/5) tickets. Bonus balls are drawn independently and may
 * coincide across tickets without duplicating the full ticket combination.
 * Jackpot chance is still exactly count/outcomeCount(game).
 */
export function generateDisjointPack(game,count,randomBelow=randomBigIntBelow){
  const odds=disjointThreePlusOdds(game,count);
  const pool=Array.from({length:game.n},(_,i)=>i+1);
  const ballsNeeded=count*game.k;
  for(let i=0;i<ballsNeeded;i++){
    const span=BigInt(game.n-i);
    const shift=randomBelow(span);
    if(typeof shift!=='bigint'||shift<0n||shift>=span)
      throw RangeError('Valor aleatorio fuera del rango');
    const j=i+Number(shift);
    [pool[i],pool[j]]=[pool[j],pool[i]];
  }
  const tickets=[];
  for(let i=0;i<count;i++){
    const main=pool.slice(i*5,(i+1)*5).sort((a,b)=>a-b);
    const bonus=game.bonus?1+Number(randomBelow(BigInt(game.bonus))):null;
    const ticket={main,bonus};
    tickets.push({...ticket,rank:rankTicket(game,ticket)});
  }
  if(new Set(tickets.flatMap(t=>t.main)).size!==ballsNeeded)
    throw Error('La selección contiene números repetidos entre boletos');
  return {total:outcomeCount(game),count,tickets,
    coverageNumerator:BigInt(count),
    coverageDenominator:outcomeCount(game),threePlusOdds:odds,mode:'disjoint-main'};
}
