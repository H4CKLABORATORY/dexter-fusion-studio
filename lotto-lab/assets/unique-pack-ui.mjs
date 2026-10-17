/* Paquetes uniformes de boletos distintos; solo a petición del usuario. */
import {generateUniquePack,packCost} from './unique-pack.mjs';
import {PRICE_USD} from './payout-engine.mjs';
import {formatInteger,formatInverseOddsExact} from './exact-engine.mjs';

const $=id=>document.getElementById(id);
let latest=null;
const context=()=>window.LottoLabScientificState?.();
const formatMoney=value=>new Intl.NumberFormat('es-US',
  {style:'currency',currency:'USD',maximumFractionDigits:2}).format(value);
const ballText=(game,n)=>String(n).padStart(game.kind==='digits'?game.width:2,'0');
const ticketText=(game,ticket)=>ticket.main.map(n=>ballText(game,n)).join(' · ')+
  (ticket.bonus!=null?'  |  '+String(ticket.bonus).padStart(2,'0'):'');
function theoreticalSummary(){
  const item=context();
  if(!item?.game)return;
  const count=Number($('packCount').value);
  const total=item.game.kind==='digits'?BigInt(item.game.n):
    // No se genera todavía ninguna combinación: la probabilidad es exacta.
    BigInt(item.game.bonus||1)*combinationCount(item.game.n,item.game.k);
  if(BigInt(count)>total){
    $('packOdds').textContent='Cantidad no admitida';
    $('packPrice').textContent='—';
    return;
  }
  $('packOdds').textContent=formatInteger(BigInt(count))+' de '+formatInteger(total)+
    ' resultados · ~'+formatInverseOddsExact(BigInt(count),total,0);
  const cost=packCost(count,PRICE_USD[item.key]??null);
  $('packPrice').textContent=cost==null?'Precio sin verificar':formatMoney(cost);
}
function combinationCount(n,k){
  k=Math.min(k,n-k);
  let c=1n;
  for(let i=1;i<=k;i++)c=c*BigInt(n-k+i)/BigInt(i);
  return c;
}
function clearPack(){
  latest=null;$('packCopy').disabled=true;
  $('packOutput').replaceChildren();
  $('packStatus').textContent='Lista sin generar. No se han comprado boletos.';
  theoreticalSummary();
}
function generate(){
  const item=context();if(!item?.game)return;
  try{
    const count=Number($('packCount').value);
    const pack=generateUniquePack(item.game,count);
    latest={key:item.key,game:item.game,pack};
    const container=$('packOutput');container.replaceChildren();
    for(let i=0;i<pack.tickets.length;i++){
      const t=pack.tickets[i];
      const row=document.createElement('div');row.className='unique-pack-line';
      const index=document.createElement('span');index.className='unique-pack-index';
      index.textContent=String(i+1).padStart(2,'0');
      const numbers=document.createElement('strong');numbers.textContent=ticketText(item.game,t);
      row.append(index,numbers);container.append(row);
    }
    $('packCopy').disabled=false;
    $('packStatus').textContent=count+' combinaciones válidas y diferentes generadas. '+
      'Para un sorteo justo, todas las combinaciones posibles tienen igual probabilidad; '+
      'este cálculo solo evita repetir selecciones.';
    theoreticalSummary();
  }catch(error){
    clearPack();
    $('packStatus').textContent='No fue posible generar: '+error.message;
  }
}
$('packGenerate').addEventListener('click',generate);
$('packCopy').addEventListener('click',async()=>{
  if(!latest)return;
  const lines=latest.pack.tickets.map((t,i)=>
    String(i+1).padStart(2,'0')+'. '+ticketText(latest.game,t));
  const output='LOTTO LAB · '+latest.game.name+'\n'+lines.join('\n')+
    '\nSimulación matemática, no boletos comprados.';
  try{
    await navigator.clipboard.writeText(output);
    $('packStatus').textContent='Lista copiada. No representa boletos emitidos por una lotería.';
  }catch{
    $('packStatus').textContent='No fue posible acceder al portapapeles. Puedes seleccionar y copiar la lista.';
  }
});
$('packCount').addEventListener('change',clearPack);
$('proGame').addEventListener('change',clearPack);
$('uniquePack').addEventListener('toggle',()=>{
  if($('uniquePack').open)theoreticalSummary();
});
clearPack();
