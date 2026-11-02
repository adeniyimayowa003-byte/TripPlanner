// Minimal observable native-page DOM. Production code owns appearance decisions.
const fs=require('node:fs'), vm=require('node:vm');
const input=JSON.parse(fs.readFileSync(0,'utf8'));
const attrs={'data-native-appearance':input.native};
const listeners={}, network=[], storage=[], errors=[];
const select={value:'system',disabled:true,addEventListener(event,handler){listeners[event]=handler;}};
const status={textContent:''};
const elements={appearance:select,'appearance-control':{hidden:true},'appearance-fallback':{hidden:false},'appearance-status':status,
  'desktop-csrf':{content:'csrf-sentinel',getAttribute(){return 'csrf-sentinel';}}};
const context={document:{readyState:'complete',documentElement:{getAttribute(name){return attrs[name]??null;},setAttribute(name,value){attrs[name]=value;}},getElementById(id){return elements[id]??null;}},
  window:{localStorage:{getItem(key){storage.push(['read',key]);return 'light';},setItem(key,value){storage.push(['write',key,value]);}}},
  fetch(url,options){network.push({url,...options});return input.reject?Promise.reject(new Error('QA unavailable')):Promise.resolve({ok:input.ok!==false});}};
context.window.fetch=context.fetch;
(async()=>{
  try{
    vm.runInNewContext(fs.readFileSync(process.argv[2],'utf8'),context);
    if(input.change){select.value=input.change;listeners.change();}
    await new Promise(resolve=>setImmediate(resolve));
  }catch(error){errors.push(error.message);}
  process.stdout.write(JSON.stringify({mode:attrs['data-appearance'],selected:select.value,network,storage,status:status.textContent,errors}));
})();
