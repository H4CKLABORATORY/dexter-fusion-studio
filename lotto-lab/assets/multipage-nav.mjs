/* Navegación entre páginas reales: el generador siempre tiene la prioridad. */
const indicator=document.getElementById('statusIndicator');
if(indicator)indicator.innerHTML='<i></i> LOTTO LAB EN LÍNEA';
const current=document.body?.dataset?.page||'home';
/* Compatibilidad: enlaces anteriores con #seccion ahora abren la página real. */
if(current==='home'){
  const previousAnchors={
    servicesHub:'revisar.html', 'servicePanel-check':'revisar.html',
    'servicePanel-scan':'escanear.html','servicePanel-prizes':'premios.html',
    'servicePanel-budget':'presupuesto.html','servicePanel-tax':'impuestos.html',
    sorteoVirtual:'simulador.html',scientificLab:'matematicas.html',
    coverageMandel:'matematicas.html',comparador:'probabilidades.html',
    resumen:'historial.html',estadisticas:'historial.html',analisis:'historial.html',
    metodo:'historial.html',usDirectory:'historial.html',
    premios:'historial.html',archivoDetalle:'historial.html',historial:'historial.html'
  };
  const old=decodeURIComponent(location.hash.slice(1));
  const destination=previousAnchors[old];
  if(destination){
    const selected=document.getElementById('proGame')?.value;
    const query=selected?'?game='+encodeURIComponent(selected):'';
    location.replace(destination+query);
  }
}

const pages=['index.html','revisar.html','escanear.html','premios.html','presupuesto.html',
  'impuestos.html','simulador.html','matematicas.html','probabilidades.html','historial.html'];
for(const a of document.querySelectorAll('.multi-page-nav a')){
  if(a.getAttribute('aria-current')==='page')a.classList.add('nav-active');
  const href=a.getAttribute('href');
  if(!pages.includes(href))continue;
  a.addEventListener('click',()=>{
    const selected=document.getElementById('proGame')?.value;
    if(selected)try{sessionStorage.setItem('lotto-selected-game',selected)}catch{}
  });
}
const install=document.getElementById('installBtn');
if(install){
  let event=null;
  window.addEventListener('beforeinstallprompt',e=>{
    e.preventDefault();event=e;install.hidden=false;
  });
  install.addEventListener('click',async()=>{
    if(!event)return;
    event.prompt();await event.userChoice;event=null;install.hidden=true;
  });
}
if('serviceWorker' in navigator&&location.protocol==='https:')
  navigator.serviceWorker.register('sw.js').catch(()=>{});
