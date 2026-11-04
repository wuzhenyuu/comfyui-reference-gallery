// Random-node messages extend the shared gallery vocabulary.
(function(root){
  const EN={
  "本次随机发型预览": "Random hairstyle preview",
  "随机发型预览加载失败，请检查素材原图。": "The random preview could not load. Check the original image.",
  "上次运行结果": "Last execution result",
  "运行工作流后自动抽取发型": "A hairstyle reference is drawn automatically when the workflow runs",
  "随机来源": "Random source",
  "点击骰子预览，或运行工作流自动抽取发型": "Click the dice to preview, or run the workflow to draw a hairstyle",
  "正在抽取发型…": "Drawing a hairstyle…",
  "🔒 已锁定": "🔒 Locked",
  "🎲 随机": "🎲 Random",
  "随机发型": "Draw a random hairstyle",
  "仅更新此节点预览，不运行工作流": "Update this preview without running the workflow",
  "当前发型编号": "Current hairstyle ID",
  "🔒 锁定随机": "🔒 Lock random selection",
  "随机失败，请重试": "Could not draw a hairstyle. Try again",
  "请先点击骰子选择发型，再锁定": "Draw a hairstyle before locking",
  "无效的发型编号": "Invalid hairstyle ID",
  "all：全部；builtin：内置；user：自定义。": "all: all references; builtin: bundled; user: custom uploads.",
  "控制界面与文本输出语言，随工作流保存。": "Controls the UI and text output language. Saved with the workflow.",
  "当前选择的发型，锁定后运行工作流使用此图。": "The selected hairstyle. Workflow runs keep this reference while locked.",
  "保持当前发型并禁用骰子。": "Keep the current hairstyle and disable the dice.",
  "界面与提示语言": "UI / error language",
  "图像": "Image",
  "宽度": "Width",
  "高度": "Height",
  "发型编号": "Hairstyle ID",
  "界面与输出语言": "UI / output language",
  "发型名称": "Hairstyle name",
  "描述": "Description",
  "参考类型": "Reference type",
  "英文关键词": "English keywords"
};
  const LANGUAGE_KEY="hairstyle-gallery-random-language";
  const normalize=value=>value==='en'?'en':'zh';
  function preferred(){try{return normalize(localStorage.getItem(LANGUAGE_KEY));}catch{return 'zh';}}
  function persist(value){try{localStorage.setItem(LANGUAGE_KEY,normalize(value));}catch{}}
  function translate(text,language){return language==='en'?(EN[text]??root.HairstyleI18n?.translate(text,language)??text):text;}
  const api={preferred,persist,normalize,translate};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.RandomHairstyleI18n=api;
})(typeof window!=='undefined'?window:globalThis);
