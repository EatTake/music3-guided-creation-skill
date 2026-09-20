# Music3 Guided Creation Skill

面向 Music3 的引导式歌曲创作 Skill。它把自然语言创作意图逐步整理为可审阅、可修改、可追溯的 `creative_spec.json`、`lyrics_document.json` 和 `generation_request.json`。

## 解决什么问题

- 避免只问一两个问题就直接生成整首草稿。
- 让创作者参与主题、情绪、风格、场景、歌曲形态、长度、节奏、配器、人声/主奏、结构和情绪起伏等关键选择。
- 把歌词正文与音乐指令分开，输出 Music3 可适配的结构化数据。
- 把意图确认、音乐方案确认、草稿接受和生成授权严格分开。
- 支持返回修改、纯器乐、多声线软提示、版本迭代与反馈路由。

## 不包含什么

本仓库不包含模型权重、推理服务、SSH 配置、队列客户端、私有主机地址、歌曲素材或音频成品。它在“生成适配器”边界停止；具体后端必须自行实现认证、编译、提交、轮询、下载和文件验收。

## 默认流程

1. 创作意图：至少 6 个独立问答，覆盖主题、情绪、风格、使用场景、歌曲形态、目标长度。
2. 歌词：新写、检查或在明确权限内修改；纯器乐跳过歌词正文。
3. 音乐设计：至少 5 个独立问答，覆盖节奏速度、配器、人声/主奏、结构、情绪起伏。
4. 完整草稿：展示歌词和逐段音乐推进，提供风格、节奏、配器、表现、结构调整入口。
5. 结构化输出：生成 Music3 适配文件并运行只读校验。
6. 生成交接：只有用户明确授权后，才把已确认版本交给外部后端适配器。
7. 反馈迭代：区分歌词、编曲、演唱、时长和运行问题，只重做受影响部分。

## 安装

把本仓库克隆到支持 Skill 的宿主目录，确保 `SKILL.md` 位于技能根目录。不同宿主的技能目录和启用方式不同，本仓库不自动修改用户配置。

## 使用

向助手提出“创作一首歌”“做一段 Music3 配乐”或“把这份歌词整理成 Music3 输入”。Skill 会按 `references/interaction-policy.json` 逐题引导。

输出目录建议使用同一版本前缀：

```text
<slug>-v1.guidance.json
<slug>-v1.creative_spec.json
<slug>-v1.lyrics_document.json
<slug>-v1.generation_request.json
```

校验示例：

```text
python scripts/validate_bundle.py examples/vocal
python scripts/validate_bundle.py examples/instrumental
```

校验器只读取指定示例目录和仓库内配置，不联网、不读取凭据、不写文件、不调用模型。

## 目录

```text
SKILL.md                         Skill 主入口
references/interaction-policy.json  提问与放行配置
references/workflow.md          完整交互与迭代规则
references/music3-contract.md   Music3 结构化字段约定
references/lyrics-guide.md      歌词母稿、锁定与适配规则
schemas/                        输出 JSON Schema
scripts/validate_bundle.py      标准库只读校验器
examples/                       有人声与纯器乐示例
SECURITY_AUDIT.md               发布前安全审计报告
```

## 兼容性边界

- 当前结构以 Music3 的三段式音乐描述和 9 个安全段落标签为适配目标。
- 目标时长用于安排素材，不等于精确定长保证。
- 多声线、纯器乐、逐段角色和收尾均属于软提示，实际效果需要生成后听检。
- 后端字段或限制变化时，应先更新 `references/music3-contract.md`、Schema 和示例，再重新审计。

## 商标与许可

Music3 与 MiniMax-Music3 的名称归其权利人所有。本项目是独立的兼容性工作流，不隶属于或代表模型提供方，也不分发模型权重。

本仓库当前未附带开源许可证。公开可读不等于获得复制、修改或商用授权；如需开放复用，请由仓库所有者另行选择许可证。
