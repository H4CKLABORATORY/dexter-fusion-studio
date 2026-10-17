import {test} from 'node:test';import {strict as assert} from 'node:assert';
import {GAMES,choose,totalCombos,exactJackpotChance,normalizeRows,currentRegime,stats,randomTicket,overlaps,backtest,csvForRows} from '../assets/core.mjs';
test('combinaciones Powerball y Mega Millions',()=>{
 assert.equal(totalCombos('powerball'),292201338n);assert.equal(totalCombos('megamillions'),290472336n);
 assert.equal(choose(49,6),13983816n);assert.equal(exactJackpotChance('powerball'),1/292201338);
});
test('regímenes se mantienen separados',()=>{
 const rows=normalizeRows({game:'megamillions',rows:[['2025-04-04',2,3,4,5,6,25],['2025-04-08',2,3,4,5,6,23],['2026-10-16',2,15,31,41,68,11]]},'megamillions');
 assert.equal(rows.length,3);assert.equal(currentRegime(rows,'megamillions').length,2);
});
test('frecuencias y pares no crean predicciones',()=>{
 const rs=[{date:'2026-10-16',main:[1,2,3,4,5],bonus:1},{date:'2026-10-13',main:[1,2,3,4,6],bonus:2}];
 const s=stats(rs,'powerball');assert.equal(s.n,2);assert.equal(s.hot[0].count,2);assert.equal(s.pairs[0].count,2);
 assert.deepEqual(overlaps({main:[1,2,3,8,9],bonus:1},rs[0]),{main:3,bonus:true});
 assert.equal(csvForRows(rs).split('\n').length,4);
});
test('generador sin duplicados y dentro de rango',()=>{
 let state=1;const seeded=max=>{state=(state*1103515245+12345)>>>0;return state%max};
 for(const game of Object.keys(GAMES)){const t=randomTicket(game,seeded);assert.equal(t.main.length,5);assert.equal(new Set(t.main).size,5);assert(t.bonus>=1&&t.bonus<=GAMES[game].bonus)}
});
test('walk-forward usa únicamente sorteos anteriores',()=>{
 const rows=Array.from({length:72},(_,i)=>({date:`2026-${String(1+Math.floor(i/28)).padStart(2,'0')}-${String(i%28+1).padStart(2,'0')}`,main:[1,2,3,4,5].map(n=>n+i%60),bonus:i%26+1}));
 const result=backtest(rows,'powerball',{evaluations:25});
 assert.equal(result.n,25);assert.ok(Math.abs(result.randomExpected-25/69)<1e-12);
});