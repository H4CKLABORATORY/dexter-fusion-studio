import {test} from 'node:test';
import {strict as assert} from 'node:assert';
import {readFileSync} from 'node:fs';
import {
  uniformInt,validDraw,fairDraw,matchDraw,parseUserTicket,chooseHistorical,
  simulateMany,assessHistorical,rollingStats
} from '../assets/draw-simulator.mjs';

const games={
  powerball:{name:'Powerball',n:69,k:5,bonus:26},
  megamillions:{name:'Mega Millions',n:70,k:5,bonus:24},
  nytake5:{name:'NY Take 5',n:39,k:5,bonus:0},
  vacash5:{name:'Virginia Cash 5',n:45,k:5,bonus:0},
  mdpick3:{name:'MD Pick 3',n:1000,k:1,bonus:0,kind:'digits',width:3},
  mdpick4:{name:'MD Pick 4',n:10000,k:1,bonus:0,kind:'digits',width:4},
  chica:{name:'La Chica',n:100,k:1,bonus:0}
};
function pseudo(seed=258987){
  let value=seed>>>0;
  // Pseudorandom fixture for TESTS ONLY, never for real simulation.
  return max=>{
    value=(Math.imul(value,1664525)+1013904223)>>>0;
    return value%max;
  };
}
test('sin sesgo de módulo: rechaza números fuera del múltiplo permitido',()=>{
  const provided=[4294967295,7],picked=uniformInt(10,()=>provided.shift());
  assert.equal(picked,7);
  assert.throws(()=>uniformInt(0),/Límite/);
  assert.throws(()=>uniformInt(10,()=>-1),/aleatoria inválida/);
  assert.throws(()=>uniformInt(10,()=>4294967296),/aleatoria inválida/);
});
test('sorteos virtuales respetan los límites de cada lotería y no duplican bolas',()=>{
  for(const [name,game] of Object.entries(games)){
    const random=pseudo();
    for(let i=0;i<80;i++){
      const draw=fairDraw(game,random);
      assert.ok(validDraw(game,draw),name+' '+i);
      assert.equal(new Set(draw.main).size,draw.main.length);
      assert.ok(draw.main.every(Number.isInteger));
      if(game.bonus)assert.ok(draw.bonus>=1&&draw.bonus<=game.bonus);
      else assert.equal(draw.bonus,null);
    }
  }
});
test('Powerball: jackpot, especial sola y categoría de cuatro + bonus',()=>{
  const game=games.powerball,ticket={main:[1,2,3,4,5],bonus:6};
  let result=matchDraw(game,ticket,{main:[1,2,3,4,5],bonus:6},'powerball');
  assert.deepEqual([result.mainHits,result.bonusHit,result.exact,result.prizeVerified],
    [5,true,true,true]);
  result=matchDraw(game,ticket,{main:[7,8,9,10,11],bonus:6},'powerball');
  assert.equal(result.mainHits,0);
  assert.equal(result.tier,'Solo Powerball');
  assert.equal(result.prizeVerified,true);
  result=matchDraw(game,ticket,{main:[1,2,3,4,9],bonus:6},'powerball');
  assert.equal(result.mainHits,4);
  assert.equal(result.tier,'4 + Powerball');
  assert.equal(result.exact,false);
  result=matchDraw(game,ticket,{main:[1,2,3,4,5],bonus:9},'powerball');
  assert.equal(result.exact,false);
  assert.equal(result.tier,'5 números');
});
test('Pick 3 respeta ceros iniciales y el orden exacto de posiciones',()=>{
  const game=games.mdpick3;
  assert.deepEqual(parseUserTicket(game,'007'),{main:[7],bonus:null});
  assert.deepEqual(parseUserTicket(game,'000'),{main:[0],bonus:null});
  assert.equal(matchDraw(game,{main:[7],bonus:null},{main:[70],bonus:null}).mainHits,1);
  assert.equal(matchDraw(game,{main:[7],bonus:null},{main:[7],bonus:null}).exact,true);
  assert.throws(()=>parseUserTicket(game,'1000'));
  assert.throws(()=>parseUserTicket(game,'1 2 3'));
});
test('números principales, duplicados, especiales y reglas invalidan boletos erróneos',()=>{
  assert.deepEqual(parseUserTicket(games.powerball,'01, 12, 20, 45, 69 | 26'),
    {main:[1,12,20,45,69],bonus:26});
  assert.equal(validDraw(games.powerball,{main:[0,1,2,3,4],bonus:5}),false);
  assert.equal(validDraw(games.powerball,{main:[1,1,2,3,4],bonus:5}),false);
  assert.equal(validDraw(games.powerball,{main:[1,2,3,4,5],bonus:27}),false);
  assert.throws(()=>parseUserTicket(games.powerball,'1 2 3 4 5'));
  assert.throws(()=>parseUserTicket(games.powerball,'1 2 3 4 5 | 27'));
  assert.throws(()=>parseUserTicket(games.nytake5,'0 2 3 4 5'));
  assert.throws(()=>parseUserTicket(games.nytake5,'1 2 3 4 40'));
  assert.throws(()=>parseUserTicket(games.nytake5,'1 2 2 3 4'));
  assert.equal(validDraw(games.chica,{main:[0],bonus:null}),true);
  assert.equal(validDraw(games.chica,{main:[99],bonus:null}),true);
});
test('reproducción histórica utiliza solo resultados presentes en el archivo',()=>{
  const rows=[
    {date:'2026-10-10',main:[1,2,3,4,5],bonus:1},
    {date:'2026-10-12',main:[6,7,8,9,10],bonus:2},
    {date:'2026-10-13',main:[1,1,2,3,4],bonus:5}
  ];
  const sample=chooseHistorical(rows,games.powerball,()=>1);
  assert.deepEqual(sample,{date:'2026-10-12',main:[6,7,8,9,10],bonus:2,period:null});
  assert.throws(()=>chooseHistorical([],games.powerball),/No hay historial/);
  const ticket={main:[1,2,3,4,5],bonus:1};
  const report=assessHistorical(rows,games.powerball,ticket,'powerball');
  assert.equal(report.compared,2);
  assert.equal(report.exact,1);
  assert.equal(report.latestExact,'2026-10-10');
  assert.equal(report.highestMainMatches,5);
  assert.equal(report.bonusHits,1);
});
test('1.000 sorteos simulados se verifican como experimento, no como pronóstico',()=>{
  const game=games.vacash5;
  const ticket={main:[1,2,3,4,5],bonus:null};
  const result=simulateMany(game,ticket,'vacash5',1000,pseudo(234567));
  assert.equal(result.draws,1000);
  assert.equal(result.buckets.reduce((x,y)=>x+y,0),1000);
  assert.equal(result.buckets.length,6);
  assert.equal(result.fairBaseline,25/45);
  assert.ok(result.exact<=result.anyKnownPrize);
  assert.ok(result.meanHits>=0&&result.meanHits<=5);
  assert.throws(()=>simulateMany(game,ticket,'vacash5',10001,pseudo()));
});
test('resumen histórico de ventanas 50, 200 y 500 usa únicamente registros válidos',()=>{
  const rows=Array.from({length:230},(_,i)=>({
    date:'2026-'+String(1+Math.floor(i/28)).padStart(2,'0')+'-'+String(i%28+1).padStart(2,'0'),
    main:[1,2,3,4,5],bonus:null
  }));
  rows.push({date:'2026-12-20',main:[0,2,3,4,5],bonus:null});
  const snapshots=rollingStats(rows,games.nytake5);
  assert.deepEqual(snapshots.map(r=>r.draws),[50,200,230]);
  assert.ok(snapshots.every(r=>r.top[0].count===r.draws));
  assert.ok(snapshots.every(r=>r.oddPercent===3/5));
  assert.deepEqual(rollingStats(rows,games.mdpick3),[]);
});
test('animación transparente se integra en la página sin alterar el generador',()=>{
  const page=readFileSync(new URL('../index.html',import.meta.url),'utf8');
  const ui=readFileSync(new URL('../assets/draw-ui.mjs',import.meta.url),'utf8');
  const style=readFileSync(new URL('../assets/lottery-pro.css',import.meta.url),'utf8');
  const service=readFileSync(new URL('../sw.js',import.meta.url),'utf8');
  assert.ok(page.indexOf('id="generador"')<page.indexOf('id="sorteoVirtual"'));
  assert.ok(page.includes('id="drawStage"')&&page.includes('id="drawSource"'));
  assert.ok(page.includes('id="drawStart"')&&page.includes('id="drawBatch"'));
  assert.ok(page.includes('assets/draw-ui.mjs'));
  assert.ok(ui.includes("matchDraw(")&&ui.includes("fairDraw("));
  assert.ok(style.includes('.draw-presenter{')&&style.includes('.draw-machine-globe{'));
  assert.ok(style.includes('prefers-reduced-motion'));
  assert.ok(service.includes('draw-simulator.mjs')&&service.includes('draw-ui.mjs'));
});
