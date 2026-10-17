/**
 * LOTTO LAB · premios, presupuesto e impuestos (módulo matemático puro).
 * Distingue: cotejo numérico, premio condicionado a reglas, retención y
 * liquidación fiscal final. No verifica códigos con servidores de lotería.
 */
import {exactSpectrum,GAME_TIERS,outcomeCount,prizeSpectrum} from './scientific-math.mjs';

export const PRICE_USD=Object.freeze({
  powerball:2,megamillions:5,mdpick3:1,mdpick4:1,mdpick5:1,
  vapick3:1,vacash5:1,cafantasy5:1,nytake5:null,chica:null
});
export const OFFICIAL_CHECKERS=Object.freeze({
  VA:'https://www.valottery.com/aboutus/mobileapp',
  MD:'https://www.mdlottery.com/mobile-apps/',
  CA:'https://www.calottery.com/',
  NY:'https://nylottery.ny.gov/',
  US:'https://www.powerball.com/'
});
export const PRIZE_SOURCES=Object.freeze({
  powerball:'https://www.powerball.com/powerball-prize-chart/',
  megamillions:'https://www.megamillions.com/Media-Center/MegaMillions_New_Prize_Matrix.aspx',
  vacash5:'https://www.valottery.com/data/draw-games/cash5',
  mdpick3:'https://www.mdlottery.com/games/pick-3-pick-4-pick-5/prize-structure/',
  mdpick4:'https://www.mdlottery.com/games/pick-3-pick-4-pick-5/prize-structure/',
  mdpick5:'https://www.mdlottery.com/games/pick-3-pick-4-pick-5/prize-structure/',
  cafantasy5:'https://www.calottery.com/draw-games/fantasy-5'
});
export const MULTIPLIER_WEIGHTS=Object.freeze([
  Object.freeze({multiplier:2,weight:15}),Object.freeze({multiplier:3,weight:10}),
  Object.freeze({multiplier:4,weight:4}),Object.freeze({multiplier:5,weight:2}),
  Object.freeze({multiplier:10,weight:1})
]);
const MD_STRAIGHT=Object.freeze({mdpick3:500,mdpick4:5000,mdpick5:50000});
export function finiteMoney(value,name='Cantidad'){
  const n=Number(value);
  if(!Number.isFinite(n)||n<0||n>1_000_000_000_000)throw RangeError(name+' fuera de rango');
  return n;
}
const validMult=multiplier=>[2,3,4,5,10].includes(Number(multiplier));
export function tierKey(match){
  return match.mainHits+'|'+Number(match.bonusHit===true);
}
/**
 * Tabla de premio que se podría cobrar POR UNA JUGADA si el resultado
 * resulta ser oficial, si la jugada es válida y no ha sido cobrada.
 * status: fixed | range | variable | freeplay | none | unsupported.
 */
export function prizeForMatch(key,match,{multiplier=null,powerPlay=false,wager=1,claimState='VA'}={}){
  if(!match||!Number.isInteger(match.mainHits))throw TypeError('Coincidencias inválidas');
  const originalStake=finiteMoney(wager,'Apuesta');
  if(key in MD_STRAIGHT){
    const width={mdpick3:3,mdpick4:4,mdpick5:5}[key];
    if(![0.5,1].includes(originalStake))return {status:'unsupported',label:'Esta calculadora Straight acepta apuestas de US$0,50 o US$1 por jugada'};
    return match.exact||match.mainHits===width?
      {status:'fixed',amount:MD_STRAIGHT[key]*originalStake,label:'Straight, dígitos en orden exacto'}:
      {status:'none',amount:0,label:'Sin premio en modalidad Straight'};
  }
  if(key==='vacash5'){
    const cash={2:1,3:5,4:200}[match.mainHits];
    if(match.mainHits===5)return {status:'variable',label:'Jackpot acumulado y posiblemente compartido; valor por verificar'};
    if(cash)return {status:'fixed',amount:cash,label:match.mainHits+' números · Cash 5 básico'};
    return {status:'none',amount:0,label:'Sin premio en Cash 5 básico'};
  }
  if(key==='cafantasy5'){
    if(match.mainHits===2)return {status:'freeplay',label:'Boleto gratis; no equivale a dinero en efectivo'};
    if(match.mainHits>=3)return {status:'variable',label:'Premio pari-mutuel variable; se requiere monto oficial'};
    return {status:'none',amount:0,label:'Sin premio básico'};
  }
  if(key!=='powerball'&&key!=='megamillions')
    return {status:'unsupported',label:'Falta tabla de pagos verificable para esta modalidad'};
  const tier=GAME_TIERS[key]?.[tierKey(match)];
  if(!tier)return {status:'none',amount:0,label:'Sin combinación premiada en el juego base'};
  if(tier.base==null)return {status:'variable',label:'JACKPOT: no se conoce el pago en efectivo ni posibles ganadores compartidos'};
  if(key==='powerball'&&claimState==='CA'){
    return {status:'variable',label:'Powerball en California: premios pari-mutuel según ventas y ganadores'};
  }
  if(key==='powerball'){
    if(!powerPlay)return {status:'fixed',amount:tier.base,label:tier.label+' · juego base'};
    if(!validMult(multiplier))return {status:'range',min:tier.base===1000000?2000000:tier.base*2,
      max:tier.base===1000000?2000000:tier.base*10,
      label:'Power Play contratado, pero falta confirmar el multiplicador oficial del sorteo'};
    return {status:'fixed',amount:tier.base===1000000?2000000:tier.base*Number(multiplier),
      label:tier.label+' · Power Play '+multiplier+'×'};
  }
  if(!validMult(multiplier))return {status:'range',min:tier.base*2,max:tier.base*10,
    label:tier.label+' · el multiplicador impreso en el boleto es obligatorio'};
  return {status:'fixed',amount:tier.base*Number(multiplier),
    label:tier.label+' · multiplicador '+multiplier+'×'};
}
/**
 * ROI educativo: solo ganancias FIJAS / verificables; excluye jackpot,
 * premios variables, Fireball, EZ Match y otros complementos.
 */
export function expectedFixedReturn(game,key,{powerPlay=false,claimState='VA',wager=1}={}){
  if(!game||!Number.isInteger(game.n)||!Number.isInteger(game.k))throw TypeError('Matriz inválida');
  if(key==='powerball'&&claimState==='CA')return null;
  const cost=PRICE_USD[key];
  if(cost==null)return null;
  if(key in MD_STRAIGHT){
    if(![0.5,1].includes(Number(wager)))return null;
    return {baseCost:Number(wager),expectedGrossPerPlay:(MD_STRAIGHT[key]*Number(wager))/game.n,
      excludes:'Solo Straight; no otros tipos de apuesta'};
  }
  if(key!=='powerball'&&key!=='megamillions'&&key!=='vacash5')return null;
  const spectrum=exactSpectrum(game);
  let gross=0;
  for(const tier of spectrum){
    const base=GAME_TIERS[key]?.[tier.main+'|'+Number(tier.bonus===true)]?.base;
    if(!Number.isFinite(base)||base<=0)continue;
    let rate=1;
    if(key==='megamillions')rate=3; // promedio oficial de 32 posiciones de los multiplicadores.
    else if(key==='powerball'&&powerPlay){
      // Sin 10x (jackpot mayor de 150M): 24*2 + 13*3 + 3*4 + 2*5 = 109 / 42.
      rate=base===1000000?2:109/42;
    }
    gross+=tier.probability*base*rate;
  }
  return {baseCost:cost+(key==='powerball'&&powerPlay?1:0),
    expectedGrossPerPlay:gross,excludes:'Jackpot y premios variables excluidos; no predice ganancias'};
}
export function budgetProjection(game,key,budget,options={}){
  const money=finiteMoney(budget,'Presupuesto');
  const model=expectedFixedReturn(game,key,options);
  if(!model)return null;
  const numberOfPlays=Math.floor((money+1e-9)/model.baseCost);
  const spent=numberOfPlays*model.baseCost;
  const expectedFixedGross=numberOfPlays*model.expectedGrossPerPlay;
  return {budget:money,numberOfPlays,spent,remaining:money-spent,expectedFixedGross,
    expectedNetExcludingJackpot:expectedFixedGross-spent,perPlay:model.expectedGrossPerPlay,
    baseCost:model.baseCost,excludes:model.excludes};
}
/**
 * Retención del impuesto !== obligación fiscal definitiva.
 * La retención federal estándar solo se aplica si proceeds=prize-wager > $5,000.
 * Las retenciones estatales varían según la jurisdicción y el cobro.
 */
export function estimateTaxes({
  grossPrize,stake=0,region='VA',mdResident=true,federalFinalRate=32,stateFinalRate=5.75,
  otherStateWithholdingRate=0
}){
  const gross=finiteMoney(grossPrize,'Premio');
  const cost=finiteMoney(stake,'Costo de la jugada');
  if(!['VA','MD','OTHER'].includes(region))throw RangeError('Jurisdicción inválida');
  for(const [name,value] of [
    ['Tasa federal estimada',federalFinalRate],
    ['Tasa estatal final estimada',stateFinalRate],
    ['Retención estatal personalizada',otherStateWithholdingRate]
  ])if(!Number.isFinite(Number(value))||Number(value)<0||Number(value)>60)throw RangeError(name+' inválida');
  const proceeds=Math.max(0,gross-cost);
  const federalWithholding=proceeds>5000?proceeds*.24:0;
  // Operadores oficiales (2026): VA 4 % sobre premio bruto si proceeds > $5.000;
  // MD 9,5 % para residentes, 8,75 % para no residentes sobre premio bruto.
  // Federal: 24 % sobre el premio neto de la apuesta, no el premio bruto.
  const stateWithholdRate=region==='VA'?4:region==='MD'?(mdResident?9.5:8.75):Number(otherStateWithholdingRate);
  const stateWithholding=proceeds>5000?gross*stateWithholdRate/100:0;
  const withheld=federalWithholding+stateWithholding;
  const netAfterWithholding=gross-withheld;
  const estimatedFinalFederal=proceeds*Number(federalFinalRate)/100;
  const estimatedFinalState=proceeds*Number(stateFinalRate)/100;
  const estimatedFinalTotal=estimatedFinalFederal+estimatedFinalState;
  return {
    gross,stake:cost,proceeds,region,
    federalWithholding,stateWithholding,withheld,netAfterWithholding,
    estimatedFinalFederal,estimatedFinalState,estimatedFinalTotal,
    estimatedAfterFinalTax:gross-estimatedFinalTotal,
    finalCashLessStake:gross-estimatedFinalTotal-cost,
    extraDueEstimated:estimatedFinalTotal-withheld,
    mdResident,
    taxLiabilityIsScenario:true
  };
}
export function oddsPrizeTable(game,key,{claimState='VA'}={}){
  if(!game)return [];
  if(key in MD_STRAIGHT){
    const n=game.n,width=game.width;
    return [{key:'exact',label:width+' dígitos Straight',odds:BigInt(n),
      min:MD_STRAIGHT[key]*0.5,max:MD_STRAIGHT[key],payout:'Según apuesta de US$0,50 o US$1'}];
  }
  if(!GAME_TIERS[key])return [];
  return exactSpectrum(game).filter(x=>GAME_TIERS[key][x.main+'|'+Number(x.bonus===true)]).map(x=>{
    const tier=GAME_TIERS[key][x.main+'|'+Number(x.bonus===true)];
    const variable=tier.base===null||key==='powerball'&&claimState==='CA'||key==='cafantasy5';
    return {key:x.main+'|'+Number(x.bonus===true),label:tier.label,
      ways:x.ways,total:x.total,odds:Number(x.total)/Number(x.ways),
      status:variable?'variable':key==='megamillions'?'range':'fixed',
      min:variable?null:key==='megamillions'?tier.base*2:tier.base,
      max:variable?null:key==='megamillions'?tier.base*10:tier.base,
      payout:variable?tier.prize||'Variable':tier.prize};
  }).sort((a,b)=>a.odds-b.odds);
}
