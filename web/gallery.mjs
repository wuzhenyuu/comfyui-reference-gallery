const $ = id => document.getElementById(id);
const params = new URLSearchParams(location.search);
const embedded = window.parent !== window;
const readonly = params.get('readonly') === '1';
// The page route is relative to ComfyUI's reverse-proxy prefix.
const route = location.pathname.replace(/\/gallery\/?$/, '');
const prefix = route.endsWith('/costume_gallery') ? route.slice(0, -'/costume_gallery'.length) : '';
const assetURL = path => {
  if (!path || typeof path !== 'string') return '';
  if (path.startsWith('/costume_gallery/')) return `${prefix}${path}`;
  if (path.startsWith(`${route}/`)) return path;
  return '';
};
const norm = value => String(value ?? '').normalize('NFKC').toLocaleLowerCase();
const idOK = value => typeof value === 'string' && /^(real|anime):[a-z\d_-]+$/i.test(value);
const langOK = value => value === 'zh' || value === 'en';
const storage = { get() { try { return localStorage.getItem('costume-gallery-language'); } catch { return null; } }, set(value) { try { localStorage.setItem('costume-gallery-language', value); } catch {} } };
const words = {
  zh: { title:'服装参考图库',local:'本地图库',language:'语言',categories:'服装分类',all:'全部',real:'写实',anime:'动漫',allItems:'全部服装',search:'搜索',searchLabel:'搜索服装',placeholder:'搜索编号、服装、颜色…（支持中英文）',reset:'重置筛选',loading:'正在读取本地图库…',loadFailed:'本地图库读取失败。请确认素材已安装，ComfyUI 正在运行，再点击重试。',retry:'重试',empty:'没有找到匹配服装。试试减少关键词，或重置筛选。',more:'加载更多',selected:'已选择',preview:'服装预览',close:'关闭预览',previous:'上一件',next:'下一件',keywords:'服装关键词',use:'使用此服装',copy:'复制服装编号',download:'下载原图 WebP',imageLoading:'正在读取原图尺寸…',imageFailed:'原图加载失败。请检查本地素材是否完整，再重新打开预览。',selectionHint:'将原图写入当前服装图库节点，作为参考图片使用。',standaloneHint:'独立浏览模式：复制编号后，可粘贴到 ComfyUI 服装图库节点。',readonlyHint:'随机节点浏览模式：复制编号后，可在普通服装图库节点使用。',sidebarNote:'选择服装查看大图，再点击「使用此服装」。',standaloneNote:'选择服装查看大图、下载原图或复制编号。',copied:'编号已复制',copyFailed:'无法自动复制，请选择并复制编号：',selectedID:'已选择服装编号：',found:(count,total)=>`找到 ${count.toLocaleString()} / ${total.toLocaleString()} 件`,shown:(n,total)=>`已显示 ${n.toLocaleString()} / ${total.toLocaleString()} 件`,pixels:(w,h)=>`原图 ${w} × ${h} 像素`,position:(i,n)=>`${i} / ${n}`,missingKeywords:'暂无服装关键词',source:'nvzhuang 本地素材' },
  en: { title:'Costume reference gallery',local:'Local library',language:'Language',categories:'Categories',all:'All',real:'Realistic',anime:'Anime',allItems:'All costumes',search:'Search',searchLabel:'Search costumes',placeholder:'Search ID, costume, color… (Chinese / English)',reset:'Reset filters',loading:'Loading local library…',loadFailed:'Cannot load the local library. Check the installed assets and ComfyUI connection, then retry.',retry:'Retry',empty:'No matching costumes. Try fewer keywords, or reset the filters.',more:'Load more',selected:'Selected',preview:'Costume preview',close:'Close preview',previous:'Previous costume',next:'Next costume',keywords:'Costume keywords',use:'Use this costume',copy:'Copy costume ID',download:'Download original WebP',imageLoading:'Loading original dimensions…',imageFailed:'Cannot load the original image. Check the local asset files and reopen this preview.',selectionHint:'Send the original image to the current costume gallery node for use as a reference image.',standaloneHint:'Standalone browsing: copy the ID and paste it into a ComfyUI costume gallery node.',readonlyHint:'Random node browsing: copy the ID to use it in a regular costume gallery node.',sidebarNote:'Open a costume preview, then select “Use this costume”.',standaloneNote:'Open a costume to preview, download, or copy its ID.',copied:'ID copied',copyFailed:'Automatic copy failed. Select and copy this ID:',selectedID:'Selected costume ID: ',found:(count,total)=>`${count.toLocaleString()} of ${total.toLocaleString()} costumes`,shown:(n,total)=>`Showing ${n.toLocaleString()} of ${total.toLocaleString()}`,pixels:(w,h)=>`Original ${w} × ${h} px`,position:(i,n)=>`${i} / ${n}`,missingKeywords:'No costume keywords available',source:'nvzhuang local assets' }
};
let language = langOK(params.get('lang')) ? params.get('lang') : langOK(storage.get()) ? storage.get() : 'zh';
let catalog = { items:[],categories:[],source:{} }, library = 'all', category = 'all', query = '', filtered = [], shown = 0, selected = '', active = null, loaded = false, failed = false, loading = false, imageReady = false;
const batchSize = 60;
const t = key => words[language][key];
const text = value => Array.isArray(value) ? value.join(' ') : String(value ?? '');
function keywords(item) { return text(language === 'en' ? item.keywords_en : item.keywords_zh) || text(item.keywords_en) || text(item.description); }
function categoryLabel(value) { const info = catalog.categories.find(c => c.value === value); return value === 'all' ? t('allItems') : info?.[`label_${language}`] || value; }
function imageURL(item, kind) { return assetURL(item[`${kind === 'img' ? 'image' : 'thumbnail'}_url`]) || `${route}/assets/${kind}/${encodeURIComponent(item.id)}`; }
function post(message) { if (embedded) window.parent.postMessage(message, location.origin); }
function translate() {
  document.documentElement.lang = language === 'zh' ? 'zh-CN' : 'en'; document.title = t('title'); $('language').value = language;
  for (const [id,key] of Object.entries({title:'title','local-label':'local','language-label':'language','category-title':'categories','search-label':'searchLabel','search-button':'search',reset:'reset',retry:'retry',more:'more','detail-title':'preview','keywords-title':'keywords',copy:'copy',download:'download','source-label':'source'})) $(id).textContent = t(key);
  $('language').setAttribute('aria-label',t('language')); $('search').placeholder = t('placeholder'); $('categories').setAttribute('aria-label',t('categories')); $('libraries').setAttribute('aria-label',t('categories'));
  $('sidebar-note').textContent = t(embedded && !readonly ? 'sidebarNote' : 'standaloneNote');
  for (const button of $('libraries').children) button.textContent = t(button.dataset.library);
  for (const [id,key] of [['close-detail','close'],['previous','previous'],['next','next']]) $(id).setAttribute('aria-label',t(key));
  $('use').textContent = t(embedded && !readonly ? 'use' : 'copy');
  $('copy').hidden = !embedded || readonly;
  renderCategories(); renderResults();
  if (active) renderDetail(false);
}
function renderCategories() {
  const categories = [{value:'all'},...catalog.categories.filter(c => c.value !== 'all')];
  const nodes = categories.map(info => {
    const button = document.createElement('button'); button.type = 'button'; button.className = 'category-button'; button.dataset.category = info.value;
    button.setAttribute('aria-current',String(category === info.value));
    const label = document.createElement('span'); label.textContent = categoryLabel(info.value);
    const count = document.createElement('span'); count.className = 'category-count'; count.textContent = catalog.items.filter(item => (library === 'all' || item.library === library) && (info.value === 'all' || item.category === info.value)).length.toLocaleString();
    button.append(label,count); button.onclick = () => { category = info.value; applyFilters(); }; return button;
  });
  $('categories').replaceChildren(...nodes);
}
function searchTerms(token) {
  const aliases = catalog.source?.search_aliases || {};
  const terms = [token];
  for (const [key,value] of Object.entries(aliases)) if (norm(key) === token) terms.push(...(Array.isArray(value) ? value.map(norm) : [norm(value)]));
  return terms.filter(Boolean);
}
function applyFilters() {
  const tokens = norm(query).split(/\s+/).filter(Boolean).map(searchTerms);
  filtered = catalog.items.filter(item => (library === 'all' || item.library === library) && (category === 'all' || item.category === category) && tokens.every(terms => terms.some(token => item._search.includes(token))));
  shown = 0; renderCategories(); renderResults();
}
function renderResults() {
  $('results-title').textContent = categoryLabel(category);
  $('result-count').textContent = loading ? t('loading') : loaded ? t('found')(filtered.length,catalog.items.length) : '';
  $('status').hidden = loaded && filtered.length > 0;
  $('status-text').textContent = failed ? t('loadFailed') : loaded ? t('empty') : t('loading'); $('retry').hidden = !failed;
  for (const button of $('libraries').children) button.setAttribute('aria-pressed',String(button.dataset.library === library));
  const target = Math.min(filtered.length,shown || batchSize); shown = 0; $('grid').replaceChildren(); appendCards(target);
}
function appendCards(amount = batchSize) {
  const fragment = document.createDocumentFragment();
  for (const item of filtered.slice(shown,shown + amount)) {
    const card = document.createElement('button'); card.type = 'button'; card.className = 'costume-card'; card.dataset.id = item.id; card.setAttribute('aria-current',String(selected === item.id)); card.setAttribute('aria-label',`${item.id}, ${t(item.library)}, ${keywords(item)}`);
    const img = document.createElement('img'); img.className = 'card-image'; img.src = imageURL(item,'thumb'); img.alt = keywords(item) || item.id; img.loading = 'lazy'; img.decoding = 'async'; img.width = 360; img.height = 540;
    img.onerror = () => { if (img.dataset.fallback) { img.alt = `${item.id} — ${t('imageFailed')}`; return; } img.dataset.fallback = '1'; img.src = imageURL(item,'img'); };
    const caption = document.createElement('div'); caption.className = 'card-caption'; const name = document.createElement('strong'); name.textContent = item.source_id || item.id; const badge = document.createElement('span'); badge.className = 'card-library'; badge.textContent = t(item.library); caption.append(name,badge);
    const desc = document.createElement('p'); desc.className = 'card-description'; desc.textContent = keywords(item); card.append(img,caption,desc);
    if (selected === item.id) { const marker = document.createElement('span'); marker.className = 'selected-marker'; marker.textContent = t('selected'); card.append(marker); }
    card.onclick = () => openDetail(item); fragment.append(card);
  }
  shown = Math.min(filtered.length,shown + amount); $('grid').append(fragment); $('more').hidden = shown >= filtered.length; $('page-count').textContent = loaded && filtered.length ? t('shown')(shown,filtered.length) : '';
}
function openDetail(item) { active = item; renderDetail(true); if (!$('detail').open) $('detail').showModal(); }
function renderDetail(reload) {
  $('detail-library').textContent = `${t(active.library)} / ${categoryLabel(active.category)}`; $('detail-id').textContent = active.id; $('detail-keywords').textContent = keywords(active) || t('missingKeywords'); $('detail-hint').textContent = t(embedded ? readonly ? 'readonlyHint' : 'selectionHint' : 'standaloneHint'); $('position').textContent = t('position')(filtered.findIndex(item => item.id === active.id)+1,filtered.length);
  $('action-status').textContent = ''; $('download').href = imageURL(active,'img'); $('download').download = `${active.id.replace(':','-')}.webp`;
  const index = filtered.indexOf(active); $('previous').disabled = index <= 0; $('next').disabled = index < 0 || index >= filtered.length - 1;
  const img = $('detail-image'); img.alt = `${active.id} ${keywords(active)}`;
  if (reload) {
    imageReady = false; $('dimensions').textContent = t('imageLoading'); $('image-error').hidden = true; $('use').disabled = embedded && !readonly; img.style.visibility = 'hidden';
    const expected = imageURL(active,'img');
    img.onload = () => { if (img.getAttribute('src') !== expected) return; imageReady = true; img.style.visibility = 'visible'; $('dimensions').textContent = t('pixels')(img.naturalWidth,img.naturalHeight); $('use').disabled = false; };
    img.onerror = () => { imageReady = false; $('dimensions').textContent = ''; $('image-error').textContent = t('imageFailed'); $('image-error').hidden = false; $('use').disabled = embedded && !readonly; };
    img.src = expected;
  } else {
    $('dimensions').textContent = imageReady ? t('pixels')(img.naturalWidth,img.naturalHeight) : $('image-error').hidden ? t('imageLoading') : '';
    if (!$('image-error').hidden) $('image-error').textContent = t('imageFailed');
  }
}
function move(delta) { const next = filtered[filtered.indexOf(active)+delta]; if (next) { active = next; renderDetail(true); } }
async function copyID() {
  if (!active) return;
  try { await navigator.clipboard.writeText(active.id); $('action-status').textContent = `${t('copied')}: ${active.id}`; }
  catch { $('action-status').textContent = `${t('copyFailed')} ${active.id}`; const range = document.createRange(); range.selectNodeContents($('detail-id')); const selection = window.getSelection(); selection.removeAllRanges(); selection.addRange(range); }
}
async function load() {
  loading = true; failed = false; loaded = false; renderResults();
  try {
    const response = await fetch(`${route}/catalog`,{credentials:'same-origin'}); if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json(); if (!Array.isArray(data.items) || !Array.isArray(data.categories)) throw new Error('Invalid catalog');
    catalog = data;
    catalog.items = catalog.items.filter(item => idOK(item.id) && ['real','anime'].includes(item.library)).map(item => {
      const base = norm([item.id,item.source_id,item.category,item.category_zh,item.category_en,text(item.keywords_zh),text(item.keywords_en)].join(' '));
      return {...item,_search:base};
    });
    loaded = true; loading = false; applyFilters();
  } catch (error) { console.error('[Costume Gallery]',error); failed = true; loading = false; renderResults(); }
}
$('language').onchange = () => { language = $('language').value; storage.set(language); translate(); post({type:'costume-gallery-language',language}); };
$('libraries').onclick = event => { const button = event.target.closest('button[data-library]'); if (button) { library = button.dataset.library; applyFilters(); } };
let debounce;
$('search').oninput = () => { clearTimeout(debounce); debounce = setTimeout(() => { query = $('search').value; applyFilters(); },180); };
$('search-form').onsubmit = event => { event.preventDefault(); clearTimeout(debounce); query = $('search').value; applyFilters(); };
$('reset').onclick = () => { clearTimeout(debounce); library = 'all'; category = 'all'; query = ''; $('search').value = ''; applyFilters(); };
$('retry').onclick = load; $('more').onclick = () => appendCards(); $('close-detail').onclick = () => $('detail').close(); $('previous').onclick = () => move(-1); $('next').onclick = () => move(1); $('copy').onclick = copyID;
$('use').onclick = () => {
  if (!active) return;
  if (embedded && !readonly) { if (!imageReady) return; selected = active.id; post({type:'costume-gallery-select',id:active.id}); $('detail').close(); renderResults(); }
  else { $('action-status').textContent = `${t('selectedID')}${active.id}`; copyID(); }
};
$('detail').addEventListener('click',event => { if (event.target === $('detail')) { const rect = $('detail').getBoundingClientRect(); if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) $('detail').close(); } });
document.addEventListener('keydown',event => { if (!$('detail').open || event.altKey || event.ctrlKey || event.metaKey || /^(INPUT|TEXTAREA|SELECT)$/.test(event.target.tagName)) return; if (event.key === 'ArrowLeft') {event.preventDefault();move(-1);} if (event.key === 'ArrowRight') {event.preventDefault();move(1);} });
window.addEventListener('message',event => {
  if (!embedded || event.origin !== location.origin || event.source !== window.parent || event.data?.type !== 'costume-gallery-current') return;
  if (idOK(event.data.id)) selected = event.data.id;
  if (langOK(event.data.language)) language = event.data.language;
  translate();
});
translate(); post({type:'costume-gallery-ready'}); load();
