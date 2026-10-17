import {test} from 'node:test';
import {strict as assert} from 'node:assert';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
const script=readFileSync(new URL('../assets/generator-pro.js',import.meta.url),'utf8');
const html=readFileSync(new URL('../index.html',import.meta.url),'utf8');
const dom={proFavorites:{value:''},proStyle:{value:'balanced',selectedOptions:[{textContent:'Equilibrados'}]}};
const ctx=vm.createContext({document:{getElementById:id=>dom[id]||{value:''}},console});
const logic=script.split("$p('proGame').addEventListener")[0];
assert.ok(logic.includes('function createTicket()'),'La lógica debe estar accesible');
vm.runInContext(logic+';globalThis.T={specs,totalOutcomes,theoretical,theoreticalCoverage,createTicket,parseFav,pickHash,histRows,wilson,renderTicketReveal};',ctx);
const {T}=ctx;
function select(game,style='balanced',favorites=''){
  dom.proStyle.value=style;dom.proFavorites.value=favorites;
  vm.runInContext('selected='+JSON.stringify(game)+';generation=0;verified=[];',ctx);
}
test('fórmulas combinatorias correctas para los tres juegos',()=>{
  assert.equal(T.totalOutcomes(T.specs.powerball),292201338n);
  assert.equal(T.totalOutcomes(T.specs.megamillions),290472336n);
  assert.equal(T.totalOutcomes(T.specs.chica),100n);
  assert.equal(T.theoretical(T.specs.powerball),5/69);
  assert.equal(T.theoretical(T.specs.megamillions),5/70);
  assert.equal(T.theoretical(T.specs.chica),1/100);
});
test('cobertura de boletos distintos crece linealmente sin superar el espacio de resultados',()=>{
  for(const game of ['powerball','megamillions','chica']){
    const g=T.specs[game];
    assert.equal(T.theoreticalCoverage(g,10),10/Number(T.totalOutcomes(g)));
    assert.equal(T.theoreticalCoverage(g,1),1/Number(T.totalOutcomes(g)));
    assert.throws(()=>T.theoreticalCoverage(g,0));
    assert.throws(()=>T.theoreticalCoverage(g,T.totalOutcomes(g)+1n));
  }
});
test('la semilla interna produce cálculos reproducibles sin Math.random',()=>{
  assert.ok(!logic.includes('Math.random('));
  select('powerball','balanced');
  const a=T.createTicket();vm.runInContext('generation=0',ctx);const b=T.createTicket();
  assert.deepEqual(Array.from(a.main),Array.from(b.main));
  assert.equal(a.bonus,b.bonus);
});
test('rangos, duplicados y especial: Powerball, Mega Millions y La Chica',()=>{
  for(const game of ['powerball','megamillions','chica']){
    select(game);
    const g=T.specs[game];
    for(let k=0;k<20;k++){
      const t=T.createTicket();
      assert.equal(t.main.length,g.k);
      assert.equal(new Set(t.main).size,g.k);
      assert.ok(t.main.every(v=>v>=(game==='chica'?0:1)&&v<=(game==='chica'?99:g.n)));
      if(g.bonus)assert.ok(t.bonus>=1&&t.bonus<=g.bonus);
      else assert.equal(t.bonus,null);
    }
  }
});
test('preferencias explícitas se respetan y números fuera de rango se rechazan',()=>{
  select('powerball','seed','7, 13');assert.ok(T.createTicket().main.includes(7));vm.runInContext('generation=0',ctx);
  assert.ok(T.createTicket().main.includes(13));
  select('chica','odd','00');assert.equal(T.createTicket().main[0],0);
  select('chica','seed','100');assert.throws(()=>T.createTicket(),/números diferentes/);
});
test('filtrado de frecuencias solo incluye el régimen vigente',()=>{
  select('powerball');
  const payload={game:'powerball',rows:[['2015-10-06',1,2,3,4,5,1],['2015-10-07',2,3,4,5,6,2],['2025-10-06',2,3,4,5,7,3],['2025-10-06',2,3,4,5,7,3]]};
  const rows=T.histRows(payload,T.specs.powerball);
  assert.equal(rows.length,2);
});
test('intervalo Wilson es descriptivo, no una predicción',()=>{
  const arr=T.wilson(10,100);
  assert.ok(arr[0]<0.1&&arr[1]>0.1);
});
test('revelación animada del boleto y reinicio seguro en clics repetidos',()=>{
  const oldCreate=ctx.document.createElement,oldMatch=ctx.matchMedia;
  function fakeElement(){
    const classes=new Set();
    return {
      children:[],className:'',attributes:{},events:{},textContent:'',
      style:{props:{},setProperty(key,value){this.props[key]=value;}},
      classList:{add(v){classes.add(v);},remove(v){classes.delete(v);},contains(v){return classes.has(v);}},
      append(node){this.children.push(node);},
      replaceChildren(...nodes){this.children=[...nodes];},
      addEventListener(name,callback){this.events[name]=callback;},
      setAttribute(name,value){this.attributes[name]=value;},
      remove(){this.removed=true;},
      get offsetWidth(){return 300;}
    };
  }
  try{
    ctx.document.createElement=fakeElement;
    ctx.matchMedia=()=>({matches:false});
    const container=fakeElement();
    const draw={main:[4,13,25,38,66],bonus:9};
    T.renderTicketReveal(container,draw,'powerball',1);
    assert.equal(container.children.filter(x=>x.className.includes('ticket-ball')).length,6);
    assert.equal(container.children.filter(x=>x.className==='lotto-spark').length,15);
    assert.ok(container.classList.contains('lotto-revealing'));
    const sparks=container.children.filter(x=>x.className==='lotto-spark');
    assert.ok(sparks.every(x=>x.attributes['aria-hidden']==='true'));
    const firstChildren=container.children;
    T.renderTicketReveal(container,draw,'powerball',2);
    assert.equal(container.children.length,21);
    assert.ok(firstChildren.every(x=>!container.children.includes(x)),'No deben quedar efectos de una animación anterior');
    assert.ok(container.children[5].className.includes('bonus'));
    ctx.matchMedia=()=>({matches:true});
    T.renderTicketReveal(container,draw,'powerball',3);
    assert.equal(container.children.length,6,'En movimiento reducido no debe haber confeti');
    assert.ok(container.children.every(x=>!x.className.includes('lotto-ball-reveal')));
    assert.ok(!container.classList.contains('lotto-revealing'));
    ctx.matchMedia=()=>({matches:false});
    T.renderTicketReveal(container,{main:[7],bonus:null},'chica',1);
    assert.equal(container.children.filter(x=>x.className.includes('ticket-ball')).length,1);
    assert.equal(container.children.filter(x=>x.className==='lotto-spark').length,8);
  }finally{
    ctx.document.createElement=oldCreate;ctx.matchMedia=oldMatch;
  }
});
test('diseño primero generador, archivo secundario, fuentes correctas',()=>{
  assert.ok(html.indexOf('id="generador"')<html.indexOf('id="resumen"'));
  assert.ok(html.indexOf('id="historial"')>html.indexOf('id="premios"'));
  assert.ok(html.includes('id="archivoDetalle"')&&html.includes('assets/generator-pro.js'));
  assert.ok(html.includes('assets/lottery-pro.css'));
  assert.ok(script.includes('renderTicketReveal('),'La revelación debe estar integrada con el generador');
  assert.ok(!html.includes('id="proSeed"'),'La semilla no debe ser campo editable');
  assert.ok(!script.includes("$p('proSeed')"),'El motor no debe leer una semilla editable');
  assert.ok(script.includes('const INTERNAL_SEED='),'El motor debe conservar semilla interna');
  assert.ok(html.includes('id="proCoverage"')&&html.includes('id="proCoverageChance"'),'Debe existir la simulación de cobertura');
});
