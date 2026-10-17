import {test} from 'node:test';
import {strict as assert} from 'node:assert';
import {readFileSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {dirname,resolve} from 'node:path';
import {exactSpectrum,outcomeCount} from '../assets/scientific-math.mjs';
import {dayKeyUTC,luckySuggestion,validLucky} from '../assets/lucky-engine.mjs';
import {
  gcd,fraction,plus,times,formatInteger,formatDecimal,
  formatPercentExact,formatInverseOddsExact,formatUSDDollarsExact,
  multiplierExpectedExact,fixedPrizeExpectedExact,probabilityExact
} from '../assets/exact-engine.mjs';

const games={
  powerball:{n:69,k:5,bonus:26},
  megamillions:{n:70,k:5,bonus:24},
  vacash5:{n:45,k:5,bonus:0},
  cafantasy5:{n:39,k:5,bonus:0},
  nytake5:{n:39,k:5,bonus:0},
  chica:{n:100,k:1,bonus:0},
  mdpick3:{n:1000,k:1,bonus:0,kind:'digits',width:3},
  mdpick4:{n:10000,k:1,bonus:0,kind:'digits',width:4},
  mdpick5:{n:100000,k:1,bonus:0,kind:'digits',width:5},
  vapick3:{n:1000,k:1,bonus:0,kind:'digits',width:3},
};
test('aritmética BigInt simplifica y suma fracciones sin coma flotante',()=>{
  assert.deepEqual(fraction(10,20),{n:1n,d:2n});
  assert.deepEqual(fraction(-2,-4),{n:1n,d:2n});
  assert.deepEqual(plus(fraction(1,6),fraction(1,3)),{n:1n,d:2n});
  assert.deepEqual(times(fraction(12,18),fraction(9,16)),{n:3n,d:8n});
  assert.equal(gcd(144n,96n),48n);
  assert.throws(()=>fraction(1,0));
  assert.throws(()=>fraction(1.25,4));
  assert.throws(()=>fraction(Number.MAX_SAFE_INTEGER+10,5));
});
test('formato matemático preciso y porcentaje visible sin error binario',()=>{
  assert.equal(formatInteger(292201338n),'292.201.338');
  assert.equal(formatDecimal(1n,3n,12),'0,333333333333');
  assert.equal(formatDecimal(1n,8n,5),'0,12500');
  assert.equal(formatDecimal(9n,10n,0),'1');
  assert.equal(formatPercentExact(1n,100n,0),'1 %');
  assert.equal(formatPercentExact(5n,69n,0),'7 %');
  assert.equal(formatPercentExact(1n,26n,0),'4 %');
  assert.equal(formatPercentExact(1n,292201338n,14),'0,000000342229 %');
  assert.equal(formatInverseOddsExact(1n,292201338n,0),'1 entre 292.201.338');
  assert.equal(formatUSDDollarsExact(1025n,100n),'US$ 10,25');
});
test('distribución del multiplicador integrado de Mega Millions es 96/32 = 3',()=>{
  assert.deepEqual(multiplierExpectedExact(),{n:3n,d:1n});
  const pb=fixedPrizeExpectedExact(games.powerball,'powerball');
  const mm=fixedPrizeExpectedExact(games.megamillions,'megamillions');
  assert.ok(pb.n>0n&&pb.d>0n);
  assert.ok(mm.n>0n&&mm.d>0n);
  assert.equal(fixedPrizeExpectedExact(games.cafantasy5,'cafantasy5'),null);
});
test('Python Fraction verifica 87+ fracciones generadas por BigInt',()=>{
  const vectors=[];
  for(const [name,game] of Object.entries(games)){
    const n=outcomeCount(game);
    const main=probabilityExact(game);
    vectors.push({name,game,total:n.toString(),numerator:main.n.toString(),denominator:main.d.toString()});
    if(game.kind==='digits')continue;
    for(const item of exactSpectrum(game)){
      const f=fraction(item.ways,item.total);
      vectors.push({name,game,total:n.toString(),numerator:f.n.toString(),
        denominator:f.d.toString(),r:item.main,special:item.bonus});
    }
  }
  assert.ok(vectors.length>=80);
  const script=resolve(dirname(fileURLToPath(import.meta.url)),'../scripts/verify_exact.py');
  const output=execFileSync('python',[script],{
    input:JSON.stringify(vectors),encoding:'utf8',timeout:15000
  });
  assert.match(output,/VALIDACIÓN CRUZADA/);
});
test('sugerencias diarias se reproducen y siempre respetan las reglas',()=>{
  const date='2026-10-17';
  for(const [name,game] of Object.entries(games)){
    const one=luckySuggestion(game,name,[],date);
    const repeated=luckySuggestion(game,name,[],date);
    assert.deepEqual(one,repeated,name);
    assert.ok(validLucky(game,one),name);
    for(let j=1;j<20;j++){
      const suggestion=luckySuggestion(game,name,[],'2026-10-18',j);
      assert.ok(validLucky(game,suggestion),name+' '+j);
    }
  }
  assert.equal(dayKeyUTC(new Date('2026-10-17T23:59:59Z')),'2026-10-17');
  assert.equal(dayKeyUTC(new Date('2026-10-18T00:00:00Z')),'2026-10-18');
  assert.throws(()=>dayKeyUTC(new Date('abc')));
});
test('números de la suerte usan frecuencias pasadas solo cuando hay muestra suficiente',()=>{
  const game=games.powerball,draws=Array.from({length:120},(_,index)=>({
    date:'2026-10-'+String(index%30+1).padStart(2,'0'),
    main:[1,2,3,4,5],bonus:1
  }));
  const a=luckySuggestion(game,'powerball',draws,'2026-10-17',0);
  assert.equal(a.history,true);
  assert.equal(a.sample,120);
  assert.ok(validLucky(game,a));
  const b=luckySuggestion(game,'powerball',draws.slice(0,10),'2026-10-17',0);
  assert.equal(b.history,false);
  assert.equal(luckySuggestion(games.mdpick3,'mdpick3',draws,'2026-10-17').history,false);
  assert.throws(()=>luckySuggestion(game,'powerball',draws,'bad-date'));
});
test('portada da prioridad al generador, al lucky diario y a los porcentajes simples',()=>{
  const html=readFileSync(new URL('../index.html',import.meta.url),'utf8');
  const script=readFileSync(new URL('../assets/generator-pro.js',import.meta.url),'utf8');
  assert.ok(html.indexOf('id="luckyDaily"')>html.indexOf('id="generador"'));
  assert.ok(html.indexOf('id="luckyDaily"')<html.indexOf('id="comparador"'));
  assert.ok(html.includes('assets/lucky-ui.mjs'));
  assert.ok(script.includes('pctCompact(individual)'));
  assert.ok(!html.includes('id="proSeed"'));
});
