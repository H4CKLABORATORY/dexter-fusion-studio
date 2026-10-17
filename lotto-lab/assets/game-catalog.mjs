/* LOTTO LAB · reglas compartidas para páginas secundarias. Sin predicciones. */
export const specs = Object.freeze({
  // Nacionales: matriz y precios vigentes documentados en sitios de las loterías.
  powerball:{name:'Powerball',n:69,k:5,bonus:26,start:'2015-10-07',source:'data/powerball.json',web:'https://www.powerball.com/',price:'$2'},
  megamillions:{name:'Mega Millions',n:70,k:5,bonus:24,start:'2025-04-08',source:'data/megamillions.json',web:'https://www.megamillions.com/',price:'$5'},
  // Estatales: solo reglas específicas contrastadas. Sin historial integrado salvo NY Take 5.
  mdpick3:{name:'Maryland Pick 3 · exacto',n:1000,k:1,bonus:0,kind:'digits',width:3,start:null,source:null,web:'https://www.mdlottery.com/games/pick-3-pick-4-pick-5/',price:'Consultar MD'},
  mdpick4:{name:'Maryland Pick 4 · exacto',n:10000,k:1,bonus:0,kind:'digits',width:4,start:null,source:null,web:'https://www.mdlottery.com/games/pick-3-pick-4-pick-5/',price:'Consultar MD'},
  mdpick5:{name:'Maryland Pick 5 · exacto',n:100000,k:1,bonus:0,kind:'digits',width:5,start:null,source:null,web:'https://www.mdlottery.com/games/pick-3-pick-4-pick-5/',price:'Consultar MD'},
  vapick3:{name:'Virginia Pick 3 · exacto',n:1000,k:1,bonus:0,kind:'digits',width:3,start:null,source:null,web:'https://www.valottery.com/data/draw-games/pick3',price:'Consultar VA'},
  vacash5:{name:'Virginia Cash 5',n:45,k:5,bonus:0,start:null,source:null,web:'https://www.valottery.com/data/draw-games/cash5',price:'$1'},
  cafantasy5:{name:'California Fantasy 5',n:39,k:5,bonus:0,start:null,source:null,web:'https://www.calottery.com/es-us/draw-games/fantasy-5',price:'$1'},
  nytake5:{name:'Nueva York Take 5',n:39,k:5,bonus:0,start:'1992-01-17',source:'data/nytake5.json',historyFormat:'nytake5',web:'https://nylottery.ny.gov/draw-game?game=take5',price:'Consultar NY'},
  chica:{name:'La Chica · Honduras',n:100,k:1,bonus:0,start:null,source:null,web:'https://www.pani.gob.hn/',price:'Consultar PANI'}
});
export const DEFAULT_GAME='powerball';
