import {test} from 'node:test';
import {strict as assert} from 'node:assert';
import {readTicketBarcodeImage,ticketCodeMetadata,maskedBarcode} from '../assets/barcode-reader.mjs';

const photo={type:'image/jpeg',size:56000};
test('los ID de boletos nunca se muestran íntegros ni se marcan válidos',()=>{
  assert.equal(maskedBarcode('1234567890123456'),'••••••3456');
  const meta=ticketCodeMetadata([{format:'pdf417',rawValue:'1234567890123456'}]);
  assert.equal(meta.length,1);
  assert.equal(meta[0].masked,'••••••3456');
  assert.equal(meta[0].length,16);
  assert.equal(meta[0].verified,false);
  assert.ok(!JSON.stringify(meta).includes('1234567890123456'));
});
test('lector BarcodeDetector nativo no envía imágenes ni usa ZXing si ya lee el código',async()=>{
  class Detector{
    static async getSupportedFormats(){return ['qr_code','code_128']}
    constructor({formats}){assert.ok(formats.includes('qr_code'))}
    async detect(blob){assert.equal(blob,photo);return [{rawValue:'ABCDEF123456',format:'qr_code'}]}
  }
  const result=await readTicketBarcodeImage(photo,{
    NativeDetector:Detector,
    loadOpenSource:()=>{throw Error('No debería cargar dependencia externa')}
  });
  assert.equal(result.codes[0].rawValue,'ABCDEF123456');
  assert.equal(result.decoder,'lector nativo');
  assert.equal(result.remoteDependency,false);
});
test('fallback ZXing funciona localmente en un navegador sin BarcodeDetector',async()=>{
  let revoked=false,passed=false;
  class ZXing{
    async decodeFromImageElement(image){
      assert.equal(image.src,'blob:boleto-local');
      passed=true;
      return {getText:()=> 'TICKET9999',getBarcodeFormat:()=> 'PDF_417'};
    }
    reset(){}
  }
  const result=await readTicketBarcodeImage(photo,{
    NativeDetector:undefined,
    loadOpenSource:async()=>({BrowserMultiFormatReader:ZXing}),
    createUrl:()=> 'blob:boleto-local',
    revokeUrl:()=>{revoked=true},
    createImage:()=>{
      const image={};
      Object.defineProperty(image,'src',{set(value){this.value=value;queueMicrotask(()=>this.onload())},
        get(){return this.value}});
      return image;
    }
  });
  assert.equal(result.codes[0].rawValue,'TICKET9999');
  assert.equal(result.decoder,'ZXing local (iPhone compatible)');
  assert.equal(result.remoteDependency,true);
  assert.equal(passed,true);
  assert.equal(revoked,true);
});
test('rechaza archivos no fotográficos, grandes o bibliotecas ausentes',async()=>{
  await assert.rejects(()=>readTicketBarcodeImage({type:'text/plain',size:5}),/fotografía/);
  await assert.rejects(()=>readTicketBarcodeImage({type:'image/png',size:15_000_000}),/12 MB/);
  await assert.rejects(()=>readTicketBarcodeImage(photo,{
    NativeDetector:undefined,
    loadOpenSource:async()=>{throw Error('Sin conexión')}
  }),/aplicación oficial/);
});
