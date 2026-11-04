const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const root=path.join(__dirname,'..');
async function setup(){
 let extension,changes=0;
 class Element{
  constructor(tag){this.tag=tag;this.style={};this.children=[];this.attributes={};this.listeners={};this.contentWindow={postMessage:(...args)=>this.messages.push(args)};this.messages=[];}
  append(...children){this.children.push(...children);}
  setAttribute(key,value){this.attributes[key]=value;}
  addEventListener(type,callback){this.listeners[type]=callback;}
  fire(type,event={}){return this.listeners[type]?.(event);}
  showModal(){this.open=true;}
  remove(){this.removed=true;this.open=false;}
 }
 const selection={name:'hairstyle_id',value:'h001'},language={name:'language',value:'zh'};
 class Node{
  constructor(){this.widgets=[selection,language];this.dom={};this.outputs=Array.from({length:8},()=>({}));this.title='HairstyleGallery';}
  addWidget(type,name,value,callback,options){const widget={type,name,value,callback,options};this.widgets.push(widget);return widget;}
  addDOMWidget(name,type,el){assert.notEqual(type,'button','Vue button widgets require a native callback');this.dom[name]=el;}
  setSize(){}setDirtyCanvas(){}
 }
 const listeners={},body=new Element('body');
 const context=vm.createContext({URLSearchParams,window:{addEventListener:(name,callback)=>{listeners[name]=callback;},removeEventListener:(name,callback)=>{if(listeners[name]===callback)delete listeners[name];}},localStorage:{getItem:()=>null,setItem(){}},document:{createElement:tag=>new Element(tag),body},location:{origin:'http://localhost:8191'},api:{apiURL:p=>'/api'+p},app:{registerExtension:e=>{extension=e;},graph:{change(){changes++;}}}});
 vm.runInContext(fs.readFileSync(path.join(root,'../web/hairstyle/i18n.mjs'),'utf8'),context);
 vm.runInContext(fs.readFileSync(path.join(root,'../web/hairstyle/hairstyle_gallery.js'),'utf8').replace(/^import .*;\s*$/gm,''),context);
 await extension.beforeRegisterNodeDef(Node,{name:'HairstyleGallery'});const node=new Node();node.onNodeCreated();
 return{node,selection,language,body,listeners,browse:node.widgets.find(w=>w.name==='hairstyle_browser'),toggle:node.widgets.find(w=>w.name==='hairstyle_language'),preview:node.dom.hairstyle_preview,image:node.dom.hairstyle_preview.children[0],get changes(){return changes;}};
}

test('native browse and language callbacks preserve saved inputs and open one gallery',async()=>{
 const s=await setup();assert.deepEqual(s.node.widgets.slice(0,2).map(w=>w.name),['hairstyle_id','language']);
 for(const widget of [s.browse,s.toggle]){assert.equal(widget.type,'button');assert.equal(widget.options.serialize,false);assert.equal(typeof widget.callback,'function');}
 s.toggle.callback();assert.equal(s.language.value,'en');assert.equal(s.toggle.label,'中文');assert.equal(s.changes,1);assert.doesNotMatch(s.browse.label,/[\u3400-\u9fff]/);
 s.browse.callback();s.browse.callback();assert.equal(s.body.children.length,1);const dialog=s.body.children[0],frame=dialog.children[1];
 assert.equal(dialog.open,true);assert.equal(frame.src,'/api/hairstyle_gallery/gallery?lang=en');
 s.listeners.message({origin:'http://localhost:8191',source:frame.contentWindow,data:{type:'hairstyle-gallery-ready'}});
 assert.equal(frame.messages[0][0].id,'h001');assert.equal(frame.messages[1][0].language,'en');
 s.node.onRemoved();assert.equal(dialog.removed,true);assert.equal(s.listeners.message,undefined);
});

test('preview opens by click, Enter or Space and ignores unrelated keys',async()=>{
 const s=await setup();assert.equal(s.preview.attributes.role,'button');assert.equal(s.preview.tabIndex,0);assert.ok(s.preview.attributes['aria-label']);
 s.preview.fire('keydown',{key:'Escape'});assert.equal(s.body.children.length,0);
 let prevented=0;
 for(const event of ['click','Enter',' ']){
  if(event==='click')s.preview.fire('click');else s.preview.fire('keydown',{key:event,preventDefault(){prevented++;}});
  const dialog=s.body.children.at(-1);assert.equal(dialog.open,true);dialog.fire('cancel',{preventDefault(){}});assert.equal(dialog.removed,true);
 }
 assert.equal(prevented,2);assert.equal(s.body.children.length,3);
});

test('trusted gallery selection updates preview and invalid or foreign messages do not',async()=>{
 const s=await setup();s.browse.callback();const dialog=s.body.children[0],frame=dialog.children[1];
 const send=(data,origin='http://localhost:8191',source=frame.contentWindow)=>s.listeners.message({origin,source,data});
 send({type:'hairstyle-gallery-select',id:'wrong-origin'},'http://other');send({type:'hairstyle-gallery-select',id:'wrong-source'},undefined,{});send({type:'hairstyle-gallery-select',id:'../bad'});
 assert.equal(s.selection.value,'h001');assert.equal(s.changes,0);
 send({type:'hairstyle-gallery-select',id:'h-next'});assert.equal(s.selection.value,'h-next');assert.equal(s.image.src,'/api/hairstyle_gallery/assets/full/h-next.png');assert.equal(dialog.removed,true);assert.equal(s.changes,1);
});

test('saved language and preview restore while stale image errors cannot replace a newer preview',async()=>{
 const s=await setup();const stale=s.image.onerror;s.selection.value='saved-hair';s.node.onConfigure({widgets_values:['saved-hair','en']});s.image.onload();stale();
 assert.equal(s.language.value,'en');assert.equal(s.toggle.label,'中文');assert.equal(s.image.src,'/api/hairstyle_gallery/assets/full/saved-hair.png');assert.equal(s.image.style.display,'block');assert.equal(s.preview.children[1].style.display,'none');assert.equal(s.changes,0);
});
