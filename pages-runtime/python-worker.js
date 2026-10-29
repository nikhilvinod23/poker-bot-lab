import {loadPyodide} from './runtime/pyodide.mjs';
let py;
const ready=(async()=>{
 py=await loadPyodide({indexURL:new URL('./runtime/',self.location.href).href});
 py.FS.mkdirTree('/home/pyodide/pokerbot');
 for(const name of ['__init__.py','engine.py','table.py','bot_baseline.py','browser_api.py']){
  const response=await fetch('./python/pokerbot/'+name);if(!response.ok)throw Error('Could not load Python game');
  py.FS.writeFile('/home/pyodide/pokerbot/'+name,await response.text());
 }
 py.runPython('import sys; sys.path.insert(0,"/home/pyodide"); from pokerbot import browser_api');
})();
let queue=Promise.resolve();
onmessage=({data})=>{queue=queue.then(async()=>{
 try{
  await ready;
  if(data.init){if(data.snapshot){py.globals.set('_snapshot',data.snapshot);py.runPython('browser_api.restore(_snapshot)')}postMessage({id:data.id,ready:true});return}
  py.globals.set('_request',JSON.stringify(data.request));
  postMessage({id:data.id,...JSON.parse(py.runPython('browser_api.request(_request)'))});
 }catch(error){postMessage({id:data.id,status:500,result:{detail:String(error)}})}
})};
