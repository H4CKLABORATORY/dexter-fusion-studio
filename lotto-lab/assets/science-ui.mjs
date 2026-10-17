import {
  exactSpectrum,prizeSpectrum,outcomeCount,multiDrawChance,historicalAudit,SOURCE_ODDS
} from './scientific-math.mjs';

const $=id=>document.getElementById(id);
const money=n=>new Intl.NumberFormat('es-ES',{style:'currency',currency:'USD',minimumFractionDigits:2,maximumFractionDigits:2}).format(n);
const number=n=>Number(n).toLocaleString('es-ES',{maximumFractionDigits:2});
const percentage=p=>{
  if(!Number.isFinite(p)||p<0)return '—';
  const value=p*100;
  if(value===0)return '0 %';
  if(value<0.000001)return value.toExponential(6).replace('.',',')+' %';
  return value.toLocaleString('es-ES',{minimumFractionDigits:2,maximumFractionDigits:10})+' %';
};
const state=()=>window.LottoLabScientificState?.();
let auditFor=null;
function cell(text){
  const td=document.createElement('td');
  td.textContent=text;return td;
}
function render(){
  const current=state();
  if(!current)return;
  const {key,game,rows}=current;
  if(!game)return;
  const {rows:prizes,anyPrize,expectedFixed,knownPayout}=prizeSpectrum(game,key);
  $('sciAnyPrize').textContent=anyPrize===null?'Sin tabla completa':percentage(anyPrize);
  $('sciPrizeCaution').textContent=anyPrize===null?
    'Aquí mostramos aciertos exactos, no premios sin verificar.':
    '1 entre '+number(1/anyPrize)+(key==='cafantasy5'?' · incluye boleto gratuito':'')+'.';
  $('sciFixedValue').textContent=knownPayout?money(expectedFixed):'Variable/no publicado';
  $('sciExpectedHits').textContent=game.kind==='digits'?
    (game.width/10).toLocaleString('es-ES',{maximumFractionDigits:3})+' dígitos en posición':
    (game.k*game.k/game.n).toLocaleString('es-ES',{maximumFractionDigits:6});
  const entries=prizes.length?prizes:exactSpectrum(game);
  const tbody=$('sciTierRows');tbody.replaceChildren();
  for(const item of entries.sort((a,b)=>b.main-a.main||Number(b.bonus===true)-Number(a.bonus===true))){
    const tr=document.createElement('tr');
    const title=item.label||item.main+' números';
    const payout=prizes.length?(item.prize||'No especificado'):'Coincidencia matemática · premio no verificado';
    tr.append(cell(title),cell(payout),cell(percentage(item.probability)),
      cell(item.probability>0?number(1/item.probability):'—'));
    tr.title=number(item.ways)+' de '+number(outcomeCount(game))+' resultados equiprobables.';
    tbody.append(tr);
  }
  $('sciTiersTitle').textContent=prizes.length?
    'Categorías de premio calculadas: '+prizes.length:
    'Distribución matemática de coincidencias (sin premios inferidos)';
  const href=SOURCE_ODDS[key]||game.web;
  const link=$('sciOfficialOdds');link.href=href;
  link.textContent=SOURCE_ODDS[key]?'Ver premios oficiales ↗':'Ver reglas oficiales ↗';
  $('sciTierDisclaimer').textContent=prizes.length?
    'Las categorías y matrices mostradas corresponden al juego base, sin complementos opcionales. Para California algunas recompensas son variables o un boleto gratuito. El jackpot es variable.':
    'No existe una tabla completa de premios integrada para este juego. Acertar dígitos o bolas parcialmente no siempre genera un premio.';
  const m=Number($('proCoverage').value),draws=Number($('sciDrawCount').value);
  try{
    $('sciRepeated').textContent=percentage(multiDrawChance(game,m,draws));
    $('sciRepeatedNote').textContent=
      m+' combinación'+(m===1?'':'es')+' distinta'+(m===1?'':'s')+
      ' por sorteo × '+draws+' sorteo'+(draws===1?'':'s')+
      ' independiente'+(draws===1?'':'s')+'. Modelo teórico, sin transacciones.';
  }catch(error){
    $('sciRepeated').textContent='—';$('sciRepeatedNote').textContent=error.message;
  }
  const available=Array.isArray(rows)&&rows.length>=80&&!game.kind;
  $('sciRunAudit').disabled=!available;
  if(auditFor!==key){
    $('sciAuditResult').replaceChildren();
    const info=document.createElement('p');info.className='subtle';
    info.textContent=available?'Historial disponible: '+number(rows.length)+' sorteos. Pulsa «Analizar datos» para probar el modelo contra la línea base justa.':
      'Auditoría estadística no disponible: hace falta un historial verificado de al menos 80 sorteos con la misma matriz.';
    $('sciAuditResult').append(info);
    auditFor=key;
  }else if(!available){
    $('sciAuditResult').textContent='No hay datos suficientes para esta lotería.';
  }
}
function audit(){
  const current=state();
  if(!current)return;
  const {game,rows,key}=current;
  const output=$('sciAuditResult');output.replaceChildren();
  const p=document.createElement('p');p.className='subtle';p.textContent='Calculando y evaluando únicamente contra resultados posteriores…';output.append(p);
  try{
    const report=historicalAudit(rows,game,{holdout:180,minTrain:60,priorStrength:120,alpha:.05});
    const metric=document.createElement('div');metric.className='scientific-metrics';
    for(const [label,value] of [
      ['Historial comparable',number(report.totalDraws)+' sorteos'],
      ['Sorteos de evaluación',number(report.evaluationDraws)],
      ['Cambio observado en Brier Score',report.skillPercent.toLocaleString('es-ES',{minimumFractionDigits:3,maximumFractionDigits:4})+' %']]){
      const article=document.createElement('article');
      const span=document.createElement('span');span.textContent=label;
      const strong=document.createElement('strong');strong.textContent=value;
      article.append(span,strong);metric.append(article);
    }
    const sample=document.createElement('p');
    sample.textContent='Error Brier (menor es mejor): modelo justo '+report.brierFair.toFixed(8)+
      ' vs. frecuencia suavizada '+report.brierHistory.toFixed(8)+'. '+
      (report.skillPercent>0?'La estrategia histórica mostró una diferencia favorable en esta muestra; NO está demostrado que prediga sorteos futuros.':
       'El modelo histórico NO mejoró la referencia justa en esta evaluación.');
    const band=document.createElement('p');
    band.textContent='Banda simultánea conservadora (95 %): del '+percentage(report.band.lower)+' al '+
      percentage(report.band.upper)+' por bola principal. Números fuera de la banda: '+
      number(report.anomalies.length)+' de '+game.n+
      '. Es un detector de desviaciones descriptivas; ninguna anomalía prueba por sí sola una oportunidad de ganar.';
    const explain=document.createElement('p');explain.className='lotto-compact-note';
    explain.textContent='Procedimiento: entrenamiento en '+number(report.trainDraws)+
      ' sorteos; luego evaluación en '+number(report.evaluationDraws)+
      ' sorteos ordenados cronológicamente. El modelo experimental aplica suavizado fijo de 120 observaciones. No mira sorteos futuros para emitir sus probabilidades. No se han demostrado ventajas comerciales ni predictivas.';
    output.replaceChildren(metric,sample,band,explain);
  }catch(error){
    output.textContent='No se pudo ejecutar la auditoría: '+error.message;
  }
}
$('sciDrawCount').addEventListener('change',render);
$('proCoverage').addEventListener('change',render);
$('sciRunAudit').addEventListener('click',audit);
$('scientificLab').addEventListener('toggle',()=>{if($('scientificLab').open)render()});
$('proGame').addEventListener('change',()=>{auditFor=null;render()});
window.addEventListener('lotto-science-updated',render);
render();
