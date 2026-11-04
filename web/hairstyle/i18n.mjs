// Shared, deterministic text translations for the gallery and ComfyUI node.
(function(root){
  'use strict';
  const EN = {
  "本次随机发型预览": "Random hairstyle preview",
  "随机发型预览加载失败，请检查素材原图。": "The random preview could not load. Check the original image.",
  "上次运行结果": "Last execution result",
  "运行工作流后自动抽取发型": "A hairstyle is drawn automatically when the workflow runs",
  "随机来源": "Random source",
  "AI 假人发型参考库 · HAIRSTYLE Atlas": "AI Mannequin Hairstyle Gallery · HAIRSTYLE Atlas",
  "HAIRSTYLE Atlas 首页": "HAIRSTYLE Atlas home",
  "跳到发型图库": "Skip to hairstyle gallery",
  "主导航": "Main navigation",
  "发型图库": "Hairstyles",
  "使用指南": "Guide",
  "来源与许可": "Sources & license",
  "中文": "English",
  "切换深色模式": "Switch to dark mode",
  "切换浅色模式": "Switch to light mode",
  "为你的下一个角色，": "For your next character,",
  "挑选一款": "find your ",
  "合适的发型。": "perfect hairstyle.",
  "从人物参考中提取头发，呈现在假人头模上。": "Hairstyles extracted from portraits and displayed on mannequin heads.",
  "按长度与名称挑选，让发型成为独立的创作参考。": "Browse by length and name to use hair as a separate creative reference.",
  "探索发型图库": "Explore hairstyles",
  "如何使用": "How it works",
  "已生成发型": "Generated hairstyles",
  "来源正脸": "Source portraits",
  "发型长度": "Hair length",
  "完整生成图": "Full-size images",
  "不同发型的发型参考预览": "Preview of different hairstyle lengths",
  "从节点打开可选择发型": "Open from a node to select a hairstyle",
  "本地生成素材": "Locally generated assets",
  "假人发型参考，仅供创作参考": "Mannequin hairstyles for creative reference",
  "灵感，从这里开始": "Start with inspiration ",
  "四种长度 · 发型速览": "Four lengths · Quick preview",
  "本地生成 · 按原始素材顺序": "Locally generated · Source order",
  "发型速览分类": "Hairstyle preview categories",
  "你的发型参考库": "Your hairstyle collection ",
  "按名称、发长与风格找到合适的参考": "Find a reference by name, length, and style",
  "我的收藏": "Favorites",
  "参考类型": "Reference type",
  "搜索发型、风格或 ID…": "Search hairstyles, styles, or IDs…",
  "搜索发型、风格或 ID": "Search hairstyles, styles, or IDs",
  "筛选": "Filters",
  "发型风格": "Hair style",
  "全部风格": "All styles",
  "全部发型": "All hairstyles",
  "假人发型": "Mannequin hairstyle",
  "短发": "Short",
  "中发": "Medium",
  "中长发": "Medium-long",
  "长发": "Long",
  "重置筛选": "Reset filters",
  "排序": "Sort",
  "排序方式": "Sort order",
  "来源顺序": "Source order",
  "编号 A–Z": "ID A–Z",
  "原图尺寸优先": "Largest images first",
  "参考图片列表": "Reference images",
  "还没有找到合适的发型": "No matching hairstyles",
  "换个关键词，或清除筛选再看看。": "Try another keyword or clear your filters.",
  "清除全部筛选": "Clear all filters",
  "加载更多": "Load more",
  "你已看完当前筛选下的全部发型。": "You have seen all hairstyles matching these filters.",
  "让灵感，成为你的角色。": "Turn inspiration into your character.",
  "将参考图带进熟悉的创作工具，": "Bring references into your creative tools,",
  "将头发与人物身份分开参考。": "and reference hair separately from character identity.",
  "找到喜欢的发型": "Find a hairstyle",
  "按发型和风格筛选。查看假人头模上的发型轮廓。中文与日文名称沿用来源数据。": "Filter by length and style. Inspect the silhouette on a mannequin head. Chinese and Japanese names are retained from the source; English names are translations.",
  "下载 PNG 原图": "Download full-size PNG",
  "打开大图查看细节，下载完整分辨率生成图，也可收藏发型，方便下次回来继续创作。": "Inspect the details, download the full-resolution image, and save favorites for your next visit.",
  "带入你的创作流程": "Use in your workflow",
  "在 ComfyUI 中将发型输出接入支持参考图的工作流。输出假人发型PNG和名称，供支持参考图的模型使用。": "Connect the hairstyle image and name to a ComfyUI workflow that supports image references.",
  "为角色挑选发型，让参考各司其职。": "Choose hair for your character and give each reference a clear role.",
  "本地工作流生成项目。来源人物素材：": "Generated with a local workflow. Source portraits:",
  "AI モデル顔データベース ↗": "AI Model Face Database ↗",
  "原作者 あぎ ↗": "Original creator: Agi ↗",
  "中文数据 JSON ↓": "Bilingual catalog JSON ↓",
  "张假人发型 · 来源为 893 张正脸参考": "mannequin hairstyles · Based on 893 source portraits",
  "本站不收集浏览或下载数据；收藏仅保存在当前浏览器。": "No browsing or download tracking. Favorites stay in this browser.",
  "正在加载原图…": "Loading full-size image…",
  "上一张": "Previous image",
  "下一张": "Next image",
  "复制 ID": "Copy ID",
  "使用此发型 → ComfyUI": "Use hairstyle → ComfyUI",
  "新窗口打开原图": "Open full-size image in a new tab",
  "收藏这张发型": "Favorite this hairstyle",
  "← → 切换发型 · Esc 关闭": "← → Browse hairstyles · Esc Close",
  "触屏支持左右滑动": "Swipe left or right on touch screens",
  "FLUX.2 Klein 生成的假人发型": "Mannequin hairstyle generated with FLUX.2 Klein",
  "人物来源：あぎ 的人像数据库": "Portrait source: Agi's face database",
  "关闭大图": "Close image viewer",
  "关闭说明": "Close information",
  "请启用 JavaScript 以浏览图库。全部原图保存在 img/full/，原始与中文清单保存在 data/。": "Enable JavaScript to browse the gallery. Full-size images are in img/full/; catalogs are in data/.",
  "本地假人发型图库，按长度、中文名称、日文名称及来源ID检索。": "Offline mannequin hairstyle gallery. Search by length, English, Chinese or Japanese names, and source ID.",
  "界面语言": "Interface language",
  "大图界面语言": "Viewer language",
  "由正脸参考提取的假人发型；人物身份与发型分开参考": "Extracted from portraits; reference hair separately from identity",
  "发型速览第 {n} 张：{name}": "Hairstyle preview {n}: {name}",
  "发型参考": "Hairstyle reference",
  "搜索：{query}": "Search: {query}",
  "移除筛选：{value}": "Remove filter: {value}",
  "查看大图：{name}": "View full-size image: {name}",
  "收藏": "Favorite",
  "取消收藏": "Unfavorite",
  "下载 {id} PNG 原图，{size}": "Download {id} full-size PNG, {size}",
  "共 <strong>{total}</strong> 张{favorites}参考 <span>· 已加载 {shown} 张</span>": "{favorites}References: <strong>{total}</strong> <span>· Loaded: {shown}</span>",
  "加载更多（剩余 {count} 张）": "Load more ({count} remaining)",
  "收藏夹还没有发型": "No favorite hairstyles yet",
  "点击图片右上角的爱心，将喜欢的发型留在这里。": "Click the heart on an image to save it here.",
  "当前浏览器无法保存收藏，关闭页面后将不会保留": "This browser cannot save favorites; they will be lost when the page closes.",
  "已收藏 · 取消收藏": "Saved · Remove favorite",
  "正在加载 PNG 原图…": "Loading full-size PNG…",
  "原图加载失败，可尝试新窗口打开": "Image could not load. Try opening it in a new tab.",
  "来源编号": "Source ID",
  "原图尺寸": "Image dimensions",
  "文件大小": "File size",
  "原始日文名称：{name}": "Original Japanese name: {name}",
  "原始素材没有细分发型名称，以发长类别命名。": "No detailed style name was provided; the name uses the source hair-length category.",
  "请从 ComfyUI 节点打开以使用发型": "Open from a ComfyUI node to use this hairstyle",
  "已复制": "Copied",
  "请手动复制": "Please copy manually",
  "当前节点发型：{id}": "Current node hairstyle: {id}",
  "{count} 张正脸已全部转换": "All {count} source portraits have been converted",
  "已生成 {count} / {target} 张，刷新查看新增素材": "Generated {count} / {target}. Refresh to see new items.",
  "浏览发型图库 · 长度 / 风格 / 名称 / 搜索": "Browse hairstyles · Length / Style / Name / Search",
  "所选发型原图预览": "Selected hairstyle preview",
  "发型原图加载失败：{path}。请检查完整素材库，重启 ComfyUI 并刷新页面。": "Cannot load hairstyle: {path}. Check the library, restart ComfyUI, and refresh the page.",
  "Hairstyle Gallery · 选择发型后点击「使用此发型 → ComfyUI」": "Hairstyle Gallery · Select a hairstyle, then click “Use hairstyle → ComfyUI”",
  "关闭": "Close",
  "中文发型参考图库": "Hairstyle reference gallery",
  "发型编号": "Hairstyle ID",
  "界面与文本语言": "UI / text language",
  "图像": "Image",
  "宽度": "Width",
  "高度": "Height",
  "名称": "Name",
  "描述": "Description",
  "上传发型": "Upload hairstyle",
  "浏览内置假人发型，或上传自己的发型参考。": "Browse built-in mannequin hairstyles or upload your own hairstyle reference.",
  "可用发型": "Available hairstyles",
  "内置": "Built-in",
  "自定义": "Custom",
  "全部来源": "All sources",
  "未分类": "Unspecified",
  "素材来源": "Asset source",
  "按发长速览": "Quick preview by length",
  "本地素材 · 按入库顺序": "Local assets · Catalog order",
  "内置库未安装，可上传自定义发型继续使用。": "The built-in library is not installed. Upload custom hairstyles to continue.",
  "内置 {builtin} · 自定义 {user}": "Built-in {builtin} · Custom {user}",
  "张可用参考 · 内置": "available references · Built-in",
  "/ 自定义": "/ Custom",
  "直接导入图片，不自动提取头发或去除人物面部。": "Images are imported directly. Hair extraction and face removal are not performed.",
  "支持静态 PNG、JPEG、WebP；单张不超过 20 MiB、3200 万像素。": "Static PNG, JPEG, or WebP. Up to 20 MiB and 32 megapixels per image.",
  "选择图片": "Choose image",
  "尚未选择图片": "No image selected",
  "待上传发型预览": "Preview of the hairstyle to upload",
  "名称（必填）": "Name (required)",
  "中文名称（必填）": "Chinese name (required)",
  "英文名称（必填）": "English name (required)",
  "中文名称（可选）": "Chinese name (optional)",
  "英文名称（可选）": "English name (optional)",
  "取消": "Cancel",
  "保存到图库": "Save to gallery",
  "正在保存…": "Saving…",
  "请选择一张图片。": "Choose an image.",
  "每次只能上传一张图片。": "Upload one image at a time.",
  "图片超过 20 MiB 限制。": "The image exceeds the 20 MiB limit.",
  "图片超过 3200 万像素限制。": "The image exceeds the 32-megapixel limit.",
  "仅支持静态 PNG、JPEG、WebP 图片。": "Only static PNG, JPEG, and WebP images are supported.",
  "暂不支持动画图片。": "Animated images are not supported.",
  "图片损坏或无法读取，请重新选择。": "The image is damaged or cannot be read. Choose another image.",
  "文件名无效，请重命名后重试。": "The filename is invalid. Rename the file and try again.",
  "请填写名称。": "Enter a name.",
  "请检查名称和发长选项，名称最多 120 个字符。": "Check the name and hair length. Names are limited to 120 characters.",
  "上传请求无效，请重新选择图片后重试。": "Invalid upload request. Select the image again and retry.",
  "无法保存到用户素材目录，请检查写入权限后重试。": "Cannot save to the user library. Check write permissions and retry.",
  "上传失败，请重试。": "Upload failed. Please retry.",
  "发型已保存，可点击“使用此发型”写回节点。": "Saved. Click “Use hairstyle” to update the node.",
  "自定义上传，没有原始日文名称。": "Custom upload; no original Japanese name.",
  "用户上传：{filename}\n上传时间：{time}": "User upload: {filename}\nUploaded at: {time}"
};
  const LANGUAGE_KEY='hairstyle-gallery-language';
  const normalize=value=>value==='en'?'en':'zh';
  function translate(source,language,values={}) {
    const text=normalize(language)==='en'?(EN[source]??source):source;
    return text.replace(/\{(\w+)\}/g,(_,key)=>String(values[key]??'{'+key+'}'));
  }
  function preferred(search='') {
    const explicit=new URLSearchParams(search).get('lang');
    if(explicit==='zh'||explicit==='en')return explicit;
    try{return normalize(localStorage.getItem(LANGUAGE_KEY));}catch{return 'zh';}
  }
  function persist(language){try{localStorage.setItem(LANGUAGE_KEY,normalize(language));}catch{}}
  function captureStatic(body) {
    const texts=[],attrs=[];
    const walker=document.createTreeWalker(body,NodeFilter.SHOW_TEXT);
    while(walker.nextNode()){
      const node=walker.currentNode;
      if(!['SCRIPT','STYLE'].includes(node.parentElement?.tagName)&&!node.parentElement?.closest('#language, #viewer-language')&&EN[node.nodeValue.trim()])texts.push([node,node.nodeValue]);
    }
    for(const el of body.querySelectorAll('*'))for(const key of ['aria-label','placeholder','title','alt']){
      const value=el.getAttribute(key);if(value&&EN[value])attrs.push([el,key,value]);
    }
    const originalTitle=document.title;
    const description=document.querySelector('meta[name="description"]');const originalDescription=description?.content;
    return language=>{
      document.documentElement.lang=language==='en'?'en':'zh-CN';document.title=translate(originalTitle,language);
      if(description)description.content=translate(originalDescription,language);
      for(const [node,value] of texts)if(node.isConnected)node.nodeValue=value.replace(value.trim(),translate(value.trim(),language));
      for(const [el,key,value] of attrs)if(el.isConnected)el.setAttribute(key,translate(value,language));
    };
  }
 let catalogPromise;
 function loadCatalog(url){
  if(!catalogPromise)catalogPromise=fetch(url).then(response=>{if(!response.ok)throw Error('Cannot load catalog');return response.json();}).catch(error=>{catalogPromise=null;throw error;});
  return catalogPromise;
 }
  const api={loadCatalog,translate,normalize,preferred,persist,captureStatic,EN,LANGUAGE_KEY};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.HairstyleI18n=api;
})(typeof window!=='undefined'?window:globalThis);
