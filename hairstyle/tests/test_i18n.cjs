const assert=require('node:assert/strict');const fs=require('node:fs');const vm=require('node:vm');const path=require('node:path');
const context={module:{exports:{}},URLSearchParams};vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../../web/hairstyle/i18n.mjs'),'utf8'),context);
const I=context.module.exports;
assert.equal(I.translate('全部发型','en'),'All hairstyles');assert.equal(I.translate('全部发型','zh'),'全部发型');
assert.equal(I.translate('当前节点发型：{id}','en',{id:'h-f123'}),'Current node hairstyle: h-f123');
assert.equal(I.preferred('?lang=en'),'en');assert.equal(I.preferred('?lang=zh'),'zh');assert.equal(I.normalize('invalid'),'zh');
for(const [zh,en] of Object.entries(I.EN))assert.deepEqual((zh.match(/\{\w+\}/g)||[]).sort(),(en.match(/\{\w+\}/g)||[]).sort(),zh);
console.log('Language selection, translation placeholders and Chinese fallback passed.');
