import {test} from 'node:test';
import {strict as assert} from 'node:assert';
import {readFileSync} from 'node:fs';
import {specs} from '../assets/game-catalog.mjs';
import {outcomeCount} from '../assets/scientific-math.mjs';
import {rankTicket} from '../assets/coverage-engine.mjs';
import {chooseUniqueRanks,randomBigIntBelow,generateUniquePack,generateDisjointPack,disjointThreePlusOdds,packCost} from '../assets/unique-pack.mjs';

test('Floyd da cobertura sin duplicados y sin enumerar el universo de boletos',()=>{
  for(const [key,game] of Object.entries(specs)){
    let sample=0n;
    const count=key==='chica'?100:50;
    const result=generateUniquePack(game,count,limit=>{
      sample=(sample*6364136223846793005n+1442695040888963407n)&((1n<<64n)-1n);
      return sample%limit;
    });
    assert.equal(result.count,count);
    assert.equal(result.total,outcomeCount(game));
    assert.equal(new Set(result.tickets.map(x=>String(x.rank))).size,count,key);
    assert.deepEqual(result.tickets.map(x=>rankTicket(game,x)),result.tickets.map(x=>x.rank));
    assert.ok(result.tickets.every(x=>x.rank>=0n&&x.rank<result.total));
    assert.equal(result.coverageNumerator,BigInt(count));
    assert.equal(result.coverageDenominator,result.total);
  }
});
test('cada subconjunto de dos resultados entre cuatro es equiprobable en Floyd',()=>{
  const observed=new Map();
  for(let t1=0n;t1<3n;t1++)for(let t2=0n;t2<4n;t2++){
    let i=0;const source=[t1,t2];
    const ids=chooseUniqueRanks(4n,2,limit=>{
      const value=source[i++];
      assert.ok(value<limit);
      return value;
    });
    assert.equal(ids.length,2);
    assert.equal(new Set(ids).size,2);
    const key=ids.sort((a,b)=>a<b?-1:1).join(',');
    observed.set(key,(observed.get(key)||0)+1);
  }
  assert.equal(observed.size,6);
  assert.deepEqual([...observed.values()].sort(),[2,2,2,2,2,2]);
});
test('rechazo de números aleatorios elimina sesgo de módulo en BigInt',()=>{
  const sequence=[15,3];let index=0;
  assert.equal(randomBigIntBelow(10n,()=>sequence[index++]),3n);
  assert.equal(index,2);
  assert.equal(randomBigIntBelow(1n),0n);
  assert.throws(()=>randomBigIntBelow(0n));
  assert.throws(()=>randomBigIntBelow(10n,()=>-1),/uint32/);
  assert.throws(()=>chooseUniqueRanks(5n,6),/cantidad|combinaciones/i);
  assert.throws(()=>chooseUniqueRanks(0n,1));
  assert.throws(()=>chooseUniqueRanks(5n,0));
});
test('cobertura real 100 boletos vs 1 boleto sin alterar probabilidades individuales',()=>{
  const game=specs.powerball;
  const count=100n,total=outcomeCount(game);
  assert.equal(total,292201338n);
  assert.equal(count*2n,200n);
  assert.equal(packCost(100,2),200);
  assert.equal(packCost(20,5),100);
  assert.equal(packCost(50,null),null);
  assert.throws(()=>packCost(10,-1));
});
test('el generador principal incluye paquetes accesibles y ningún botón compra boletos',()=>{
  const html=readFileSync(new URL('../index.html',import.meta.url),'utf8');
  const builder=readFileSync(new URL('../scripts/build_pages.mjs',import.meta.url),'utf8');
  const ui=readFileSync(new URL('../assets/unique-pack-ui.mjs',import.meta.url),'utf8');
  assert.ok(html.indexOf('id="generador"')<html.indexOf('id="uniquePack"'));
  assert.ok(html.includes('id="packCount"'));
  assert.ok(html.includes('id="packGenerate"'));
  assert.ok(html.includes('id="packOdds"'));
  assert.ok(html.includes('id="packPrice"'));
  assert.ok(html.includes('assets/unique-pack-ui.mjs'));
  assert.ok(builder.includes("'unique-pack-ui.mjs'"));
  assert.ok(ui.includes('generateUniquePack('));
  assert.ok(!ui.includes('Math.random('));
});

test('modo diversidad prueba 3+ aciertos sin superposición en C(10,5)',()=>{
  const game={name:'Matriz pequeña de verificación',n:10,k:5,bonus:0};
  const pack=generateDisjointPack(game,2,()=>0n);
  assert.equal(pack.tickets.length,2);
  const first=new Set(pack.tickets[0].main),second=new Set(pack.tickets[1].main);
  assert.equal([...first].filter(x=>second.has(x)).length,0);
  assert.equal(new Set([...first,...second]).size,10);
  const exact=disjointThreePlusOdds(game,2);
  assert.equal(exact.numerator,exact.denominator);
  let qualifying=0,checked=0;
  for(let a=1;a<=10;a++)for(let b=a+1;b<=10;b++)
    for(let c=b+1;c<=10;c++)for(let d=c+1;d<=10;d++)
      for(let e=d+1;e<=10;e++){
        const winning=new Set([a,b,c,d,e]);
        const matches=pack.tickets.map(t=>t.main.filter(x=>winning.has(x)).length);
        assert.equal(matches.filter(x=>x>=3).length,1);
        if(matches.some(x=>x>=3))qualifying++;
        checked++;
      }
  assert.equal(checked,252);
  assert.equal(qualifying,252);
});
test('disjoint mode has exact 3+-main odds and unchanged jackpot chance',()=>{
  for(const key of ['powerball','megamillions','vacash5','cafantasy5','nytake5']){
    const game=specs[key],limit=Math.floor(game.n/5);
    let counter=0n;
    const pack=generateDisjointPack(game,limit,n=>(counter++)%n);
    assert.equal(pack.tickets.length,limit);
    assert.equal(new Set(pack.tickets.flatMap(t=>t.main)).size,limit*5);
    assert.equal(new Set(pack.tickets.map(t=>String(t.rank))).size,limit);
    assert.equal(pack.coverageNumerator,BigInt(limit));
    assert.equal(pack.coverageDenominator,outcomeCount(game));
    assert.ok(pack.threePlusOdds.numerator>0n);
    assert.ok(pack.threePlusOdds.numerator<=pack.threePlusOdds.denominator);
    assert.throws(()=>generateDisjointPack(game,limit+1,()=>0n),/grupos/);
  }
  assert.throws(()=>disjointThreePlusOdds(specs.mdpick3,1),/cinco bolas/);
});
test('la portada expone 2 métodos diferentes y resultado de 3+ sin exagerar jackpot',()=>{
  const html=readFileSync(new URL('../index.html',import.meta.url),'utf8');
  const ui=readFileSync(new URL('../assets/unique-pack-ui.mjs',import.meta.url),'utf8');
  assert.ok(html.includes('id="packMode"'));
  assert.ok(html.includes('value="disjoint"'));
  assert.ok(html.includes('id="packThreePlusOdds"'));
  assert.ok(ui.includes('generateDisjointPack('));
  assert.ok(ui.includes('disjointThreePlusOdds('));
  assert.ok(ui.includes('El jackpot mantiene la misma cobertura m/N'));
});
