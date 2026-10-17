/* Catálogo de jurisdicciones públicas, separado de bibliotecas históricas. */
export const OFFICIAL_DIRECTORY = 'https://www.naspl.org/naspl-lottery-members';
export const STATES_WITHOUT_LOTTERY = Object.freeze([
  'Alabama','Alaska','Hawái','Nevada','Utah'
]);
export function validateJurisdictions(payload) {
  if (!payload || payload.schema!==1 || !Array.isArray(payload.jurisdictions)) throw new Error('Catálogo inválido');
  const codes=new Set();
  for(const j of payload.jurisdictions){
    if(!j || typeof j.code!=='string' || !/^[A-Z]{2}$/.test(j.code)||codes.has(j.code)) throw new Error('Código de jurisdicción duplicado o inválido');
    if(typeof j.name!=='string'||j.name.length<3)throw new Error('Nombre inválido');
    if(j.source!==null&&(!/^https:\/\//.test(j.source)||!j.source_label)) throw new Error('Referencia oficial inválida');
    if(!Array.isArray(j.verified_game_keys)||j.verified_game_keys.some(g=>typeof g!=='string'))throw new Error('Juegos sin respaldo verificable');
    codes.add(j.code);
  }
  if(codes.size!==48||payload.jurisdiction_count!==48)throw new Error('Se esperan 48 jurisdicciones de lotería');
  return payload.jurisdictions;
}
export function searchJurisdictions(jurisdictions,query='',scope='all'){
  const q=String(query||'').trim().normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
  return jurisdictions.filter(j=>{
    if(scope==='states'&&j.region!=='estado')return false;
    if(scope==='territories'&&j.region==='estado')return false;
    const searchable=(j.name+' '+j.code).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
    return searchable.includes(q);
  }).sort((a,b)=>a.name.localeCompare(b.name,'es'));
}
