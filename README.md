# 课程思政暨习近平文化思想“三进”示范课堂比赛多Agent评审助手

这是一个本地命令行和 Streamlit 前端工具，用于批量处理选手材料，并根据已提供材料生成辅助评分建议。最终分数应由人工评委结合完整材料确认。

## 1. 评分范围

系统现在支持完整评分表三部分：

- 线上评审：案例整体设计，20分
- 线上评审：教案，20分
- 现场教学展示，60分

材料齐全时，系统可以形成100分辅助评分建议。材料不全时，只对可评审模块给出建议，显示“已评审分数 / 可评审满分”，不会把缺失项记为0分。

示例：

- 只有现场材料：`48 / 60`
- 有教案和现场材料：`68 / 80`
- 三类材料齐全：`86 / 100`

## 2. 材料要求

每位选手目录建议如下：

```text
materials/
  A01/
    application_form.docx      # 申报表/案例整体设计，推荐
    application_form.pdf
    lesson_plan.docx           # 教案，推荐
    lesson_plan.pdf
    slides.pptx 或 slides.html（也可使用 slides_001.pptx、slides_002.html 等多个课件文件）
    videos.mp4                 # 或 video.mp4
    transcript.srt
```

兼容的申报表别名：

- `application_form.docx/pdf`
- `application.docx/pdf`
- `case_design.docx/pdf`
- `申报表.docx/pdf`
- `案例整体设计.docx/pdf`
- `参赛申报表.docx/pdf`

兼容的教案别名：

- `lesson_plan.docx/pdf`
- `teaching_plan.docx/pdf`
- `教案.docx/pdf`
- `教学设计.docx/pdf`

旧版 `.doc` 第一版不解析，请转换为 `.docx` 后重新上传。

## 3. 材料不全时如何处理

- 缺申报表/案例整体设计：不评价案例整体设计20分，不记0分。
- 缺教案：不评价教案20分，不记0分。
- 缺视频：不能生成现场教学展示60分正式建议。
- 缺PPT/HTML课件：课件页码证据不足，但不阻断可用材料分析。
- 缺 `transcript.srt`：无法进行完整评审，请补充字幕稿后再运行。
- 文档解析失败：对应文档证据不足，需要人工复核。

只有当申报表、教案、现场材料都具备且完成评审时，才显示100分总分建议。否则显示“当前材料不足以形成100分总评”。

## 4. 环境要求

- Python 3.10 或更高版本
- ffmpeg 和 ffprobe 可在命令行中使用
- Windows下如需导出PPT截图，建议安装 Microsoft PowerPoint

## 5. 安装依赖

```bash
python -m pip install -r requirements.txt
```

## 6. 设置 DEEPSEEK_API_KEY

公开仓库不包含任何 DeepSeek API Key，默认也不会预置 Key。每位使用者需要自行补充自己的 Key。

推荐方式：启动前端后，进入左侧导航的“API设置”，选择“使用我的个人 API”，填写自己的 `DEEPSEEK_API_KEY`。该配置只保存在当前浏览器会话中，不会写入代码、README 或 GitHub。

项目也支持通过环境变量读取 DeepSeek API Key。项目使用 DeepSeek 兼容 OpenAI SDK 的 Chat API 进行多Agent文本评审。

PowerShell 示例：

```powershell
$env:DEEPSEEK_API_KEY="你的DeepSeek API Key"
$env:DEEPSEEK_BASE_URL="https://api.deepseek.com"
$env:DEEPSEEK_MODEL="deepseek-v4-flash"
```

可选设置模型：

```powershell
$env:DEEPSEEK_MODEL="deepseek-v4-flash"
```

不要把 `DEEPSEEK_API_KEY` 写入代码、README或任何要提交的文件中。

## 7. 启动前端

```bash
streamlit run frontend/app.py
```

或：

```bash
python -m streamlit run frontend/app.py
```

前端可用于：

- 上传申报表/案例整体设计材料
- 上传教案
- 上传视频、PPT/HTML课件、SRT
- 调用现有后端评审
- 查看证据链、Agent输出、横向排名
- 查看整体性评价，包括“三进”融合、AI应用、材料一致性、职业教育特色、美育表达和教学闭环
- 下载 `report.docx`、`score.xlsx`、`summary_ranking.xlsx`

前端只负责上传、保存、调用后端和展示结果，不直接调用大模型，不修改评分逻辑，不把缺失项算0分。

本项目已将 Streamlit 单文件上传上限提高到 10GB，配置位于 `.streamlit/config.toml`。如果修改该配置，需要重启前端后生效。

## 8. 命令行运行

处理所有选手：

```bash
python app.py
```

只处理 A01：

```bash
python app.py --candidate A01
```

## 9. 字幕稿说明

系统直接读取用户提供的 `transcript.srt`，不自动转写视频，也不会自动上传视频或音频生成字幕稿。

请将字幕稿放在：

```text
materials/{选手编号}/transcript.srt
```

如果没有 `transcript.srt`，前端会要求补充字幕稿后再运行评审。

## 10. 输出文件

每位选手输出：

```text
outputs/
  A01/
    evidence/
      evidence_package.json
      application_form_evidence.xlsx
      lesson_plan_evidence.xlsx
      speech_evidence.xlsx
      visual_evidence.xlsx
      ppt_evidence.xlsx
      timeline_evidence.xlsx
      consistency_review.json
      bias_review.json
      keyframes/
      slide_images/
    agents/
      case_goal_agent.json
      case_overview_implementation_agent.json
      case_feature_innovation_agent.json
      case_material_norm_agent.json
      lesson_elements_agent.json
      lesson_ideology_culture_agent.json
      lesson_student_objectives_agent.json
      lesson_content_strategy_agent.json
      lesson_evaluation_reflection_agent.json
      moral_culture.json
      vocational_feature.json
      aesthetic_education.json
      teaching_quality.json
      ai_application.json
      teacher_quality.json
      final_judgement.json
      overall_review.json
    report.docx
    score.xlsx
  summary_ranking.xlsx
```

`outputs/` 是生成结果目录，可以删除后重新运行生成。

## 11. 第一版限制

- 最终分数必须由人工评委确认。
- `.doc` 文件不解析，请转换为 `.docx`。
- 系统不自动转写视频，需要人工提供 `transcript.srt`。
- DeepSeek 负责文本评审，不负责音频转写；如需自动转写，需要独立转写服务。
- 文档评审依赖文本提取质量，解析失败时需人工复核。
- 关键帧只作为画面辅助证据，不得用单帧推断整堂课整体状态。
- 不得因为文字包装、PPT美观、课堂热闹、AI露出、思政口号直接给高分。
