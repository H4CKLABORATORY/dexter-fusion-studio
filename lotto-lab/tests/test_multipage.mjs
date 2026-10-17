import {test} from 'node:test';
import {strict as assert} from 'node:assert';
import {execFileSync} from 'node:child_process';
import {mkdtempSync,readFileSync,rmSync,statSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join,resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const filenames=['index.html','revisar.html','escanear.html','premios.html',
  'presupuesto.html','impuestos.html','simulador.html','matematicas.html',
  'probabilidades.html','historial.html'];
function buildAndVerify(check){
  const output=mkdtempSync(join(tmpdir(),'lotto-pages-'));
  try{
    const result=execFileSync('node',[join(root,'scripts/build_pages.mjs'),root,output],
      {encoding:'utf8',timeout:15000});
    assert.match(result,/10 páginas/);
    const pages=Object.fromEntries(filenames.map(file=>[file,
      readFileSync(join(output,file),'utf8')]));
    check(pages,output);
  }finally{rmSync(output,{recursive:true,force:true})}
}
test('Inicio es una página real dedicada primero al generador',()=>{
  buildAndVerify(p=>{
    const home=p['index.html'];
    assert.ok(home.includes('id="generador"'));
    assert.ok(home.includes('id="luckyDaily"'));
    assert.ok(home.includes('id="proGenerate"'));
    assert.ok(home.includes('assets/generator-pro.js'));
    assert.ok(home.indexOf('id="generador"')<home.indexOf('home-service-cards'));
    assert.ok(!home.includes('id="servicesHub"'));
    assert.ok(!home.includes('id="sorteoVirtual"'));
    assert.ok(!home.includes('id="scientificLab"'));
    assert.ok(!home.includes('id="archivoDetalle"'));
    assert.ok(!home.includes('id="proSeed"'));
    assert.ok(home.includes('href="revisar.html"'));
    assert.ok(home.includes('href="escanear.html"'));
    assert.ok(home.includes('href="impuestos.html"'));
    assert.ok(home.includes('href="simulador.html"'));
    assert.ok(home.includes('aria-current="page"'));
  });
});
test('cada pestaña secundaria navega a un archivo HTML diferente y usable',()=>{
  buildAndVerify(p=>{
    const services={
      'revisar.html':'check','escanear.html':'scan','premios.html':'prizes',
      'presupuesto.html':'budget','impuestos.html':'tax'
    };
    for(const [file,key] of Object.entries(services)){
      const html=p[file];
      assert.ok(html.includes('<body data-page="'+key+'" data-service="'+key+'"'));
      assert.ok(html.includes('id="servicePanel-'+key+'"'));
      assert.ok(html.includes('assets/services-ui.mjs'));
      assert.ok(html.includes('assets/page-context.mjs'));
      assert.ok(html.includes('href="index.html"'));
      assert.ok(!html.includes('id="generador"'));
      assert.ok(html.includes('id="proGame"'));
      assert.ok(html.includes('aria-current="page"'));
      assert.ok(html.length>15000);
    }
    assert.ok(p['escanear.html'].includes('id="scanFile"'));
    assert.ok(p['presupuesto.html'].includes('id="budgetMoney"'));
    assert.ok(p['impuestos.html'].includes('id="taxMDResidency"'));
  });
});
test('simulador, matemáticas, probabilidades e historial tienen URLs independientes',()=>{
  buildAndVerify(p=>{
    assert.ok(p['simulador.html'].includes('id="drawStage"'));
    assert.ok(p['simulador.html'].includes('assets/draw-ui.mjs'));
    assert.ok(p['matematicas.html'].includes('id="coverageMandel"'));
    assert.ok(p['matematicas.html'].includes('id="scientificLab"'));
    assert.ok(p['matematicas.html'].includes('id="proCoverage"'));
    assert.ok(p['probabilidades.html'].includes('id="usComparisonRows"'));
    assert.ok(p['probabilidades.html'].includes('assets/probabilities-page.mjs'));
    assert.ok(p['historial.html'].includes('id="archivoDetalle"'));
    assert.ok(p['historial.html'].includes('id="usDirectory"'));
    assert.ok(p['historial.html'].includes("fetchRows()"));
    for(const html of Object.values(p))assert.equal((html.match(/<main id="contenido">/g)||[]).length,1);
  });
});
test('navegación accesible y responsive presente en las 10 páginas',()=>{
  buildAndVerify(p=>{
    for(const file of filenames){
      const html=p[file];
      assert.ok(html.includes('class="navscroll multi-page-nav"'),file);
      assert.ok(html.includes('assets/multipage-nav.mjs'),file);
      assert.ok(html.includes('assets/lottery-pro.css'),file);
      assert.ok(html.includes('href="index.html"'),file);
      assert.ok(html.includes('<title>'),file);
      assert.ok(html.includes('</body>'),file);
    }
    const original=readFileSync(join(root,'index.html'),'utf8');
    assert.ok(p['index.html'].length<original.length*.45,'Inicio debe ser mucho más corto que la página antigua');
  });
});
