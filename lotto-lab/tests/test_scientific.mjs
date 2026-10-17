import {test} from 'node:test';
import {strict as assert} from 'node:assert';
import {
  comb,outcomeCount,exactMainWays,exactSpectrum,prizeSpectrum,GAME_TIERS,
  multiDrawChance,simultaneousBand,historicalAudit
} from '../assets/scientific-math.mjs';

const games={
  powerball:{n:69,k:5,bonus:26},
  megamillions:{n:70,k:5,bonus:24},
  vacash5:{n:45,k:5,bonus:0},
  cafantasy5:{n:39,k:5,bonus:0},
  chica:{n:100,k:1,bonus:0},
  mdpick3:{n:1000,k:1,bonus:0,kind:'digits',width:3},
  mdpick4:{n:10000,k:1,bonus:0,kind:'digits',width:4},
  mdpick5:{n:100000,k:1,bonus:0,kind:'digits',width:5}
};

test('coincidencias exactas suman TODO el espacio de resultados sin error flotante',()=>{
  const expectations={powerball:292201338n,megamillions:290472336n,vacash5:1221759n,cafantasy5:575757n,chica:100n,mdpick3:1000n,mdpick4:10000n,mdpick5:100000n};
  for(const [key,game] of Object.entries(games)){
    const rows=exactSpectrum(game),total=outcomeCount(game);
    assert.equal(total,expectations[key],key);
    assert.equal(rows.reduce((acc,row)=>acc+row.ways,0n),total,'La suma debe ser exacta en '+key);
    assert.ok(Math.abs(rows.reduce((acc,row)=>acc+row.probability,0)-1)<1e-13);
  }
});
test('hipergeométrica validada por enumeración exhaustiva 3 de 7',()=>{
  const n=7,k=3,reference=new Set([1,2,3]),actual=[0,0,0,0];
  for(let a=1;a<=n;a++)for(let b=a+1;b<=n;b++)for(let c=b+1;c<=n;c++){
    const matches=[a,b,c].filter(x=>reference.has(x)).length;
    actual[matches]++;
  }
  for(let r=0;r<=k;r++)assert.equal(exactMainWays(n,k,r),BigInt(actual[r]));
  assert.equal(comb(69,5),11238513n);
});
test('Powerball: nueve niveles coinciden con tabla oficial dentro del redondeo',()=>{
  const output=prizeSpectrum(games.powerball,'powerball');
  assert.equal(output.rows.length,9);
  assert.ok(Math.abs(1/output.anyPrize-24.87)<0.01);
  assert.equal(output.rows.find(x=>x.main===5&&x.bonus===true).ways,1n);
  const five=output.rows.find(x=>x.main===5&&x.bonus===false);
  const fourBonus=output.rows.find(x=>x.main===4&&x.bonus===true);
  const onlyBonus=output.rows.find(x=>x.main===0&&x.bonus===true);
  assert.ok(Math.abs(1/five.probability-11688053.52)<0.01);
  assert.ok(Math.abs(1/fourBonus.probability-913129.18)<0.01);
  assert.ok(Math.abs(1/onlyBonus.probability-38.32)<0.01);
  assert.ok(output.expectedFixed>0&&output.expectedFixed<2);
});
test('Mega Millions 2025: 24 bolas especiales y nueve premios actuales',()=>{
  const output=prizeSpectrum(games.megamillions,'megamillions');
  assert.equal(output.rows.length,9);
  assert.ok(Math.abs(1/output.anyPrize-23.07)<0.01);
  assert.equal(output.rows.find(x=>x.main===5&&x.bonus===true).ways,1n);
  assert.ok(Math.abs(1/output.rows.find(x=>x.main===5&&x.bonus===false).probability-12629232)<1);
  assert.equal(GAME_TIERS.megamillions['0|1'].prize,'US$10–50');
  assert.ok(output.expectedFixed>0&&output.expectedFixed<5);
});
test('juegos con premio variable no inventan un valor monetario esperado',()=>{
  const c=prizeSpectrum(games.cafantasy5,'cafantasy5');
  assert.equal(c.rows.length,4);
  assert.equal(c.knownPayout,false);
  assert.ok(Math.abs(1/c.anyPrize-9)<1);
  const v=prizeSpectrum(games.vacash5,'vacash5');
  assert.equal(v.rows.length,4);
  assert.ok(Math.abs(1/v.anyPrize-11.44)<0.01);
  assert.equal(prizeSpectrum(games.chica,'chica').anyPrize,null);
});
test('modelos ordenados no confunden posiciones exactas con premios',()=>{
  const spectrum=exactSpectrum(games.mdpick3);
  assert.equal(spectrum.find(x=>x.main===3).ways,1n);
  assert.equal(spectrum.find(x=>x.main===2).ways,27n);
  assert.equal(spectrum.find(x=>x.main===1).ways,243n);
  assert.equal(spectrum.find(x=>x.main===0).ways,729n);
  assert.equal(prizeSpectrum(games.mdpick3,'mdpick3').anyPrize,null);
});
test('exactitud de múltiples sorteos y cobertura no lineal correcta',()=>{
  for(const game of Object.values(games)){
    const total=outcomeCount(game);
    const one=multiDrawChance(game,1,1);
    assert.ok(Math.abs(one-1/Number(total))<1e-15);
    assert.ok(multiDrawChance(game,1,10)>one);
    assert.ok(multiDrawChance(game,10,1)>one);
    assert.ok(multiDrawChance(game,total,1)>0.999999999999);
    assert.throws(()=>multiDrawChance(game,total+1n,1));
    assert.throws(()=>multiDrawChance(game,0,1));
    assert.throws(()=>multiDrawChance(game,1,0));
  }
  const p=1/Number(outcomeCount(games.powerball));
  assert.ok(Math.abs(multiDrawChance(games.powerball,1,500)-(-Math.expm1(500*Math.log1p(-p))))<1e-15);
});
test('banda de Hoeffding contempla comparaciones simultáneas',()=>{
  const a=simultaneousBand(69,5,500);
  const b=simultaneousBand(69,5,2000);
  assert.equal(a.expected,5/69);
  assert.ok(a.lower<=a.expected&&a.upper>=a.expected);
  assert.ok(b.margin<a.margin);
  assert.ok(simultaneousBand(70,5,500).margin>a.margin);
  assert.throws(()=>simultaneousBand(69,5,0));
});
function sequence(length,n=69){
  const result=[];
  for(let i=0;i<length;i++){
    const main=Array.from({length:5},(_,j)=>1+(i+j*13)%n);
    result.push({date:'2026-'+String(1+Math.floor(i/28)).padStart(2,'0')+'-'+String(i%28+1).padStart(2,'0'),main});
  }
  return result;
}
test('Brier walk-forward separa pasado y período de evaluación',()=>{
  const result=historicalAudit(sequence(240),games.powerball,{minTrain:60,holdout:80});
  assert.equal(result.totalDraws,240);
  assert.equal(result.trainDraws,160);
  assert.equal(result.evaluationDraws,80);
  assert.ok(Math.abs(result.brierFair-(5/69)*(1-5/69))<1e-12);
  assert.ok(Number.isFinite(result.skillPercent));
  assert.ok(result.largestDeviations.length===5);
});
test('auditor detecta patrones artificiales evidentes sin afirmar predictividad real',()=>{
  const seq=Array.from({length:240},(_,i)=>({date:String(2000+i).padStart(4,'0')+'-01-01',main:[1,2,3,4,5]}));
  const result=historicalAudit(seq,games.powerball);
  assert.ok(result.skillPercent>0);
  assert.ok(result.anomalies.length>0);
  assert.match(result.interpretation,/NO demuestran ventaja predictiva/);
});
test('errores para matrices imposibles no crean probabilidades ficticias',()=>{
  assert.throws(()=>exactSpectrum({n:5,k:6,bonus:0}));
  assert.throws(()=>outcomeCount({n:1000,k:1,kind:'digits',width:4,bonus:0}));
  assert.throws(()=>historicalAudit([],games.powerball));
});
