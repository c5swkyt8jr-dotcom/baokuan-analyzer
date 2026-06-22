"""
爆款拆解机 - FastAPI Backend
Video viral analysis platform powered by StepFun AI
"""

import os
import shutil
import threading
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from config import UPLOAD_DIR, MAX_UPLOAD_SIZE
from database import (
    get_analysis, list_analyses, delete_analysis,
    get_completed_analyses, get_db
)
from analyzer import run_full_analysis
from video_processor import check_ffmpeg

app = FastAPI(
    title="爆款拆解机 API",
    description="短视频爆款分析平台 - 基于阶跃星辰 StepFun AI",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
os.makedirs(os.path.join(os.path.dirname(__file__), "static"), exist_ok=True)
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")


@app.get("/")
async def root():
    """Serve the main frontend page."""
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    return FileResponse(os.path.join(static_dir, "index.html"))


@app.get("/api/health")
async def health_check():
    """Health check with ffmpeg status."""
    return {
        "status": "ok",
        "ffmpeg_available": check_ffmpeg(),
        "version": "1.0.0",
    }


@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    """Upload a video file for analysis."""
    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    ext = file.filename.lower().split(".")[-1] if "." in file.filename else ""
    if ext not in ["mp4", "mov", "mkv"]:
        raise HTTPException(status_code=400, detail=f"不支持的视频格式: .{ext}，请上传 MP4/MOV/MKV 格式")

    # Save uploaded file
    import uuid
    import sqlite3
    from datetime import datetime
    from config import DATABASE_PATH

    safe_filename = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    # Create analysis record FIRST (before background thread, to avoid race)
    analysis_id = str(uuid.uuid4())
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute(
        "INSERT INTO analyses (id, filename, original_filename, status, created_at) VALUES (?, ?, ?, ?, ?)",
        (analysis_id, safe_filename, file.filename, "uploading", datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

    # Stream the file to disk
    total_size = 0
    try:
        with open(file_path, "wb") as f:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                total_size += len(chunk)
                if total_size > MAX_UPLOAD_SIZE:
                    f.close()
                    os.remove(file_path)
                    # Clean up DB record
                    from database import delete_analysis
                    delete_analysis(analysis_id)
                    raise HTTPException(status_code=400, detail=f"文件过大，最大支持 {MAX_UPLOAD_SIZE // (1024*1024)}MB")
                f.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        from database import delete_analysis
        delete_analysis(analysis_id)
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")

    # Update record with file size
    file_size = os.path.getsize(file_path)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("UPDATE analyses SET file_size = ? WHERE id = ?", (file_size, analysis_id))
    conn.commit()
    conn.close()

    # Start analysis in background (DB record already exists, no race condition)
    def analyze_task():
        try:
            run_full_analysis(file_path, file.filename, analysis_id)
        except Exception as e:
            print(f"Analysis error: {e}")

    thread = threading.Thread(target=analyze_task, daemon=True)
    thread.start()

    return JSONResponse({
        "analysis_id": analysis_id,
        "filename": file.filename,
        "status": "uploading",
    })


@app.get("/api/analysis/{analysis_id}")
async def get_analysis_result(analysis_id: str):
    """Get analysis result by ID."""
    result = get_analysis(analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="分析记录不存在")
    return JSONResponse(result)


@app.get("/api/analysis/{analysis_id}/poll")
async def poll_analysis_status(analysis_id: str):
    """Lightweight polling endpoint for analysis status."""
    result = get_analysis(analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="分析记录不存在")
    return JSONResponse({
        "status": result.get("status"),
        "overall_score": result.get("overall_score"),
        "error_message": result.get("error_message"),
    })


@app.get("/api/history")
async def get_history(limit: int = Query(default=50, le=100), offset: int = Query(default=0, ge=0)):
    """Get analysis history list."""
    analyses = list_analyses(limit=limit, offset=offset)
    return JSONResponse({"total": len(analyses), "items": analyses})


@app.delete("/api/analysis/{analysis_id}")
async def delete_analysis_record(analysis_id: str):
    """Delete an analysis record and its files."""
    result = get_analysis(analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="分析记录不存在")

    # Clean up uploaded files
    video_path = os.path.join(UPLOAD_DIR, result.get("filename", ""))
    if os.path.exists(video_path):
        os.remove(video_path)

    delete_analysis(analysis_id)
    return JSONResponse({"success": True})


@app.get("/api/compare")
async def compare_analyses(ids: str = Query(description="Comma-separated analysis IDs")):
    """Compare multiple analyses."""
    id_list = [i.strip() for i in ids.split(",") if i.strip()]
    if len(id_list) < 2:
        raise HTTPException(status_code=400, detail="至少需要2个分析ID进行对比")
    if len(id_list) > 5:
        raise HTTPException(status_code=400, detail="最多支持5个视频同时对比")

    results = []
    for aid in id_list:
        analysis = get_analysis(aid)
        if analysis:
            results.append({
                "id": analysis["id"],
                "filename": analysis["original_filename"],
                "overall_score": analysis["overall_score"],
                "opening_hook_score": analysis["opening_hook_score"],
                "script_structure_score": analysis["script_structure_score"],
                "emotional_curve_score": analysis["emotional_curve_score"],
                "interaction_guide_score": analysis["interaction_guide_score"],
                "data_prediction_score": analysis["data_prediction_score"],
                "content_formula_score": analysis["content_formula_score"],
                "viral_style": analysis["viral_style"],
                "summary": analysis["summary"],
                "result_json": analysis.get("result_json"),
            })

    return JSONResponse({"videos": results})


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
