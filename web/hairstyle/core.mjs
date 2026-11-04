(function (root) {
  'use strict';
  const sectionLabels = {all: '全部发型', hairstyle: '假人发型'};
  const hairLabels = {'ショート': '短发', 'ミディアム': '中发', 'セミロング': '中长发', 'ロング': '长发', unknown: '未分类'};
  const originLabels = {all:'全部来源', builtin:'内置', user:'自定义'};
  function filterRecords(records, state, favorites = new Set()) {
    const words = String(state.q || '').trim().toLowerCase().split(/\s+/).filter(Boolean);
    const result = records.filter(item =>
      (!state.section || state.section === 'all' || item.section === state.section) &&
      (!state.origin || state.origin === 'all' || (item.origin || 'builtin') === state.origin) &&
      (!state.hair || item.hair === state.hair) && (!state.style || item.style === state.style) &&
      (!state.favorites || favorites.has(item.id)) && words.every(word => item.search.includes(word)));
    if (state.sort === 'id') result.sort((a, b) => a.id.localeCompare(b.id));
    if (state.sort === 'size') result.sort((a, b) => b.w * b.h - a.w * a.h);
    return result;
  }
  function readState(hash, records) {
    const p = new URLSearchParams(hash.replace(/^#/, ''));
    const section = 'all';
    const hair = Object.hasOwn(hairLabels, p.get('hair')) ? p.get('hair') : '';
    const style = records.some(item => item.style === p.get('style')) ? p.get('style') : '';
    const sort = ['default', 'id', 'size'].includes(p.get('sort')) ? p.get('sort') : 'default';
    const origin = Object.hasOwn(originLabels, p.get('origin')) ? p.get('origin') : 'all';
    return {section, origin, hair, style, sort, q: p.get('q') || '', favorites: p.get('fav') === '1'};
  }
  const api = {filterRecords, readState, sectionLabels, hairLabels, originLabels};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.HairstyleCore = api;
})(typeof window !== 'undefined' ? window : globalThis);
