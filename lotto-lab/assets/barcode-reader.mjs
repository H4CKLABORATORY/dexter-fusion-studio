/**
 * Lectura local del contenido de códigos de barras.
 * Intento 1: BarcodeDetector nativo.
 * Intento 2: biblioteca open-source ZXing MIT (descargada bajo demanda).
 *
 * Solo se descarga código JS de jsDelivr. No se sube el archivo/foto del boleto.
 * El código leído no es un ticket oficialmente validado.
 */
const ZXING_CDN='https://cdn.jsdelivr.net/npm/@zxing/browser@0.1.5/+esm';

export function maskedBarcode(raw){
  const value=String(raw||'');
  return '••••••'+value.slice(-4);
}
export function ticketCodeMetadata(codes){
  return codes.slice(0,3).map(item=>({
    format:String(item.format||'sin identificar'),
    masked:maskedBarcode(item.rawValue),
    length:String(item.rawValue||'').length,
    verified:false
  }));
}
export async function readTicketBarcodeImage(file,{
  NativeDetector=globalThis.BarcodeDetector,
  loadOpenSource=()=>import(ZXING_CDN),
  createUrl=object=>URL.createObjectURL(object),
  revokeUrl=url=>URL.revokeObjectURL(url),
  createImage=()=>new Image()
}={}){
  if(!file?.type?.startsWith('image/'))throw Error('Adjunta una fotografía');
  if(file.size>12_000_000)throw Error('El archivo supera los 12 MB');
  let nativeError=null;
  if(typeof NativeDetector==='function'){
    try{
      const supported=await NativeDetector.getSupportedFormats();
      const formats=['code_128','pdf417','qr_code','data_matrix','ean_13','itf','aztec']
        .filter(f=>supported.includes(f));
      if(formats.length){
        const detector=new NativeDetector({formats});
        const results=await detector.detect(file);
        if(results?.length)return {codes:results.map(r=>({
          format:r.format,rawValue:r.rawValue})),decoder:'lector nativo',remoteDependency:false};
      }
    }catch(error){nativeError=error}
  }
  // Safari/iOS no garantiza BarcodeDetector. ZXing se descarga solo cuando
  // el usuario aporta explícitamente una foto y necesita la alternativa.
  let codeReader;
  try{
    const library=await loadOpenSource();
    if(typeof library.BrowserMultiFormatReader!=='function')throw Error('Módulo ZXing incompatible');
    codeReader=new library.BrowserMultiFormatReader();
  }catch(error){
    throw Error('La lectura automática no está disponible en este navegador o sin conexión. Usa la aplicación oficial de la lotería.');
  }
  let url=null;
  try{
    url=createUrl(file);
    const img=createImage();
    await new Promise((resolve,reject)=>{
      img.onload=resolve;img.onerror=()=>reject(Error('No se pudo abrir la fotografía'));
      img.src=url;
    });
    const result=await codeReader.decodeFromImageElement(img);
    const rawValue=typeof result.getText==='function'?result.getText():String(result.text||'');
    const code=result.getBarcodeFormat?.();
    if(!rawValue)throw Error('No se encontró código');
    return {codes:[{format:code!=null?String(code):'ZXing',rawValue}],
      decoder:'ZXing local (iPhone compatible)',remoteDependency:true};
  }catch{
    throw Error('No se pudo descifrar el código. Mejora la iluminación o usa el escáner oficial de tu estado.');
  }finally{
    try{if(url)revokeUrl(url)}catch{}
    try{codeReader?.reset?.()}catch{}
  }
}
