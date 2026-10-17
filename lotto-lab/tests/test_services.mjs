import {test} from 'node:test';
import {strict as assert} from 'node:assert';
import {readFileSync} from 'node:fs';
import {
  PRICE_USD,prizeForMatch,expectedFixedReturn,budgetProjection,
  estimateTaxes,oddsPrizeTable
} from '../assets/payout-engine.mjs';
const games={
  powerball:{n:69,k:5,bonus:26},
  megamillions:{n:70,k:5,bonus:24},
  vacash5:{n:45,k:5,bonus:0},
  cafantasy5:{n:39,k:5,bonus:0},
  mdpick3:{n:1000,k:1,bonus:0,kind:'digits',width:3},
  mdpick4:{n:10000,k:1,bonus:0,kind:'digits',width:4},
  mdpick5:{n:100000,k:1,bonus:0,kind:'digits',width:5},
  nytake5:{n:39,k:5,bonus:0}
};
const match=(mainHits,bonusHit=false,exact=false)=>({mainHits,bonusHit,exact});

test('Powerball: cada categoría de premio base usa el monto oficial',()=>{
  const g=games.powerball;
  const pairs=[[5,false,1e6],[4,true,50000],[4,false,100],[3,true,100],
    [3,false,7],[2,true,7],[1,true,4],[0,true,4]];
  for(const [k,special,amount] of pairs){
    const result=prizeForMatch('powerball',match(k,special,false));
    assert.equal(result.status,'fixed');
    assert.equal(result.amount,amount);
  }
  assert.equal(prizeForMatch('powerball',match(5,true,true)).status,'variable');
  assert.equal(prizeForMatch('powerball',match(0,false)).amount,0);
  assert.equal(prizeForMatch('powerball',match(4,true),{claimState:'CA'}).status,'variable');
});
test('Power Play: el segundo premio se limita a 2 millones',()=>{
  const base={powerPlay:true,multiplier:10};
  assert.equal(prizeForMatch('powerball',match(5,false),base).amount,2000000);
  assert.equal(prizeForMatch('powerball',match(4,true),base).amount,500000);
  assert.equal(prizeForMatch('powerball',match(3,false),base).amount,70);
  assert.equal(prizeForMatch('powerball',match(5,false),{powerPlay:true}).status,'range');
  assert.equal(prizeForMatch('powerball',match(5,true,true),base).status,'variable');
});
test('Mega Millions: multiplicador 2x a 10x obligatorio para importe exacto',()=>{
  const tiers=[[5,false,1000000],[4,true,10000],[4,false,500],
    [3,true,200],[3,false,10],[2,true,10],[1,true,7],[0,true,5]];
  for(const [k,bonus,base] of tiers){
    assert.equal(prizeForMatch('megamillions',match(k,bonus),{multiplier:2}).amount,base*2);
    assert.equal(prizeForMatch('megamillions',match(k,bonus),{multiplier:10}).amount,base*10);
    const absent=prizeForMatch('megamillions',match(k,bonus));
    assert.equal(absent.status,'range');assert.equal(absent.min,base*2);
    assert.equal(absent.max,base*10);
  }
  assert.equal(prizeForMatch('megamillions',match(5,true,true),{multiplier:5}).status,'variable');
});
test('Maryland Pick 3, Pick 4 y Pick 5: únicamente Straight y apuesta US$0,50 o US$1',()=>{
  for(const [key,width,amount] of [['mdpick3',3,500],['mdpick4',4,5000],['mdpick5',5,50000]]){
    assert.equal(prizeForMatch(key,match(width,null,true),{wager:1}).amount,amount);
    assert.equal(prizeForMatch(key,match(width,null,true),{wager:0.5}).amount,amount/2);
    assert.equal(prizeForMatch(key,match(width-1,null,false),{wager:1}).amount,0);
    assert.equal(prizeForMatch(key,match(width,null,true),{wager:2}).status,'unsupported');
  }
  assert.equal(prizeForMatch('nytake5',match(5,null,true)).status,'unsupported');
});
test('Virginia Cash 5 tiene pagos fijos 1, 5, 200 y premio mayor variable',()=>{
  for(const [hits,amount] of [[2,1],[3,5],[4,200]]){
    assert.equal(prizeForMatch('vacash5',match(hits,null,false)).amount,amount);
  }
  assert.equal(prizeForMatch('vacash5',match(5,null,true)).status,'variable');
  assert.equal(prizeForMatch('cafantasy5',match(2,null,false)).status,'freeplay');
  assert.equal(prizeForMatch('cafantasy5',match(5,null,true)).status,'variable');
});
test('presupuesto: calcula cantidad de jugadas y pérdida estadística posible sin simular ganancias garantizadas',()=>{
  const a=budgetProjection(games.powerball,'powerball',20);
  assert.equal(a.numberOfPlays,10);assert.equal(a.spent,20);
  assert.equal(a.remaining,0);
  assert.ok(a.expectedFixedGross>0&&a.expectedFixedGross<20);
  assert.ok(a.expectedNetExcludingJackpot<0);
  const b=budgetProjection(games.megamillions,'megamillions',24);
  assert.equal(b.numberOfPlays,4);assert.equal(b.spent,20);
  assert.equal(b.remaining,4);assert.ok(b.expectedFixedGross<20);
  const c=budgetProjection(games.powerball,'powerball',12,{powerPlay:true});
  assert.equal(c.numberOfPlays,4);assert.equal(c.baseCost,3);
  const straight=budgetProjection(games.mdpick5,'mdpick5',10);
  assert.equal(straight.numberOfPlays,10);assert.equal(straight.expectedFixedGross,5);
  assert.equal(budgetProjection(games.cafantasy5,'cafantasy5',100),null);
  assert.equal(budgetProjection(games.nytake5,'nytake5',100),null);
  assert.throws(()=>budgetProjection(games.powerball,'powerball',-1));
});
test('expectativas no atribuyen falso retorno monetario a California pari-mutuel',()=>{
  const ca=expectedFixedReturn(games.powerball,'powerball',{claimState:'CA'});
  assert.equal(ca,null);
  assert.equal(PRICE_USD.megamillions,5);
  assert.equal(expectedFixedReturn(games.mdpick3,'mdpick3',{wager:0.5}).expectedGrossPerPlay,0.25);
});
test('premio VA: 24 % federal sobre proceeds + 4 % estatal sobre bruto si supera umbral',()=>{
  const item=estimateTaxes({grossPrize:10000,stake:2,region:'VA',
    federalFinalRate:32,stateFinalRate:5.75});
  assert.ok(Math.abs(item.federalWithholding-2399.52)<1e-7);
  assert.equal(item.stateWithholding,400);
  assert.ok(Math.abs(item.netAfterWithholding-7200.48)<1e-7);
  assert.ok(item.estimatedAfterFinalTax<item.netAfterWithholding);
  assert.equal(item.taxLiabilityIsScenario,true);
  const smaller=estimateTaxes({grossPrize:5000,stake:1,region:'VA'});
  assert.equal(smaller.federalWithholding,0);
  assert.equal(smaller.stateWithholding,0);
  const borderline=estimateTaxes({grossPrize:5002,stake:2,region:'VA'});
  assert.equal(borderline.federalWithholding,0);
  assert.equal(borderline.stateWithholding,0);
  const higher=estimateTaxes({grossPrize:5002.01,stake:2,region:'VA'});
  assert.equal(higher.federalWithholding>0,true);
  assert.equal(higher.stateWithholding>0,true);
});
test('impuestos: Maryland 9,5 % residente o 8,75 % no residente, y otros estados editables',()=>{
  const md=estimateTaxes({grossPrize:50000,stake:1,region:'MD'});
  assert.ok(Math.abs(md.stateWithholding-4750)<1e-7);
  const mdNonResident=estimateTaxes({grossPrize:50000,stake:1,region:'MD',mdResident:false});
  assert.equal(mdNonResident.stateWithholding,4375);
  const other=estimateTaxes({grossPrize:10000,stake:2,region:'OTHER',
    otherStateWithholdingRate:7.5,federalFinalRate:24,stateFinalRate:0});
  assert.equal(other.stateWithholding,750);
  assert.ok(other.extraDueEstimated<0);
  assert.throws(()=>estimateTaxes({grossPrize:-1}));
  assert.throws(()=>estimateTaxes({grossPrize:1000,federalFinalRate:101}));
});
test('tabla de premios contiene cuotas exactas y se actualiza sin inventar jackpot',()=>{
  const pb=oddsPrizeTable(games.powerball,'powerball');
  assert.equal(pb.length,9);
  assert.equal(pb.find(x=>x.key==='5|1').status,'variable');
  assert.equal(pb.find(x=>x.key==='4|1').min,50000);
  const mm=oddsPrizeTable(games.megamillions,'megamillions');
  assert.equal(mm.length,9);
  assert.equal(mm.find(x=>x.key==='0|1').min,10);
  assert.equal(mm.find(x=>x.key==='0|1').max,50);
  const md=oddsPrizeTable(games.mdpick4,'mdpick4');
  assert.equal(md.length,1);assert.equal(md[0].odds,10000n);
  assert.equal(oddsPrizeTable(games.nytake5,'nytake5').length,0);
});
test('las cinco pestañas, enlaces y avisos de validación están presentes',()=>{
  const html=readFileSync(new URL('../index.html',import.meta.url),'utf8');
  const js=readFileSync(new URL('../assets/services-ui.mjs',import.meta.url),'utf8');
  const css=readFileSync(new URL('../assets/lottery-pro.css',import.meta.url),'utf8');
  assert.ok(html.indexOf('id="generador"')<html.indexOf('id="servicesHub"'));
  for(const tab of ['check','scan','prizes','budget','tax']){
    assert.ok(html.includes('id="serviceTab-'+tab+'"'));
    assert.ok(html.includes('id="servicePanel-'+tab+'"'));
  }
  assert.ok(html.includes('assets/services-ui.mjs'));
  assert.ok(html.includes('id="scanFile"'));
  assert.ok(js.includes('readTicketBarcodeImage'));
  const reader=readFileSync(new URL('../assets/barcode-reader.mjs',import.meta.url),'utf8');
  assert.ok(reader.includes('BarcodeDetector'));
  assert.ok(css.includes('.services-hub{'));
  assert.ok(js.includes('No se ha confirmado un sorteo'));
});
