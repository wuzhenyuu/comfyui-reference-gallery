async (page, options = {}) => {
  // Evaluate this function with playwright-cli run-code. Pass qwenWorkflow (UI
  // JSON object) or qwenWorkflowUrl to check Qwen wiring. The caller must create
  // screenshotDir before running. No generation is queued or local files read.
  const env = typeof process === 'undefined' ? {} : process.env;
  const assert = (value, message) => { if (!value) throw new Error(message); };
  const kinds = options.kinds || ['pose', 'costume'];
  const usePose = kinds.includes('pose'), useCostume = kinds.includes('costume');
  const baseURL = options.baseURL || env.REFERENCE_GALLERY_BASE_URL || new URL('.', page.url()).href;
  const url = path => new URL(path.replace(/^\//, ''), baseURL.endsWith('/') ? baseURL : `${baseURL}/`).href;
  const appURL = url('scripts/app.js');
  const screenshots = options.screenshotDir || env.REFERENCE_GALLERY_SCREENSHOTS;
  const nodeNames = [...(usePose ? ['PoseGallery','RandomPoseGallery'] : []), ...(useCostume ? ['CostumeGallery','RandomCostumeGallery'] : [])];
  await page.waitForFunction(names => names.every(name => !!window.LiteGraph?.registered_node_types?.[name]), nodeNames);
  async function inApp(action, args = {}) {
    return page.evaluate(async ({appURL, action, args}) => {
      const { app } = await import(appURL);
      const find = kind => app.graph._nodes.find(node => node.type === kind && !node.properties?.reference_gallery_test_other);
      if (action === 'snapshot') return app.graph.serialize();
      if (action === 'fixture') {
        await app.loadGraphData({id:crypto.randomUUID(),version:0.4,last_node_id:0,last_link_id:0,nodes:[],links:[],groups:[],config:{},extra:{ds:{scale:0.64,offset:[40,40]}}});
        args.names.forEach((name,index) => {
          const node = window.LiteGraph.createNode(name); node.pos = [(index % 2) * 470, Math.floor(index / 2) * 650]; app.graph.add(node);
          const field = name === 'PoseGallery' ? 'pose_id' : name === 'CostumeGallery' ? 'costume_id' : null;
          if (field) { const widget = node.widgets.find(w => w.name === field); widget.value = args.initial[name]; widget.callback?.(widget.value); }
          const language = node.widgets?.find(w => w.name === 'language'); if (language) {language.value='zh';language.callback?.('zh');}
        });
        if (app.canvas?.ds) {app.canvas.ds.scale=0.64;app.canvas.ds.offset=[40,40];app.canvas.setDirty(true,true);}
        return app.graph._nodes.map(node => node.type);
      }
      if (action === 'ids') return Object.fromEntries(app.graph._nodes.filter(node => ['PoseGallery','CostumeGallery'].includes(node.type)).map(node => [node.type,node.widgets.find(w => w.name === (node.type === 'PoseGallery' ? 'pose_id' : 'costume_id')).value]));
      if (action === 'restoreCurrent') { const data = app.graph.serialize(); await app.loadGraphData(data); return data; }
      if (action === 'restore') { await app.loadGraphData(args.workflow); return; }
      if (action === 'randomPreview') {
        for (const name of args.names) {
          const node = find(name); if (!node) continue;
          if (name === 'RandomPoseGallery') node.onExecuted?.({pose_id:[args.pose.id],name:[args.pose.姿势名称 || args.pose.name_zh || args.pose.id],name_zh:[args.pose.name_zh],name_en:[args.pose.name_en]});
          if (name === 'RandomCostumeGallery') node.onExecuted?.({costume_id:[args.costume.id]});
        }
        return Object.fromEntries(args.names.map(name => [name,find(name)?.properties]));
      }
      if (action === 'qwen') {
        await app.loadGraphData(args.workflow);
        const { output } = await app.graphToPrompt();
        return output;
      }
    }, {appURL, action, args});
  }
  async function json(path) { const response = await page.request.get(url(path)); assert(response.ok(),`Cannot read ${path}: ${response.status()}`); return response.json(); }
  async function screenshot(name) {
    if (!screenshots) return;
    await page.screenshot({path:`${screenshots.replace(/[\\/]+$/,'')}/${name}`});
  }
  async function closeGallery() {
    const dialog = page.locator('dialog').filter({has:page.locator('iframe')});
    await dialog.getByRole('button',{name:/^(关闭|Close)$/}).click();
    await page.locator('dialog iframe').waitFor({state:'detached'});
  }
  async function clickNative(nodeType,widgetName,accessibleName) {
    const button=page.getByRole('button',{name:accessibleName}).first();
    if(await button.isVisible().catch(()=>false)) {
      await button.click();result.clicks.push({nodeType,widgetName,renderer:'dom'});return;
    }
    // Legacy LiteGraph buttons are painted on the canvas. Read the rendered row
    // position and click real screen coordinates; never invoke its callback here.
    await page.waitForFunction(async ({appURL,nodeType,widgetName})=>{
      const {app}=await import(appURL);const node=app.graph._nodes.find(node=>node.type===nodeType);
      const widget=node?.widgets?.find(widget=>widget.name===widgetName);
      return Number.isFinite(widget?.last_y)&&!!app.canvas?.canvas;
    },{appURL,nodeType,widgetName});
    const point=await page.evaluate(async ({appURL,nodeType,widgetName})=>{
      const {app}=await import(appURL),node=app.graph._nodes.find(node=>node.type===nodeType);
      const widget=node.widgets.find(widget=>widget.name===widgetName),view=app.canvas,canvas=view.canvas,rect=canvas.getBoundingClientRect();
      const height=widget.computedHeight??window.LiteGraph.NODE_WIDGET_HEIGHT??20;
      const ratioX=canvas.clientWidth?rect.width/canvas.clientWidth:1,ratioY=canvas.clientHeight?rect.height/canvas.clientHeight:1;
      return {x:rect.left+(node.pos[0]+node.size[0]/2+view.ds.offset[0])*view.ds.scale*ratioX,y:rect.top+(node.pos[1]+widget.last_y+height/2+view.ds.offset[1])*view.ds.scale*ratioY,rect:{left:rect.left,right:rect.right,top:rect.top,bottom:rect.bottom}};
    },{appURL,nodeType,widgetName});
    assert(Number.isFinite(point.x)&&Number.isFinite(point.y)&&point.x>=point.rect.left&&point.x<=point.rect.right&&point.y>=point.rect.top&&point.y<=point.rect.bottom,`${nodeType}.${widgetName} is outside the visible graph canvas.`);
    await page.mouse.click(point.x,point.y);result.clicks.push({nodeType,widgetName,renderer:'canvas',x:point.x,y:point.y});
  }
  async function readQwen() {
    if (options.qwenWorkflow) return options.qwenWorkflow;
    const workflowUrl = options.qwenWorkflowUrl || env.REFERENCE_GALLERY_QWEN_WORKFLOW_URL;
    if (workflowUrl) {const response=await page.request.get(new URL(workflowUrl,baseURL).href);assert(response.ok(),'Qwen sample URL unavailable');return response.json();}
    return null;
  }
  const original = await inApp('snapshot');
  const result = {loadedNodeTypes:[],clicks:[],selection:{},independentIDs:false,savedRestore:false,randomPreviewMode:'simulated backend UI messages; no prompt execution',qwen:null};
  try {
    const poseRows = usePose ? await json('pose_gallery/catalog') : [];
    const costumes = useCostume ? (await json('costume_gallery/catalog')).items : [];
    if (usePose) assert(poseRows.length > 1,'Install the optional pose assets before live gallery checks.');
    if (useCostume) assert(costumes.length > 1,'Install the optional costume assets before live gallery checks.');
    const initial = {...(usePose ? {PoseGallery:poseRows[0].id} : {}),...(useCostume ? {CostumeGallery:costumes[0].id} : {})};
    result.loadedNodeTypes = await inApp('fixture',{names:nodeNames,initial});
    assert(nodeNames.every(name => result.loadedNodeTypes.includes(name)),'All requested node types must coexist.');
    const beforeQueue = await json('queue');
    if (usePose) {
      // Exercise the real native button and the preserved preview-click opener.
      await clickNative('PoseGallery','pose_browser',/^浏览姿势图库|^Browse poses/);
      await page.locator('dialog iframe').waitFor({state:'attached'});
      assert(await page.locator('dialog iframe').count() === 1,'Pose native button must open one gallery iframe.');
      await closeGallery();
      await page.getByRole('button',{name:/^(打开姿势图库|Open pose gallery)$/}).click();
      const frame = page.frameLocator('dialog iframe');
      await frame.locator('.pose-card[data-index]').first().waitFor();
      const chosen = poseRows.find(row => row.id !== initial.PoseGallery && /_front$/.test(row.id) && row.original_available !== false) || poseRows.find(row=>row.id!==initial.PoseGallery);
      await frame.locator('#searchInput').fill(chosen.id);
      const chosenCard=frame.locator('.pose-card[data-index]').filter({has:frame.locator(`img.main-image[src*="${chosen.id}"]`)});
      // Wait for the debounced search to replace the old card list, rather than
      // accidentally selecting a card still present from the initial results.
      await frame.locator('#grid').evaluate((grid,id)=>new Promise((resolve,reject)=>{
        const ready=()=>{const cards=[...grid.querySelectorAll('.pose-card[data-index]')];return cards.length===1&&cards[0].querySelector('img.main-image')?.getAttribute('src')?.includes(id);};
        if(ready()){resolve();return;}let timer;const observer=new MutationObserver(()=>{if(ready()){clearTimeout(timer);observer.disconnect();resolve();}});observer.observe(grid,{childList:true,subtree:true,attributes:true});timer=setTimeout(()=>{observer.disconnect();reject(new Error('Pose search did not filter to the requested ID.'));},5000);
      }),chosen.id);
      await chosenCard.click();
      await frame.locator('#viewer:not([hidden])').waitFor();
      const selectedID = await frame.locator('#viewerId').innerText();
      assert(selectedID.trim()===chosen.id,'The selected pose must equal the searched ID after filtering.');
      await frame.locator('#usePose').click();
      await page.locator('dialog iframe').waitFor({state:'detached'});
      result.selection.PoseGallery = selectedID.trim();
      const ids = await inApp('ids');assert(ids.PoseGallery === result.selection.PoseGallery,'Pose selection must persist on its own node.');
      if (useCostume) assert(ids.CostumeGallery === initial.CostumeGallery,'Pose selection must not change the costume node.');
    }
    if (useCostume) {
      const chosen = costumes.find(row => row.id !== initial.CostumeGallery && row.library === 'anime') || costumes.find(row=>row.id!==initial.CostumeGallery);
      await clickNative('CostumeGallery','costume_browser',/^浏览服装图库 ·|^Browse costumes ·/);
      await page.locator('dialog iframe').waitFor({state:'attached'});
      assert(await page.locator('dialog iframe').count() === 1,'Costume native button must open one gallery iframe.');
      const frame = page.frameLocator('dialog iframe');await frame.locator('#grid .costume-card').first().waitFor();
      await frame.locator('#search').fill(chosen.id);await frame.locator('#search-form').evaluate(form=>form.requestSubmit());
      await frame.locator(`[data-id="${chosen.id}"]`).click();await frame.locator('#use:not(:disabled)').waitFor();
      const dimensions = await frame.locator('#detail-image').evaluate(img=>({width:img.naturalWidth,height:img.naturalHeight}));assert(dimensions.width>0&&dimensions.height>0,'Costume preview must load the actual original image.');
      await frame.locator('#use').click();await page.locator('dialog iframe').waitFor({state:'detached'});
      result.selection.CostumeGallery = chosen.id;
      const ids=await inApp('ids');assert(ids.CostumeGallery===chosen.id,'Costume selection must persist on its own node.');
      if(usePose)assert(ids.PoseGallery===result.selection.PoseGallery,'Costume selection must not change the pose node.');
      // The random node can browse, but its gallery must never write a fixed ID.
      await clickNative('RandomCostumeGallery','costume_browser',/^浏览服装图库（|^Browse costumes \(view/);
      assert((await page.locator('dialog iframe').getAttribute('src')).includes('readonly=1'),'Random costume browsing must be read-only.');await closeGallery();
    }
    if(usePose){
      await clickNative('RandomPoseGallery','random_language',/^English$/);
      const language=await page.evaluate(async appURL=>{const {app}=await import(appURL);return app.graph._nodes.find(node=>node.type==='RandomPoseGallery').widgets.find(widget=>widget.name==='language').value;},appURL);
      assert(language==='en','The random pose native language shortcut must update its saved language field.');
      result.randomLanguageShortcut=true;
    }
    result.independentIDs = true;
    await inApp('randomPreview',{names:nodeNames.filter(name=>name.startsWith('Random')),pose:poseRows[0],costume:costumes[0]});
    await inApp('restoreCurrent');
    const restored = await inApp('ids');for(const [name,id]of Object.entries(result.selection))assert(restored[name]===id,`${name} ID must survive save/reopen.`);
    for (const id of Object.values(result.selection)) await page.locator(`img[title="${id}"]`).first().waitFor({state:'visible'});
    result.savedRestore = true; await screenshot('merged-nodes.png');
    const afterQueue=await json('queue');
    const queueIDs=q=>[...(q.queue_running||[]),...(q.queue_pending||[])].map(row=>row[1]);
    const known=new Set(queueIDs(beforeQueue));assert(queueIDs(afterQueue).every(id=>known.has(id)),'Gallery selection must not queue a prompt.');result.noAutomaticQueue=true;
    if(useCostume&&options.checkQwen!==false){
      const workflow=await readQwen();
      if(!workflow){
        assert(options.checkQwen!==true,'checkQwen:true requires options.qwenWorkflow (UI workflow JSON object) or options.qwenWorkflowUrl.');
        result.qwen={skipped:true,reason:'No qwenWorkflow object or qwenWorkflowUrl supplied. Set checkQwen:true to require this check.'};
      }else{
        assert(Array.isArray(workflow.nodes),'Qwen check requires the UI workflow JSON, not an API prompt.');
        const prompt=await inApp('qwen',{workflow});
        const encoder=Object.entries(prompt).find(([,node])=>node.class_type==='TextEncodeQwenImage21');assert(encoder,'Qwen image encoder missing after UI import/export.');
        const input1=encoder[1].inputs['images.image_1'],input2=encoder[1].inputs['images.image_2'];assert(Array.isArray(input1)&&Array.isArray(input2),'Qwen must export two image reference connections.');
        assert(prompt[String(input1[0])]?.class_type==='LoadImage','Qwen reference 1 must come from the portrait LoadImage.');assert(prompt[String(input2[0])]?.class_type==='CostumeGallery','Qwen reference 2 must come from CostumeGallery.');assert(input1[1]===0&&input2[1]===0,'Qwen references must use IMAGE output 0.');
        result.qwen={encoder:encoder[0],reference1:input1,reference2:input2,costumeID:prompt[String(input2[0])].inputs.costume_id,validation:'UI import/export wiring only; no model execution'};await screenshot('merged-qwen-workflow.png');
      }
    }else result.qwen={skipped:true,reason:'Qwen check explicitly disabled or costume scope not requested.'};
    return result;
  } finally {
    await page.evaluate(()=>{for(const dialog of document.querySelectorAll('dialog'))if(dialog.querySelector('iframe')){dialog.dispatchEvent(new Event('cancel',{cancelable:true}));}}).catch(()=>{});
    if(options.restoreGraph!==false)await inApp('restore',{workflow:original});
  }
}
