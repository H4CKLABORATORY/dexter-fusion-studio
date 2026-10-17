#!/usr/bin/env node
/**
 * LOTTO LAB · constructor de páginas estáticas.
 *
 * El HTML original es la fuente de las funciones. Durante el despliegue se
 * separan en archivos distintos; el generador queda solo en la portada.
 * No hay servidor ni framework de pago.
 *
 * Uso: node lotto-lab/scripts/build_pages.mjs lotto-lab _pages/lotto-lab
 */
import {readFileSync,mkdirSync,writeFileSync} from 'node:fs';
import {resolve,join} from 'node:path';
import {fileURLToPath} from 'node:url';

const sourceDir=resolve(process.argv[2]||fileURLToPath(new URL('..',import.meta.url)));
const destination=resolve(process.argv[3]||sourceDir);
const original=readFileSync(join(sourceDir,'index.html'),'utf8');

function at(needle){
  const pos=original.indexOf(needle);
  if(pos<0)throw Error('No se encontró el bloque original: '+needle);
  return pos;
}
function between(from,to){
  const i=at(from),j=at(to);
  if(i>=j)throw Error('Orden de secciones inesperado: '+from+' / '+to);
  return original.slice(i,j);
}
const generator=between('<section id="generador"','<details id="coverageMandel"');
const coverage=between('<details id="coverageMandel"','<section id="servicesHub"')
  .replace(/<\/section>\s*$/,'').trim();
const services=between('<section id="servicesHub"','<section id="sorteoVirtual"');
const simulator=between('<section id="sorteoVirtual"','<details id="scientificLab"');
const science=between('<details id="scientificLab"','<section id="comparador"');
const comparison=between('<section id="comparador"','<section id="resumen"');
const legacy=original.slice(at('<section id="resumen"'),at('</main>'));
const legacyScriptStart=at('<script type="module">');
const legacyScriptEnd=original.indexOf('</script>',legacyScriptStart);
if(legacyScriptEnd<0)throw Error('No se encontró el cierre del motor histórico');
const legacyScript=original.slice(legacyScriptStart,legacyScriptEnd+'</script>'.length);
const optionsMatch=original.match(/<select id="proGame"[^>]*>([\s\S]*?)<\/select>/);
if(!optionsMatch)throw Error('No se encontró el selector de loterías');
const options=optionsMatch[1];
const baseHead=original.slice(0,at('<body>'));
const baseShell=original.slice(at('<a class="skip"'),at('<main id="contenido">'));
const footer=original.slice(at('</main>')+'</main>'.length,legacyScriptStart);

const urls=[
  ['index.html','Generador','home'],['revisar.html','Revisar boleto','check'],
  ['escanear.html','Escanear','scan'],['premios.html','Premios','prizes'],
  ['presupuesto.html','Presupuesto','budget'],['impuestos.html','Impuestos','tax'],
  ['simulador.html','Sorteo animado','simulator'],['matematicas.html','Laboratorio','math'],
  ['probabilidades.html','Probabilidades','odds'],['historial.html','Historial y estados','history']
];
const tags={
  home:'Generador matemático',check:'Revisar boleto',scan:'Escanear código',
  prizes:'Premios y probabilidades',budget:'Presupuesto',tax:'Impuestos',
  simulator:'Sorteo animado',math:'Laboratorio matemático',
  odds:'Probabilidades por juego',history:'Historial y estados'
};
const descriptions={
  check:'Compara tus números con los resultados oficiales disponibles, sin afirmar que el boleto fue validado.',
  scan:'Lee el código desde tu iPhone o selecciona una imagen. Para validar premios utiliza la aplicación oficial.',
  prizes:'Consulta las posibilidades de cada nivel de acierto y su premio cuando las reglas permiten calcularlo.',
  budget:'Introduce un presupuesto y revisa cuántos boletos cubriría y el promedio matemático de los premios fijos.',
  tax:'Distingue las retenciones del posible impuesto final. Modifica las tasas de tu escenario.',
  simulator:'Prueba tu combinación en un plató animado con resultados virtuales o anteriores.',
  math:'Explora cobertura de combinaciones, fórmulas y pruebas estadísticas sin prometer predicciones.',
  odds:'Compara las probabilidades del premio mayor entre las loterías integradas.',
  history:'Explora los resultados históricos verificados y el directorio estadounidense de loterías.'
};
const escaped=(value)=>String(value).replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;');
function nav(active){
  return '<nav class="navscroll multi-page-nav" aria-label="Páginas principales">'+
    urls.map(([url,title,key])=>'<a href="'+url+'"'+(key===active?' aria-current="page"':'')+
      '>'+title+'</a>').join('')+'</nav>';
}
function screenTitle(active){
  if(active==='home')return '';
  return '<div class="page-heading"><a class="page-back" href="index.html">← Volver al generador</a>'+
    '<span class="lotto-kicker">LOTTO LAB · SERVICIOS</span><h1>'+tags[active]+'</h1>'+
    '<p>'+descriptions[active]+'</p></div>';
}
function selector(extra=''){
  return '<div class="page-context-chooser"><label for="proGame">Lotería seleccionada</label>'+
    '<select id="proGame" aria-label="Seleccionar lotería">'+options+'</select>'+extra+
    '<p>La selección se mantiene al cambiar de página.</p></div>';
}
function navCards(){
  const cards=urls.filter(([url])=>url!=='index.html');
  const icons={check:'✓',scan:'▦',prizes:'★',budget:'$',tax:'%',simulator:'◉',
    math:'Σ',odds:'↗',history:'▤'};
  return '<section class="home-service-cards" aria-label="Abrir servicios independientes">'+
    '<div class="home-services-head"><span class="lotto-kicker">ELIGE QUÉ QUIERES HACER</span>'+
    '<h2>Más herramientas, <span>cada una en su página.</span></h2>'+
    '<p>Primero generas los números. Después puedes revisar boletos, escanear, conocer premios y abrir cualquier herramienta sin recorrer una página interminable.</p></div>'+
    '<div class="home-services-grid">'+cards.map(([url,title,key])=>
      '<a class="home-service-card" href="'+url+'"><span class="home-card-icon" aria-hidden="true">'+
      icons[key]+'</span><strong>'+title+'</strong><small>'+
      descriptions[key]+'</small><span class="home-card-arrow">Abrir →</span></a>').join('')+
    '</div></section>';
}
function serviceNav(){
  const choices=urls.filter(x=>['check','scan','prizes','budget','tax'].includes(x[2]));
  return '<div class="service-page-links" aria-label="Cambiar de servicio">'+
    choices.map(([url,title,key])=>'<a href="'+url+'">'+title+' →</a>').join('')+
    '</div>';
}
function showOnlyService(html,active){
  const valid=new Set(['check','scan','prizes','budget','tax']);
  if(!valid.has(active))throw Error('Servicio no válido');
  return html.replace(/<section id="servicePanel-([a-z]+)"[^>]*>/g,(tag,key)=>{
    const withoutHidden=tag.replace(/\s+hidden(?=[\s>])/g,'');
    return key===active?withoutHidden:withoutHidden.replace(/>$/,' hidden>');
  }).replace(/<button id="serviceTab-([a-z]+)"[^>]*>/g,(tag,key)=>{
    let updated=tag.replace(/aria-selected="(true|false)"/,'aria-selected="'+(key===active)+'"');
    updated=updated.replace(/\s+tabindex="-1"/g,'');
    return key===active?updated:updated.replace(/>$/,' tabindex="-1">');
  });
}
function makePage({key,body,modules=[],classic=false,extraSelector='',heading=true}){
  const head=baseHead.replace(/<title>[\s\S]*?<\/title>/,
    '<title>'+tags[key]+' · LOTTO LAB DEXTER</title>');
  let shell=baseShell.replace(/<nav class="navscroll"[\s\S]*?<\/nav>/,nav(key))
    .replace('href="#generador" aria-label="Lotto Lab Dexter"','href="index.html" aria-label="Lotto Lab Dexter"');
  const scripts=(classic?legacyScript:'')+modules.map(module=>
    '<script type="module" src="assets/'+module+'"></script>').join('\n')+
    '<script type="module" src="assets/multipage-nav.mjs"></script>';
  return head+'<body data-page="'+key+'"'+(
    ['check','scan','prizes','budget','tax'].includes(key)?' data-service="'+key+'"':'')+
    '>'+shell+'<main id="contenido">'+(heading?screenTitle(key):'')+body+
    '</main>'+footer+'\n'+scripts+'\n</body>\n</html>\n';
}
const pages={
  'index.html':makePage({key:'home',heading:false,
    body:generator+'</section>'+navCards(),
    modules:['generator-pro.js','lucky-ui.mjs']}),
  'revisar.html':null,'escanear.html':null,'premios.html':null,
  'presupuesto.html':null,'impuestos.html':null,
  'simulador.html':makePage({key:'simulator',
    body:selector()+simulator,modules:['page-context.mjs','draw-ui.mjs']}),
  'matematicas.html':makePage({key:'math',
    body:selector('<label for="proCoverage">Cantidad de combinaciones</label>'+
      '<select id="proCoverage"><option value="1">1</option><option value="5">5</option><option value="10">10</option><option value="20">20</option><option value="100">100</option></select>')+
      coverage+'\n'+science,modules:['page-context.mjs','coverage-ui.mjs','science-ui.mjs']}),
  'probabilidades.html':makePage({key:'odds',
    body:selector()+comparison,modules:['page-context.mjs','probabilities-page.mjs']}),
  'historial.html':makePage({key:'history',
    body:selector()+legacy,classic:true,modules:['page-context.mjs','us-catalog-ui.js']})
};
for(const [key,slug] of [['check','revisar'],['scan','escanear'],['prizes','premios'],
  ['budget','presupuesto'],['tax','impuestos']]){
  pages[slug+'.html']=makePage({key,
    body:selector()+showOnlyService(services,key)+serviceNav(),
    modules:['page-context.mjs','services-ui.mjs']});
}
mkdirSync(destination,{recursive:true});
for(const [file,html] of Object.entries(pages)){
  if(!html?.includes('</html>'))throw Error('HTML inválido: '+file);
  if(file==='index.html'&&!html.includes('id="generador"'))throw Error('El generador no quedó en la portada');
  if(file!=='index.html'&&html.includes('id="generador"'))throw Error('Generador duplicado en '+file);
  if(file==='index.html'&&(html.includes('id="servicesHub"')||html.includes('id="sorteoVirtual"')))
    throw Error('La portada aún contiene herramientas secundarias');
  writeFileSync(join(destination,file),html,'utf8');
  console.log('Página:',file,html.length,'caracteres');
}
console.log('Publicación separada en',Object.keys(pages).length,'páginas, generador primero.');
