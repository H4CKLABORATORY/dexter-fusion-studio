import {test} from 'node:test';
import {strict as assert} from 'node:assert';
import {readFileSync} from 'node:fs';
import {
  unrankCombination,rankCombination,unrankTicket,rankTicket,
  uniqueSample,coverageTarget,drawsForAnyPrize
} from '../assets/coverage-engine.mjs';
const games={
  powerball:{n:69,k:5,bonus:26},
  megamillions:{n:70,k:5,bonus:24},
  vacash5:{n:45,k:5,bonus:0},
  cafantasy5:{n:39,k:5,bonus:0},
  mdpick3:{n:1000,k:1,bonus:0,kind:'digits',width:3},
  mdpick4:{n:10000,k:1,bonus:0,kind:'digits',width:4},
  chica:{n:100,k:1,bonus:0}
};
test('orden lexicográfico completo: desindexar e indexar cada C(7,3)',()=>{
  const seen=new Set();
  for(let i=0n;i<35n;i++){
    const combo=unrankCombination(7,3,i);
    assert.equal(rankCombination(7,3,combo),i);
    assert.equal(combo.length,3);
    assert.ok(combo.every((v,j)=>j===0||v>combo[j-1]));
    seen.add(combo.join(','));
  }
  assert.equal(seen.size,35);
  assert.deepEqual(unrankCombination(7,3,0n),[1,2,3]);
  assert.deepEqual(unrankCombination(7,3,34n),[5,6,7]);
  assert.throws(()=>unrankCombination(7,3,35n));
  assert.throws(()=>rankCombination(7,3,[1,1,2]));
});
test('cada combinación de los juegos reales tiene índice reversible',()=>{
  for(const [name,g] of Object.entries(games)){
    for(const rank of [0n,1n,13n,99n]){
      const ticket=unrankTicket(g,rank);
      assert.equal(rankTicket(g,ticket),rank,name+' '+rank);
    }
    const tickets=uniqueSample(g,20,'TEST-'+name);
    assert.equal(tickets.length,20);
    assert.equal(new Set(tickets.map(t=>t.index.toString())).size,20);
    assert.ok(tickets.every(t=>rankTicket(g,t)===t.index));
    assert.deepEqual(uniqueSample(g,20,'TEST-'+name),tickets);
  }
});
test('80 por ciento es cobertura exacta, sin inventar probabilidad favorable',()=>{
  const pb=coverageTarget(games.powerball,8000);
  assert.equal(pb.total,292201338n);
  assert.equal(pb.tickets,233761071n);
  assert.equal(pb.tickets*5n>=pb.total*4n,true);
  assert.equal((pb.tickets-1n)*5n<pb.total*4n,true);
  assert.equal(pb.tickets*2n,467522142n);
  const mm=coverageTarget(games.megamillions,8000);
  assert.equal(mm.tickets,232377869n);
  assert.equal(mm.tickets*5n,1161889345n);
  assert.equal(coverageTarget(games.powerball,10000).tickets,pb.total);
  assert.throws(()=>coverageTarget(games.powerball,0));
});
test('80 por ciento de obtener algún premio se calcula únicamente sobre sorteos independientes',()=>{
  assert.equal(drawsForAnyPrize(games.powerball,'powerball',8000),40);
  assert.equal(drawsForAnyPrize(games.megamillions,'megamillions',8000),37);
  assert.equal(drawsForAnyPrize(games.chica,'chica',8000),null);
});
test('el explorador de 80 por ciento no desplaza el generador ni el lucky diario',()=>{
  const page=readFileSync(new URL('../index.html',import.meta.url),'utf8');
  assert.ok(page.indexOf('id="generador"')<page.indexOf('id="coverageMandel"'));
  assert.ok(page.indexOf('id="luckyDaily"')<page.indexOf('id="coverageMandel"'));
  assert.ok(page.includes('assets/coverage-ui.mjs'));
  assert.ok(!page.includes('id="proSeed"'));
});
