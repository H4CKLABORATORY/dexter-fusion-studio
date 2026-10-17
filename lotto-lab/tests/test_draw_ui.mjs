import {test} from 'node:test';
import {strict as assert} from 'node:assert';

test('el estudio interactivo inicia, anima y analiza sin servidor ni apuestas',async()=>{
  const registry=new Map();
  function node(){
    const listeners={};
    const classes=new Set();
    return {
      listeners,children:[],textContent:'',className:'',title:'',hidden:false,open:false,value:'',
      classList:{add(...names){for(const n of names)classes.add(n)},remove(...names){for(const n of names)classes.delete(n)},contains(n){return classes.has(n)}},
      addEventListener(event,listener){listeners[event]=listener},
      append(...children){this.children.push(...children)},
      replaceChildren(...children){this.children=[...children]},
      get offsetWidth(){return 300}
    };
  }
  function get(id){
    if(!registry.has(id))registry.set(id,node());
    return registry.get(id);
  }
  const state={
    key:'powerball',
    game:{name:'Powerball',n:69,k:5,bonus:26},
    rows:[{date:'2026-10-12',main:[1,4,22,37,69],bonus:11}]
  };
  const lucky={key:'powerball',main:[1,4,22,37,69],bonus:11};
  const oldWindow=globalThis.window,oldDocument=globalThis.document,oldMatch=globalThis.matchMedia;
  const oldCrypto=globalThis.crypto;
  try{
    globalThis.window={
      LottoLabScientificState:()=>state,
      LottoLabLuckyState:()=>lucky,
      LottoLabTicketState:()=>({key:'powerball',ticket:{main:[2,3,5,6,17],bonus:8}}),
      addEventListener(){}
    };
    globalThis.document={
      hidden:false,
      createElement:()=>node(),
      getElementById:get,
      addEventListener(){}
    };
    globalThis.matchMedia=()=>({matches:true});
    get('drawSource').value='lucky';
    get('drawMode').value='virtual';
    get('drawSpeed').value='fast';
    const crypto=await import('node:crypto');
    globalThis.crypto=crypto.webcrypto;
    await import('../assets/draw-ui.mjs?integration-smoke');
    assert.match(get('drawYourNumbers').textContent,/69/);
    assert.ok(get('drawStart').listeners.click);
    await get('drawStart').listeners.click();
    assert.equal(get('drawRevealedBalls').children.length,6);
    assert.match(get('drawOutcome').textContent,/Sorteo generado virtualmente/);
    assert.match(get('drawOutcome').textContent,/NO significa que hayas ganado/);
    get('drawBatch').listeners.click();
    assert.equal(get('drawStatResults').children.length,4);
    assert.match(get('drawOutcome').textContent,/1.000 sorteos nuevos/);
    get('drawHistoryCheck').listeners.click();
    assert.equal(get('drawStatResults').children.length,4);
    assert.match(get('drawOutcome').textContent,/Comparación retrospectiva/);
    get('drawMode').value='historical';
    get('drawMode').listeners.change();
    await get('drawStart').listeners.click();
    assert.match(get('drawOutcome').textContent,/Reproducción de un resultado oficial pasado/);
    get('drawSource').value='custom';
    get('drawSource').listeners.change();
    get('drawCustomNumbers').value='1,4,22,37,69 | 11';
    get('drawCustomNumbers').listeners.input();
    assert.match(get('drawYourNumbers').textContent,/37/);
    assert.equal(get('drawCustomWrapper').hidden,false);
    get('drawWindowsPanel').open=true;
    get('drawWindowsPanel').listeners.toggle();
    assert.equal(get('drawWindowCards').children.length,3);
  }finally{
    globalThis.window=oldWindow;
    globalThis.document=oldDocument;
    globalThis.matchMedia=oldMatch;
    globalThis.crypto=oldCrypto;
  }
});
