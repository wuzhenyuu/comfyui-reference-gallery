import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const languageKey = 'costume-gallery-language';
const validID = id => typeof id === 'string' && /^(real|anime):[a-z\d_-]+$/i.test(id);
const getLanguage = () => { try { return localStorage.getItem(languageKey) === 'en' ? 'en' : 'zh'; } catch { return 'zh'; } };

app.registerExtension({
  name:'comfyui-costume-gallery.browser',
  async beforeRegisterNodeDef(nodeType,nodeData) {
    if (!['CostumeGallery','RandomCostumeGallery'].includes(nodeData.name)) return;
    const random = nodeData.name === 'RandomCostumeGallery';
    const created = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function() {
      created?.apply(this,arguments);
      const node = this, value = node.widgets?.find(w => w.name === 'costume_id'), languageWidget = node.widgets?.find(w => w.name === 'language');
      let language = ['zh','en'].includes(languageWidget?.value) ? languageWidget.value : getLanguage();
      let dialog,frame,heading,closeButton,returnFocus,request = 0,currentID = random ? String(node.properties?.costume_gallery_last_id || '') : String(value?.value || ''),imageFailed = false;
      const tr = (zh,en) => language === 'en' ? en : zh;
      const previewBox = document.createElement('div'); previewBox.style.cssText = 'position:relative;width:100%;height:100%;background:#eef1f5;border:1px solid #cbd5df;border-radius:6px;overflow:hidden;';
      const preview = document.createElement('img'); preview.style.cssText = 'display:block;width:100%;height:100%;object-fit:contain;';
      const note = document.createElement('div'); note.setAttribute('role','status'); note.style.cssText = 'position:absolute;inset:15px;display:none;align-items:center;justify-content:center;text-align:center;color:#5b6c7f;font:13px/1.8 sans-serif;overflow-wrap:anywhere;';
      const caption = document.createElement('span'); caption.style.cssText = 'position:absolute;bottom:5px;left:5px;max-width:calc(100% - 10px);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;background:#ffffffeb;border-radius:3px;padding:2px 6px;color:#264353;font:11px sans-serif;';
      previewBox.append(preview,note,caption);
      const browse = node.addWidget('button','costume_browser',null,openGallery,{serialize:false});
      function renderLanguage() {
        preview.alt = tr('所选服装预览','Selected costume preview');
        browse.label = random ? tr('浏览服装图库（仅浏览 / 复制编号）','Browse costumes (view / copy ID)') : tr('浏览服装图库 · 写实 / 动漫 / 搜索','Browse costumes · Realistic / Anime / Search');
        if (languageWidget) languageWidget.label = tr('界面与输出语言','Interface and output language');
        if (value) value.label = tr('服装编号','Costume ID');
        if (random) {
          for (const [name,zh,en] of [['library','图库','Library'],['category','分类','Category'],['query','关键词','Keywords'],['seed','随机种子','Seed']]) {
            const widget = node.widgets?.find(item => item.name === name);
            if (widget) widget.label = tr(zh,en);
          }
        }
        const zh = ['图像','宽度','高度','服装编号','描述','关键词']; const en = ['Image','Width','Height','Costume ID','Description','Keywords'];
        node.outputs?.forEach((output,index) => { output.label = (language === 'en' ? en : zh)[index] || output.name; });
        if (heading) heading.textContent = tr('服装参考图库 · 查看大图后选择服装','Costume reference gallery · Preview and select');
        if (closeButton) closeButton.textContent = tr('关闭','Close');
        if (frame) frame.title = tr('本地服装参考图库','Local costume reference gallery');
        note.textContent = !validID(currentID) && !random ? tr('请选择服装，或输入有效编号，例如 real:SPR-0001。','Choose a costume or enter a valid ID, such as real:SPR-0001.') : currentID ? tr(`原图加载失败：${currentID}。请确认本地图库素材完整。`,`Cannot load ${currentID}. Check the local library assets.`) : tr('运行节点后显示随机服装预览','Run this node to preview the random costume');
        if (imageFailed || !validID(currentID)) { note.style.display = 'flex'; preview.style.display = 'none'; }
        if (['CostumeGallery','Costume Gallery','服装图库','Costume Gallery 服装图库'].includes(node.title)) node.title = tr('Costume Gallery 服装图库','Costume Gallery');
        if (['RandomCostumeGallery','Random Costume Gallery','随机服装图库','Random Costume Gallery 随机服装图库'].includes(node.title)) node.title = tr('Random Costume Gallery 随机服装图库','Random Costume Gallery');
        node.setDirtyCanvas(true,true);
      }
      function update() {
        const ticket = ++request;
        if (!random) currentID = String(value?.value || '');
        caption.textContent = currentID; caption.hidden = !validID(currentID); imageFailed = false;
        if (!validID(currentID)) { preview.removeAttribute('src'); renderLanguage(); return; }
        preview.style.display = 'block'; note.style.display = 'none';
        preview.onload = () => { if (ticket !== request) return; preview.style.display = 'block'; note.style.display = 'none'; };
        preview.onerror = () => { if (ticket !== request) return; imageFailed = true; renderLanguage(); };
        preview.src = api.apiURL(`/costume_gallery/assets/img/${encodeURIComponent(currentID)}`); preview.title = currentID;
      }
      function setLanguage(next) {
        if (!['zh','en'].includes(next)) return;
        const changed = language !== next; language = next; if (languageWidget) languageWidget.value = language;
        try { localStorage.setItem(languageKey,language); } catch {}
        renderLanguage(); if (changed) app.graph?.change();
      }
      const close = () => { window.removeEventListener('message',receive); if (dialog?.open) dialog.close(); dialog?.remove(); dialog = null; frame = null; returnFocus?.focus?.(); returnFocus = null; };
      const receive = event => {
        if (event.origin !== location.origin || event.source !== frame?.contentWindow) return;
        if (event.data?.type === 'costume-gallery-ready') frame.contentWindow.postMessage({type:'costume-gallery-current',id:currentID,language},location.origin);
        if (event.data?.type === 'costume-gallery-language') setLanguage(event.data.language);
        if (event.data?.type !== 'costume-gallery-select' || random || !value || !validID(event.data.id)) return;
        value.value = event.data.id; value.callback?.(value.value); update(); node.setDirtyCanvas(true,true); app.graph?.change(); close();
      };
      function openGallery() {
        if (dialog) return;
        returnFocus = document.activeElement;
        dialog = document.createElement('dialog'); dialog.setAttribute('aria-label',tr('服装参考图库','Costume reference gallery')); dialog.style.cssText = 'width:96vw;height:94vh;max-width:1800px;max-height:96vh;padding:0;border:1px solid #8496aa;border-radius:10px;background:#f5f7fa;box-shadow:0 14px 60px #16273d66;';
        const header = document.createElement('div'); header.style.cssText = 'height:46px;display:flex;align-items:center;justify-content:space-between;gap:10px;padding:0 16px;background:#e9eff4;color:#294356;font:13px sans-serif;';
        heading = document.createElement('strong'); closeButton = document.createElement('button'); closeButton.type = 'button'; closeButton.style.cssText = 'padding:6px 14px;border:1px solid #b7c6d3;background:white;color:#294356;border-radius:5px;cursor:pointer;'; closeButton.onclick = close; header.append(heading,closeButton);
        frame = document.createElement('iframe'); frame.src = api.apiURL(`/costume_gallery/gallery?lang=${language}${random ? '&readonly=1' : ''}`); frame.style.cssText = 'display:block;width:100%;height:calc(100% - 46px);border:0;';
        dialog.append(header,frame); renderLanguage(); window.addEventListener('message',receive);
        dialog.addEventListener('cancel',event => {event.preventDefault();close();});
        dialog.addEventListener('click',event => { if (event.target !== dialog) return; const box = dialog.getBoundingClientRect(); if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) close(); });
        document.body.append(dialog); dialog.showModal();
      }
      if (value) { const previous = value.callback; value.callback = function() {previous?.apply(this,arguments);update();}; }
      if (languageWidget) { const previous = languageWidget.callback; languageWidget.callback = function(next) {previous?.apply(this,arguments);setLanguage(next);}; }
      node.addDOMWidget('costume_preview','image',previewBox,{serialize:false,hideOnZoom:false,getMinHeight:()=>300,getMaxHeight:()=>500});
      const configured = node.onConfigure;
      node.onConfigure = function() { configured?.apply(this,arguments); if (['zh','en'].includes(languageWidget?.value)) language = languageWidget.value; if (random) currentID = String(node.properties?.costume_gallery_last_id || ''); renderLanguage(); update(); };
      const executed = node.onExecuted;
      node.onExecuted = function(message) { executed?.apply(this,arguments); const raw = message?.costume_id; const id = Array.isArray(raw) ? raw[0] : raw; if (random && validID(id)) {currentID = id; node.properties ||= {}; node.properties.costume_gallery_last_id = id; update();} };
      const removed = node.onRemoved; node.onRemoved = function() { close(); ++request; preview.removeAttribute('src'); removed?.apply(this,arguments); };
      node.setSize([360,520]); renderLanguage(); update();
    };
  }
});
