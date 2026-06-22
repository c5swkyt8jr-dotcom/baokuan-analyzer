"""
StepFun API Integration
- step-3.7-flash: Video visual analysis (Chat Completions API)
- stepaudio-2.5-asr: Speech-to-text transcription
- Files API: Upload media files for reuse
"""

import base64
import json
import re
import time
import httpx
from openai import OpenAI
from config import STEPFUN_API_KEY, STEPFUN_BASE_URL, ASR_BASE_URL


def _robust_json_parse(text: str) -> dict:
    """
    Multiple-strategy JSON parsing to handle imperfect model output.
    Tries: direct parse → markdown extraction → brace matching → line-by-line repair
    """
    original = text
    text = text.strip()

    # Strategy 1: Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Extract from markdown code blocks
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 3: Brace matching — find outermost {}
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start >= 0 and brace_end > brace_start:
        text = text[brace_start:brace_end + 1]

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 4: Try to repair common issues
    # Remove trailing commas before } or ]
    text = re.sub(r',\s*([}\]])', r'\1', text)
    # Fix unescaped newlines in strings
    text = re.sub(r'(?<!\\)\\(?!["\\/bfnrtu])', r'\\\\', text)

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            f"All parsing strategies failed. Original error: {str(e)}. "
            f"Preview (first 300 chars): {original[:300]}",
            e.doc, e.pos
        )

# Create OpenAI-compatible client for step-3.7-flash
client = OpenAI(
    api_key=STEPFUN_API_KEY,
    base_url=STEPFUN_BASE_URL,
    timeout=300.0,
)


def upload_file_to_stepfun(file_path: str, purpose: str = "storage") -> str:
    """Upload a file to StepFun storage and return the stepfile:// URL."""
    with open(file_path, "rb") as f:
        file_obj = client.files.create(
            file=f,
            purpose=purpose,
        )
    return f"stepfile://{file_obj.id}"


def analyze_video_visual(
    video_url: str,
    transcript_text: str = "",
    reasoning_effort: str = "high",
) -> dict:
    """
    Send video to step-3.7-flash for comprehensive visual analysis.
    Returns structured analysis result as dict.
    """
    transcript_section = ""
    if transcript_text:
        # Truncate if too long
        if len(transcript_text) > 8000:
            transcript_text = transcript_text[:8000] + "\n...(字幕内容过长，已截断前8000字)"
        transcript_section = f"""

【视频字幕/逐字稿（来自语音识别）】
{transcript_text}
"""

    prompt = f"""你是一位顶级的短视频爆款分析专家。请仔细观看并分析这个视频的全部画面内容，结合提供的字幕文稿，从以下6个维度进行深度剖析。

{transcript_section}

【分析要求】
请基于视频的真实画面和内容进行分析，不要编造或猜测。每个维度的分析必须引用视频中的具体画面、场景、文字、动作作为依据。

【6个分析维度】

1. **开头钩子 (Opening Hook)** — 前3秒的抓人程度
   - 开头用了什么手法？（悬念/冲突/提问/反差/视觉冲击等）
   - 钩子的强度和类型
   - 如果是你会不会继续看？为什么？

2. **脚本结构 (Script Structure)** — 内容组织逻辑
   - 整体结构模式（如：黄金圈/SCQA/并列/递进/反转等）
   - 节奏控制如何？
   - 信息密度和逻辑衔接是否流畅？

3. **情绪曲线 (Emotional Curve)** — 观众情绪牵引
   - 视频的情绪走向是怎样的？（标注关键时间点）
   - 哪些节点制造了情绪峰值？
   - 整体的情绪节奏设计如何？

4. **互动引导 (Interaction Guidance)** — 激发用户行为
   - 有哪些引导点赞/评论/关注/转发的设计？
   - 评论区引导策略如何？
   - 互动钩子的自然程度？

5. **数据预测 (Data Prediction)** — 爆款潜力预估
   - 预估完播率
   - 预估点赞率/评论率/转发率
   - 预估整体传播潜力

6. **内容公式 (Content Formula)** — 可复制性
   - 提炼这个视频的内容公式/模板
   - 核心要素有哪些？
   - 其他人如何借鉴？

【输出格式要求】
请严格按照以下JSON格式输出，不要输出任何JSON之外的内容。所有分析必须用中文。

```json
{{
  "overall_score": 85,
  "viral_style": "情绪共鸣型",
  "summary": "整体评价，2-3句话概括这个视频的爆款要素和核心亮点",

  "opening_hook": {{
    "score": 90,
    "level": "S",
    "analysis": "详细分析开头的钩子设计...",
    "hook_type": "悬念型/冲突型/提问型...",
    "key_moment": "0:00-0:03",
    "improvement": "改进建议"
  }},

  "script_structure": {{
    "score": 82,
    "level": "A",
    "analysis": "详细分析脚本结构...",
    "structure_type": "SCQA/反转/并列...",
    "key_moments": ["时间点1: 事件", "时间点2: 事件"],
    "improvement": "改进建议"
  }},

  "emotional_curve": {{
    "score": 88,
    "level": "A",
    "analysis": "详细分析情绪曲线...",
    "curve_description": "情绪变化描述",
    "peak_moments": [{{"time": "0:15", "emotion": "惊讶", "intensity": 9, "description": "..."}}],
    "improvement": "改进建议"
  }},

  "interaction_guide": {{
    "score": 75,
    "level": "B",
    "analysis": "详细分析互动引导设计...",
    "cta_moments": [{{"time": "0:30", "type": "点赞引导", "description": "..."}}],
    "improvement": "改进建议"
  }},

  "data_prediction": {{
    "score": 80,
    "level": "A",
    "analysis": "详细数据预测分析...",
    "estimated_completion_rate": 65,
    "estimated_like_rate": 4.5,
    "estimated_comment_rate": 1.2,
    "estimated_share_rate": 2.0,
    "viral_potential": "高/中/低",
    "improvement": "改进建议"
  }},

  "content_formula": {{
    "score": 85,
    "level": "A",
    "analysis": "详细内容公式分析...",
    "formula_name": "公式名称",
    "formula_template": "公式模板描述（可直接复用）",
    "core_elements": ["要素1", "要素2", "要素3"],
    "applicable_scenarios": ["场景1", "场景2"],
    "improvement": "改进建议"
  }}
}}
```

评分标准：
- S级(90-100)：顶尖爆款水准
- A级(75-89)：优质内容，有明显爆款基因
- B级(60-74)：合格内容，有优化空间
- C级(40-59)：普通内容，需要大幅改进
- D级(0-39)：缺乏爆款元素

请基于真实视频内容，给出客观、专业、有深度的分析。不要输出任何JSON之外的内容。"""

    try:
        print(f"[analyze_video_visual] Sending video_url={video_url[:50]}..., prompt_len={len(prompt)}")
        response = client.chat.completions.create(
            model="step-3.7-flash",
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "video_url",
                        "video_url": {"url": video_url}
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }],
            reasoning_effort=reasoning_effort,
            max_tokens=8192,
        )

        content = response.choices[0].message.content.strip()
        print(f"[analyze_video_visual] Response length: {len(content)}, first 200: {content[:200]}")
        result = _robust_json_parse(content)
        return result

    except json.JSONDecodeError as e:
        print(f"[analyze_video_visual] JSON decode failed: {e}")
        return {
            "overall_score": 0,
            "viral_style": "解析失败",
            "summary": f"JSON解析错误: {str(e)}。原始响应前500字: {content[:500] if content else 'N/A'}",
            "error": True,
            "raw_response": content[:2000] if content else 'N/A',
        }
    except Exception as e:
        return {
            "overall_score": 0,
            "viral_style": "API错误",
            "summary": f"API调用失败: {str(e)}",
            "error": True,
        }


def analyze_video_base64(
    file_path: str,
    transcript_text: str = "",
    reasoning_effort: str = "high",
) -> dict:
    """
    Fallback: send video as base64 data URL to step-3.7-flash.
    Used when stepfile:// URL approach fails.
    """
    # Read and encode video
    import os
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    
    # If video is larger than 50MB, base64 encoding is impractical
    if file_size_mb > 50:
        raise ValueError(f"视频太大({file_size_mb:.1f}MB)，不适合base64模式，请使用关键帧分析")

    with open(file_path, "rb") as f:
        video_base64 = base64.b64encode(f.read()).decode("utf-8")

    transcript_section = ""
    if transcript_text:
        if len(transcript_text) > 8000:
            transcript_text = transcript_text[:8000] + "\n...(字幕内容过长，已截断前8000字)"
        transcript_section = f"\n\n【视频字幕/逐字稿（来自语音识别）】\n{transcript_text}"

    prompt = f"""你是一位顶级的短视频爆款分析专家。请仔细观看并分析这个视频的全部画面内容，结合提供的字幕文稿，从以下6个维度进行深度剖析。

{transcript_section}

【分析要求】
请基于视频的真实画面和内容进行分析，不要编造或猜测。每个维度的分析必须引用视频中的具体画面、场景、文字、动作作为依据。

【6个分析维度】
1. **开头钩子 (Opening Hook)** — 前3秒的抓人程度（手法/强度/是否想继续看）
2. **脚本结构 (Script Structure)** — 内容组织逻辑（结构模式/节奏/信息密度）
3. **情绪曲线 (Emotional Curve)** — 观众情绪牵引（情绪走向/峰值节点/节奏设计）
4. **互动引导 (Interaction Guidance)** — 激发用户行为（点赞/评论/关注/转发引导/自然度）
5. **数据预测 (Data Prediction)** — 爆款潜力预估（完播率/互动率/传播潜力）
6. **内容公式 (Content Formula)** — 可复制性（公式/模板提炼/核心要素/借鉴方法）

评分标准：S级(90-100) / A级(75-89) / B级(60-74) / C级(40-59) / D级(0-39)

请严格按照JSON格式输出，不要输出JSON之外的任何内容。格式如下：
{{"overall_score":85,"viral_style":"风格","summary":"2-3句话概括","opening_hook":{{"score":90,"level":"S级","analysis":"分析","hook_type":"类型","key_moment":"0:00","improvement":"建议"}},"script_structure":{{"score":82,"level":"A级","analysis":"分析","structure_type":"类型","key_moments":["时间:描述"],"improvement":"建议"}},"emotional_curve":{{"score":88,"level":"A级","analysis":"分析","curve_description":"描述","peak_moments":[{{"time":"时间","emotion":"情绪","intensity":5,"description":"描述"}}],"improvement":"建议"}},"interaction_guide":{{"score":75,"level":"B级","analysis":"分析","cta_moments":[{{"time":"时间","type":"类型","description":"描述"}}],"improvement":"建议"}},"data_prediction":{{"score":80,"level":"A级","analysis":"分析","estimated_completion_rate":65,"estimated_like_rate":4.5,"estimated_comment_rate":1.2,"estimated_share_rate":2.0,"viral_potential":"中","improvement":"建议"}},"content_formula":{{"score":85,"level":"A级","analysis":"分析","formula_name":"名称","formula_template":"可复用模板","core_elements":["要素"],"applicable_scenarios":["场景"],"improvement":"建议"}}}}"""

    try:
        response = client.chat.completions.create(
            model="step-3.7-flash",
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "video_url",
                        "video_url": {"url": f"data:video/mp4;base64,{video_base64}"}
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }],
            reasoning_effort=reasoning_effort,
            max_tokens=8192,
        )

        content = response.choices[0].message.content.strip()
        print(f"[analyze_video_base64] Response length: {len(content)}, first 200: {content[:200]}")
        return _robust_json_parse(content)

    except json.JSONDecodeError as e:
        return {
            "overall_score": 0,
            "viral_style": "解析失败",
            "summary": f"Base64视频分析JSON错误: {str(e)}",
            "error": True,
            "raw_response": content[:2000] if content else 'N/A',
        }
    except Exception as e:
        raise  # Re-raise to trigger fallback


def analyze_video_frames(
    frame_paths: list[str],
    transcript_text: str = "",
    reasoning_effort: str = "high",
) -> dict:
    """
    Fallback: Send extracted frames to step-3.7-flash for analysis.
    Used when video exceeds 128MB or direct upload fails.
    """
    # Build content array with frames
    content = []

    # Add frames as base64 images (max ~20 frames to stay within limits)
    for i, frame_path in enumerate(frame_paths[:20]):
        with open(frame_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{b64}",
                "detail": "low"
            }
        })

    transcript_section = ""
    if transcript_text:
        if len(transcript_text) > 6000:
            transcript_text = transcript_text[:6000]
        transcript_section = f"\n\n【视频字幕文稿（来自语音识别）】\n{transcript_text}"

    prompt = f"""你是一位顶级的短视频爆款分析专家。以下是按时间顺序从视频中抽取的关键画面帧，请结合字幕文稿和画面内容，从以下6个维度进行深度剖析。{transcript_section}

（提示词与上面相同的6维度分析要求，输出相同JSON格式）

请基于真实画面内容，给出客观、专业、有深度的分析。不要输出任何JSON之外的内容。"""

    # Full prompt is too long, let me create a separate one
    content.append({
        "type": "text",
        "text": _get_analysis_prompt(transcript_text, is_frames=True)
    })

    try:
        response = client.chat.completions.create(
            model="step-3.7-flash",
            messages=[{"role": "user", "content": content}],
            reasoning_effort=reasoning_effort,
            max_tokens=8192,
        )

        content_str = response.choices[0].message.content.strip()
        print(f"[analyze_video_frames] Raw response length: {len(content_str)}, first 200: {content_str[:200]}")
        result = _robust_json_parse(content_str)
        return result

    except json.JSONDecodeError as e:
        return {
            "overall_score": 0,
            "viral_style": "解析失败",
            "summary": f"帧分析JSON解析错误: {str(e)}",
            "error": True,
            "raw_response": content_str[:2000] if content_str else 'N/A',
        }
    except Exception as e:
        return {
            "overall_score": 0,
            "viral_style": "帧分析错误",
            "summary": f"帧分析失败: {str(e)}",
            "error": True,
        }


def _get_analysis_prompt(transcript_text: str = "", is_frames: bool = False) -> str:
    """Generate the comprehensive analysis prompt."""
    media_desc = "以下是按时间顺序从视频中抽取的关键画面帧" if is_frames else "请仔细观看并分析这个视频的全部画面内容"

    transcript_section = ""
    if transcript_text:
        if len(transcript_text) > 6000:
            transcript_text = transcript_text[:6000] + "\n...(字幕过长，已截断)"
        transcript_section = f"""

【视频字幕/逐字稿（来自语音识别）】
{transcript_text}
"""

    return f"""你是一位顶级的短视频爆款分析专家。{media_desc}，结合提供的字幕文稿，从以下6个维度进行深度剖析。

{transcript_section}

【分析要求】
请基于真实内容分析，不要编造。每个维度的分析必须引用视频中的具体画面、场景、文字、动作作为依据。

【6个分析维度】

1. **开头钩子** — 前3秒的抓人程度（手法、强度、是否想继续看）
2. **脚本结构** — 内容组织逻辑（结构模式、节奏、信息密度）
3. **情绪曲线** — 观众情绪牵引（情绪走向、峰值节点、节奏设计）
4. **互动引导** — 激发用户行为（点赞/评论/关注/转发引导、自然度）
5. **数据预测** — 爆款潜力预估（完播率、互动率、传播潜力）
6. **内容公式** — 可复制性（公式/模板提炼、核心要素、借鉴方法）

评分标准：S级(90-100)、A级(75-89)、B级(60-74)、C级(40-59)、D级(0-39)

请严格按照以下JSON格式输出，不要输出任何JSON之外的内容：

```json
{{
  "overall_score": 85,
  "viral_style": "风格分类（情绪共鸣型/知识干货型/剧情反转型/视觉冲击型/幽默搞笑型/其他）",
  "summary": "整体评价，2-3句话概括爆款要素和核心亮点",

  "opening_hook": {{
    "score": 90, "level": "S级", "analysis": "详细分析...",
    "hook_type": "悬念型/冲突型/提问型/反差型/视觉冲击型/其他",
    "key_moment": "时间范围", "improvement": "改进建议"
  }},

  "script_structure": {{
    "score": 82, "level": "A级", "analysis": "详细分析...",
    "structure_type": "SCQA/反转/递进/并列/其他",
    "key_moments": ["时间: 关键节点描述"],
    "improvement": "改进建议"
  }},

  "emotional_curve": {{
    "score": 88, "level": "A级", "analysis": "详细分析...",
    "curve_description": "整体情绪变化描述",
    "peak_moments": [{{"time": "时间", "emotion": "情绪类型", "intensity": 1-10, "description": "描述"}}],
    "improvement": "改进建议"
  }},

  "interaction_guide": {{
    "score": 75, "level": "B级", "analysis": "详细分析...",
    "cta_moments": [{{"time": "时间", "type": "点赞/评论/关注/转发引导", "description": "描述"}}],
    "improvement": "改进建议"
  }},

  "data_prediction": {{
    "score": 80, "level": "A级", "analysis": "详细分析...",
    "estimated_completion_rate": 65,
    "estimated_like_rate": 4.5,
    "estimated_comment_rate": 1.2,
    "estimated_share_rate": 2.0,
    "viral_potential": "高/中/低",
    "improvement": "改进建议"
  }},

  "content_formula": {{
    "score": 85, "level": "A级", "analysis": "详细分析...",
    "formula_name": "公式名称",
    "formula_template": "可复用的公式模板描述",
    "core_elements": ["核心要素"],
    "applicable_scenarios": ["适用场景"],
    "improvement": "改进建议"
  }}
}}
```

请基于真实视频/画面内容，给出客观、专业、有深度的分析。"""


def transcribe_audio(audio_base64: str, audio_format: str = "pcm", sample_rate: int = 16000) -> str:
    """
    Transcribe audio using stepaudio-2.5-asr.
    Returns the full transcript text.
    """
    payload = {
        "audio": {
            "data": audio_base64,
            "input": {
                "transcription": {
                    "model": "stepaudio-2.5-asr",
                    "language": "zh",
                    "enable_itn": True,
                },
                "format": {
                    "type": audio_format,
                    "codec": "pcm_s16le",
                    "rate": sample_rate,
                    "bits": 16,
                    "channel": 1,
                }
            }
        }
    }

    full_transcript = ""

    try:
        with httpx.Client(timeout=120.0) as http_client:
            with http_client.stream(
                "POST",
                f"{ASR_BASE_URL}/audio/asr/sse",
                headers={
                    "Authorization": f"Bearer {STEPFUN_API_KEY}",
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream",
                },
                json=payload,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            event = json.loads(data_str)
                            # StepFun ASR SSE format:
                            # - transcript.text.delta events have "delta" field
                            # - transcript.text.done event has "text" field (full text)
                            if "delta" in event:
                                full_transcript += event["delta"]
                            elif "text" in event:
                                # Final event contains complete transcript
                                full_transcript = event["text"]
                        except json.JSONDecodeError:
                            continue

        return full_transcript.strip()

    except Exception as e:
        raise Exception(f"语音识别失败: {str(e)}")


def transcribe_audio_file(audio_file_path: str) -> str:
    """Transcribe an audio file using stepaudio-2.5-asr."""
    # Determine format from extension
    ext = audio_file_path.lower().split(".")[-1]
    format_map = {
        "wav": "wav",
        "mp3": "mp3",
        "ogg": "ogg",
        "pcm": "pcm",
    }
    audio_format = format_map.get(ext, "wav")

    with open(audio_file_path, "rb") as f:
        audio_base64 = base64.b64encode(f.read()).decode("utf-8")

    # For non-PCM formats, we need to know the sample rate
    # Default to PCM 16kHz for our extracted audio
    sample_rate = 16000

    return transcribe_audio(audio_base64, audio_format, sample_rate)
