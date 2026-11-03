# ComfyUI Reference Gallery · 姿势与服装图库

一个 ComfyUI 插件，提供独立的姿势图库和服装图库。选择本地参考图后输出标准 `IMAGE`，可连接 Qwen Image 2.1 等支持参考图的工作流。

合并自 `comfyui-pose-gallery` 与 `comfyui-costume-gallery`，保留四个节点名称、原有编号、输入输出、图库地址及姿势自定义素材目录。现有工作流可以继续使用。

## 功能

| 节点 | 用途 |
| --- | --- |
| `PoseGallery` | 浏览姿势，按体系、动作与视角选择；支持上传自定义姿势图 |
| `RandomPoseGallery` | 按来源、体系与视角随机选择姿势 |
| `CostumeGallery` | 浏览写实 / 动漫服装，分类及中英文关键词检索 |
| `RandomCostumeGallery` | 按类型、分类、关键词与种子选择服装，固定种子可复现 |

姿势节点可点击“浏览姿势图库”或直接点击预览图打开图库；服装节点通过“浏览服装图库”打开。选图只更新当前节点，不自动提交生成。选择和预览随工作流保存。

- 姿势素材：1,439 张，288 组，多视角。
- 服装素材：写实 1,407 张，动漫 1,320 张；两套库分开筛选，编号分别使用 `real:`、`anime:` 前缀。
- 图库、选图与节点执行均使用本地文件，无需 API Key。
- 服装图保留上游展示 WebP 的实际尺寸，不自动放大；动漫为 512×768，多数写实为 1366×2048，部分更小。

## 安装

在 ComfyUI 的 `custom_nodes` 目录执行：

```bash
git clone https://github.com/wuzhenyuu/comfyui-reference-gallery.git
```

图库图片和原始数据单独安装。在 ComfyUI 根目录、使用其 Python 环境执行：

```bash
python custom_nodes/comfyui-reference-gallery/scripts/install_libraries.py --library all
```

Windows venv 示例：

```powershell
.\venv\Scripts\python.exe .\custom_nodes\comfyui-reference-gallery\scripts\install_libraries.py --library all
```

也可以用 `--library pose` 或 `--library costume` 只安装一套素材。安装器固定上游版本，只有显式运行安装器时才访问网络；日常使用无需连接原站。完成后重启 ComfyUI。

## 从两个独立插件迁移

1. 先让当前 ComfyUI 完成队列并退出。
2. 将旧的 `comfyui-pose-gallery` 与 `comfyui-costume-gallery` 目录改为以 `.disabled` 结尾，保留为备份。
3. 安装本插件。可将旧姿势 `library/` 复制到本插件 `pose/library/`，旧服装 `library/` 复制到 `costume/library/`，或重新运行安装器。
4. 启动 ComfyUI 并刷新浏览器，打开原工作流即可。

同一时间只启用合并版或两个独立版中的一组，否则会重复注册相同节点和接口。姿势自定义上传及管理记录继续使用 ComfyUI 用户目录下的 `pose_gallery/`，无需重新上传。不要把用户目录复制进插件内置图库。

保留原有环境变量：`COMFYUI_POSE_GALLERY_LIBRARY`、`COMFYUI_POSE_GALLERY_USER_LIBRARY`、`COMFYUI_COSTUME_GALLERY_LIBRARY`。设置这些变量时，本插件继续使用指定目录。

## 工作流与 Qwen Image 2.1

- [四节点预览示例](example_workflows/01_reference_galleries_preview.json)：同时查看固定 / 随机姿势与服装，不加载大模型。
- [Qwen Image 2.1 换装示例](example_workflows/02_qwen_image_2_1_costume_edit.json)：图1为用户人物图，图2为服装图库图；均提供对应的 `.api.json`。

导入 Qwen 示例后，在 Load Image 中选择自己的人物图，并在三个加载器中重新选择本机 Qwen Image 2.1 模型、Qwen3-VL 编码器和对应 VAE。示例不包含人物照片或模型权重。

在已有工作流中，将服装节点 `image` 连接到 `TextEncodeQwenImage21` 的服装参考输入；图像编号由连线决定。人物作为 `image_1`、服装作为 `image_2` 时，提示词可写：

> 为 `<image1>` 中的人物更换服装，服装参考 `<image2>`。保留人物身份、姿势、背景和构图。

姿势节点输出 `image / width / height / pose_id / description / action`；服装节点输出 `image / width / height / costume_id / description / keywords`。参考图能参与生成不等于模型保证服装细节或姿势完全还原。

## 来源与许可

插件源代码按所附 MIT 条款提供，保留上游版权说明。图库图片、缩略图和原始 metadata 不随本仓库发布，不自动适用代码的 MIT 许可；请遵循各素材来源的条款。具体来源、固定版本和上游许可文档差异见 [NOTICE.md](NOTICE.md) 与 [sources/](sources/)。

## 验证

本次合并后的验证范围见 [docs/validation.md](docs/validation.md)。Python 测试需要 ComfyUI Python 环境，Node 测试不需要真实模型；完整素材与模型生成验收另行标注。
