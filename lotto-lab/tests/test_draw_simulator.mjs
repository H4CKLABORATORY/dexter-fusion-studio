import {test} from 'node:test';
import {strict as assert} from 'node:assert';
import {readFileSync} from 'node:fs';
import {
  uniformInt,validDraw,fairDraw,matchDraw,parseUserTicket,chooseHistorical,
  simulateMany,assessHistorical,rollingStats
} from '../assets/draw-simulator.mjs';

const games={
  powerball:{n:69,k:5,bonus:26},
  megamillions:{n:70,k:5,bonus:24},
  nytake5:{n:39,k:5,bonus:0},
  vacash5:{n:45,k:5,bonus:0},
  cafantasy5:{n:39,k:5,bonus:0},
  mdpick3:{n:1000,k:1,bonus:0,kind:'digits',width:3},
  mdpick4:{n:10000,k:1,bonus:0,kind:'digits',width:4},
  mdpick5:{n:100000,k:1,bonus:0,kind:'digits',width:5},
  chica:{n:100,k:1,bonus:0}
};
function makePRNG(seed){
  let state=seed>>>0;
  return max=>{
    state=(Math.imul(state,1664525)+1013904223)>>>0;
    return state%max;
  };
}
test('rechazo criptográfico: evita sesgo de módulo cuando no divide 2^32',()=>{
  let calls=0;
  const value=uniformInt(10,()=>{calls++;return calls===1?4294967295:23});
  assert.equal(value,3);
  assert.equal(calls,2);
  assert.equal(uniformInt(1,()=>4294967295),0);
  assert.throws(()=>uniformInt(0));
  assert.throws(()=>uniformInt(5,()=>-1));
  assert.throws(()=>uniformInt(5,()=>1.2));
});
test('mezcla Fisher-Yates sin reemplazo y bola especial separada',()=>{
  for(const [key,game] of Object.entries(games)){
    for(let i=0;i<70;i++){
      const result=fairDraw(game,makePRNG(i*31337+7));
      assert.ok(validDraw(game,result),key+' '+i);
      if(game.k===5){
        assert.equal(new Set(result.main).size,5);
        assert.ok(result.main.every(v=>v>=1&&v<=game.n));
      }
    }
  }
  const max=fairDraw(games.powerball,n=>n-1);
  assert.deepEqual(max.main,[1,2,3,4,69]);assert.equal(max.bonus,26);
  const min=fairDraw(games.powerball,()=>0);
  assert.deepEqual(min.main,[1,2,3,4,5]);assert.equal(min.bonus,1);
  assert.equal(fairDraw(games.chica,()=>0).main[0],0);
  assert.equal(fairDraw(games.mdpick3,n=>n-1).main[0],999);
});
test('números manuales: validar bola extra, dígitos y rango',()=>{
  assert.deepEqual(parseUserTicket(games.powerball,'05, 12,19 28, 41 | 26'),
    {main:[5,12,19,28,41],bonus:26});
  assert.deepEqual(parseUserTicket(games.nytake5,'39, 3, 5, 21, 7'),
    {main:[3,5,7,21,39],bonus:null});
  assert.deepEqual(parseUserTicket(games.mdpick3,'007'),{main:[7],bonus:null});
  assert.deepEqual(parseUserTicket(games.chica,'00'),{main:[0],bonus:null});
  for(const text of ['1,2,3,4,4|1','1,2,3,4,70|1','1,2,3,4,5|27','1,2,3,4,5'])assert.throws(()=>parseUserTicket(games.powerball,text));
  assert.throws(()=>parseUserTicket(games.mdpick3,'9999'));
  assert.throws(()=>parseUserTicket(games.mdpick3,'-5'));
});
test('comparación: especial correcta, categoría verificada y orden de Pick 3',()=>{
  const g=games.powerball,pick={main:[1,2,3,4,5],bonus:8};
  const same=matchDraw(g,pick,{main:[1,2,3,4,5],bonus:8},'powerball');
  assert.equal(same.exact,true);assert.equal(same.mainHits,5);assert.equal(same.bonusHit,true);
  const four=matchDraw(g,pick,{main:[1,2,3,4,6],bonus:8},'powerball');
  assert.equal(four.mainHits,4);assert.equal(four.prizeVerified,true);assert.match(four.tier,/4/);
  const no=matchDraw(g,pick,{main:[25,26,27,28,29],bonus:13},'powerball');
  assert.equal(no.exact,false);assert.equal(no.prizeVerified,false);
  const digits=games.mdpick3;
  const digitResult=matchDraw(digits,{main:[101],bonus:null},{main:[110],bonus:null},'mdpick3');
  assert.equal(digitResult.mainHits,1);assert.equal(digitResult.exact,false);
  assert.equal(matchDraw(digits,{main:[101],bonus:null},{main:[101],bonus:null},'mdpick3').exact,true);
});
test('modo archivo elige resultado oficial ya publicado, sin inventar fechas',()=>{
  const rows=[
    {date:'2026-09-02',main:[1,2,3,4,5],bonus:1},
    {date:'2026-09-05',main:[12,13,14,15,16],bonus:8},
  ];
  const r=chooseHistorical(rows,games.powerball,()=>1);
  assert.equal(r.date,'2026-09-05');
  assert.deepEqual(r.main,[12,13,14,15,16]);
  assert.throws(()=>chooseHistorical([],games.powerball,()=>0));
});
test('experimento de 1.000 sorteos no altera el boleto e informa frecuencia observada',()=>{
  const game=games.powerball,ticket={main:[1,2,3,4,5],bonus:1};
  const result=simulateMany(game,ticket,'powerball',1000,()=>0);
  assert.equal(result.exact,1000);assert.equal(result.draws,1000);
  assert.equal(result.anyKnownPrize,1000);
  assert.equal(result.buckets[5],1000);
  assert.ok(result.meanHits===5);
  assert.deepEqual(ticket,{main:[1,2,3,4,5],bonus:1});
  assert.throws(()=>simulateMany(game,ticket,'powerball',10001,()=>0));
});
test('comparar todos los sorteos históricos disponibles y aciertos pasados',()=>{
  const rows=[
    {date:'2025-01-01',main:[1,2,3,4,5],bonus:3},
    {date:'2025-01-02',main:[1,2,3,4,6],bonus:3},
    {date:'2025-01-03',main:[10,11,12,13,14],bonus:7},
  ];
  const target={main:[1,2,3,4,5],bonus:3};
  const result=assessHistorical(rows,games.powerball,target,'powerball');
  assert.equal(result.compared,3);
  assert.equal(result.exact,1);
  assert.equal(result.highestMainMatches,5);
  assert.equal(result.latestExact,'2025-01-01');
  assert.equal(result.bonusHits,2);
  assert.throws(()=>assessHistorical([],games.powerball,target,'powerball'));
});
test('estadísticas descriptivas 50/200/500 no equivalen a pronósticos',()=>{
  const rows=Array.from({length:300},(_,i)=>({
    date:'2026-'+String(Math.floor(i/30)+1).padStart(2,'0')+'-'+String(i%30+1).padStart(2,'0'),
    main:[1,2,3,4,5],bonus:1
  }));
  const windows=rollingStats(rows,games.powerball);
  assert.deepEqual(windows.map(x=>x.draws),[50,200,300]);
  assert.equal(windows[0].top[0].number,1);
  assert.equal(windows[0].top[0].count,50);
  assert.equal(windows[2].expectedPerNumber,300*5/69);
  assert.deepEqual(rollingStats([],games.nytake5).map(x=>x.draws),[0,0,0]);
  assert.deepEqual(rollingStats(rows,games.mdpick3),[]);
});
test('página tiene presentador, máquina, controles y avisos de simulación',()=>{
  const html=readFileSync(new URL('../index.html',import.meta.url),'utf8');
  const css=readFileSync(new URL('../assets/lottery-pro.css',import.meta.url),'utf8');
  const ui=readFileSync(new URL('../assets/draw-ui.mjs',import.meta.url),'utf8');
  for(const id of ['sorteoVirtual','drawStage','drawStart','drawBatch','drawSource','drawMode','drawCustomNumbers','drawRevealedBalls','drawWindowsPanel']){
    assert.ok(html.includes('id="'+id+'"'),id);
  }
  assert.ok(html.includes('assets/draw-ui.mjs'));
  assert.ok(html.indexOf('id="generador"')<html.indexOf('id="sorteoVirtual"'));
  assert.match(css,/draw-presenter-arm/);
  assert.match(css,/prefers-reduced-motion/);
  assert.match(ui,/crypto\.getRandomValues/);
  assert.ok(html.includes('NO OFICIAL'));
});
