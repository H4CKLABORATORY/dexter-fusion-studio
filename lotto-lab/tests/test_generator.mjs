import {test} from 'node:test';
import {strict as assert} from 'node:assert';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {validateJurisdictions,searchJurisdictions,STATES_WITHOUT_LOTTERY} from '../assets/us-catalog.mjs';
const script=readFileSync(new URL('../assets/generator-pro.js',import.meta.url),'utf8');
const html=readFileSync(new URL('../index.html',import.meta.url),'utf8');
const dom={proFavorites:{value:''},proStyle:{value:'balanced',selectedOptions:[{textContent:'Equilibrados'}]}};
const ctx=vm.createContext({document:{getElementById:id=>dom[id]||{value:''}},console});
const logic=script.split("$p('proGame').addEventListener")[0];
assert.ok(logic.includes('function createTicket()'),'La lógica debe estar accesible');
vm.runInContext(logic+';globalThis.T={specs,totalOutcomes,theoretical,theoreticalCoverage,createTicket,parseFav,pickHash,histRows,wilson,renderTicketReveal,rankedUSGames,pctHighPrecision};',ctx);
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
test('probabilidades verificadas de juegos estatales y nacionales',()=>{
  const cases={
    powerball:292201338n,megamillions:290472336n,
    mdpick3:1000n,mdpick4:10000n,mdpick5:100000n,
    vapick3:1000n,vacash5:1221759n,cafantasy5:575757n,nytake5:575757n,chica:100n
  };
  assert.equal(Object.keys(T.specs).length,Object.keys(cases).length);
  for(const [game,total] of Object.entries(cases)){
    assert.equal(T.totalOutcomes(T.specs[game]),total,'Probabilidad incorrecta: '+game);
    assert.equal(T.theoreticalCoverage(T.specs[game],1),1/Number(total));
  }
});
test('juegos de dígitos en orden exacto sin generar listas gigantes',()=>{
  for(const [game,width] of [['mdpick3',3],['mdpick4',4],['mdpick5',5],['vapick3',3]]){
    const g=T.specs[game];select(game,'seed');
    assert.equal(g.width,width);
    for(let i=0;i<8;i++){
      const t=T.createTicket();assert.equal(t.main.length,1);
      assert.ok(t.main[0]>=0&&t.main[0]<g.n);
      assert.equal(String(t.main[0]).padStart(width,'0').length,width);
      assert.equal(t.bonus,null);
    }
    for(const [style,valid] of [
      ['even',v=>v%2===0],['odd',v=>v%2===1],
      ['low',v=>v<g.n/2],['high',v=>v>=g.n/2]
    ]){
      select(game,style);assert.ok(valid(T.createTicket().main[0]),game+' '+style);
    }
  }
  select('mdpick5','seed','00000');
  assert.equal(T.createTicket().main[0],0);
  select('mdpick5','seed','99999');
  assert.equal(T.createTicket().main[0],99999);
  select('mdpick5','seed','100000');
  assert.throws(()=>T.createTicket(),/números diferentes/);
});
test('Take 5 de Nueva York conserva dos sesiones por fecha y valida 5/39',()=>{
  select('nytake5');
  const payload={schema:3,game:'nytake5',rows:[
    {date:'2026-10-16',period:'midday',main:[1,5,10,20,39]},
    {date:'2026-10-16',period:'evening',main:[2,6,11,21,33]},
    {date:'2026-10-16',period:'evening',main:[2,6,11,21,33]},
    {date:'1991-10-16',period:'evening',main:[1,2,3,4,5]},
    {date:'2026-10-15',period:'evening',main:[1,2,3,4,41]},
  ]};
  const rows=T.histRows(payload,T.specs.nytake5);
  assert.equal(rows.length,2);
  assert.equal(new Set(rows.map(x=>x.period)).size,2);
  assert.ok(rows.every(x=>x.bonus===null));
});
test('comparador ordena por probabilidades exactas con porcentajes precisos',()=>{
 const ranked=T.rankedUSGames();
 assert.equal(ranked.length,9);
 assert.equal(ranked[0].key,'mdpick3');
 assert.equal(ranked[ranked.length-1].key,'powerball');
 assert.ok(ranked.every((g,i)=>i===0||ranked[i-1].total<=g.total));
 assert.ok(ranked.every(g=>g.key!=='chica'));
 assert.match(T.pctHighPrecision(1/292201338),/e-/);
});
test('catálogo oficial mantiene 48 jurisdicciones y filtros por estado',()=>{
  const catalog=JSON.parse(readFileSync(new URL('../data/us-jurisdictions.json',import.meta.url),'utf8'));
  const jurisdictions=validateJurisdictions(catalog);
  assert.equal(jurisdictions.length,48);
  assert.equal(searchJurisdictions(jurisdictions,'', 'states').length,45);
  assert.equal(searchJurisdictions(jurisdictions,'', 'territories').length,3);
  assert.equal(searchJurisdictions(jurisdictions,'Maryland').length,1);
  assert.equal(searchJurisdictions(jurisdictions,'nueva york').length,1);
  assert.equal(new Set(STATES_WITHOUT_LOTTERY).size,5);
  assert.ok(jurisdictions.every(j=>j.source===null||j.source.startsWith('https://')));
  for(const j of jurisdictions)for(const game of j.verified_game_keys)
    assert.ok(T.specs[game],'El catálogo menciona un juego inexistente: '+game);
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
  assert.ok(html.includes('id="usDirectory"')&&html.includes('assets/us-catalog-ui.js'));
  assert.ok(html.includes('id="comparador"')&&html.includes('id="usComparisonRows"'));
  for(const game of ['mdpick3','mdpick4','mdpick5','vapick3','vacash5','cafantasy5','nytake5'])
    assert.ok(html.includes('value="'+game+'"'),'Opción no visible: '+game);
});
