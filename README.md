# Music3 Guided Creation Skill

独立的 Music3 引导式歌曲创作 Skill：先让创作者参与关键选择，再输出可审阅、可返改、可验证的结构化创作包，并可在本地编译为直接传入 Music3 的 `caption` 与 `lyrics`。

## 核心边界

- 不包含模型权重、推理服务、SSH、私有主机、队列客户端、凭据、歌曲素材或音频
- 不连接后端、不上传文件、不轮询任务、不下载资产、不安装依赖
- 不假定 FAEX1、Windows、Linux、工作目录或 API 地址
- 具体后端由外部适配器实现：认证、当前 Schema 复核、提交、监测、下载和技术验收
- 没有适配器时，Skill 仍完整交付本地创作包和可直接映射到 Music3 的结果

## 默认流程

1. **创作意图**：至少 6 个实际回答的独立问题，覆盖主题、情绪、风格、使用场景、歌曲形态、目标长度
2. **意图摘要确认**：题数、维度、缺口和冲突均通过后才继续
3. **歌词创作或适配**：新写、续写、检查或授权范围内修改；纯器乐跳过歌词正文
4. **歌词检查**：保留母稿、锁定句、段落顺序和重复次数
5. **音乐设计**：至少 5 个独立问题，覆盖节奏速度、配器、人声/主奏、结构、情绪起伏
6. **整体音乐方案确认**：确认逐段推进、声部安排、保留项和建议
7. **完整草稿与返改**：提供风格、节奏、配器、表现、结构调整；先澄清目标再改
8. **结构化输出**：生成四个版本文件并运行只读校验
9. **直接 Music3 输入**：本地编译成 `caption` 和 `lyrics`；不代表已连接或提交模型

## 独立安装

将仓库放到宿主的 Skill 目录，确保 `SKILL.md` 位于技能根目录。不同 Agent 宿主的安装和启用方式不同，本项目不自动修改宿主配置。

## 输出目录

每首歌使用一个独立版本目录：

```text
<song-id>-vN/
├── guidance.json
├── creative_spec.json
├── lyrics_document.json
└── generation_request.json
```

文件说明：

- `guidance.json`：实际问答、维度覆盖、推荐状态、阶段确认、草稿接受和生成授权
- `creative_spec.json`：音乐描述
- `lyrics_document.json`：段落标签、歌词和逐段音乐意图
- `generation_request.json`：时长、seed（随机种子）、版本数和淡出设置

## 本地命令

仅使用 Python 标准库，不联网、不安装依赖：

```text
python scripts/validate_bundle.py examples/vocal
python scripts/validate_bundle.py examples/instrumental
python scripts/compile_music3_input.py examples/vocal --out vocal-music3-input.json
python scripts/compile_music3_input.py examples/instrumental --out instrumental-music3-input.json
```

编译结果固定为：

```json
{
  "caption": "Global Metadata...",
  "lyrics": "[Verse]..."
}
```

`caption` 只包含音乐描述，`lyrics` 只包含 Music3 安全段落标签和可唱正文；器乐段使用 `(instrumental)` 占位。编译器会先拒绝结构、换行、非法标签、空段落、重复项和人声/器乐矛盾，再检查 `caption` ≤ 12000、`lyrics` ≤ 20000 字符。外部适配器仍必须对照目标后端当前 Schema、字节/token 限制和接口约束。

## 重要默认值

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

目标时长用于安排歌词量、结构和器乐留白，不自动变成硬上限。固定 seed、多版本、重试、裁剪和淡出需要额外授权。

## 目录

```text
SKILL.md                            Skill 主入口
references/interaction-policy.json  提问与放行配置
references/workflow.md              完整交互与迭代规则
references/music3-contract.md       Music3 结构化字段约定
references/lyrics-guide.md          歌词母稿、锁定与适配规则
schemas/                             结构化输出与直接输入 Schema
scripts/validate_bundle.py           标准库只读校验器
scripts/compile_music3_input.py      本地 caption/lyrics 编译器
examples/                            有人声与纯器乐示例
SECURITY_AUDIT.md                    发布前安全审计报告
NOTICE.md                            独立性和商标说明
```

## 兼容性边界

- 目标是 Music3 三段式音乐描述和 9 个安全段落标签
- 后端字段、长度限制和任务接口可能变化；快照 Schema 必须由外部适配器复核
- 多声线、纯器乐、逐段角色和收尾均属于软提示，实际效果需要生成后听检
- 编译成功只证明文本转换完成，不证明模型接受、排队、生成或音频质量合格
- 适配器须独立处理 Music3/MiniMax-Music3 许可证、用户输入权利、生成内容权利和安全策略

## 商标与许可

Music3 与 MiniMax-Music3 的名称归其权利人所有。本项目是独立兼容性工作流，不隶属于或代表模型提供方，也不分发模型权重。本仓库当前不附带开源许可证；如需开放复用，请由仓库所有者另行选择许可证。
