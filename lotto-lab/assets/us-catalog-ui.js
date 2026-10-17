import {OFFICIAL_DIRECTORY,STATES_WITHOUT_LOTTERY,validateJurisdictions,searchJurisdictions} from './us-catalog.mjs';

const root=document.getElementById('usDirectory');
const search=document.getElementById('usSearch');
const scope=document.getElementById('usScope');
const results=document.getElementById('usResults');
const status=document.getElementById('usStatus');
const count=document.getElementById('usCount');
const gameSelector=document.getElementById('proGame');
let catalogue=null,loading=false;

const labelFor=(gameKey)=>gameSelector.querySelector('option[value="'+gameKey+'"]')?.textContent||gameKey;
function createText(tag,text,cl){
  const element=document.createElement(tag);
  if(cl)element.className=cl;
  element.textContent=text;
  return element;
}
function showItems(){
  if(!catalogue)return;
  const items=searchJurisdictions(catalogue,search.value,scope.value);
  results.replaceChildren();
  count.textContent=items.length+' de 48 jurisdicciones';
  if(!items.length){
    results.append(createText('p','No se encontraron jurisdicciones con ese filtro.','subtle'));
    return;
  }
  for(const jurisdiction of items){
    const card=document.createElement('article');card.className='us-state-card';
    const top=createText('div','','us-state-head');
    top.append(createText('strong',jurisdiction.name));
    top.append(createText('span',jurisdiction.code,'us-state-code'));
    card.append(top);
    const supported=jurisdiction.verified_game_keys||[];
    card.append(createText('p',supported.length?
      'Generador matemático disponible para '+supported.length+' juego'+(supported.length===1?'':'s')+'.':
      'Jurisdicción catalogada · modalidades pendientes de verificación.',
      'us-state-note'));
    if(supported.length){
      const buttons=createText('div','','us-state-games');
      for(const key of supported){
        const button=createText('button',labelFor(key),'us-game-link');
        button.type='button';
        button.addEventListener('click',()=>{
          if(document.getElementById('generador')){
            gameSelector.value=key;
            gameSelector.dispatchEvent(new Event('change',{bubbles:true}));
            document.getElementById('generador').scrollIntoView({behavior:'smooth'});
          }else{
            try{sessionStorage.setItem('lotto-selected-game',key)}catch{}
            window.location.assign('index.html?game='+encodeURIComponent(key));
          }
        });
        buttons.append(button);
      }
      card.append(buttons);
    }
    const source=document.createElement('a');
    source.href=jurisdiction.source||OFFICIAL_DIRECTORY;
    source.target='_blank';source.rel='noopener noreferrer';
    source.textContent=jurisdiction.source?'Consultar '+jurisdiction.source_label+' ↗':'Ver directorio NASPL ↗';
    source.className='us-official-link';
    card.append(source);
    results.append(card);
  }
}
async function loadCatalogue(){
  if(catalogue||loading)return;
  loading=true;
  status.textContent='Cargando las 48 jurisdicciones del directorio…';
  try{
    const response=await fetch('data/us-jurisdictions.json',{cache:'no-cache'});
    if(!response.ok)throw Error('HTTP '+response.status);
    const data=await response.json();
    catalogue=validateJurisdictions(data);
    status.textContent='Directorio NASPL: 45 estados + Washington D. C., Puerto Rico e Islas Vírgenes. Un enlace en el catálogo no equivale a datos históricos descargados.';
    showItems();
  }catch(error){
    status.textContent='No fue posible cargar el catálogo: '+error.message+'. Consulta el directorio público NASPL.';
    const a=document.createElement('a');a.href=OFFICIAL_DIRECTORY;a.textContent='Abrir el directorio NASPL ↗';a.target='_blank';a.rel='noopener noreferrer';results.replaceChildren(a);
  }finally{loading=false}
}
root.addEventListener('toggle',()=>{if(root.open)loadCatalogue()});
search.addEventListener('input',showItems);
scope.addEventListener('change',showItems);
document.getElementById('usNonLottery').textContent='Estados sin lotería estatal: '+STATES_WITHOUT_LOTTERY.join(', ')+'.';
