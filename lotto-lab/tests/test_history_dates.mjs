import {test} from 'node:test';
import {strict as assert} from 'node:assert';
import {readFileSync} from 'node:fs';

// Evaluate only the two pure parser functions; page-context itself requires a DOM.
const source=readFileSync(new URL('../assets/page-context.mjs',import.meta.url),'utf8');
const start=source.indexOf('function isValidDrawDate(value){');
const end=source.indexOf('async function loadHistory(){',start);
assert.ok(start>=0&&end>start,'History parser functions must be present');
const parseHistory=new Function(source.slice(start,end)+'\nreturn parseHistory;')();
const game={start:'2015-10-07',n:69,k:5,bonus:26};
const draw=date=>[date,1,2,3,4,5,6];

test('history ignores impossible dates and malformed date strings',()=>{
  const rows=[draw('2026-10-20'),draw('2026-13-99'),draw('2026-02-30'),
    draw('2026-1-02'),draw('2024-02-29'),draw('2025-02-29')];
  const result=parseHistory({game:'powerball',rows},game,'powerball');
  assert.deepEqual(result.map(x=>x.date),['2026-10-20','2024-02-29']);
});

test('history keeps current regime, valid bonus, and date deduplication',()=>{
  const rows=[draw('2015-10-06'),draw('2015-10-07'),draw('2015-10-07'),
    ['2016-01-01',1,1,3,4,5,6],['2016-01-02',1,2,3,4,5,27]];
  const result=parseHistory({game:'powerball',rows},game,'powerball');
  assert.deepEqual(result.map(x=>x.date),['2015-10-07']);
});

test('history still rejects mismatched game payloads',()=>{
  assert.throws(()=>parseHistory({game:'megamillions',rows:[draw('2026-10-20')]},game,'powerball'),/Historial incompatible/);
});
