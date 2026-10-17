import {coverageTarget,drawsForAnyPrize,uniqueSample} from './coverage-engine.mjs';
import {formatInteger} from './exact-engine.mjs';

const byId=id=>document.getElementById(id);
const current=()=>window.LottoLabDailyState?.();
const priceOf=game=>{
  const text=String(game.price||'');
  return /^\$\d+$/.test(text)?BigInt(text.slice(1)):null;
};
function renderCoverageTarget(){
  const state=current();
  if(!state?.game)return;
  const {key,game}=state;
  const bp=Number(byId('coverageTarget').value);
  const data=coverageTarget(game,bp);
  byId('coverageNeed').textContent=formatInteger(data.tickets);
  const cost=priceOf(game);
  byId('coverageCost').textContent=cost===null?'Precio por verificar':
    'US$ '+formatInteger(cost*data.tickets);
  byId('coverageCostNote').textContent=cost===null?
    'No se calcula costo hasta verificar el precio en la web oficial.':
    'Estimación al precio base de '+game.price+
    ' por combinación. No incluye impuestos, operaciones ni premios compartidos.';
  const draws=drawsForAnyPrize(game,key,8000);
  byId('coverageAny').textContent=draws===null?'Sin tabla verificada':
    formatInteger(BigInt(draws))+' sorteos';
  byId('coverageExplanation').textContent=
    'Para cubrir al menos '+(bp/100)+' % de los resultados de '+game.name+
    ' en un único sorteo se necesitarían '+formatInteger(data.tickets)+
    ' combinaciones distintas de un total de '+formatInteger(data.total)+
    '. Esto no demuestra que exista una fórmula predictiva.';
  byId('coveragePreviewOutput').replaceChildren();
}
function generatePreview(){
  const state=current();if(!state?.game)return;
  const count=Number(byId('coveragePreviewCount').value);
  const tickets=uniqueSample(state.game,count,'LOTTO-LAB-DEMO|'+state.key);
  const out=byId('coveragePreviewOutput');out.replaceChildren();
  tickets.forEach((ticket,i)=>{
    const p=document.createElement('div');
    p.className='coverage-line';
    const identifier=document.createElement('strong');
    identifier.textContent='#'+String(i+1).padStart(2,'0');
    const nums=document.createElement('span');nums.className='coverage-line-numbers';
    nums.textContent=ticket.main.map(n=>String(n).padStart(state.game.kind==='digits'?state.game.width:2,'0')).join(' · ')+
      (ticket.bonus?'  |  '+String(ticket.bonus).padStart(2,'0'):'');
    p.append(identifier,nums);out.append(p);
  });
  const caption=document.createElement('p');caption.className='lotto-compact-note';
  caption.textContent=count+' combinaciones únicas verificables mediante índices matemáticos. Solo demostración: ninguna fue comprada.';
  out.append(caption);
}
byId('coverageTarget').addEventListener('change',renderCoverageTarget);
byId('coveragePreview').addEventListener('click',generatePreview);
byId('proGame').addEventListener('change',renderCoverageTarget);
byId('coverageMandel').addEventListener('toggle',()=>{
  if(byId('coverageMandel').open)renderCoverageTarget();
});
renderCoverageTarget();
