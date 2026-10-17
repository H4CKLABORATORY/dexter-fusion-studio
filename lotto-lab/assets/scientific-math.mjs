/**
 * LOTTO LAB — Auditor de probabilidad exacta y evidencia empírica.
 *
 * CAPA 1. Distribución exacta hipergeométrica, bola adicional independiente y dígitos en orden.
 * CAPA 2. Banda simultánea Hoeffding + Bonferroni, conservadora para verificar desviaciones.
 * CAPA 3. Walk-forward con Brier Score: compara un modelo histórico suavizado
 *         contra el modelo de sorteo justo, usando solo sorteos anteriores.
 *
 * Ningún resultado de esta biblioteca constituye una predicción verificada.
 */
export const GAME_TIERS=Object.freeze({
  powerball:Object.freeze({
    "5|1":{label:"5 + Powerball",prize:"Jackpot",base:null},
    "5|0":{label:"5 números",prize:"US$1.000.000",base:1000000},
    "4|1":{label:"4 + Powerball",prize:"US$50.000",base:50000},
    "4|0":{label:"4 números",prize:"US$100",base:100},
    "3|1":{label:"3 + Powerball",prize:"US$100",base:100},
    "3|0":{label:"3 números",prize:"US$7",base:7},
    "2|1":{label:"2 + Powerball",prize:"US$7",base:7},
    "1|1":{label:"1 + Powerball",prize:"US$4",base:4},
    "0|1":{label:"Solo Powerball",prize:"US$4",base:4}
  }),
  megamillions:Object.freeze({
    "5|1":{label:"5 + Mega Ball",prize:"Jackpot",base:null},
    "5|0":{label:"5 números",prize:"US$2M–10M",base:1000000},
    "4|1":{label:"4 + Mega Ball",prize:"US$20.000–100.000",base:10000},
    "4|0":{label:"4 números",prize:"US$1.000–5.000",base:500},
    "3|1":{label:"3 + Mega Ball",prize:"US$400–2.000",base:200},
    "3|0":{label:"3 números",prize:"US$20–100",base:10},
    "2|1":{label:"2 + Mega Ball",prize:"US$20–100",base:10},
    "1|1":{label:"1 + Mega Ball",prize:"US$14–70",base:7},
    "0|1":{label:"Solo Mega Ball",prize:"US$10–50",base:5}
  }),
  vacash5:Object.freeze({
    "5|0":{label:"5 números",prize:"Jackpot",base:null},
    "4|0":{label:"4 números",prize:"US$200",base:200},
    "3|0":{label:"3 números",prize:"US$5",base:5},
    "2|0":{label:"2 números",prize:"US$1",base:1}
  }),
  cafantasy5:Object.freeze({
    "5|0":{label:"5 números",prize:"Jackpot variable",base:null},
    "4|0":{label:"4 números",prize:"Variable",base:null},
    "3|0":{label:"3 números",prize:"Variable",base:null},
    "2|0":{label:"2 números",prize:"Boleto gratuito",base:null}
  })
});
export const SOURCE_ODDS=Object.freeze({
  powerball:"https://www.powerball.com/powerball-prize-chart",
  megamillions:"https://www.megamillions.com/Media-Center/MegaMillions_New_Prize_Matrix.aspx",
  vacash5:"https://www.valottery.com/data/draw-games/cash5",
  cafantasy5:"https://www.calottery.com/draw-games/fantasy-5"
});
function integer(name,value,min,max=Number.MAX_SAFE_INTEGER){
  if(!Number.isSafeInteger(value)||value<min||value>max)throw RangeError(name+' fuera de rango');
  return value;
}
export function comb(n,k){
  integer('n',n,0);integer('k',k,0);
  if(k>n)return 0n;
  k=Math.min(k,n-k);let product=1n;
  for(let i=1;i<=k;i++)product=product*BigInt(n-k+i)/BigInt(i);
  return product;
}
export function outcomeCount(game){
  if(!game||!Number.isInteger(game.n)||!Number.isInteger(game.k)||game.k>game.n||game.k<1)
    throw Error('Matriz inválida');
  if(game.kind==='digits'){
    const width=integer('dígitos',game.width,1,8);
    if(game.n!==10**width||game.k!==1||game.bonus)throw Error('Matriz ordenada incompatible');
    return BigInt(game.n);
  }
  const bonus=game.bonus||0;
  return comb(game.n,game.k)*BigInt(bonus||1);
}
export function exactMainWays(n,k,matches){
  integer('aciertos',matches,0,k);
  return comb(k,matches)*comb(n-k,k-matches);
}
/**
 * Pr(match exactly r | one play) = C(k,r)*C(n-k,k-r)/C(n,k)
 * En juegos con bola especial, multiplicar el conteo por 1 o (b-1).
 * Las cuentas son BigInt; solo se convierten a Number al mostrar la proporción.
 */
export function exactSpectrum(game){
  const total=outcomeCount(game),rows=[];
  if(game.kind==='digits'){
    for(let matches=0;matches<=game.width;matches++){
      const ways=comb(game.width,matches)*9n**BigInt(game.width-matches);
      rows.push({main:matches,bonus:null,ways,total,probability:Number(ways)/Number(total),
        label:matches+' posiciones exactas'});
    }
  }else if(game.k===1&&!game.bonus){
    // La Chica: un resultado de dos cifras, no una selección de cinco bolas.
    for(let hits=0;hits<=1;hits++){
      const ways=hits?1n:BigInt(game.n-1);
      rows.push({main:hits,bonus:null,ways,total,probability:Number(ways)/Number(total),
        label:hits?'Número exacto':'Número distinto'});
    }
  }else{
    for(let r=0;r<=game.k;r++){
      const ways=exactMainWays(game.n,game.k,r);
      for(const extra of (game.bonus?[false,true]:[null])){
        const adjusted=ways*BigInt(extra===false?game.bonus-1:1);
        rows.push({main:r,bonus:extra,ways:adjusted,total,probability:Number(adjusted)/Number(total),
          label:r+' principales'+(extra===true?' + especial':extra===false?' sin especial':'')});
      }
    }
  }
  const check=rows.reduce((acc,row)=>acc+row.ways,0n);
  if(check!==total)throw Error('Inconsistencia: probabilidades no suman 1');
  return rows;
}
export function prizeSpectrum(game,key){
  const tiers=GAME_TIERS[key];
  if(!tiers)return {rows:[],anyPrize:null,knownPayout:null,total:outcomeCount(game)};
  const all=exactSpectrum(game),rows=[],total=outcomeCount(game);
  let winningWays=0n,expectedFixed=0;
  for(const outcome of all){
    const row=tiers[outcome.main+'|'+Number(outcome.bonus===true)];
    if(!row)continue;
    const result={...outcome,...row};
    rows.push(result);
    winningWays+=outcome.ways;
    if(Number.isFinite(row.base)){
      const factor=key==='megamillions'?3:1; // multiplicador integrado promedio: 96/32 = 3.
      expectedFixed+=outcome.probability*row.base*factor;
    }
  }
  return {rows,anyPrize:Number(winningWays)/Number(total),
    winningWays,total,expectedFixed,
    knownPayout:key==='powerball'||key==='megamillions'||key==='vacash5',
    missingJackpot:true};
}
/** Probabilidad de por lo menos un acierto de jackpot en t sorteos independientes. */
export function multiDrawChance(game,distinctPlays,draws){
  const total=outcomeCount(game),m=BigInt(distinctPlays);
  integer('sorteos',draws,1,1_000_000);
  if(m<1n||m>total)throw RangeError('Boletos distintos fuera de rango');
  const p=Number(m)/Number(total);
  return -Math.expm1(draws*Math.log1p(-p));
}
export function simultaneousBand(n,k,drawCount,alpha=.05){
  integer('n',n,2);integer('k',k,1,n);integer('muestra',drawCount,1);
  if(!(alpha>0&&alpha<1))throw RangeError('Nivel alfa inválido');
  const p=k/n,margin=Math.sqrt(Math.log(2*n/alpha)/(2*drawCount));
  return {expected:p,margin,lower:Math.max(0,p-margin),upper:Math.min(1,p+margin),alpha};
}
export function historicalAudit(draws,game,{alpha=.05,priorStrength=120,holdout=180,minTrain=60}={}){
  if(!game||game.kind==='digits')throw Error('El auditor necesita sorteos de bolas sin reemplazo');
  integer('muestra mínima',minTrain,1);integer('holdout',holdout,1);integer('priorStrength',priorStrength,1);
  const n=game.n,k=game.k,p=k/n,seq=[...draws].sort((a,b)=>{
    const ad=a.date+'|'+(a.period||''),bd=b.date+'|'+(b.period||'');
    return ad.localeCompare(bd);
  }).filter(row=>Array.isArray(row.main)&&row.main.length===k&&new Set(row.main).size===k
    &&row.main.every(x=>Number.isInteger(x)&&x>=1&&x<=n));
  if(seq.length<minTrain+20)throw Error('Historial insuficiente para evaluación fuera de muestra');
  const start=Math.max(minTrain,seq.length-holdout);
  const counts=new Uint32Array(n+1);
  let seen=0,brierUniform=0,brierHistory=0,evaluated=0;
  // Entrenamiento exclusivo con las fechas ANTERIORES al período de evaluación.
  for(const row of seq.slice(0,start)){
    for(const x of row.main)counts[x]++;
    seen++;
  }
  for(let i=start;i<seq.length;i++){
    const actual=new Set(seq[i].main);
    let lossHistory=0,lossUniform=0;
    for(let x=1;x<=n;x++){
      const y=actual.has(x)?1:0;
      const q=(counts[x]+priorStrength*p)/(seen+priorStrength);
      lossHistory+=(q-y)**2;
      lossUniform+=(p-y)**2;
    }
    brierUniform+=lossUniform/n;
    brierHistory+=lossHistory/n;
    for(const x of seq[i].main)counts[x]++;
    seen++;evaluated++;
  }
  const band=simultaneousBand(n,k,seq.length,alpha);
  const rows=Array.from({length:n},(_,i)=>{
    const number=i+1,observed=counts[number]/seq.length;
    return {number,count:counts[number],observed,difference:observed-p,
      beyondBand:observed<band.lower||observed>band.upper};
  });
  rows.sort((a,b)=>Math.abs(b.difference)-Math.abs(a.difference)||a.number-b.number);
  const baseline=brierUniform/evaluated,history=brierHistory/evaluated;
  const delta=(baseline-history)/baseline;
  return {
    totalDraws:seq.length,trainDraws:start,evaluationDraws:evaluated,
    brierFair:baseline,brierHistory:history,
    skillPercent:100*delta,
    band,anomalies:rows.filter(x=>x.beyondBand),
    largestDeviations:rows.slice(0,5),
    method:'Brier walk-forward con prior fijo + banda simultánea de Hoeffding',
    interpretation:'Diferencias en muestras finitas NO demuestran ventaja predictiva para el próximo sorteo.'
  };
}
