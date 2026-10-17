import {
  fairDraw,validDraw,matchDraw,parseUserTicket,chooseHistorical,
  simulateMany,assessHistorical,rollingStats
} from './draw-simulator.mjs';

const el=id=>document.getElementById(id);
const now=()=>window.LottoLabScientificState?.();
let playToken=0,busy=false,shownKey='',latest=null,trendCacheKey='';
const compact=n=>Number(n).toLocaleString('es-ES',{maximumFractionDigits:2});
const presenter=el('drawStage');
const prefersLess=()=>typeof matchMedia==='function'&&matchMedia('(prefers-reduced-motion: reduce)').matches;
const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));
function ballText(game,value){
  return String(value).padStart(game.kind==='digits'?game.width:2,'0');
}
function lineText(game,ticket){
  return ticket.main.map(n=>ballText(game,n)).join(' · ')+
    (ticket.bonus!=null?' | '+String(ticket.bonus).padStart(2,'0'):'');
}
function chosenTicket(showError=false){
  const state=now();
  if(!state)return null;
  const source=el('drawSource').value;
  try{
    let ticket;
    if(source==='custom')ticket=parseUserTicket(state.game,el('drawCustomNumbers').value);
    else if(source==='generated'){
      const item=window.LottoLabTicketState?.();
      ticket=item?.key===state.key?item.ticket:null;
      if(!ticket)throw Error('Primero presiona «CALCULAR MI COMBINACIÓN» arriba.');
    }else{
      const item=window.LottoLabLuckyState?.();
      ticket=item?.key===state.key?item:null;
      if(!ticket)throw Error('Espera a que se generen los números de la suerte.');
    }
    if(!validDraw(state.game,ticket))throw Error('Los números no cumplen las reglas del juego');
    return {main:[...ticket.main],bonus:ticket.bonus??null};
  }catch(error){
    if(showError)el('drawConsoleNote').textContent=error.message;
    return null;
  }
}
function paintSelection(){
  if(!now())return;
  el('drawCustomWrapper').hidden=el('drawSource').value!=='custom';
  const current=now(),t=chosenTicket(false);
  el('drawYourNumbers').textContent=t?lineText(current.game,t):
    el('drawSource').value==='custom'?'Escribe tus números':
    'Primero genera un boleto en la parte superior';
  el('drawCustomNumbers').placeholder=current.game.kind==='digits'?'Ej. '+String(7).padStart(current.game.width,'0'):
    current.game.k===1&&!current.game.bonus?'Ej. 07':
    current.game.bonus?'Ej. 5, 12, 19, 28, 41 | 7':'Ej. 5, 12, 19, 28, 41';
}
function createResultBall(value,game,{bonus=false,matched=false}={}){
  const ball=document.createElement('span');
  ball.className='draw-revealed-ball'+(bonus?' bonus':'')+(matched?' matched':'');
  ball.textContent=ballText(game,value);
  ball.title=matched?'Coincide con tu boleto':'Bola del sorteo ficticio';
  return ball;
}
function displayProgress(message){
  el('drawStageStatus').textContent=message;
  el('drawLiveStatus').textContent=message;
}
function invalidate(){
  playToken++;busy=false;
  presenter.classList.remove('draw-spinning','draw-extracting','draw-complete');
  el('drawEmergingBall').textContent='★';
  el('drawStart').disabled=false;el('drawBatch').disabled=false;el('drawHistoryCheck').disabled=false;
}
function prepareGame(){
  invalidate();latest=null;
  el('drawRevealedBalls').replaceChildren();
  const p=document.createElement('span');p.className='ticket-empty';
  p.textContent='Esperando el siguiente sorteo virtual.';
  el('drawRevealedBalls').append(p);
  el('drawMatchBadge').textContent='SIN SORTEO';
  el('drawOutcome').textContent='Elige qué combinación probar y pulsa «INICIAR SORTEO».';
  el('drawStatResults').replaceChildren();
  displayProgress('ESTUDIO LISTO');
  el('drawConsoleNote').textContent='Simulación educativa gratuita. El personaje y la máquina no son un sorteo oficial.';
  paintSelection();
  renderTrends();
}
function beginBusy(){
  playToken++;busy=true;
  el('drawStart').disabled=true;el('drawBatch').disabled=true;el('drawHistoryCheck').disabled=true;
  el('drawStatResults').replaceChildren();
  const rack=el('drawRevealedBalls');rack.replaceChildren();
  el('drawMatchBadge').textContent='EN PROCESO';
  el('drawOutcome').textContent='Mezclando las bolas…';
  displayProgress('MEZCLANDO NÚMEROS');
  return playToken;
}
function completeBusy(){
  busy=false;el('drawStart').disabled=false;el('drawBatch').disabled=false;el('drawHistoryCheck').disabled=false;
  presenter.classList.remove('draw-spinning','draw-extracting');
  presenter.classList.add('draw-complete');
  displayProgress('EXTRACCIÓN COMPLETADA');
}
function showComparison(ticket,result,game,match,historical=false){
  const label=game.kind==='digits'?'posiciones':game.k===1&&!game.bonus?'números':'bolas principales';
  const bonus=game.bonus?' · bola especial '+(match.bonusHit?'acertada':'sin acierto'):'';
  const source=historical?'Reproducción de un resultado oficial pasado':'Sorteo generado virtualmente';
  el('drawMatchBadge').textContent=match.exact?'COMBINACIÓN EXACTA EN DEMO':match.mainHits+' COINCIDENCIA'+(match.mainHits===1?'':'S');
  el('drawOutcome').textContent=
    source+': '+match.mainHits+' de '+(game.kind==='digits'?game.width:game.k)+' '+label+
    bonus+'. '+(match.prizeVerified?
      'Categoría orientativa: '+match.tier+'.':
      match.exact?'Combinación exacta en esta prueba.':'No se certifica ningún premio.')+
    ' Esto NO significa que hayas ganado dinero ni predice el siguiente sorteo.';
  if(historical){
    el('drawConsoleNote').textContent='Resultado histórico reproducido: '+(result.date||'fecha sin datos')+
      (result.period?' · '+(result.period==='midday'?'Mediodía':'Noche'):'')+
      '. Las fuentes oficiales prevalecen.';
  }else{
    el('drawConsoleNote').textContent='Selección aleatoria uniforme obtenida con crypto.getRandomValues y rechazo de sesgo módulo. Simulación independiente.';
  }
}
async function singleDraw(){
  const state=now(),ticket=chosenTicket(true);
  if(!state||!ticket||busy)return;
  let result,historical=el('drawMode').value==='historical';
  try{
    // Generar el resultado ANTES de la animación; la presentación nunca manipula bolas.
    result=historical?chooseHistorical(state.rows,state.game):fairDraw(state.game);
  }catch(error){el('drawConsoleNote').textContent=error.message;return}
  const token=beginBusy();
  const game=state.game;
  const match=matchDraw(game,ticket,result,state.key);
  const selection=new Set(ticket.main);
  const rack=el('drawRevealedBalls');
  presenter.classList.remove('draw-complete');
  presenter.classList.add('draw-spinning');
  const slow=!prefersLess();
  const delay=el('drawSpeed').value==='fast'?240:550;
  const numbers=[...result.main.map(value=>({value,bonus:false})),
    ...(result.bonus!=null?[{value:result.bonus,bonus:true}]:[])];
  if(slow)await wait(660);
  for(let i=0;i<numbers.length;i++){
    if(token!==playToken)return;
    const item=numbers[i];
    presenter.classList.remove('draw-extracting');void presenter.offsetWidth;
    presenter.classList.add('draw-extracting');
    el('drawEmergingBall').textContent=ballText(game,item.value);
    displayProgress('EXTRAYENDO BOLA '+(i+1)+' DE '+numbers.length);
    if(slow)await wait(Math.round(delay*.55));
    if(token!==playToken)return;
    const matched=item.bonus?ticket.bonus===item.value:
      game.kind==='digits'?ticket.main[0]===item.value:selection.has(item.value);
    rack.append(createResultBall(item.value,game,{bonus:item.bonus,matched}));
    if(slow)await wait(Math.round(delay*.45));
  }
  if(token!==playToken)return;
  completeBusy();
  latest={ticket,result,match,game,key:state.key,historical};
  showComparison(ticket,result,game,match,historical);
}
function metric(parent,name,value){
  const box=document.createElement('div');box.className='draw-stat-metric';
  const span=document.createElement('span');span.textContent=name;
  const strong=document.createElement('strong');strong.textContent=value;
  box.append(span,strong);parent.append(box);
}
function batch(){
  const state=now(),ticket=chosenTicket(true);
  if(!state||!ticket||busy)return;
  if(el('drawMode').value==='historical'){
    el('drawConsoleNote').textContent='Las 1.000 pruebas se hacen con sorteos virtuales nuevos. Para datos históricos utiliza «Comprobar historial».';
  }
  try{
    const report=simulateMany(state.game,ticket,state.key,1000);
    const out=el('drawStatResults');out.replaceChildren();
    metric(out,'Pruebas simuladas',compact(report.draws));
    metric(out,'Coincidencias exactas',compact(report.exact));
    metric(out,'Categorías premiadas del juego base',compact(report.anyKnownPrize));
    metric(out,'Media de coincidencias',report.meanHits.toLocaleString('es-ES',{maximumFractionDigits:3}));
    el('drawOutcome').textContent=
      'Experimento virtual de 1.000 sorteos nuevos. Media observada de coincidencias: '+
      report.meanHits.toLocaleString('es-ES',{maximumFractionDigits:3})+
      '; referencia matemática justa: '+
      report.fairBaseline.toLocaleString('es-ES',{maximumFractionDigits:3})+
      '. Los resultados se deben a variación muestral, no prueban eficacia predictiva.';
    el('drawMatchBadge').textContent='1.000 ENSAYOS FICTICIOS';
    displayProgress('SIMULACIÓN TERMINADA');
  }catch(error){el('drawConsoleNote').textContent='No se completó el experimento: '+error.message}
}
function compareHistory(){
  const state=now(),ticket=chosenTicket(true);
  if(!state||!ticket||busy)return;
  try{
    const report=assessHistorical(state.rows,state.game,ticket,state.key);
    const out=el('drawStatResults');out.replaceChildren();
    metric(out,'Sorteos reales comparados',compact(report.compared));
    metric(out,'Combinaciones exactas previas',compact(report.exact));
    metric(out,'Coincidencias máximas',compact(report.highestMainMatches));
    metric(out,'Bola especial coincidente',compact(report.bonusHits));
    el('drawOutcome').textContent='Comparación retrospectiva: los números del boleto se cotejaron con '+
      compact(report.compared)+' resultados oficiales bajo reglas compatibles. Que una combinación haya salido antes no cambia sus posibilidades futuras.';
    el('drawMatchBadge').textContent='ARCHIVO OFICIAL · PASADO';
    displayProgress('HISTORIAL VERIFICADO');
  }catch(error){el('drawConsoleNote').textContent=error.message}
}
function renderTrends(){
  if(!el('drawWindowsPanel').open)return;
  const state=now();if(!state)return;
  const container=el('drawWindowCards');container.replaceChildren();
  const windows=rollingStats(state.rows,state.game);
  if(!windows.length||!windows.some(w=>w.draws)){
    const p=document.createElement('p');p.className='subtle';
    p.textContent='Esta lotería todavía no cuenta con un archivo de sorteos oficiales compatible.';
    container.append(p);return;
  }
  for(const snapshot of windows){
    const card=document.createElement('article');card.className='draw-window-card';
    const heading=document.createElement('strong');heading.textContent='Últimos '+snapshot.window;
    const stamp=document.createElement('small');stamp.textContent=compact(snapshot.draws)+' sorteos disponibles';
    const hot=document.createElement('p');hot.textContent='Más repetidos: '+snapshot.top.map(o=>String(o.number).padStart(2,'0')+' ('+o.count+')').join(' · ');
    const expected=document.createElement('p');
    expected.textContent='Media esperada por bola: '+snapshot.expectedPerNumber.toLocaleString('es-ES',{maximumFractionDigits:2})+
      ' · impares '+Math.round(snapshot.oddPercent*100)+' % · bajos '+Math.round(snapshot.lowPercent*100)+' %';
    card.append(heading,stamp,hot,expected);
    container.append(card);
  }
}
el('drawStart').addEventListener('click',singleDraw);
el('drawBatch').addEventListener('click',batch);
el('drawHistoryCheck').addEventListener('click',compareHistory);
el('drawSource').addEventListener('change',()=>{invalidate();paintSelection()});
el('drawCustomNumbers').addEventListener('input',paintSelection);
el('drawMode').addEventListener('change',()=>{invalidate();
  el('drawConsoleNote').textContent=el('drawMode').value==='historical'?
    'Reproducción de un sorteo pasado. Necesita el archivo oficial de esa lotería.':
    'Sorteo ficticio con números aleatorios uniformes, no oficiales.';
});
el('proGame').addEventListener('change',prepareGame);
window.addEventListener('lotto-science-updated',()=>{paintSelection();renderTrends()});
window.addEventListener('lotto-lucky-updated',paintSelection);
window.addEventListener('lotto-ticket-updated',paintSelection);
el('drawWindowsPanel').addEventListener('toggle',renderTrends);
prepareGame();
