import {dayKeyUTC,luckySuggestion,validLucky} from './lucky-engine.mjs';
import {outcomeCount} from './scientific-math.mjs';
import {formatInverseOddsExact} from './exact-engine.mjs';

const byId=id=>document.getElementById(id);
let round=0,lastKey='',date='',selection=null;
function refreshLucky(another=false){
  const current=window.LottoLabDailyState?.();
  if(!current||!current.game)return;
  const {key,game,rows}=current;
  const day=dayKeyUTC();
  if(key!==lastKey||date!==day){round=0;lastKey=key;date=day}
  else if(another)round++;
  const ticket=luckySuggestion(game,key,rows,day,round);
  if(!validLucky(game,ticket))throw Error('Combinación no válida');
  selection={game,...ticket};
  byId('luckyDay').textContent='Día '+day+' · UTC';
  byId('luckyGameName').textContent=game.name+' · propuesta '+(round+1);
  const container=byId('luckyBalls');container.replaceChildren();
  for(const v of ticket.main){
    const span=document.createElement('span');
    span.className='ticket-ball'+(game.kind==='digits'?' digits':'')+(key==='chica'?' chica':'');
    span.textContent=String(v).padStart(game.kind==='digits'?game.width:2,'0');
    container.append(span);
  }
  if(ticket.bonus){
    const span=document.createElement('span');span.className='ticket-ball bonus';
    span.textContent=String(ticket.bonus).padStart(2,'0');span.title='Bola especial';
    container.append(span);
  }
  byId('luckyExplanation').textContent=ticket.history?
    'Selección entre números destacados por frecuencia en '+ticket.sample.toLocaleString('es-ES')+' sorteos anteriores. No tienen más probabilidad real que otros números.':
    'Sugerencia matemática diaria. Todavía no hay historial oficial comparable para este juego: no se han inventado datos.';
  byId('luckyProbability').textContent='Probabilidad de la combinación exacta: '+
    formatInverseOddsExact(1n,outcomeCount(game),0)+'. Igual para todas las combinaciones válidas.';
  byId('luckyCopy').disabled=false;
}
byId('luckyRefresh').addEventListener('click',()=>refreshLucky(true));
byId('luckyCopy').addEventListener('click',()=>{
  if(!selection)return;
  const g=selection.game;
  const text=selection.main.map(v=>String(v).padStart(g.kind==='digits'?g.width:2,'0')).join(' ')+
    (selection.bonus?' | '+String(selection.bonus).padStart(2,'0'):'');
  byId('luckyExplanation').textContent='Números del día: '+text+' · Puedes seleccionarlos para copiarlos.';
});
byId('proGame').addEventListener('change',()=>refreshLucky());
window.addEventListener('lotto-science-updated',()=>refreshLucky());
document.addEventListener('visibilitychange',()=>{if(!document.hidden&&date!==dayKeyUTC())refreshLucky()});
refreshLucky();
