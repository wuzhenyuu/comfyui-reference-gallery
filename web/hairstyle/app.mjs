(function () {
  'use strict';
  let {records, meta, ranking} = window.HAIRSTYLE_DATA;
  const {filterRecords, readState, sectionLabels, hairLabels, originLabels} = window.HairstyleCore;
  const $ = selector => document.querySelector(selector);
  const escape = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const I18N=window.HairstyleI18n;
  let language=I18N.preferred(location.search);
  const applyStatic=I18N.captureStatic(document.body);
  const t=(source,values)=>I18N.translate(source,language,values);
  const title=item=>language==='en'?item.name_en:item.title;
  const hair=item=>language==='en'?item.hair_en:item.hair_zh;
  const section=item=>language==='en'?item.section_en:item.section_zh;
  const fmt = number => Number(number).toLocaleString(language==='en'?'en-US':'zh-CN');
  const mb = bytes => (bytes / 1048576).toFixed(1) + ' MiB';
  const byId = new Map(records.map(item => [item.id, item]));
  const paths = {
    'arrow-right':'M4 12h16m-6-6 6 6-6 6', 'arrow-down':'M12 4v16m-6-6 6 6 6-6',
    search:'m21 21-5-5M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0',
    heart:'M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8Z',
    download:'M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5',
    close:'m6 6 12 12M6 18 18 6', 'chevron-left':'m15 5-7 7 7 7', 'chevron-right':'m9 5 7 7-7 7',
    moon:'M21 13A9 9 0 0 1 11 3a9 9 0 1 0 10 10Z', sun:'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5',
    reset:'M3 10a9 9 0 1 1 2.6 8.4M3 4v6h6', sliders:'M4 7h5m5 0h6M4 17h10m5 0h1M9 4v6m5-6v6m0 4v6m5-6v6'
  };
  function icon(name) {return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${paths[name] || paths['arrow-right']}"/></svg>`;}
  document.querySelectorAll('[data-icon]').forEach(node => {node.innerHTML = icon(node.dataset.icon);});
  function stored(key, fallback) {try {return JSON.parse(localStorage.getItem(key)) ?? fallback;} catch {return fallback;}}
  function save(key, value) {try {localStorage.setItem(key, JSON.stringify(value));return true;} catch {return false;}}
  const savedFavorites = stored('hairstyle-atlas-favorites-v1', []);
  const favorites = new Set(Array.isArray(savedFavorites) ? savedFavorites.filter(id => byId.has(id)) : []);
  const state = {...readState(location.hash, records), limit:40};
  let editor;
  let filtered = [], shown = 0, rankCategory = ranking.cats[0], viewerList = [], viewerIndex = -1, imageVersion = 0, lastFocus = null, toastTimer;
  let selectedId = '';
  const viewer = $('#viewer');
  const info = $('#info-dialog');
  const themePreference = stored('hairstyle-atlas-theme', 'system');
  let theme = ['light','dark'].includes(themePreference) ? themePreference : (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  function applyTheme() {
    document.documentElement.dataset.theme = theme;
    $('#theme').innerHTML = icon(theme === 'dark' ? 'sun' : 'moon');
    $('#theme').setAttribute('aria-label', t(theme === 'dark' ? '切换浅色模式' : '切换深色模式'));
    $('#theme').title = $('#theme').getAttribute('aria-label');
  }
  applyTheme();
  $('#theme').addEventListener('click', () => {theme = theme === 'dark' ? 'light' : 'dark';save('hairstyle-atlas-theme', theme);applyTheme();});

  function toast(message) {clearTimeout(toastTimer);$('#toast').textContent = message;$('#toast').hidden = false;toastTimer = setTimeout(() => {$('#toast').hidden = true;}, 2400);}
  function writeURL(id = '') {
    const p = new URLSearchParams();
    if (state.section !== 'all') p.set('sec', state.section);
    if (state.origin && state.origin !== 'all') p.set('origin',state.origin);
    if (state.hair) p.set('hair', state.hair);
    if (state.style) p.set('style', state.style);
    if (state.q) p.set('q', state.q);
    if (state.favorites) p.set('fav', '1');
    if (state.sort !== 'default') p.set('sort', state.sort);
    if (id) p.set('id', id);
    const hash = p.size ? '#' + p.toString() : '';
    try {history.replaceState(null, '', location.pathname + location.search + hash);} catch {if (location.hash !== hash) location.hash = hash;}
  }

  function buildHero() {
    const picks = [...new Map(records.map(item => [item.hair, item])).values()];
    $('#hero-art').innerHTML = picks.slice(0,3).map((item,i) => `<figure class="hero-hairstyle"><img src="${escape(item.thumb)}" width="${item.thumb_w}" height="${item.thumb_h}" alt="${escape(hair(item))} ${t('发型参考')}" ${i ? 'loading="eager"' : 'fetchpriority="high"'}><figcaption>${escape(hair(item))} / HAIRSTYLE</figcaption></figure>`).join('');
  }
  function renderRanking() {
    $('#rank-tabs').innerHTML = ranking.cats.map(key => `<button type="button" data-rank="${escape(key)}" aria-pressed="${key === rankCategory}">${escape(t(ranking.labels[key]))}</button>`).join('');
    const list = (ranking.top[rankCategory] || []).map(id => byId.get(id)).filter(Boolean);
    $('#rank-list').innerHTML = list.map((item,i) => `<li class="rank-item"><button type="button" data-rank-id="${escape(item.id)}" aria-label="${escape(t('发型速览第 {n} 张：{name}',{n:i+1,name:title(item)}))}"><div class="rank-image"><img src="${escape(item.thumb)}" width="${item.thumb_w}" height="${item.thumb_h}" alt="${escape(title(item))}" loading="lazy" decoding="async"></div><span class="rank-no">${String(i+1).padStart(2,'0')}</span><span class="rank-label">${escape(hair(item))} · ${escape(item.id)}</span></button></li>`).join('');
  }
  $('#rank-tabs').addEventListener('click', event => {const button=event.target.closest('[data-rank]');if(button){rankCategory=button.dataset.rank;renderRanking();}});
  $('#rank-list').addEventListener('click', event => {const button=event.target.closest('[data-rank-id]');if(button){const list=ranking.top[rankCategory].map(id=>byId.get(id)).filter(Boolean);openViewer(list,list.findIndex(item=>item.id===button.dataset.rankId));}});

  function renderControls() {
    $('#section-tabs').innerHTML = ['all'].map(section => `<button id="tab-${section}" type="button" role="tab" class="section-tab" data-section="${section}" aria-controls="grid" aria-selected="${state.section===section}" tabindex="${state.section===section?0:-1}">${t(sectionLabels[section])} <small>${fmt(section==='all'?meta.total:meta.sections[section])}</small></button>`).join('');
    $('#grid').setAttribute('aria-labelledby', 'tab-' + state.section);
    $('#origin-filters').innerHTML=Object.entries(originLabels).map(([key,label])=>`<button type="button" data-origin="${key}" aria-pressed="${state.origin===key}">${t(label)} <small>${fmt(key==='all'?meta.total:key==='builtin'?meta.builtin_count:meta.user_count)}</small></button>`).join('');
    const base = filterRecords(records, {...state, hair:'', style:''}, favorites);
    $('#hair-filters').innerHTML = [['','全部发型'], ...Object.entries(hairLabels)].map(([hair,label]) => `<button type="button" class="hair-chip" data-hair="${escape(hair)}" aria-pressed="${state.hair===hair}">${t(label)}<small>${fmt(hair ? base.filter(item=>item.hair===hair).length : base.length)}</small></button>`).join('');
    const styleBase = filterRecords(records, {...state, style:'', q:''}, favorites);
    const styles = [...new Map(styleBase.filter(item=>item.style).map(item=>[item.style,title(item)])).entries()];
    $('#style-filter').innerHTML = '<option value="">'+t('全部风格')+'</option>' + styles.map(([key,label]) => `<option value="${escape(key)}">${escape(label)}</option>`).join('');
    $('#style-filter').value = state.style;
    $('#search').value = state.q;
    $('#sort').value = state.sort;
    $('#favorite-filter').innerHTML=icon('heart')+' '+t('我的收藏')+' <span id="favorite-count">'+favorites.size+'</span>';
    $('#favorite-filter').setAttribute('aria-pressed', String(state.favorites));
    $('#section-note').textContent = t('由正脸参考提取的假人发型；人物身份与发型分开参考');
    const active = [['origin',state.origin!=='all'&&t(originLabels[state.origin])], ['hair',state.hair && t(hairLabels[state.hair])], ['style',state.style && title(records.find(item=>item.style===state.style))], ['q',state.q && t('搜索：{query}',{query:state.q})], ['favorites',state.favorites && t('我的收藏')]].filter(([,value])=>value);
    $('#active-filters').innerHTML = active.map(([key,value])=>`<button type="button" class="active-chip" data-clear="${key}" aria-label="${escape(t('移除筛选：{value}',{value}))}">${escape(value)}<span aria-hidden="true">×</span></button>`).join('');
    const n = active.length;
    $('#filter-toggle').innerHTML = icon('sliders') + ' '+t('筛选') + (n ? ` (${n})` : '');
  }
  function card(item) {
    const liked = favorites.has(item.id);
    return `<article class="hairstyle-card" data-id="${escape(item.id)}" aria-current="${item.id === selectedId}"><div class="card-image"><button class="card-open" type="button" data-open="${escape(item.id)}" aria-label="${escape(t('查看大图：{name}',{name:title(item)}))}"><img src="${escape(item.thumb)}" alt="${escape(section(item)+' · '+title(item))}" loading="lazy" decoding="async" width="${item.thumb_w}" height="${item.thumb_h}"></button><button type="button" class="card-favorite" data-favorite="${escape(item.id)}" aria-pressed="${liked}" aria-label="${t(liked?'取消收藏':'收藏')}: ${escape(item.id)}">${icon('heart')}</button><span class="card-type">${escape(section(item))}</span></div><div class="card-body"><div class="card-heading"><h3>${escape(title(item))}</h3><a class="card-download" href="${escape(item.full)}" download="${escape(item.id)}.png" aria-label="${escape(t('下载 {id} PNG 原图，{size}',{id:item.id,size:mb(item.bytes)}))}" title="${item.w}×${item.h} · ${mb(item.bytes)}">${icon('download')}<span>PNG</span></a></div><div class="card-meta"><span>${escape(hair(item))}</span><span>·</span><code>${escape(item.id)}</code></div></div></article>`;
  }
  function updateResult() {
    $('#result-count').innerHTML = t('共 <strong>{total}</strong> 张{favorites}参考 <span>· 已加载 {shown} 张</span>',{total:fmt(filtered.length),favorites:state.favorites?t('收藏')+(language==='en'?' ':''):'',shown:fmt(shown)});
    $('#empty').hidden = filtered.length > 0;
    $('#more').hidden = shown >= filtered.length;
    $('#more').innerHTML = t('加载更多（剩余 {count} 张）',{count:fmt(filtered.length-shown)}) + icon('arrow-down');
    $('#end-note').hidden = filtered.length===0 || shown<filtered.length;
    if (state.favorites && favorites.size===0) {
      $('#empty h3').textContent = t('收藏夹还没有发型');
      $('#empty p').textContent = t('点击图片右上角的爱心，将喜欢的发型留在这里。');
    } else {
      $('#empty h3').textContent = t('还没有找到合适的发型');
      $('#empty p').textContent = t('换个关键词，或清除筛选再看看。');
    }
  }
  function showMore() {
    const next = Math.min(shown+state.limit, filtered.length);
    $('#grid').insertAdjacentHTML('beforeend', filtered.slice(shown,next).map(card).join(''));
    shown = next;updateResult();editor?.paint();
  }
  function render(updateURL=true) {
    filtered = filterRecords(records,state,favorites);
    $('#grid').replaceChildren();shown=0;
    renderControls();showMore();
    if (updateURL) writeURL(viewer.open && viewerList[viewerIndex] ? viewerList[viewerIndex].id : '');
  }
  function reset() {clearTimeout(searchTimer);Object.assign(state,{section:'all',origin:'all',hair:'',style:'',q:'',favorites:false,sort:'default'});render();}
  function setSection(section) {state.section=section;state.style='';render();}
  $('#section-tabs').addEventListener('click',event=>{const button=event.target.closest('[data-section]');if(button)setSection(button.dataset.section);});
  $('#section-tabs').addEventListener('keydown',event=>{
    if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
    event.preventDefault();const sections=['all'];const i=sections.indexOf(state.section);
    const next=event.key==='Home'?0:event.key==='End'?0:0;
    setSection(sections[next]);$('#tab-'+sections[next]).focus();
  });
  $('#origin-filters').addEventListener('click',event=>{const button=event.target.closest('[data-origin]');if(button){state.origin=button.dataset.origin;render();}});
  $('#hair-filters').addEventListener('click',event=>{const button=event.target.closest('[data-hair]');if(button){state.hair=button.dataset.hair;state.style='';render();}});
  $('#style-filter').addEventListener('change',event=>{state.style=event.target.value;render();});
  $('#sort').addEventListener('change',event=>{state.sort=event.target.value;render();});
  let searchTimer;
  $('#search').addEventListener('input',event=>{const value=event.target.value;clearTimeout(searchTimer);searchTimer=setTimeout(()=>{state.q=value.trim();render();},120);});
  $('#reset').addEventListener('click',reset);$('#empty-reset').addEventListener('click',reset);
  $('#active-filters').addEventListener('click',event=>{const button=event.target.closest('[data-clear]');if(button){state[button.dataset.clear]=button.dataset.clear==='favorites'?false:'';if(button.dataset.clear==='hair')state.style='';if(button.dataset.clear==='origin')state.origin='all';render();}});
  $('#favorite-filter').addEventListener('click',()=>{state.favorites=!state.favorites;render();});
  $('#filter-toggle').addEventListener('click',()=>{const open=$('#filter-toggle').getAttribute('aria-expanded')!=='true';$('#filter-toggle').setAttribute('aria-expanded',String(open));$('#filter-panel').classList.toggle('is-open',open);});
  $('#more').addEventListener('click',showMore);
  // Keep keyboard access predictable: automatic loading follows the first user scroll.
  let hasScrolled=false;
  addEventListener('scroll',()=>{hasScrolled=true;},{passive:true});
  if ('IntersectionObserver' in window) new IntersectionObserver(entries=>{if(entries.some(entry=>entry.isIntersecting)&&hasScrolled&&shown<filtered.length)showMore();},{rootMargin:'180px'}).observe($('#sentinel'));
  $('#grid').addEventListener('click',event=>{
    const favorite=event.target.closest('[data-favorite]');if(favorite){toggleFavorite(favorite.dataset.favorite);return;}
    const open=event.target.closest('[data-open]');if(open)openViewer(filtered,filtered.findIndex(item=>item.id===open.dataset.open));
  });
  $('#grid').addEventListener('error',event=>{if(event.target.tagName==='IMG')event.target.closest('.card-image')?.classList.add('image-error');},true);

  function toggleFavorite(id) {
    if(favorites.has(id))favorites.delete(id);else favorites.add(id);
    const persisted=save('hairstyle-atlas-favorites-v1',[...favorites]);
    const liked=favorites.has(id);
    document.querySelectorAll('[data-favorite]').forEach(button=>{if(button.dataset.favorite===id){button.setAttribute('aria-pressed',String(liked));button.setAttribute('aria-label',t(liked?'取消收藏':'收藏')+': '+id);}});
    $('#favorite-count').textContent=favorites.size;
    if(viewer.open)updateViewerFavorite();
    if(state.favorites)render();
    if(!persisted)toast(t('当前浏览器无法保存收藏，关闭页面后将不会保留'));
  }
  function updateViewerFavorite() {
    const item=viewerList[viewerIndex];if(!item)return;
    const liked=favorites.has(item.id);
    $('#viewer-favorite').innerHTML=icon('heart')+' '+t(liked?'已收藏 · 取消收藏':'收藏这张发型');
    $('#viewer-favorite').setAttribute('aria-pressed',String(liked));
  }
  function showViewer(index) {
    const item=viewerList[index];if(!item)return;
    viewerIndex=index;const request=++imageVersion;
    const image=$('#viewer-image');image.src=item.thumb;image.alt=section(item)+' · '+title(item);
    $('#image-status').hidden=false;$('#image-status').textContent=t('正在加载 PNG 原图…');
    const full=new Image();full.onload=()=>{if(request===imageVersion&&viewer.open){image.src=item.full;$('#image-status').hidden=true;}};
    full.onerror=()=>{if(request===imageVersion){$('#image-status').hidden=false;$('#image-status').textContent=t('原图加载失败，可尝试新窗口打开');}};full.src=item.full;
    $('#viewer-section').textContent=section(item)+' / HAIRSTYLE REFERENCE';
    $('#viewer-title').textContent=title(item);$('#viewer-id').textContent=item.id;
    $('#viewer-position').textContent=`${fmt(index+1)} / ${fmt(viewerList.length)}`;
    $('#viewer-meta').innerHTML=[['参考类型',section(item)],['发型长度',hair(item)],['来源编号',item.source_id||'—'],['原图尺寸',item.w+' × '+item.h],['文件大小',mb(item.bytes)]].map(([key,value])=>`<dt>${escape(t(key))}</dt><dd>${escape(value)}</dd>`).join('');
    $('#viewer-original-style').hidden=item.origin==='user';
    $('#viewer-original-style').textContent=item.origin==='user'?'':item.style?(language==='en'?'Style: '+item.name_en:t('原始日文名称：{name}',{name:item.style})):t('原始素材没有细分发型名称，以发长类别命名。');
    $('.viewer-source').textContent=item.origin==='user'?t('用户上传：{filename}\n上传时间：{time}',{filename:item.original_filename,time:new Date(item.uploaded_at).toLocaleString(language==='en'?'en-US':'zh-CN',{timeZoneName:'short'})}):t('FLUX.2 Klein 生成的假人发型')+'\n'+t('人物来源：あぎ 的人像数据库');
    $('#viewer-download').href=item.full;$('#viewer-download').download=item.id+'.png';$('#viewer-open').href=item.full;
    $('#viewer-prev').disabled=index===0;$('#viewer-next').disabled=index===viewerList.length-1;
    $('#use-hairstyle').disabled = window.parent === window;
    $('#use-hairstyle').textContent = t(window.parent === window ? '请从 ComfyUI 节点打开以使用发型' : '使用此发型 → ComfyUI');
    updateViewerFavorite();writeURL(item.id);editor?.paint();
  }
  function openViewer(list,index) {
    if(!list[index])return;lastFocus=document.activeElement;viewerList=[...list];
    if(!viewer.open)viewer.showModal();document.body.classList.add('modal-open');
    showViewer(index);$('#viewer-close').focus();
  }
  function closeViewer() {if(viewer.open)viewer.close();}
  viewer.addEventListener('close',()=>{imageVersion++;$('#viewer-image').removeAttribute('src');viewerIndex=-1;if(!info.open)document.body.classList.remove('modal-open');writeURL();if(lastFocus?.isConnected)lastFocus.focus();});
  $('#viewer-close').addEventListener('click',closeViewer);
  $('#viewer-prev').addEventListener('click',()=>showViewer(viewerIndex-1));
  $('#viewer-next').addEventListener('click',()=>showViewer(viewerIndex+1));
  $('#viewer-favorite').addEventListener('click',()=>{const item=viewerList[viewerIndex];if(item)toggleFavorite(item.id);});
  viewer.addEventListener('click',event=>{if(event.target===viewer){const rect=viewer.getBoundingClientRect();if(event.clientX<rect.left||event.clientX>rect.right||event.clientY<rect.top||event.clientY>rect.bottom)closeViewer();}});
  $('#copy-id').addEventListener('click',async()=>{
    const text=viewerList[viewerIndex]?.id;if(!text)return;
    try {if(navigator.clipboard?.writeText)await navigator.clipboard.writeText(text);else {const input=document.createElement('textarea');input.value=text;input.style.position='fixed';input.style.opacity='0';viewer.appendChild(input);input.select();if(!document.execCommand('copy'))throw Error();input.remove();}$('#copy-id').textContent=t('已复制');setTimeout(()=>{$('#copy-id').textContent=t('复制 ID');},1800);} catch {$('#copy-id').textContent=t('请手动复制');}
  });
  let touchStart=null;
  $('#viewer-stage').addEventListener('touchstart',event=>{if(event.touches.length===1)touchStart=[event.touches[0].clientX,event.touches[0].clientY];else touchStart=null;},{passive:true});
  $('#viewer-stage').addEventListener('touchend',event=>{if(!touchStart)return;const dx=event.changedTouches[0].clientX-touchStart[0],dy=event.changedTouches[0].clientY-touchStart[1];if(Math.abs(dx)>55&&Math.abs(dx)>Math.abs(dy)*1.3)showViewer(viewerIndex+(dx<0?1:-1));touchStart=null;},{passive:true});
  document.addEventListener('keydown',event=>{
    if(viewer.open){if(['ArrowLeft','ArrowRight'].includes(event.key)&&!['INPUT','TEXTAREA'].includes(event.target.tagName)){event.preventDefault();showViewer(viewerIndex+(event.key==='ArrowRight'?1:-1));}return;}
    if(!info.open&&event.key==='/'&&!['INPUT','TEXTAREA','SELECT'].includes(event.target.tagName)){event.preventDefault();$('#search').focus();}
    if(event.key==='Escape'&&document.activeElement===$('#search')){$('#search').value='';state.q='';render();$('#search').blur();}
  });
  const infoContent = {
    tips:`<h2 id="info-title">使用发型图库</h2><p>按短发、中发、中长发、长发筛选，搜索中文、英文、日文名称或来源 ID，也可直接上传现成发型图。点开图片查看假人发型大图，点击「使用此发型 → ComfyUI」写回当前节点。选择不会自动运行工作流。</p><p>节点输出 PNG、宽高、发型 ID、当前语言的名称、描述、长度和来源编号；自定义素材没有来源人物编号。将图像输出接入支持发型参考的图像编辑工作流。</p><p>PNG 保留生成分辨率，预览和缩略图单独生成。没有细分名称的素材只标注原始发长，不编造刘海或发色标签。</p>`,
    rules:`<h2 id="info-title">来源与生成说明</h2><p>来源为 <a href="https://ai-portrait-gallery.pages.dev/" target="_blank" rel="noopener noreferrer">AI モデル顔データベース</a> 的正脸参考集合，原作者あぎ（@agi_aibusi）。内置素材由本地 comfyui-portrait-gallery 的893张正脸图，经「flux-klein-提取发型」工作流生成。自定义图片由用户直接上传并单独保存。</p><p>原站标注CC0 1.0，同时附带使用请求；完整说明见项目 THIRD_PARTY_NOTICES.md。程序代码许可不改变第三方素材条款。</p><p>这是生成式发型参考，并非像素级抠发。假人头模可能保留浅五官起伏，发丝、轮廓和发色也可能有变化；请以预览和原图检查。</p>`
  };
  const infoEnglish={
    tips:`<h2 id="info-title">Using the hairstyle gallery</h2><p>Filter by short, medium, medium-long or long hair. Search English, Chinese or Japanese names and source IDs, or upload a finished hairstyle reference. Open a large preview and click “Use hairstyle → ComfyUI” to update the current node. Selecting a hairstyle never runs a workflow automatically.</p><p>The node outputs the PNG, dimensions, hairstyle ID, localized name and description, hair length, and source ID. Connect the image to an editing workflow that supports references.</p><p>English names translate the source labels. Entries without detailed names use only their source length category; no extra bangs or hair-color labels are inferred.</p>`,
    rules:`<h2 id="info-title">Sources and generation</h2><p>Based on 893 face references from <a href="https://ai-portrait-gallery.pages.dev/" target="_blank" rel="noopener noreferrer">AI Model Face Database</a> by Agi (@agi_aibusi), processed locally with the FLUX Klein hairstyle-extraction workflow. Custom references are uploaded directly and stored separately.</p><p>The source states CC0 1.0 and includes additional requests. See THIRD_PARTY_NOTICES.md for the preserved source notice. The software license does not change third-party material terms.</p><p>This is generative editing rather than pixel-accurate hair segmentation. Mannequin heads may retain faint facial contours; silhouettes, strands and colors can vary.</p>`
  };
  let infoKind='tips';
  function showInfo(){ $('#info-content').innerHTML=(language==='en'?infoEnglish:infoContent)[infoKind]; }
  document.querySelectorAll('[data-info]').forEach(button=>button.addEventListener('click',()=>{infoKind=button.dataset.info;showInfo();if(!info.open)info.showModal();document.body.classList.add('modal-open');$('#info-close').focus();}));
  $('#info-close').addEventListener('click',()=>info.close());
  info.addEventListener('close',()=>{if(!viewer.open)document.body.classList.remove('modal-open');});
  info.addEventListener('click',event=>{if(event.target===info){const rect=info.getBoundingClientRect();if(event.clientX<rect.left||event.clientX>rect.right||event.clientY<rect.top||event.clientY>rect.bottom)info.close();}});
  window.addEventListener('hashchange',()=>{
    if(['#gallery','', '#'].includes(location.hash))return;
    Object.assign(state,readState(location.hash,records));render(false);
    const id=new URLSearchParams(location.hash.slice(1)).get('id');
    if(id&&byId.has(id)){const list=filtered.some(item=>item.id===id)?filtered:records;openViewer(list,list.findIndex(item=>item.id===id));}
  });
  $('#use-hairstyle').addEventListener('click', () => {
    const item = viewerList[viewerIndex];
    if (item && window.parent !== window) window.parent.postMessage({type:'hairstyle-gallery-select', id:item.id}, location.origin);
  });
  window.addEventListener('message', event => {
    if (event.origin !== location.origin || event.source !== window.parent || event.data?.type !== 'hairstyle-gallery-current') return;
    if (typeof event.data.id !== 'string' || !byId.has(event.data.id)) return;
    selectedId = event.data.id;
    $('#current-hairstyle').textContent = t('当前节点发型：{id}',{id:selectedId});
    render(false);
  });
  const uploadDialog=$('#upload-dialog'), uploadForm=$('#upload-form');
  let uploadFile=null,uploadURL=null,uploadReady=false,uploadBusy=false,uploadVersion=0,uploadLanguage=language;
  const uploadErrors={
    image_required:'请选择一张图片。',single_image_only:'每次只能上传一张图片。',
    file_too_large:'图片超过 20 MiB 限制。',too_many_pixels:'图片超过 3200 万像素限制。',
    unsupported_format:'仅支持静态 PNG、JPEG、WebP 图片。',animated_image:'暂不支持动画图片。',
    invalid_image:'图片损坏或无法读取，请重新选择。',invalid_filename:'文件名无效，请重命名后重试。',
    name_required:'请填写名称。',invalid_metadata:'请检查名称和发长选项，名称最多 120 个字符。',
    invalid_request:'上传请求无效，请重新选择图片后重试。',storage_error:'无法保存到用户素材目录，请检查写入权限后重试。'
  };
  function uploadError(code){const el=$('#upload-error');el.dataset.code=code;el.textContent=t(uploadErrors[code]||'上传失败，请重试。');el.hidden=false;}
  function renderUpload(){
    $('#upload-name-label').textContent=t(uploadLanguage==='en'?'英文名称（必填）':'中文名称（必填）');
    $('#upload-other-label').textContent=t(uploadLanguage==='en'?'中文名称（可选）':'英文名称（可选）');
    $('#upload-filename').textContent=uploadFile?uploadFile.name:t('尚未选择图片');
    $('#upload-save').textContent=t(uploadBusy?'正在保存…':'保存到图库');
    $('#upload-save').disabled=uploadBusy||!uploadReady;
    for(const id of ['upload-cancel','upload-choose','upload-name','upload-other-name','upload-hair'])$('#'+id).disabled=uploadBusy;
    if(!$('#upload-error').hidden)uploadError($('#upload-error').dataset.code);
  }
  function releaseUpload(){
    uploadVersion++;if(uploadURL)URL.revokeObjectURL(uploadURL);
    uploadURL=null;uploadFile=null;uploadReady=false;uploadForm.reset();
    $('#upload-preview').removeAttribute('src');$('#upload-preview').hidden=true;$('#upload-error').hidden=true;
    if(!viewer.open&&!info.open)document.body.classList.remove('modal-open');renderUpload();
  }
  $('#upload-open').addEventListener('click',()=>{
    releaseUpload();uploadLanguage=language;renderUpload();uploadDialog.showModal();document.body.classList.add('modal-open');$('#upload-choose').focus();
  });
  $('#upload-choose').addEventListener('click',()=>$('#upload-file').click());
  $('#upload-file').addEventListener('change',()=>{
    const file=$('#upload-file').files[0];uploadVersion++;const version=uploadVersion;
    if(uploadURL)URL.revokeObjectURL(uploadURL);uploadURL=null;uploadFile=file||null;uploadReady=false;
    $('#upload-preview').hidden=true;$('#upload-preview').removeAttribute('src');$('#upload-error').hidden=true;renderUpload();
    if(!file)return;
    if(file.size>20*1024*1024){uploadError('file_too_large');return;}
    if(file.type&&!['image/png','image/jpeg','image/webp'].includes(file.type)){uploadError('unsupported_format');return;}
    const image=$('#upload-preview');
    image.onload=()=>{if(version!==uploadVersion)return;if(image.naturalWidth*image.naturalHeight>32000000){uploadError('too_many_pixels');return;}uploadReady=true;image.hidden=false;renderUpload();};
    image.onerror=()=>{if(version===uploadVersion){uploadReady=false;uploadError('invalid_image');renderUpload();}};
    uploadURL=URL.createObjectURL(file);image.src=uploadURL;
  });
  $('#upload-cancel').addEventListener('click',()=>{if(!uploadBusy)uploadDialog.close();});
  uploadDialog.addEventListener('cancel',event=>{if(uploadBusy)event.preventDefault();});
  uploadDialog.addEventListener('close',releaseUpload);
  uploadForm.addEventListener('submit',async event=>{
    event.preventDefault();if(uploadBusy)return;
    if(!uploadReady||!uploadFile){uploadError('image_required');return;}
    const name=$('#upload-name').value.trim();if(!name){uploadError('name_required');$('#upload-name').focus();return;}
    uploadBusy=true;$('#upload-error').hidden=true;renderUpload();
    const data=new FormData();data.append('image',uploadFile);data.append('name',name);data.append('other_name',$('#upload-other-name').value.trim());data.append('language',uploadLanguage);data.append('hair',$('#upload-hair').value);
    try{
      const response=await fetch(new URL('upload',location.href),{method:'POST',body:data,credentials:'same-origin'});
      const result=await response.json();if(!response.ok){uploadError(result.error||'invalid_request');return;}
      records=result.catalog.records;meta=result.catalog.meta;ranking=result.catalog.ranking;
      byId.clear();records.forEach(row=>byId.set(row.id,row));
      Object.assign(state,{section:'all',origin:'user',hair:'',style:'',q:'',favorites:false,sort:'default'});
      uploadBusy=false;uploadDialog.close();setLanguage(language,false);
      openViewer(filtered,filtered.findIndex(row=>row.id===result.record.id));toast(t('发型已保存，可点击“使用此发型”写回节点。'));
    }catch{uploadError('upload_failed');}
    finally{uploadBusy=false;renderUpload();}
  });

  function setLanguage(value,notify=true){
    language=I18N.normalize(value);editor?.setLanguage(language);I18N.persist(language);applyStatic(language);
    const url=new URL(location.href);url.searchParams.set('lang',language);history.replaceState(null,'',url.pathname+url.search+url.hash);
    $('#language').value=language;$('#viewer-language').value=language;$('.brand-language').textContent=language==='en'?'EN':'中文';
    document.querySelectorAll('[data-total]').forEach(el=>el.textContent=fmt(meta.total));
    document.querySelectorAll('[data-builtin]').forEach(el=>el.textContent=fmt(meta.builtin_count));
    document.querySelectorAll('[data-user]').forEach(el=>el.textContent=fmt(meta.user_count));
    $('#generation-status').textContent=t('内置 {builtin} · 自定义 {user}',{builtin:fmt(meta.builtin_count),user:fmt(meta.user_count)});
    $('#library-warning').hidden=!meta.builtin_missing;
    $('#current-hairstyle').textContent=selectedId?t('当前节点发型：{id}',{id:selectedId}):t('从节点打开可选择发型');
    const keepShown=shown;buildHero();renderRanking();render(false);
    while(shown<Math.min(keepShown,filtered.length))showMore();
    if(viewer.open)showViewer(viewerIndex);
    if(info.open)showInfo();renderUpload();applyTheme();
    if(notify&&window.parent!==window)window.parent.postMessage({type:'hairstyle-gallery-language',language},location.origin);
  }
  $('#language').addEventListener('change',event=>setLanguage(event.target.value));
  $('#viewer-language').addEventListener('change',event=>setLanguage(event.target.value));
  window.addEventListener('message',event=>{
    if(event.origin===location.origin&&event.source===window.parent&&event.data?.type==='hairstyle-gallery-language'&&['zh','en'].includes(event.data.language))setLanguage(event.data.language,false);
  });
  editor=window.GalleryAssetEditor.mount({
    language,toolbar:$('.nav'),feedback:$('.controls-inner'),grid:$('#grid'),cardSelector:'.hairstyle-card',openLink:$('#viewer-open'),
    translate:(value,lang)=>I18N.translate(value,lang),records:()=>records,visible:()=>filtered,current:()=>viewer.open?viewerList[viewerIndex]:null,
    async reload({keepId}={}){
      closeViewer();
      const [rows,stats]=await Promise.all([fetch('catalog',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error();return r.json();}),fetch('meta',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error();return r.json();})]);
      records=rows.map(row=>({...row,...Object.fromEntries(['full','preview','thumb'].filter(key=>row[key]).map(key=>[key,`assets/${key}/${row.id}${key==='full'?'.png':'.webp'}${row.asset_version?'?v='+encodeURIComponent(row.asset_version):''}`]))}));meta=stats;
      byId.clear();records.forEach(row=>byId.set(row.id,row));
      setLanguage(language,false);
      if(keepId){const list=filtered.some(row=>row.id===keepId)?filtered:records;openViewer(list,list.findIndex(row=>row.id===keepId));}
      window.parent.postMessage({type:'hairstyle-gallery-library-changed'},location.origin);
    }
  });
  setLanguage(language,false);
  if (window.parent !== window) window.parent.postMessage({type:'hairstyle-gallery-ready'}, location.origin);
  const initialId=new URLSearchParams(location.hash.slice(1)).get('id');
  if(initialId&&byId.has(initialId)){const list=filtered.some(item=>item.id===initialId)?filtered:records;openViewer(list,list.findIndex(item=>item.id===initialId));}
})();
