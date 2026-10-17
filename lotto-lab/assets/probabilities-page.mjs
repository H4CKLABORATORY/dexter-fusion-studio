/* Comparador independiente: no necesita cargar el generador ni todas las funciones. */
import {specs} from './game-catalog.mjs';
import {outcomeCount} from './scientific-math.mjs';
import {formatInverseOddsExact,formatPercentExact} from './exact-engine.mjs';
const body=document.getElementById('usComparisonRows');
const rank=()=>Object.entries(specs).filter(([key])=>key!=='chica')
 .map(([key,game])=>({key,game,total:outcomeCount(game)}))
 .sort((a,b)=>a.total<b.total?-1:a.total>b.total?1:a.key.localeCompare(b.key));
function render(){
  const rows=rank();body.replaceChildren();
  for(const entry of rows){
    const row=document.createElement('tr');
    const add=t=>{const cell=document.createElement('td');cell.textContent=t;row.append(cell);};
    add(entry.game.name);
    add(formatInverseOddsExact(1n,entry.total,0));
    add(formatPercentExact(1n,entry.total,12));
    add(entry.game.source?'Datos históricos oficiales disponibles':'Reglas verificadas, sin archivo local');
    const action=document.createElement('td'),link=document.createElement('a');
    link.className='us-game-link';
    link.href='index.html?game='+encodeURIComponent(entry.key);
    link.textContent='Generar →';
    action.append(link);row.append(action);body.append(row);
  }
}
render();
