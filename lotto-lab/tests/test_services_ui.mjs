import {test} from 'node:test';
import {strict as assert} from 'node:assert';

test('pestañas, comprobación de premio, impuestos y vínculos se ejecutan en el navegador',async()=>{
  const memory=new Map();
  function element(id=''){
    const listeners={};
    const attributes={};
    return {
      id,children:[],listeners,attributes,hidden:false,disabled:false,value:'',textContent:'',
      className:'',tabIndex:0,files:[],colSpan:1,href:'',
      addEventListener(event,callback){listeners[event]=callback;},
      setAttribute(name,value){attributes[name]=value;},
      replaceChildren(...nodes){this.children=[...nodes];},
      append(...nodes){this.children.push(...nodes);},
      focus(){this.focused=true;},
      scrollIntoView(){this.scrolled=true;},
      querySelectorAll(selector){return selector==='option'?[
        {value:'powerball',textContent:'Powerball'},
        {value:'megamillions',textContent:'Mega Millions'},
        {value:'mdpick3',textContent:'MD Pick 3'}
      ]:[]},
      dispatchEvent(event){for(const k of [event.type])this.listeners[k]?.(event);return true;}
    };
  }
  function byId(id){if(!memory.has(id))memory.set(id,element(id));return memory.get(id)}
  const defaults={
    proGame:'powerball',checkTicketMode:'manual',checkResultSource:'official',
    checkClaimState:'VA',checkStake:'2',checkMultiplier:'unknown',checkPowerPlay:'no',
    checkPeriod:'evening',taxRegion:'VA',taxGross:'10000',taxStake:'2',
    taxFederalRate:'32',taxStateFinalRate:'5.75',taxOtherWithhold:'0',
    budgetMoney:'20',budgetPowerPlay:'base'
  };
  for(const [id,value] of Object.entries(defaults))byId(id).value=value;
  const game={name:'Powerball',n:69,k:5,bonus:26,price:'$2',web:'https://www.powerball.com/'};
  const rows=[{date:'2026-10-14',main:[1,12,20,45,69],bonus:26}];
  const old={window:globalThis.window,document:globalThis.document,
    BarcodeDetector:globalThis.BarcodeDetector};
  try{
    globalThis.window={
      LottoLabScientificState:()=>({key:'powerball',game,rows}),
      LottoLabTicketState:()=>({key:'powerball',ticket:{main:[1,12,20,45,69],bonus:25}}),
      LottoLabLuckyState:()=>({key:'powerball',main:[1,12,20,45,69],bonus:25}),
      listeners:{},
      addEventListener(event,fn){this.listeners[event]=fn;}
    };
    globalThis.document={getElementById:byId,createElement:tag=>element(tag)};
    await import('../assets/services-ui.mjs?test-once');
    assert.equal(byId('serviceTab-check').attributes['aria-selected'],'true');
    assert.equal(byId('servicePanel-tax').hidden,true);
    assert.equal(byId('checkDate').value,'2026-10-14');
    byId('checkNumbers').value='1 12 20 45 69 | 25';
    byId('checkRun').listeners.click();
    assert.ok(byId('checkResult').children.some(c=>c.textContent.includes('US$1,000,000.00')));
    assert.equal(byId('checkSendTax').disabled,false);
    byId('checkSendTax').listeners.click();
    assert.equal(byId('taxGross').value,'1000000');
    assert.equal(byId('servicePanel-tax').hidden,false);
    assert.equal(byId('serviceTab-tax').attributes['aria-selected'],'true');
    assert.match(byId('taxNetWithholding').textContent,/\$/);
    byId('serviceTab-prizes').listeners.click();
    assert.equal(byId('servicePanel-prizes').hidden,false);
    assert.equal(byId('prizeTableRows').children.length,9);
    byId('serviceTab-budget').listeners.click();
    assert.equal(byId('budgetPlays').textContent,'10');
    byId('serviceTab-scan').listeners.click();
    assert.equal(byId('servicePanel-scan').hidden,false);
    byId('scanGoManual').listeners.click();
    assert.equal(byId('servicePanel-check').hidden,false);
  }finally{
    globalThis.window=old.window;
    globalThis.document=old.document;
    if(old.BarcodeDetector===undefined)delete globalThis.BarcodeDetector;
    else globalThis.BarcodeDetector=old.BarcodeDetector;
  }
});
