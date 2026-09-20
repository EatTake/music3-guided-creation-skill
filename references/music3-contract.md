# Music3 结构化适配契约

本页描述本 Skill 输出的兼容性快照，不代表所有 Music3 后端都实现相同 API。外部适配器提交前必须与目标后端的当前 Schema 对照。

## 双通道原则

- 音乐描述：风格、情绪、速度、声线、乐器、段落推进和制作质感。
- 歌词：段落标签和可唱正文。

不要把整段歌词复制进音乐描述，也不要把乐器、模型参数、文件路径或命令写进歌词正文。

## creative_spec

顶层：

- `schema_version`: 当前为 `2.0`
- `project_id`: UUID
- `revision`: 非负整数
- `global`
- `vocal`
- `arrangement`

### global

- `primary_genre`: 主风格
- `fusion_genres`: 最多 3 个融合风格
- `primary_mood`: 主情绪
- `secondary_moods`: 辅助情绪
- `tempo_mode`: `slow`、`medium`、`fast`、`bpm` 或 `null`
- `bpm`: 仅在用户明确指定且 `tempo_mode=bpm` 时使用，20–300
- `key`: 调性或 `null`，无依据不猜
- `energy`: 全局能量描述或 `null`
- `imagery`: 场景与意象
- `production`: 声音和制作质感
- `custom_notes`: 跨段硬约束；不重复其他字段

### vocal

- `mode`: `vocal` 或 `instrumental`
- `lead`: 主唱描述；纯器乐为 `null`
- `timbre`: 音色
- `delivery`: 唱法、语言和发音要求
- `harmony`: 和声或伴唱
- `effects`: 必要的人声效果

纯器乐必须清空人声设置，并在编曲中指定承担旋律角色的主奏乐器。输入只能降低出现无词人声的概率，不能保证模型绝不哼唱。

### arrangement

- `template_id`: 只有选定真实模板时填写，否则 `null`
- `primary_layers`: 主要乐器生命周期
- `secondary_layers`: 辅助层
- `foundation`: 鼓、贝斯与律动基础
- `transitions`: 转场、高潮和空间效果
- `section_development`: 默认 `[]`；逐段变化统一写进歌词文档的 `music_intent`

列表项不要人为添加尾部句号，避免后端拼接时出现重复标点。此约定不适用于用户歌词正文。

## lyrics_document

- `schema_version`: `2.0`
- `language`: BCP 47 风格语言标识；纯器乐使用 `und`
- `sections`: 至少 1 段

每段包含：

- `section_id`: UUID
- `tag`: `Intro`、`Verse`、`Pre-Chorus`、`Chorus`、`Post-Chorus`、`Bridge`、`Instrumental`、`Solo`、`Outro`
- `title`: 可读段名；编译为直接 Music3 文本时使用安全 `tag`，不把中文标题作为标签
- 直接文本中的器乐段：使用 `(instrumental)`，不把它当歌词
- `instrumental`: 布尔值
- `lines`: 可唱正文；器乐段为空数组
- `music_intent`: 本段进入、退出、强弱、声部和转场变化

合同没有逐行歌手硬绑定字段。多声线要求通过全局人声字段和逐段 `title`、`music_intent` 传入，属于软提示。不要往 `lines` 添加歌手标签。

## generation_request

本 Skill 的默认适配值：

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

目标时长用于安排歌词量、结构和留白，不自动变成数值硬上限。只有用户明确要求并接受截断风险时才使用 `target`。随机 seed、单版本、无淡出是默认值；重试、多版本和后期处理都需要额外授权。

## 输出限制

- 音乐描述总长度应服从目标后端上限；不要为了达到字数而重复描述。
- 歌词每行保持可唱短句，标签独占逻辑段落。
- 歌词正文避免模型、seed、API、路径和混音命令等技术词。
- 编译或 JSON 校验通过仅证明输入结构可接受，不证明实际歌词、声线、时长或听感合格。
