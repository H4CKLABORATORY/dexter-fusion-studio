/**
 * LOTTO LAB · Exact Arithmetic v4
 * Fractions, percentages, odds and expected fixed payouts use BigInt.
 * No Number conversion in the calculation/rounding of displayed exact ratios.
 * Browser-compatible native JavaScript: no external library or paid backend.
 */
import {outcomeCount,prizeSpectrum} from './scientific-math.mjs';

function asInteger(value,name){
  if(typeof value==='bigint')return value;
  if(typeof value==='number'&&Number.isSafeInteger(value))return BigInt(value);
  throw TypeError(name+' debe ser entero representable sin pérdida');
}
export function gcd(a,b){
  a=asInteger(a,'a');b=asInteger(b,'b');
  if(a<0n)a=-a;if(b<0n)b=-b;
  while(b){const r=a%b;a=b;b=r}
  return a;
}
export function fraction(n,d){
  n=asInteger(n,'numerador');d=asInteger(d,'denominador');
  if(d===0n)throw RangeError('Denominador cero');
  if(d<0n){n=-n;d=-d}
  const divisor=gcd(n,d);
  return Object.freeze({n:n/divisor,d:d/divisor});
}
export function plus(a,b){return fraction(a.n*b.d+b.n*a.d,a.d*b.d)}
export function times(a,b){return fraction(a.n*b.n,a.d*b.d)}
export function probabilityExact(game,count=1){
  return fraction(asInteger(count,'cobertura'),outcomeCount(game));
}
export function tierProbabilityExact(tier){
  if(!tier||tier.ways===undefined||tier.total===undefined)throw TypeError('Categoría incompatible');
  return fraction(tier.ways,tier.total);
}
export function formatInteger(value){
  const n=asInteger(value,'valor');
  const text=n.toString(),negative=text.startsWith('-');
  const digits=negative?text.slice(1):text;
  return (negative?'-':'')+digits.replace(/\B(?=(\d{3})+(?!\d))/g,'.');
}
function rounded(n,d){
  const q=n/d,r=n%d;
  return q+(r*2n>=d?1n:0n);
}
/**
 * Returns Spanish decimal with HALF-UP rounding (not binary floating point).
 * Ex.: formatDecimal(1n,3n,12) = "0,333333333333"
 */
export function formatDecimal(n,d,places=12,{minPlaces=0,trim=false}={}){
  n=asInteger(n,'n');d=asInteger(d,'d');
  if(d<=0n)throw RangeError('Denominador positivo requerido');
  if(!Number.isInteger(places)||places<0||places>60)throw RangeError('Precisión fuera de 0..60');
  if(!Number.isInteger(minPlaces)||minPlaces<0||minPlaces>places)throw RangeError('minPlaces inválido');
  const negative=n<0n;
  if(negative)n=-n;
  const scale=10n**BigInt(places);
  const scaled=rounded(n*scale,d);
  const whole=scaled/scale;
  const decimal=places?String(scaled%scale).padStart(places,'0'):'';
  let fractional=trim?decimal.replace(/0+$/,''):decimal;
  fractional=fractional.padEnd(minPlaces,'0');
  return (negative&&scaled!==0n?'-':'')+formatInteger(whole)+(fractional?','+fractional:'');
}
export function formatPercentExact(n,d,places=14){
  const f=fraction(n,d);
  return formatDecimal(f.n*100n,f.d,places,{minPlaces:2,trim:true})+' %';
}
export function formatInverseOddsExact(n,d,places=2){
  const f=fraction(n,d);
  if(f.n<=0n)throw RangeError('Probabilidad positiva requerida');
  return '1 entre '+formatDecimal(f.d,f.n,places,{minPlaces:0,trim:true});
}
export function formatUSDDollarsExact(n,d,places=2){
  const f=fraction(n,d);
  return 'US$ '+formatDecimal(f.n,f.d,places,{minPlaces:2,trim:false});
}
export const MEGA_MULTIPLIER_WEIGHTS=Object.freeze([
  Object.freeze({multiplier:2,weight:15}),
  Object.freeze({multiplier:3,weight:10}),
  Object.freeze({multiplier:4,weight:4}),
  Object.freeze({multiplier:5,weight:2}),
  Object.freeze({multiplier:10,weight:1})
]);
export function multiplierExpectedExact(weights=MEGA_MULTIPLIER_WEIGHTS){
  const total=weights.reduce((sum,w)=>sum+asInteger(w.weight,'peso'),0n);
  const weighted=weights.reduce((sum,w)=>sum+asInteger(w.weight,'peso')*asInteger(w.multiplier,'factor'),0n);
  if(total===0n)throw RangeError('Sin pesos');
  return fraction(weighted,total);
}
/**
 * Gross expected non-jackpot fixed cash components only.
 * $ assumptions are invalid for pari-mutuel jurisdictions and jackpots.
 * This result is never a prediction or a ticket net return.
 */
export function fixedPrizeExpectedExact(game,key){
  const report=prizeSpectrum(game,key);
  if(!report.knownPayout)return null;
  const mult=key==='megamillions'?multiplierExpectedExact():fraction(1,1);
  const sum=report.rows.reduce((acc,row)=>{
    if(!Number.isSafeInteger(row.base)||row.base<=0)return acc;
    return plus(acc,times(fraction(row.ways*BigInt(row.base),row.total),mult));
  },fraction(0,1));
  return sum;
}
