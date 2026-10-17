// LOTTO LAB DEXTER v3: datos oficiales y archivos visuales con prioridad de red.
// No se crean resultados ficticios ni se comparten caches entre aplicaciones.
const CACHE='lotto-lab-dexter-v11';
const SHELL=['./','./index.html','./manifest.webmanifest','./icon.svg','./assets/generator-pro.js','./assets/lottery-pro.css','./assets/us-catalog.mjs','./assets/us-catalog-ui.js','./assets/scientific-math.mjs','./assets/science-ui.mjs','./assets/exact-engine.mjs','./assets/lucky-engine.mjs','./assets/lucky-ui.mjs','./assets/coverage-engine.mjs','./assets/coverage-ui.mjs','./assets/draw-simulator.mjs','./assets/draw-ui.mjs','./assets/payout-engine.mjs','./assets/services-ui.mjs','./assets/barcode-reader.mjs','./data/us-jurisdictions.json','./data/scientific-report.json'];
self.addEventListener('install',event=>{
  event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(SHELL)));
  self.skipWaiting();
});
self.addEventListener('activate',event=>{
  event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('lotto-lab-dexter-')&&k!==CACHE).map(k=>caches.delete(k)))));
  self.clients.claim();
});
self.addEventListener('fetch',event=>{
  const request=event.request;
  if(request.method!=='GET')return;
  const url=new URL(request.url);
  if(url.origin!==self.location.origin)return;
  const scope=new URL(self.registration.scope);
  if(!url.pathname.startsWith(scope.pathname))return;
  // Red primero: conservar la última copia válida para uso offline.
  event.respondWith(fetch(request).then(response=>{
    if(response.ok){
      const copy=response.clone();
      event.waitUntil(caches.open(CACHE).then(cache=>cache.put(request,copy)));
    }
    return response;
  }).catch(async()=>{
    const cached=await caches.match(request);
    if(cached)return cached;
    return Response.error();
  }));
});