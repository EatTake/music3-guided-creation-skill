---
name: music3-guided-creation
description: 通过分阶段、多维度问答完成歌曲意图、歌词和音乐设计，确认后输出适配 Music3 的结构化创作文件；不连接模型服务或擅自提交生成。
agent_created: true
---

# Music3 引导式创作

将自然语言需求整理为可确认、可返改、可验证的 Music3 创作包。只负责创作和适配，不负责部署模型、连接主机、上传文件、调用后端或自动消耗生成算力。

## 独立调用边界

- 不假定 FAEX1、操作系统、工作目录、SSH、API 地址或前端存在
- 不联网、不安装依赖、不读取凭据、不执行外部命令
- 只使用宿主提供的对话、文件读写和结构化输出能力
- 生成适配器、凭据、网络、路径、上传、队列、资产下载和音频验收由宿主另行提供
- 不存在适配器时，仍交付完整本地创作包和可直接映射到 Music3 的结果；不伪造已提交或已生成

## 参考资料

按需读取：

1. [交互策略](references/interaction-policy.json)
2. [完整工作流](references/workflow.md)
3. [Music3 结构化契约](references/music3-contract.md)
4. 有歌词时读取 [歌词与适配](references/lyrics-guide.md)

## 处理流程

1. **收集创作意图**：默认至少 6 个已回答的独立问题，覆盖主题、情绪、风格、使用场景、歌曲形态、目标长度
2. **确认意图摘要**：题数、维度、缺口和冲突全部满足后，展示摘要并等待明确确认
3. **歌词创作或适配**：新写、续写、检查或局部修改；纯器乐跳过歌词正文
4. **歌词检查**：保留母稿、锁定句、段落顺序和重复次数，区分审美提示与阻断问题
5. **音乐设计**：默认至少 5 个已回答的独立问题，覆盖节奏与速度、配器、人声或主奏表现、歌曲结构、情绪起伏
6. **确认整体音乐方案**：展示逐段推进、声部安排、保留项和建议
7. **输出完整草稿**：展示歌词、音乐方向、目标长度、排除项和代选内容
8. **处理草稿调整**：提供调整风格、节奏、配器、人声或主奏、歌曲结构、保持当前版本；选择调整后先澄清目标、范围和保留项
9. **输出创作包**：按契约生成 `guidance.json`、`creative_spec.json`、`lyrics_document.json` 和 `generation_request.json`
10. **交给宿主适配器**：宿主自行校验目标后端 Schema、编译、提交、跟踪、下载和验收

只有“本版生成授权”才允许宿主适配器进行外部提交；“确认意图”“确认音乐方案”“保持当前版本”均不是生成授权。

## 输入

接受自然语言、故事、已有歌词、参考方向、目标用途、目标时长、段落要求和修改意见。区分：

- 用户明确要求
- 用户提供的事实
- 用户授权范围
- 助手建议或推断
- 后端实际能力与未验证项

用户说“你定”只授权助手在当前问题给出建议，不得虚构未问过的问题、答案、覆盖率或授权。

## 输出

### 机器可读创作包

固定四个文件，放在同一个版本目录：

```text
<song-id>-vN/
├── guidance.json
├── creative_spec.json
├── lyrics_document.json
└── generation_request.json
```

- `guidance.json`：实际问答、维度覆盖、推荐状态、阶段确认、草稿接受和生成授权状态
- `creative_spec.json`：音乐描述，符合 `schemas/creative-spec.schema.json`
- `lyrics_document.json`：段落标签、歌词和逐段音乐意图，符合 `schemas/lyrics-document.schema.json`
- `generation_request.json`：独立生成设置，符合 `schemas/generation-request.schema.json`

同时提供面向用户的草稿摘要，不把 JSON 当成唯一确认界面。

### 默认生成设置

```json
{
  "duration_mode": "auto",
  "duration_seconds": null,
  "seed_mode": "random",
  "seed": null,
  "versions": 1,
  "fade_out_seconds": 0
}
```

目标时长用于安排歌词、结构和器乐留白，不自动变成数值硬上限。固定 seed、多版本、重试、裁剪和淡出需要额外授权。`duration_seconds:null` 是 auto 的显式值；不要省略，也不要把目标秒数直接写入 auto 请求。

## 后端适配规则

不同 Music3 后端的 Schema、字段、长度上限、编译结果和任务接口可能不同。宿主适配器必须：

1. 读取当前部署 Schema，不把本仓库快照当成永远有效的接口事实
2. 验证 `creative_spec`、`lyrics_document` 和 `generation_request`
3. 将 `creative_spec` 编译为目标后端的音乐描述，将 `lyrics_document` 编译为标签歌词
4. 在提交前报告字段差异、警告和未验证项
5. 将本地问答、哈希、授权和版本记录留在本地侧车，不塞进模型输入
6. 只提交用户明确授权的当前版本
7. 不因网络失败、任务失败或用户未确认而自动重试

本 Skill 输出“可适配的 Music3 结构化结果”，不声称任何具体后端已经接受、排队或生成成功。

## 能力边界

- 结构校验通过，不代表实际演唱逐字正确、声线严格遵从、时长精准或听感合格
- Music3 合同没有逐行歌手硬绑定字段；多声线通过全局和逐段音乐描述传入，属于软控制
- 没有音频理解证据时，听检写 `unverified`
- 参考模板只能提供结构和词汇方向，不复制其句子、歌词或完整结构
- 适配器需独立处理模型许可证、用户输入权利、生成内容权利和安全策略

## 本地验证

使用标准库校验两个示例：

```text
python scripts/validate_bundle.py examples/vocal
python scripts/validate_bundle.py examples/instrumental
```

脚本只读本地 JSON，禁止覆盖文件，不联网，不安装依赖，不连接 Music3，不生成音频。编译器会拒绝结构错误、非法标签、换行注入、空段落、重复项、人声/器乐矛盾和超出本地 `caption`/`lyrics` 字符上限的结果。
