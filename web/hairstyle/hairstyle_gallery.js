import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";
import "./i18n.mjs";

app.registerExtension({
  name: "comfyui-hairstyle-gallery.browser",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== "HairstyleGallery") return;
    const originalCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      originalCreated?.apply(this, arguments);
      const node=this, I=window.HairstyleI18n;
      const widget=node.widgets.find(value=>value.name==='hairstyle_id');
      const langWidget=node.widgets.find(value=>value.name==='language');
      let language=I.preferred(),dialog=null,frame=null,requestId=0,headerTitle=null,done=null;
      if(langWidget)langWidget.value=language;
      const t=(source,values)=>I.translate(source,language,values);
      const box=document.createElement('div');
      box.style.cssText='position:relative;width:100%;height:100%;background:#f7f5f0;border-radius:8px;overflow:hidden;cursor:pointer;';
      box.setAttribute('role','button');box.tabIndex=0;
      box.addEventListener('click',openGallery);
      box.addEventListener('keydown',event=>{
        if(event.key!=='Enter'&&event.key!==' ')return;
        event.preventDefault();openGallery();
      });
      const image=document.createElement('img');image.style.cssText='display:block;width:100%;height:100%;object-fit:contain;';
      const error=document.createElement('div');error.setAttribute('role','status');
      error.style.cssText='display:none;position:absolute;inset:15px;place-items:center;color:#9a493c;font:13px/1.7 sans-serif;overflow-wrap:anywhere;';
      box.append(image,error);
      const errorText=()=>t('发型原图加载失败：{path}。请检查完整素材库，重启 ComfyUI 并刷新页面。',{path:`library/img/full/${widget.value}.png`});
      const update=(version='')=>{
        const current=++requestId;image.style.display='block';error.style.display='none';
        image.onload=()=>{if(current===requestId){image.style.display='block';error.style.display='none';}};
        image.onerror=()=>{if(current===requestId){image.style.display='none';error.textContent=errorText();error.style.display='grid';}};
        image.src=api.apiURL(`/hairstyle_gallery/assets/full/${encodeURIComponent(String(widget.value))}.png${version?'?v='+encodeURIComponent(version):''}`);image.title=widget.value;
      };
      const close=()=>{window.removeEventListener('message',receive);dialog?.remove();dialog=null;frame=null;headerTitle=null;done=null;};
      const setLanguage=(value,notify=true)=>{
        language=I.normalize(value);I.persist(language);if(langWidget)langWidget.value=language;
        image.alt=t('所选发型原图预览');browse.label=t('浏览发型图库 · 长度 / 风格 / 名称 / 搜索');
        box.setAttribute('aria-label',browse.label);
        toggle.label=language==='en'?'中文':'English';toggle.tooltip=language==='en'?'切换到中文':'Switch to English';
        widget.label=t('发型编号');if(langWidget)langWidget.label=t('界面与文本语言');
        const outputLabels=['图像','宽度','高度','发型编号','名称','描述','发型长度','来源编号'];
        node.outputs?.forEach((output,i)=>{output.label=t(outputLabels[i]||output.name);});
        if(['Hairstyle Gallery 发型图库','Hairstyle Gallery','HairstyleGallery'].includes(node.title))node.title=language==='en'?'Hairstyle Gallery':'Hairstyle Gallery 发型图库';
        if(headerTitle)headerTitle.textContent=t('Hairstyle Gallery · 选择发型后点击「使用此发型 → ComfyUI」');
        if(done)done.textContent=t('关闭');if(frame)frame.title=t('中文发型参考图库');
        if(error.style.display==='grid')error.textContent=errorText();
        if(notify&&frame)frame.contentWindow.postMessage({type:'hairstyle-gallery-language',language},location.origin);
        node.setDirtyCanvas(true,true);
      };
      const receive=event=>{
        if(event.origin!==location.origin||event.source!==frame?.contentWindow)return;
        if(event.data?.type==='hairstyle-gallery-library-changed'){update(Date.now().toString());return;}
        if(event.data?.type==='hairstyle-gallery-ready'){
          frame.contentWindow.postMessage({type:'hairstyle-gallery-current',id:widget.value},location.origin);
          frame.contentWindow.postMessage({type:'hairstyle-gallery-language',language},location.origin);
        }
        if(event.data?.type==='hairstyle-gallery-language'&&['zh','en'].includes(event.data.language)){
          setLanguage(event.data.language,false);app.graph.change();return;
        }
        if(event.data?.type!=='hairstyle-gallery-select'||typeof event.data.id!=='string'||!/^[a-z0-9_-]{1,80}$/.test(event.data.id))return;
        widget.value=event.data.id;widget.callback?.(widget.value);node.setDirtyCanvas(true,true);app.graph.change();close();
      };
      const callback=widget.callback;widget.callback=function(){callback?.apply(this,arguments);update();};
      if(langWidget){const original=langWidget.callback;langWidget.callback=function(value){original?.apply(this,arguments);setLanguage(value);app.graph.change();};}
      // Native buttons keep their callbacks in both Vue and canvas node renderers.
      const browse=node.addWidget('button','hairstyle_browser',null,openGallery,{serialize:false});
      const toggle=node.addWidget('button','hairstyle_language',null,()=>{setLanguage(language==='en'?'zh':'en');app.graph.change();},{serialize:false});
      function openGallery(){
        if(dialog)return;dialog=document.createElement('dialog');
        dialog.style.cssText='width:96vw;height:94vh;max-width:1800px;max-height:96vh;padding:0;border:1px solid #c6c9bb;border-radius:12px;background:#f7f5f0;';
        const header=document.createElement('div');header.style.cssText='height:46px;display:flex;align-items:center;justify-content:space-between;gap:12px;padding:0 18px;color:#343c2d;background:#e9ecdf;font:13px sans-serif;';
        headerTitle=document.createElement('strong');done=document.createElement('button');done.onclick=close;
        done.style.cssText='padding:5px 13px;border:1px solid #bdc5ae;background:#fff;color:#343c2d;border-radius:5px;cursor:pointer;';header.append(headerTitle,done);
        frame=document.createElement('iframe');frame.src=api.apiURL('/hairstyle_gallery/gallery')+'?lang='+language;
        frame.style.cssText='width:100%;height:calc(100% - 46px);border:0;';dialog.append(header,frame);window.addEventListener('message',receive);
        dialog.addEventListener('cancel',event=>{event.preventDefault();close();});
        dialog.addEventListener('click',event=>{if(event.target===dialog){const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)close();}});
        document.body.append(dialog);setLanguage(language,false);dialog.showModal();
      }
      node.addDOMWidget('hairstyle_preview','image',box,{serialize:false,hideOnZoom:false,getMinHeight:()=>300,getMaxHeight:()=>500});
      const configured=node.onConfigure;node.onConfigure=function(config){configured?.apply(this,arguments);if(langWidget){const saved=config?.widgets_values?.[1];setLanguage(['zh','en'].includes(saved)?saved:'zh');}update();};
      const removed=node.onRemoved;node.onRemoved=function(){close();removed?.apply(this,arguments);};
      node.setSize([420,565]);setLanguage(language,false);update();
    };
  },
});
