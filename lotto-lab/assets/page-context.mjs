/* Contexto común para herramientas en páginas HTML independientes. */
import {specs,DEFAULT_GAME} from './game-catalog.mjs';
import {dayKeyUTC,luckySuggestion} from './lucky-engine.mjs';

const picker=document.getElementById('proGame');
if(!picker)throw Error('Falta el selector de loterías en esta página.');
const storageGet=(k)=>{
  try{return sessionStorage.getItem(k)}catch{return null}
};
const storageSet=(k,v)=>{
  try{sessionStorage.setItem(k,v)}catch{}
};
const initialFromURL=new URLSearchParams(location.search).get('game');
const initial=[initialFromURL,storageGet('lotto-selected-game'),DEFAULT_GAME]
  .find(key=>key&&Object.hasOwn(specs,key));
picker.value=initial;
let selected=initial,verified=[],loading=0;
function announce(){
  window.dispatchEvent(new Event('lotto-science-updated'));
  window.dispatchEvent(new Event('lotto-lucky-updated'));
}
function parseHistory(payload,game,key){
  if(!payload||payload.game!==key||!Array.isArray(payload.rows))throw Error('Historial incompatible');
  const seen=new Set(),output=[];
  for(const row of payload.rows){
    let main,bonus,date,period=null;
    if(key==='nytake5'){
      if(!row||!Array.isArray(row.main)||!['midday','evening'].includes(row.period))continue;
      ({date,main,period}=row);bonus=null;
    }else{
      if(!Array.isArray(row)||row.length!==7)continue;
      [date,...main]=row;bonus=main.pop();
    }
    if(typeof date!=='string'||date<game.start||main.length!==game.k||
      new Set(main).size!==game.k||!main.every(x=>Number.isInteger(x)&&x>=1&&x<=game.n)||
      (game.bonus&&!Number.isInteger(bonus))||
      (game.bonus&&(bonus<1||bonus>game.bonus)))continue;
    const identity=date+'|'+(period||'');
    if(seen.has(identity))continue;
    seen.add(identity);
    output.push({date,period,main:[...main],bonus});
  }
  return output;
}
async function loadHistory(){
  const current=++loading;
  verified=[];
  announce();
  const game=specs[selected];
  if(!game.source)return;
  try{
    const response=await fetch(game.source,{cache:'no-cache'});
    if(!response.ok)throw Error('HTTP '+response.status);
    const payload=await response.json();
    const rows=parseHistory(payload,game,selected);
    if(rows.length<20)throw Error('Datos insuficientes bajo las reglas actuales');
    if(current!==loading)return;
    verified=rows;
    announce();
  }catch(error){
    if(current!==loading)return;
    console.warn('Historial oficial no disponible:',error);
    verified=[];
    announce();
  }
}
function getSavedTicket(){
  const raw=storageGet('lotto-last-ticket');
  if(!raw)return null;
  try{
    const item=JSON.parse(raw);
    if(item.key!==selected||!item.ticket||
      !Array.isArray(item.ticket.main))return null;
    return {key:selected,game:specs[selected],
      ticket:{main:item.ticket.main,bonus:item.ticket.bonus??null}};
  }catch{return null}
}
window.LottoLabScientificState=()=>({key:selected,game:specs[selected],rows:verified});
window.LottoLabDailyState=window.LottoLabScientificState;
window.LottoLabTicketState=()=>getSavedTicket()||{key:selected,game:specs[selected],ticket:null};
window.LottoLabLuckyState=()=>{
  const game=specs[selected];
  return {key:selected,game,...luckySuggestion(game,selected,verified,dayKeyUTC())};
};
picker.addEventListener('change',()=>{
  if(!Object.hasOwn(specs,picker.value))return;
  selected=picker.value;
  storageSet('lotto-selected-game',selected);
  loadHistory();
});
storageSet('lotto-selected-game',selected);
loadHistory();
