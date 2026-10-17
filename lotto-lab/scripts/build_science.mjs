#!/usr/bin/env node
/**
 * Informe científico local construido EXCLUSIVAMENTE a partir de los históricos
 * oficiales descargados en la ejecución diaria. No necesita API ni claves.
 * Se evalúan únicamente los últimos sorteos de los regímenes compatibles.
 */
import {readFileSync,writeFileSync} from 'node:fs';
import {join,resolve} from 'node:path';
import {
  prizeSpectrum,outcomeCount,historicalAudit,simultaneousBand
} from '../assets/scientific-math.mjs';

const output=resolve(process.argv[2]||'lotto-lab/data');
const models={
  powerball:{game:{n:69,k:5,bonus:26},file:'powerball.json'},
  megamillions:{game:{n:70,k:5,bonus:24},file:'megamillions.json'},
  nytake5:{game:{n:39,k:5,bonus:0},file:'nytake5.json'}
};
const reports={};
for(const [key,{game,file}] of Object.entries(models)){
  const source=JSON.parse(readFileSync(join(output,file),'utf8'));
  if(source.game!==key||!Array.isArray(source.rows)||source.count!==source.rows.length)
    throw new Error('Historial no válido para '+key);
  let rows;
  if(key==='nytake5'){
    if(source.schema!==3)throw Error('Take 5 formato incorrecto');
    rows=source.rows.map(r=>({date:r.date,period:r.period,main:r.main}));
  }else{
    if(source.schema!==2||!source.current_rule_from)throw Error('Matriz histórica incompatible');
    rows=source.rows.filter(r=>r[0]>=source.current_rule_from)
      .map(r=>({date:r[0],main:r.slice(1,6),bonus:r[6]}));
  }
  if(rows.length<80)throw Error('Historial insuficiente para el auditor '+key);
  const audit=historicalAudit(rows,game,{holdout:180,minTrain:60,priorStrength:120,alpha:0.05});
  const payout=prizeSpectrum(game,key);
  reports[key]={
    provider:source.provider,source:source.source,
    source_last_draw:source.last_draw,history_entries:source.count,
    comparable_draws:rows.length,total_outcomes:outcomeCount(game).toString(),
    any_prize_probability:payout.anyPrize,
    evidence:{
      totalDraws:audit.totalDraws,trainDraws:audit.trainDraws,evaluationDraws:audit.evaluationDraws,
      brierFair:audit.brierFair,brierHistory:audit.brierHistory,
      skillPercent:audit.skillPercent,band:audit.band,
      anomalies:audit.anomalies,largestDeviations:audit.largestDeviations,
      interpretation:audit.interpretation
    }
  };
  console.log('audit',key,'compatible',rows.length,'holdout',audit.evaluationDraws,
    'brier delta',audit.skillPercent.toFixed(5)+'%',
    'out-of-band',audit.anomalies.length);
}
const record={
  schema:1,title:'LOTTO LAB · Auditor científico histórico',
  source_type:'Official draw results supplied by state lottery data',
  disclaimer:'Backtests históricos y probabilidades exactas. No indica ventaja predictiva para un sorteo justo.',
  methodology:{
    distribution:'hypergeométrica + bola especial independiente',
    posterior:'frecuencia marginal Beta suavizada con 120 seudo-observaciones con base justa',
    validation:'Brier Score walk-forward, últimos 180 sorteos, mínimo 60 previos',
    multiple_comparisons:'banda Hoeffding simultánea conservadora al 95 %',
    eligible_regimes:'Solo sorteos bajo la misma matriz; Powerball desde 2015-10-07; Mega Millions desde 2025-04-08; Take 5 5/39'
  },
  refreshed_at:new Date().toISOString(),games:reports
};
writeFileSync(join(output,'scientific-report.json'),JSON.stringify(record,null,2)+'\n','utf8');
console.log('science-report',Object.keys(reports).length,'juegos',record.refreshed_at);
