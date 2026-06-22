# 爆款拆解机

上传短视频，AI 自动拆解 6 个维度：开头钩子、脚本结构、情绪曲线、互动引导、数据预测、内容公式 — 生成雷达图 + 逐字稿 + 评分报告。

## 快速开始

### 1. 获取 API Key

注册 [StepFun 开放平台](https://platform.stepfun.com)，获取 API Key。

### 2. 配置环境变量

```bash
cd backend
cp .env.example .env
```

编辑 `.env`，填入你的 API Key：

```
STEPFUN_API_KEY=你的key
STEPFUN_BASE_URL=https://api.stepfun.com/step_plan/v1
ASR_BASE_URL=https://api.stepfun.com/v1
```

### 3. 安装依赖

```bash
cd backend
python -m venv venv
venv\Scripts\pip install -r requirements.txt
```

### 4. 安装 ffmpeg（用于音频提取）

- Windows: 下载 [ffmpeg](https://ffmpeg.org/download.html) 解压后加 PATH，或放到 `~/.ffmpeg/`
- Mac: `brew install ffmpeg`
- Linux: `apt install ffmpeg`

### 5. 启动服务

```bash
cd backend
venv\Scripts\python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

打开浏览器访问 `http://127.0.0.1:8000`

## 技术栈

- **后端**: FastAPI + SQLite
- **AI**: StepFun step-3.7-flash（视觉分析）+ stepaudio-2.5-asr（语音识别）
- **视频处理**: ffmpeg
- **前端**: 原生 HTML/CSS/JS + Chart.js 雷达图

## 分析维度

| 维度 | 说明 |
|------|------|
| 开头钩子 | 前3秒吸引力评分 |
| 脚本结构 | 叙事节奏和结构分析 |
| 情绪曲线 | 情绪波动和节奏变化 |
| 互动引导 | 评论/点赞引导策略 |
| 数据预测 | 预估播放/互动数据 |
| 内容公式 | 可复用的爆款公式提取 |

## 许可

MIT
