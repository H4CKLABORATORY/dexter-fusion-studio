import {matchDraw,parseUserTicket,validDraw} from './draw-simulator.mjs';
import {outcomeCount} from './scientific-math.mjs';
import {formatInverseOddsExact} from './exact-engine.mjs';
import {
  PRICE_USD,OFFICIAL_CHECKERS,PRIZE_SOURCES,prizeForMatch,
  oddsPrizeTable,expectedFixedReturn,budgetProjection,estimateTaxes
} from './payout-engine.mjs';

const $=id=>document.getElementById(id);
const cash=n=>new Intl.NumberFormat('es-US',{style:'currency',currency:'USD',minimumFractionDigits:2,maximumFractionDigits:2}).format(n);
const num=n=>Number(n).toLocaleString('es-ES',{maximumFractionDigits:2});
const state=()=>window.LottoLabScientificState?.();
let lastGame='',lastVerifiedPayout=null;
const gameKey=()=>state()?.key||$('proGame').value;
function setStatus(element,message){element.replaceChildren();const p=document.createElement('p');p.textContent=message;element.append(p)}
function make(tag,content,className){
  const e=document.createElement(tag);
  if(className)e.className=className;
  e.textContent=String(content);
  return e;
}
const gameTicketText=(game,ticket)=>{
  if(!ticket)return '';
  const digits=game.kind==='digits'?game.width:2;
  return ticket.main.map(n=>String(n).padStart(digits,'0')).join(' ')+
    (ticket.bonus!=null?' | '+String(ticket.bonus).padStart(2,'0'):'');
};
function activateService(key,{focus=false}={}){
  const keys=['check','scan','prizes','budget','tax'];
  if(!keys.includes(key))return;
  for(const id of keys){
    const tab=$('serviceTab-'+id),panel=$('servicePanel-'+id),selected=id===key;
    tab.setAttribute('aria-selected',selected?'true':'false');
    tab.tabIndex=selected?0:-1;
    panel.hidden=!selected;
  }
  if(key==='prizes')renderPrizes();
  if(key==='budget')renderBudget();
  if(key==='tax')renderTaxes();
  if(focus)$('serviceTab-'+key).focus();
}
const keys=['check','scan','prizes','budget','tax'];
for(const key of keys){
  const node=$('serviceTab-'+key);
  node.addEventListener('click',()=>activateService(key));
  node.addEventListener('keydown',event=>{
    if(!['ArrowRight','ArrowLeft','Home','End'].includes(event.key))return;
    event.preventDefault();
    let next=keys.indexOf(key);
    if(event.key==='Home')next=0;
    else if(event.key==='End')next=keys.length-1;
    else next=(next+(event.key==='ArrowRight'?1:-1)+keys.length)%keys.length;
    activateService(keys[next],{focus:true});
  });
}
const gamePicker=$('serviceGame'),mainPicker=$('proGame');
for(const item of mainPicker.querySelectorAll('option')){
  const option=document.createElement('option');
  option.value=item.value;option.textContent=item.textContent;gamePicker.append(option);
}
function checkerLink(){
  const location=$('checkClaimState').value;
  const url=OFFICIAL_CHECKERS[location]||OFFICIAL_CHECKERS.US;
  for(const target of ['checkOfficialLink','scanOfficialLink'])$(target).href=url;
}
function updateStakeControls(){
  const key=gameKey();
  $('checkPowerPlayWrap').hidden=key!=='powerball';
  $('checkMultiplierWrap').hidden=!['powerball','megamillions'].includes(key);
  $('checkMultiplierHint').textContent=key==='powerball'?
    'Power Play es opcional y depende del multiplicador oficial de ese sorteo.':
    'Mega Millions: cada jugada tiene un multiplicador asignado de 2× a 10×.';
  const price=PRICE_USD[key];
  $('checkStake').value=key.startsWith('mdpick')?1:price??1;
  $('checkStake').step=key.startsWith('mdpick')?'0.5':'1';
  $('budgetPowerPlay').value='base';
  $('budgetPowerPlay').disabled=key!=='powerball';
  $('checkPeriodWrap').hidden=key!=='nytake5';
}
function newest(){
  const rows=state()?.rows||[];
  if(!rows.length)return null;
  return [...rows].sort((a,b)=>{
    const x=a.date+'|'+(a.period||''),y=b.date+'|'+(b.period||'');
    return y.localeCompare(x);
  })[0];
}
function selectLatestDate({notify=true}={}){
  const row=newest();
  if(!row){
    $('checkDateHint').textContent='No existe un historial verificado compatible para esta lotería; puedes ingresar resultados manualmente, pero no verificarlos.';
    if(notify)setStatus($('checkResult'),'No hay resultados oficiales descargados para esta lotería. Revisa la página del operador o introduce un resultado hipotético.');
    return;
  }
  $('checkDate').value=row.date;
  if(row.period)$('checkPeriod').value=row.period;
  $('checkDateHint').textContent='Disponible hasta '+row.date+'. Comprueba que sea la fecha impresa en tu boleto, no necesariamente la de hoy.';
}
function updateResultSource(){
  const official=$('checkResultSource').value==='official';
  $('checkOfficialDateWrap').hidden=!official;
  $('checkPeriodWrap').hidden=!official||gameKey()!=='nytake5';
  $('checkDrawManualWrap').hidden=official;
  if(official&&!$('checkDate').value)selectLatestDate({notify:false});
}
function currentTicket(){
  const context=state();if(!context)return null;
  const mode=$('checkTicketMode').value;
  if(mode==='generated'){
    const entry=window.LottoLabTicketState?.();
    if(entry?.key!==context.key||!entry.ticket)throw Error('Primero genera un boleto de esta lotería.');
    return {main:entry.ticket.main.slice(),bonus:entry.ticket.bonus??null};
  }
  if(mode==='lucky'){
    const entry=window.LottoLabLuckyState?.();
    if(entry?.key!==context.key||!entry.main)throw Error('Los números de la suerte todavía no están disponibles.');
    return {main:entry.main.slice(),bonus:entry.bonus??null};
  }
  return parseUserTicket(context.game,$('checkNumbers').value);
}
function updateTicketSource(){
  const custom=$('checkTicketMode').value==='manual';
  $('checkNumbers').disabled=!custom;
  if(!custom){
    try{$('checkNumbers').value=gameTicketText(state().game,currentTicket());}
    catch{$('checkNumbers').value='';}
  }
}
function selectedResult(){
  const context=state();
  if($('checkResultSource').value==='user')
    return {draw:parseUserTicket(context.game,$('checkWinningNumbers').value),verified:false,date:null};
  if(!Array.isArray(context.rows)||!context.rows.length)
    throw Error('Este juego no tiene archivo oficial verificado. No se pueden confirmar sorteos a partir de una simulación.');
  const date=$('checkDate').value;
  if(!/^\d{4}-\d{2}-\d{2}$/.test(date))throw Error('Elige la fecha exacta impresa en el boleto.');
  const period=$('checkPeriod').value;
  const row=context.rows.find(r=>r.date===date&&(context.key!=='nytake5'||r.period===period));
  if(!row)throw Error('La fecha y el turno no aparecen en la biblioteca oficial actual. Revisa la fecha o las fuentes.');
  if(!validDraw(context.game,row))throw Error('Se rechazó un registro histórico incompatible con las reglas actuales.');
  return {draw:row,verified:true,date:row.date,period:row.period||null};
}
function formatAward(prize){
  if(prize.status==='fixed')return cash(prize.amount);
  if(prize.status==='none')return 'US$0,00';
  if(prize.status==='range')return 'Entre '+cash(prize.min)+' y '+cash(prize.max);
  if(prize.status==='freeplay')return 'Boleto gratuito (sin pago en efectivo)';
  if(prize.status==='variable')return 'Cantidad variable · consultar al operador';
  return 'Sin tabla comprobada';
}
function verifiedResultLabel(result){
  return result.verified?'COTEJO CON ARCHIVO PÚBLICO OFICIAL':'EJERCICIO CON RESULTADO INTRODUCIDO · NO VERIFICADO';
}
function checkNumbers(){
  const context=state();if(!context)return;
  try{
    const ticket=currentTicket();
    if(!validDraw(context.game,ticket))throw Error('Boleto incompatible con este juego');
    const result=selectedResult();
    const match=matchDraw(context.game,ticket,result.draw,context.key);
    const rawMultiplier=$('checkMultiplier').value;
    const multiplier=rawMultiplier==='unknown'?null:Number(rawMultiplier);
    const powerPlay=context.key==='powerball'&&$('checkPowerPlay').value==='yes';
    const prize=prizeForMatch(context.key,match,{
      multiplier,powerPlay,wager:Number($('checkStake').value),
      claimState:$('checkClaimState').value
    });
    const pane=$('checkResult');pane.replaceChildren();
    pane.append(make('strong',verifiedResultLabel(result),'service-status-label'));
    pane.append(make('p','Tus números: '+gameTicketText(context.game,ticket)));
    pane.append(make('p','Sorteo: '+gameTicketText(context.game,result.draw)+
      (result.date?' · '+result.date:'')+(result.period?' · '+result.period:'')));
    pane.append(make('p','Aciertos: '+match.mainHits+' principales'+
      (context.game.bonus?' · especial '+(match.bonusHit?'sí':'no'):'')));
    pane.append(make('strong',formatAward(prize),'service-money-value'));
    pane.append(make('p',prize.label,'service-advice'));
    pane.append(make('p',result.verified?
      'Coincidencia calculada usando números de archivo oficial. El premio solo podría reclamarse si el boleto físico es auténtico, válido, corresponde al sorteo, tiene las opciones indicadas y no ha sido cobrado.':
      'No se ha confirmado un sorteo ni un boleto real; cualquier monto es exclusivamente hipotético.','service-fineprint'));
    lastVerifiedPayout=prize.status==='fixed'&&result.verified?prize.amount:null;
    $('checkSendTax').disabled=lastVerifiedPayout===null||lastVerifiedPayout<=0;
  }catch(error){
    lastVerifiedPayout=null;$('checkSendTax').disabled=true;
    setStatus($('checkResult'),'No es posible completar la comprobación: '+error.message);
  }
}
function makeTD(value){
  const el=document.createElement('td');el.textContent=String(value);return el;
}
function renderPrizes(){
  const ctx=state();if(!ctx)return;
  $('prizeJackpotOdds').textContent=formatInverseOddsExact(1n,outcomeCount(ctx.game),0);
  const price=PRICE_USD[ctx.key];
  $('prizeBaseCost').textContent=price==null?'Por verificar':cash(price);
  const expected=expectedFixedReturn(ctx.game,ctx.key,{claimState:$('checkClaimState').value});
  $('prizeFixedExpected').textContent=expected?cash(expected.expectedGrossPerPlay):'Pago variable/no disponible';
  const body=$('prizeTableRows');body.replaceChildren();
  const tiers=oddsPrizeTable(ctx.game,ctx.key,{claimState:$('checkClaimState').value});
  if(!tiers.length){
    const row=document.createElement('tr');
    const cell=makeTD('Todavía no hay tabla de premios contrastada para esta modalidad. Usa el enlace del operador.');cell.colSpan=3;
    row.append(cell);body.append(row);
  }else{
    for(const t of tiers){
      const row=document.createElement('tr');
      let payout=t.status==='fixed'?cash(t.min):t.status==='range'?
        cash(t.min)+' – '+cash(t.max):t.payout;
      if(ctx.key.startsWith('mdpick'))payout=cash(t.min)+' por 50¢ / '+cash(t.max)+' por US$1';
      const odds=t.ways?formatInverseOddsExact(t.ways,t.total,2):
        '1 entre '+num(t.odds);
      row.append(makeTD(t.label),makeTD(payout),makeTD(odds));
      body.append(row);
    }
  }
  $('prizeTableNote').textContent='Se muestran categorías de juegos básicos, no todas las apuestas opcionales. En Mega Millions el multiplicador 2×–10× viene impreso en el boleto. En Powerball, Power Play se compra aparte. Para jackpots, California y premios pari-mutuel no se inventa el dinero final. Los Pick de Maryland corresponden exclusivamente a Straight.';
  $('prizeOfficialLink').href=PRIZE_SOURCES[ctx.key]||ctx.game.web;
}
function renderBudget(){
  const ctx=state();if(!ctx)return;
  const powerPlay=ctx.key==='powerball'&&$('budgetPowerPlay').value==='powerplay';
  try{
    const b=budgetProjection(ctx.game,ctx.key,$('budgetMoney').value,{powerPlay,
      claimState:$('checkClaimState').value,wager:1});
    if(!b)throw Error('Este juego todavía no tiene una tabla completa de premios fijos aplicable; los premios variables no pueden proyectarse sin inventar valores.');
    $('budgetPlays').textContent=num(b.numberOfPlays);
    $('budgetSpent').textContent=cash(b.spent);
    $('budgetExpectedGross').textContent=cash(b.expectedFixedGross);
    $('budgetExpectedNet').textContent=cash(b.expectedNetExcludingJackpot);
    setStatus($('budgetDetails'),
      'Con '+cash(b.budget)+' cubrirías '+num(b.numberOfPlays)+' jugadas de '+cash(b.baseCost)+
      ' y quedaría '+cash(b.remaining)+' sin utilizar. El promedio estadístico de premios fijos sería '+cash(b.expectedFixedGross)+
      ', pero el resultado real puede ser US$0,00. '+b.excludes+'. No supone que ganarás ese importe.');
  }catch(error){
    for(const id of ['budgetPlays','budgetSpent','budgetExpectedGross','budgetExpectedNet'])$(id).textContent='—';
    setStatus($('budgetDetails'),error.message);
  }
}
function rateLabel(label,value){
  const p=document.createElement('p');p.textContent=label+': '+cash(value);return p;
}
function renderTaxes(){
  $('taxOtherStateWrap').hidden=$('taxRegion').value!=='OTHER';
  try{
    const result=estimateTaxes({
      grossPrize:$('taxGross').value,stake:$('taxStake').value,
      region:$('taxRegion').value,federalFinalRate:Number($('taxFederalRate').value),
      stateFinalRate:Number($('taxStateFinalRate').value),
      otherStateWithholdingRate:Number($('taxOtherWithhold').value)
    });
    $('taxNetWithholding').textContent=cash(result.netAfterWithholding);
    $('taxNetFinal').textContent=cash(result.estimatedAfterFinalTax);
    $('taxWithholdBreakdown').replaceChildren(
      rateLabel('Premio bruto',result.gross),
      rateLabel('Retención federal (24 % si corresponde)',result.federalWithholding),
      rateLabel('Retención estatal orientativa',result.stateWithholding),
      rateLabel('Total retenido',result.withheld)
    );
    $('taxFinalBreakdown').replaceChildren(
      rateLabel('Federal final supuesto',result.estimatedFinalFederal),
      rateLabel('Estatal final supuesto',result.estimatedFinalState),
      rateLabel('Diferencia potencial de impuestos al declarar',result.extraDueEstimated),
      rateLabel('Neto final menos costo de boleto',result.finalCashLessStake)
    );
    setStatus($('taxCaution'),
      'Esto es un escenario aritmético con tasas que puedes modificar, NO una declaración tributaria real. La retención no determina tu obligación final; pueden aplicar otros impuestos, deducciones, pérdidas permitidas, deudas y retenciones diferentes. No confundas el jackpot anunciado con su valor en efectivo.');
  }catch(error){
    $('taxNetWithholding').textContent='—';$('taxNetFinal').textContent='—';
    setStatus($('taxCaution'),'Revisa los importes y tasas: '+error.message);
  }
}
function syncGame(){
  const ctx=state();if(!ctx)return;
  const changed=lastGame!==ctx.key;
  if(gamePicker.value!==ctx.key)gamePicker.value=ctx.key;
  if(changed){
    lastGame=ctx.key;lastVerifiedPayout=null;
    $('checkSendTax').disabled=true;
    $('checkDate').value='';
    updateStakeControls();
    $('checkNumbers').value='';
    $('checkWinningNumbers').value='';
    selectLatestDate({notify:false});
    setStatus($('checkResult'),'Introduce o selecciona los números del boleto y verifica la fecha exacta del sorteo.');
  }else if(!$('checkDate').value&&ctx.rows?.length)selectLatestDate({notify:false});
  checkerLink();updateTicketSource();
  renderPrizes();renderBudget();
}
gamePicker.addEventListener('change',()=>{
  if(mainPicker.value!==gamePicker.value){
    mainPicker.value=gamePicker.value;
    mainPicker.dispatchEvent(new Event('change',{bubbles:true}));
  }
  syncGame();
});
mainPicker.addEventListener('change',syncGame);
window.addEventListener('lotto-science-updated',syncGame);
window.addEventListener('lotto-ticket-updated',updateTicketSource);
window.addEventListener('lotto-lucky-updated',updateTicketSource);
$('checkClaimState').addEventListener('change',()=>{
  checkerLink();renderPrizes();renderBudget();
});
$('checkTicketMode').addEventListener('change',updateTicketSource);
$('checkResultSource').addEventListener('change',updateResultSource);
$('checkLatest').addEventListener('click',()=>selectLatestDate());
$('checkRun').addEventListener('click',checkNumbers);
$('checkSendTax').addEventListener('click',()=>{
  if(lastVerifiedPayout===null)return;
  $('taxGross').value=String(lastVerifiedPayout);
  $('taxStake').value=$('checkStake').value;
  const st=$('checkClaimState').value;
  $('taxRegion').value=['VA','MD'].includes(st)?st:'OTHER';
  $('taxStateFinalRate').value=st==='VA'?'5.75':st==='MD'?'8.95':'0';
  activateService('tax');renderTaxes();$('servicesHub').scrollIntoView({behavior:'smooth'});
});
$('scanGoManual').addEventListener('click',()=>{
  $('checkTicketMode').value='manual';updateTicketSource();activateService('check');
});
$('budgetMoney').addEventListener('input',renderBudget);
$('budgetPowerPlay').addEventListener('change',renderBudget);
$('taxRegion').addEventListener('change',()=>{
  $('taxStateFinalRate').value=$('taxRegion').value==='VA'?'5.75':
    $('taxRegion').value==='MD'?'8.95':'0';
  renderTaxes();
});
for(const id of ['taxGross','taxStake','taxOtherWithhold','taxFederalRate','taxStateFinalRate'])
  $(id).addEventListener('input',renderTaxes);
$('taxRun').addEventListener('click',renderTaxes);

/**
 * Escáner de lectura LOCAL, solo si la API está disponible.
 * Nunca conserva ni sube el ID del boleto, jamás lo trata como premio validado.
 */
$('scanFile').addEventListener('change',async()=>{
  const file=$('scanFile').files?.[0];
  if(!file)return;
  if(!file.type.startsWith('image/')){
    setStatus($('scanOutput'),'Selecciona una imagen de un boleto.');return;
  }
  if(file.size>12_000_000){
    setStatus($('scanOutput'),'La imagen supera 12 MB. Toma otra fotografía más pequeña.');return;
  }
  const container=$('scanOutput');
  setStatus(container,'Leyendo el código localmente; ninguna imagen se transmite a LOTTO LAB…');
  if(typeof BarcodeDetector==='undefined'){
    setStatus(container,'Este navegador no permite BarcodeDetector. En iPhone utiliza el escáner de la app oficial de tu estado o introduce los números en «Revisar boleto». No se ha validado ningún premio.');
    return;
  }
  try{
    const supported=await BarcodeDetector.getSupportedFormats();
    const formats=['code_128','pdf417','qr_code','data_matrix','ean_13','itf','aztec'].filter(f=>supported.includes(f));
    if(!formats.length)throw Error('No hay formatos compatibles');
    const reader=new BarcodeDetector({formats});
    const codes=await reader.detect(file);
    if(!codes.length)throw Error('No se encontró un código legible en la fotografía');
    container.replaceChildren();
    container.append(make('strong','Código leído localmente · NO VALIDADO'));
    for(const entry of codes.slice(0,3)){
      const raw=String(entry.rawValue||'');
      const masked='••••••'+raw.slice(-4);
      container.append(make('p','Tipo '+String(entry.format||'desconocido')+' · identificador oculto '+masked));
    }
    container.append(make('p','La lectura no contiene una autorización para comprobar premios. Utiliza el enlace a la lotería oficial o introduce tus números.'));
  }catch(error){
    setStatus(container,'No fue posible leer el código: '+error.message+
      '. Intenta otra foto bien iluminada o abre el escáner oficial de tu estado.');
  }finally{$('scanFile').value='';}
});
syncGame();updateResultSource();renderTaxes();activateService('check');
