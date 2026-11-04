import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";
import "./i18n.mjs";
import "./random_i18n.mjs?v=dice-labels-20261104-2";

// Preview-name restoration must not depend on the version of the shared UI module.
// Start inside a promise so failures cannot escape onConfigure and abort graph loading.
let previewCatalogPromise;
function loadPreviewCatalog() {
  if (!previewCatalogPromise) {
    previewCatalogPromise = Promise.resolve()
      .then(() => fetch(api.apiURL('/hairstyle_gallery/catalog')))
      .then(response => {
        if (!response.ok) throw new Error('Cannot load preview names');
        return response.json();
      })
      .then(rows => {
        if (!Array.isArray(rows)) throw new Error('Invalid preview catalog');
        return rows;
      })
      .catch(error => { previewCatalogPromise = null; throw error; });
  }
  return previewCatalogPromise;
}

app.registerExtension({
  name:'comfyui-hairstyle-gallery.random-preview',
  async beforeRegisterNodeDef(nodeType,nodeData){
    if(nodeData.name!=='RandomHairstyleGallery')return;
    const created=nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated=function(){
      created?.apply(this,arguments);
      const node=this,I=window.RandomHairstyleI18n;
      const langWidget=node.widgets.find(w=>w.name==='language');
      const originWidget=node.widgets.find(w=>w.name==='origin');
      const hairstyleWidget=node.widgets.find(w=>w.name==='hairstyle_id');
      const lockWidget=node.widgets.find(w=>w.name==='locked');
      let language=I.preferred(),lastId='',lastName='',lastNames={},imageFailed=false,removed=false,imageVersion=0;
      let drawing=false,drawVersion=0,drawError='';
      node.properties??={};
      if(langWidget)langWidget.value=language;
      const t=source=>I.translate(source,language);
      const selectors = ["origin"].map(name => {
        const widget=node.widgets.find(w=>w.name===name);
        return widget ? {widget} : null;
      }).filter(Boolean);
      const box=document.createElement('div');box.style.cssText='display:flex;flex-direction:column;gap:8px;width:100%;height:100%;background:#f7f5f0;color:#343c2d;border-radius:8px;padding:10px;box-sizing:border-box;';
      const image=document.createElement('img');image.alt=t('本次随机发型预览');image.style.cssText='display:none;width:100%;flex:1;min-height:0;object-fit:contain;';
      const status=document.createElement('p');status.setAttribute('role','status');status.setAttribute('aria-live','polite');status.style.cssText='font:12px/1.6 sans-serif;overflow-wrap:anywhere;margin:0;';
      const id=document.createElement('code');id.style.cssText='font:11px/1.5 monospace;overflow-wrap:anywhere;';
      box.append(image,status,id);
      // Native buttons keep their callbacks in both Vue and canvas node renderers.
      const toggle=node.addWidget('button','random_language',null,()=>{setLanguage(language==='en'?'zh':'en');app.graph.change();},{serialize:false});
      const dice=node.addWidget('button','random_dice',null,draw,{serialize:false});
      const isLocked=()=>lockWidget?.value===true;
      function render(){
        status.textContent=drawError|| (drawing?t('正在抽取发型…'):imageFailed?t('随机发型预览加载失败，请检查素材原图。'):lastId?(lastNames[language]||t(lastName)):t('点击骰子预览，或运行工作流自动抽取发型'));
        status.style.display=status.textContent?'block':'none';
        id.textContent=lastId;
        dice.label=t(isLocked()?'🔒 已锁定':'🎲 随机');
        dice.disabled=isLocked()||drawing;
        dice.tooltip=t('仅更新此节点预览，不运行工作流');
        image.alt=t('本次随机发型预览');
        toggle.label=language==='en'?'中文':'English';
        toggle.tooltip=language==='en'?'切换到中文':'Switch to English';
        if(langWidget)langWidget.label=t('界面与输出语言');
        if(originWidget)originWidget.label=t('随机来源');
        if(hairstyleWidget)hairstyleWidget.label=t('当前发型编号');
        if(lockWidget)lockWidget.label=t('🔒 锁定随机');
        const tooltips={
          origin:'all：全部；builtin：内置；user：自定义。',
          language:'控制界面与文本输出语言，随工作流保存。',
          hairstyle_id:'当前选择的发型，锁定后运行工作流使用此图。',
          locked:'保持当前发型并禁用骰子。',
        };
        node.widgets.forEach(widget=>{if(tooltips[widget.name])widget.tooltip=t(tooltips[widget.name]);});
        const labels=["图像", "宽度", "高度", "发型编号", "名称", "描述", "发型长度", "来源编号"];
        node.outputs?.forEach((output,i)=>{output.label=t(labels[i]||output.name);});
        if(['RandomHairstyleGallery','Random Hairstyle Gallery','Random Hairstyle Gallery 随机发型图库'].includes(node.title))node.title=language==='en'?'Random Hairstyle Gallery':'Random Hairstyle Gallery 随机发型图库';
        node.setDirtyCanvas(true,true);
      }
      function setLanguage(value){language=I.normalize(value);I.persist(language);if(langWidget)langWidget.value=language;render();}
      function showResult(value,name='',names={}){
        if(typeof value!=='string'||!/^[a-z0-9_-]{1,80}$/.test(value))return false;
        lastId=value;lastName=typeof name==='string'?name:'';lastNames=names;imageFailed=false;
        if(hairstyleWidget)hairstyleWidget.value=lastId;
        node.properties.last_hairstyle_id=lastId;node.properties.last_hairstyle_name=lastName;node.properties.last_hairstyle_names=lastNames;
        const token=++imageVersion;
        image.onload=()=>{if(!removed&&token===imageVersion){image.style.display='block';imageFailed=false;render();}};
        image.onerror=()=>{if(!removed&&token===imageVersion){image.style.display='none';imageFailed=true;render();}};
        image.src=api.apiURL(`/hairstyle_gallery/assets/full/${encodeURIComponent(lastId)}.png`);image.title=lastId;render();
        // Older saved workflows contain only the Chinese preview name.
        if(!lastNames.en && typeof fetch === 'function') {
          const requestedId = lastId;
          loadPreviewCatalog().then(rows => {
            if(removed || requestedId !== lastId) return;
            const row = rows.find(item => item.id === requestedId);
            if(row) {
              lastNames = {zh:row.name_zh || row.title, en:row.name_en};
              node.properties.last_hairstyle_names = lastNames;
              render();
            }
          }).catch(() => {});
        }
        return true;
      }
      function cancelDraw(){drawVersion++;drawing=false;drawError='';}
      async function draw(){
        if(removed||isLocked()||drawing)return;
        const version=++drawVersion;
        drawing=true;drawError='';render();
        const params=new URLSearchParams({language,exclude_id:lastId});
        for(const name of ["origin"]){
          const widget=node.widgets.find(w=>w.name===name);
          params.set(name,widget?.serializeValue?widget.serializeValue():widget?.value??'all');
        }
        try{
          const response=await fetch(api.apiURL(`/hairstyle_gallery/random?${params}`));
          const result=await response.json();
          if(removed||version!==drawVersion||isLocked())return;
          if(!response.ok)throw new Error(result.error||t('随机失败，请重试'));
          if(!showResult(result.hairstyle_id,result.name,{zh:result.name_zh,en:result.name_en}))throw new Error(t('随机失败，请重试'));
          app.graph.change();
        }catch(error){
          if(!removed&&version===drawVersion&&!isLocked())drawError=t('随机失败，请重试')+' · '+error.message;
        }finally{
          if(!removed&&version===drawVersion){drawing=false;render();}
        }
      }
      if(lockWidget){const previous=lockWidget.callback;lockWidget.callback=function(value){
        previous?.apply(this,arguments);cancelDraw();
        lockWidget.value=value===true;
        if(isLocked()&&!lastId){lockWidget.value=false;drawError=t('请先点击骰子选择发型，再锁定');}
        render();app.graph.change();
      };}
      if(hairstyleWidget){const previous=hairstyleWidget.callback;hairstyleWidget.callback=function(value){
        previous?.apply(this,arguments);cancelDraw();
        if(!showResult(value)){hairstyleWidget.value=lastId;drawError=t('无效的发型编号');}
        render();app.graph.change();
      };}
      selectors.forEach(({widget})=>{const previous=widget.callback;widget.callback=function(){
        previous?.apply(this,arguments);cancelDraw();render();
      };});
      if(langWidget){const previous=langWidget.callback;langWidget.callback=function(value){previous?.apply(this,arguments);setLanguage(value);app.graph.change();};}
      node.addDOMWidget('random_hairstyle_preview','image',box,{serialize:false,hideOnZoom:false,getMinHeight:()=>310,getMaxHeight:()=>500});
      const executed=node.onExecuted;node.onExecuted=function(message){
        executed?.apply(this,arguments);if(removed)return;
        // A result queued before the user locked a newer choice must not replace it.
        if(isLocked()&&message?.hairstyle_id?.[0]!==hairstyleWidget?.value)return;
        cancelDraw();
        if(showResult(message?.hairstyle_id?.[0],message?.name?.[0],{zh:message?.name_zh?.[0],en:message?.name_en?.[0]}))app.graph.change();
      };
      const configured=node.onConfigure;node.onConfigure=function(config){
        configured?.apply(this,arguments);
        cancelDraw();
        // Older workflows saved empty placeholders for DOM-only widgets.
        if(lockWidget)lockWidget.value=isLocked();

        setLanguage(config?.widgets_values?.[1]);
        const savedId=hairstyleWidget?.value||node.properties.last_hairstyle_id;
        if(savedId)showResult(savedId,node.properties.last_hairstyle_name,node.properties.last_hairstyle_names);
        render();
      };
      const originalRemoved=node.onRemoved;node.onRemoved=function(){removed=true;imageVersion++;cancelDraw();originalRemoved?.apply(this,arguments);};
      node.setSize([420,665]);render();
    };
  },
});
