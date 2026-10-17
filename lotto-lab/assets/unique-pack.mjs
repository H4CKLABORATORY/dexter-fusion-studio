/**
 * LOTTO LAB — selección uniforme de varias jugadas únicas.
 * Floyd sampling: O(m) memoria, sin enumerar el espacio de boletos.
 * Crypto RNG y rechazo en BigInt para evitar sesgo de módulo.
 *
 * Uso matemático/educativo: NO genera predicciones ni compra boletos.
 */
import {outcomeCount} from './scientific-math.mjs';
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
