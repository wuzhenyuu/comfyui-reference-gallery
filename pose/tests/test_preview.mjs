import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const code = readFileSync(new URL('../../web/pose_gallery.js', import.meta.url), 'utf8')
  .replace(/^import .*;\s*$/gm, '');

async function createPreview(language = 'zh') {
  let extension, changes = 0, remembered = language;
  const listeners = {}, body = [];
  class Element {
    constructor() { this.style = {}; this.children = []; this.attributes = {}; this.handlers = {}; this.contentWindow = {postMessage:(message,origin)=>{this.lastMessage={message,origin};}}; }
    addEventListener(name, callback) { this.handlers[name] = callback; }
    remove() {this.removed=true;}
    showModal() {}
    append(...children) { this.children.push(...children); }
    setAttribute(name, value) { this.attributes[name] = value; }
  }
  const widget = { name: 'pose_id', value: 'full_sexy_P031_front' };
  const languageWidget = {name:'language',value:'zh'};
  class Node {
    constructor() { this.widgets = [widget, languageWidget]; this.dom = {}; this.outputs = Array.from({length:6},()=>({})); }
    addWidget(type,name,value,callback,options) {const widget={type,name,value,callback,options};this.widgets.push(widget);return widget;}
    addOutput(name,type) {this.outputs.push({name,type});}
    addDOMWidget(name, type, element) { this.previewBox = element; this.dom[name] = element; }
    setSize() {}
    setDirtyCanvas() {}
  }
  const context = vm.createContext({
    URLSearchParams,
    app: { registerExtension(value) { extension = value; }, graph: { change() { changes++; } } },
    api: { apiURL(path) { return '/api' + path; } },
    document: { createElement() { return new Element(); }, body: {append:element=>body.push(element)} },
    location:{origin:'http://test'},
    window: { addEventListener(name,callback){listeners[name]=callback;}, removeEventListener(name){delete listeners[name];}, localStorage:{getItem:()=>remembered,setItem:(key,value)=>{remembered=value;}} },
  });
  vm.runInContext(readFileSync(new URL('../../web/i18n.mjs', import.meta.url), 'utf8'), context);
  vm.runInContext(code, context);
  await extension.beforeRegisterNodeDef(Node, { name: 'PoseGallery' });
  const node = new Node();
  node.onNodeCreated();
  const [image, status] = node.previewBox.children;
  return { widget, image, status, node, languageWidget, get changes(){return changes;},
    open(){node.widgets.find(widget=>widget.name==='pose_browser').callback();},
    get dialogs(){return body.filter(element=>!element.removed);},
    get frame(){return body.at(-1).children[1];},
    send(data,origin='http://test',source=body.at(-1).children[1].contentWindow){listeners.message?.({origin,source,data});},
    sendLanguage(value){const frame=body.at(-1).children[1];listeners.message({origin:'http://test',source:frame.contentWindow,data:{type:'pose-gallery-language',language:value}});}
  };
}

test('missing original shows the exact path and repair instructions instead of a blank node', async () => {
  const { image, status } = await createPreview();
  assert.equal(image.src, '/api/pose_gallery/assets/img/full_sexy_P031_front.png');
  image.onerror();
  assert.equal(image.style.display, 'none');
  assert.equal(status.style.display, 'grid');
  assert.match(status.textContent, /library\/img\/full_sexy_P031_front\.png/);
  assert.match(status.textContent, /git pull/);
  assert.equal(status.attributes.role, 'status');
});

test('a successful selection clears the previous error and displays the original', async () => {
  const { widget, image, status } = await createPreview();
  image.onerror();
  widget.value = 'full_sexy_P031_side';
  widget.callback();
  image.onload();
  assert.equal(image.style.display, 'block');
  assert.equal(status.style.display, 'none');
  assert.equal(image.src, '/api/pose_gallery/assets/img/full_sexy_P031_side.png');
});

test('an older request cannot blank a newly selected pose', async () => {
  const { widget, image, status } = await createPreview();
  const previousError = image.onerror;
  widget.value = 'full_sexy_P031_side';
  widget.callback();
  previousError();
  assert.equal(image.style.display, 'block');
  assert.equal(status.style.display, 'none');
});

 test('English selection preview errors use English repair instructions', async () => {
  const {image,status} = await createPreview('en');
  image.onerror();
  assert.equal(image.alt, 'Selected pose preview');
  assert.match(status.textContent, /Failed to load library\/img\/full_sexy_P031_front.png/);
  assert.doesNotMatch(status.textContent, /[\u3400-\u9fff]/);
});

test('fixed node saves its output language and restores it without changing the pose',async()=>{
  const s=await createPreview('zh');
  s.languageWidget.callback('en');assert.equal(s.languageWidget.value,'en');assert.equal(s.languageWidget.label,'UI / output language');assert.equal(s.node.outputs[5].label,'Action');
  assert.equal(s.changes,1);assert.equal(s.widget.value,'full_sexy_P031_front');
  s.node.onConfigure({widgets_values:['full_sexy_P031_front','zh']});
  assert.equal(s.languageWidget.value,'zh');assert.equal(s.changes,1);
});
test('gallery language selection updates the fixed node input sent to the backend',async()=>{
  const s=await createPreview('zh');s.open();s.sendLanguage('en');
  assert.equal(s.languageWidget.value,'en');assert.equal(s.changes,1);
  s.sendLanguage('zh');assert.equal(s.languageWidget.value,'zh');assert.equal(s.changes,2);
});

test('older fixed nodes gain the action port while retaining existing output connections',async()=>{
  const s=await createPreview('en');s.node.outputs.pop();s.node.outputs[0].links=[42];
  const original=s.node.outputs.slice();s.node.onConfigure({widgets_values:[s.widget.value,'en']});
  assert.equal(s.node.outputs.length,6);assert.equal(s.node.outputs[5].name,'action');assert.equal(s.node.outputs[5].label,'Action');
  original.forEach((output,index)=>assert.equal(s.node.outputs[index],output));assert.deepEqual(s.node.outputs[0].links,[42]);
});

test('native browser button opens one gallery and keeps its label out of serialized inputs',async()=>{
  const s=await createPreview();
  const browse=s.node.widgets.find(widget=>widget.name==='pose_browser');
  assert.equal(browse.type,'button');assert.equal(typeof browse.callback,'function');
  assert.equal(browse.label,'浏览姿势图库 · 搜索 / 分类 / 多视角');
  assert.equal(browse.options.serialize,false);assert.equal(s.node.dom.pose_browser,undefined);
  s.open();s.open();assert.equal(s.dialogs.length,1);
  assert.equal(s.frame.src,'/api/pose_gallery/gallery?lang=zh');
  s.send({type:'pose-gallery-ready'});
  assert.equal(s.frame.lastMessage.message.type,'pose-gallery-current');
  assert.equal(s.frame.lastMessage.message.id,s.widget.value);
  s.languageWidget.callback('en');assert.equal(browse.label,'Browse poses · Search / Categories / Views');
});

test('preview click, Enter and Space share the gallery opener with a bilingual accessible name',async()=>{
  const s=await createPreview();const box=s.node.previewBox;
  assert.equal(box.attributes.role,'button');assert.equal(box.tabIndex,0);assert.equal(box.attributes['aria-label'],'打开姿势图库');
  box.handlers.click();assert.equal(s.dialogs.length,1);
  let prevented=0;
  box.handlers.keydown({key:'Enter',preventDefault(){prevented++;}});
  box.handlers.keydown({key:' ',preventDefault(){prevented++;}});
  assert.equal(prevented,2);assert.equal(s.dialogs.length,1);
  s.dialogs[0].handlers.cancel({preventDefault(){}});assert.equal(s.dialogs.length,0);
  box.handlers.keydown({key:'Enter',preventDefault(){}});assert.equal(s.dialogs.length,1);
  s.dialogs[0].handlers.cancel({preventDefault(){}});
  box.handlers.keydown({key:' ',preventDefault(){}});assert.equal(s.dialogs.length,1);
  s.languageWidget.callback('en');assert.equal(box.attributes['aria-label'],'Open pose gallery');
});

test('only the current same-origin gallery can select a pose, then its ID and language survive restore',async()=>{
  const s=await createPreview();s.open();
  s.send({type:'pose-gallery-select',id:'full_sexy_P031_side'},'http://other');
  s.send({type:'pose-gallery-select',id:'full_sexy_P031_side'},'http://test',{});
  assert.equal(s.widget.value,'full_sexy_P031_front');assert.equal(s.changes,0);
  s.send({type:'pose-gallery-language',language:'en'});
  s.send({type:'pose-gallery-select',id:'full_sexy_P031_side'});
  assert.equal(s.widget.value,'full_sexy_P031_side');assert.equal(s.languageWidget.value,'en');
  assert.equal(s.image.src,'/api/pose_gallery/assets/img/full_sexy_P031_side.png');assert.equal(s.dialogs.length,0);
  s.node.onConfigure({widgets_values:[s.widget.value,'en']});
  assert.equal(s.widget.value,'full_sexy_P031_side');assert.equal(s.languageWidget.value,'en');
  assert.equal(s.node.previewBox.attributes['aria-label'],'Open pose gallery');
});
