"""
Analysis Engine - Orchestrates the full video analysis pipeline.
Coordinates audio transcription, visual analysis, and result merging.
"""

import os
import time
import uuid
from config import UPLOAD_DIR, MAX_VIDEO_SIZE_MB, MAX_VIDEO_DURATION_MINUTES
from database import (
    save_analysis, update_analysis_result, update_analysis_error,
    update_analysis_status, update_video_stepfile, get_analysis
)
from video_processor import (
    get_video_info, extract_audio_wav, extract_keyframes,
    split_video, check_ffmpeg
)
from stepfun_api import (
    upload_file_to_stepfun, analyze_video_visual,
    analyze_video_frames, analyze_video_base64,
    transcribe_audio_file
)


def run_full_analysis(file_path: str, original_filename: str, analysis_id: str = None, api_key: str = None) -> dict:
    """
    Run the complete video analysis pipeline.
    1. Extract audio → Transcribe via ASR
    2. Upload video to StepFun → Visual analysis via step-3.7-flash
    3. Merge results → Structured report
    """
    if analysis_id is None:
        analysis_id = str(uuid.uuid4())
    
    start_time = time.time()

    # ffmpeg is recommended but not strictly required
    has_ffmpeg = check_ffmpeg()

    # Get video info (safely handle missing ffmpeg)
    try:
        video_info = get_video_info(file_path)
    except Exception:
        video_info = {"duration": 0, "size_bytes": os.path.getsize(file_path)}
    file_size = video_info["size_bytes"]
    duration = video_info["duration"]

    # Check if record already exists (created by main.py upload handler)
    existing = get_analysis(analysis_id)
    if existing:
        # Update the existing record with additional info
        import sqlite3
        from config import DATABASE_PATH
        conn = sqlite3.connect(DATABASE_PATH)
        conn.execute(
            "UPDATE analyses SET file_size = ?, duration_seconds = ?, status = ? WHERE id = ?",
            (file_size, duration, "processing", analysis_id)
        )
        conn.commit()
        conn.close()
    else:
        # Create record ourselves (legacy path)
        save_analysis(
            analysis_id=analysis_id,
            filename=os.path.basename(file_path),
            original_filename=original_filename,
            file_size=file_size,
            duration_seconds=duration,
        )

    try:
        # Step 1: Extract audio and transcribe (only if ffmpeg available)
        transcript_text = ""
        if has_ffmpeg:
            update_analysis_status(analysis_id, "transcribing")
            try:
                audio_path = extract_audio_wav(file_path)
                transcript_text = transcribe_audio_file(audio_path, api_key)
                # Clean up audio file
                if os.path.exists(audio_path):
                    os.remove(audio_path)
            except Exception as e:
                print(f"语音识别警告（将继续分析）: {e}")
                transcript_text = ""
        
        if not transcript_text:
            transcript_text = "（未启用语音识别，基于画面分析）"

        # Step 2: Visual analysis
        update_analysis_status(analysis_id, "analyzing_visual")

        video_size_mb = file_size / (1024 * 1024)

        if video_size_mb <= MAX_VIDEO_SIZE_MB and (duration <= MAX_VIDEO_DURATION_MINUTES * 60 or duration == 0):
            # Direct video upload — try stepfile first, then base64, then frames
            try:
                stepfile_url = upload_file_to_stepfun(file_path, api_key)
                update_video_stepfile(analysis_id, stepfile_url)
                result = analyze_video_visual(stepfile_url, transcript_text, api_key)
                if result.get("error"):
                    raise ValueError(f"Stepfile分析返回错误: {result.get('summary')}")
            except Exception as e1:
                print(f"Stepfile方式失败, 尝试base64方式: {e1}")
                try:
                    result = analyze_video_base64(file_path, transcript_text, api_key)
                    if result.get("error"):
                        raise ValueError(f"Base64分析返回错误: {result.get('summary')}")
                except Exception as e2:
                    print(f"Base64方式也失败, 切换到关键帧模式: {e2}")
                    frames = extract_keyframes(file_path)
                    result = analyze_video_frames(frames, transcript_text, api_key)
        else:
            # Video too large - use frame extraction approach
            frames = extract_keyframes(file_path)
            result = analyze_video_frames(frames, transcript_text, api_key)

        # Step 3: Parse and structure results
        update_analysis_status(analysis_id, "structuring")

        if result.get("error"):
            error_msg = result.get("summary", "分析过程出错")
            update_analysis_error(analysis_id, error_msg)
            return {"analysis_id": analysis_id, "status": "error", "error": error_msg}

        # Extract scores
        def get_dimension(data: dict, key: str, default: dict = None) -> dict:
            if default is None:
                default = {"score": 0, "level": "未知", "analysis": "未获取到分析"}
            return data.get(key, default)

        oh = get_dimension(result, "opening_hook")
        ss = get_dimension(result, "script_structure")
        ec = get_dimension(result, "emotional_curve")
        ig = get_dimension(result, "interaction_guide")
        dp = get_dimension(result, "data_prediction")
        cf = get_dimension(result, "content_formula")

        overall_score = result.get("overall_score", 0)

        processing_time = round(time.time() - start_time, 1)

        # Save results to database
        update_analysis_result(
            analysis_id=analysis_id,
            overall_score=overall_score,
            opening_hook_score=oh.get("score", 0),
            script_structure_score=ss.get("score", 0),
            emotional_curve_score=ec.get("score", 0),
            interaction_guide_score=ig.get("score", 0),
            data_prediction_score=dp.get("score", 0),
            content_formula_score=cf.get("score", 0),
            result_json=result,
            transcript_text=transcript_text,
            viral_style=result.get("viral_style", "未分类"),
            summary=result.get("summary", ""),
            processing_time=processing_time,
        )

        return {
            "analysis_id": analysis_id,
            "status": "completed",
            "overall_score": overall_score,
            "viral_style": result.get("viral_style", ""),
            "summary": result.get("summary", ""),
            "dimensions": {
                "opening_hook": oh,
                "script_structure": ss,
                "emotional_curve": ec,
                "interaction_guide": ig,
                "data_prediction": dp,
                "content_formula": cf,
            },
            "transcript": transcript_text,
            "result_json": result,
            "video_info": video_info,
            "processing_time": processing_time,
        }

    except Exception as e:
        update_analysis_error(analysis_id, str(e))
        return {"analysis_id": analysis_id, "status": "error", "error": str(e)}
