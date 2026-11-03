async (page, options = {}) => {
  // The caller supplies runMerged (the evaluated tests/browser_merged.js
  // function) or mergedTestSource (its source text). This CLI VM reads no files.
  // Configuration: screenshotDir (caller creates it), qwenWorkflow (UI JSON
  // object), or qwenWorkflowUrl. checkQwen:true requires one of those Qwen inputs.
  // This test never submits inference and restores the pre-test graph by default.
  const {runMerged,mergedTestSource,...settings}=options;
  const run=typeof runMerged==='function'?runMerged:typeof mergedTestSource==='string'?(0,eval)(`(${mergedTestSource})`):null;
  if(typeof run!=='function')throw new Error('Pass options.runMerged or options.mergedTestSource containing tests/browser_merged.js; the CLI VM cannot read local files.');
  return run(page,{...settings,kinds:['costume']});
}
