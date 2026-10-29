// This build never sends game data or logs to a server. Only static assets load.
(()=>{
 const dbReady=new Promise((resolve,reject)=>{const req=indexedDB.open('holdem-private-v1',1);req.onupgradeneeded=()=>req.result.createObjectStore('state');req.onsuccess=()=>resolve(req.result);req.onerror=()=>reject(req.error)});
 async function read(){const db=await dbReady;return new Promise((resolve,reject)=>{const r=db.transaction('state').objectStore('state').get('snapshot');r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error)})}
 async function write(snapshot){const db=await dbReady;return new Promise((resolve,reject)=>{const tx=db.transaction('state','readwrite');tx.objectStore('state').put(snapshot,'snapshot');tx.oncomplete=resolve;tx.onerror=()=>reject(tx.error)})}
 const worker=new Worker('./python-worker.js',{type:'module'});let serial=0;const waiting=new Map();
 worker.onmessage=async({data})=>{const waiter=waiting.get(data.id);if(!waiter)return;waiting.delete(data.id);try{if(data.snapshot)await write(data.snapshot);waiter.resolve(data)}catch(e){waiter.reject(e)}};
 worker.onerror=e=>{for(const w of waiting.values())w.reject(Error(e.message||'Python could not load'));waiting.clear()};
 function call(data){return new Promise((resolve,reject)=>{const id=++serial;waiting.set(id,{resolve,reject});worker.postMessage({id,...data})})}
 const status=document.querySelector('#runtime-status');status.textContent='LOADING PYTHON…';document.querySelector('#start').disabled=true;
 const ready=(async()=>{const data=await call({init:true,snapshot:await read()});if(!data.ready)throw Error(data.result?.detail||'Python could not start');status.textContent='';document.querySelector('#start').disabled=false})();
 ready.catch(e=>{status.textContent='LOAD FAILED / '+e.message});
 const nativeFetch=window.fetch.bind(window);
 window.fetch=async(input,options={})=>{
  if(typeof input!=='string'||!input.startsWith('/api/games'))return nativeFetch(input,options);
  await ready;
  const execute=async()=>{
   const snapshot=await read();if(snapshot)await call({init:true,snapshot});
   return call({request:{path:input,method:options.method||'GET',body:options.body?JSON.parse(options.body):null}});
  };
  const data=navigator.locks?await navigator.locks.request('holdem-private-state',execute):await execute();
  return new Response(JSON.stringify(data.result),{status:data.status,headers:{'Content-Type':'application/json'}});
 };
})();
