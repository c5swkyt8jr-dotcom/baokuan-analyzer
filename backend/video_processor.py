"""
Video processing utilities using ffmpeg.
- Extract audio as PCM 16kHz mono for ASR
- Extract keyframes for fallback analysis
- Get video metadata (duration, size)
- Split large videos into segments
"""

import os
import subprocess
import tempfile
import json
from pathlib import Path
from config import UPLOAD_DIR

# ffmpeg/ffprobe 可执行文件路径
_FFMPEG_DIR = Path(os.path.expanduser("~/.ffmpeg"))
_FFMPEG_CANDIDATES = list(_FFMPEG_DIR.glob("*/bin/ffmpeg.exe"))
if _FFMPEG_CANDIDATES:
    _FFMPEG_BIN = str(_FFMPEG_CANDIDATES[0])
    _FFPROBE_BIN = str(Path(_FFMPEG_BIN).with_name("ffprobe.exe"))
else:
    _FFMPEG_BIN = "ffmpeg"
    _FFPROBE_BIN = "ffprobe"

print(f"[video_processor] ffmpeg path: {_FFMPEG_BIN}")
print(f"[video_processor] ffprobe path: {_FFPROBE_BIN}")


def _to_win_path(path: str) -> str:
    """Convert any path to Windows-native format for ffmpeg.exe compatibility."""
    return str(Path(path).resolve())


def get_video_info(file_path: str) -> dict:
    """Get video metadata using ffprobe."""
    try:
        win_path = _to_win_path(file_path)
        cmd = [
            _FFPROBE_BIN, "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", win_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            info = json.loads(result.stdout)
            duration = float(info.get("format", {}).get("duration", 0))
            size = int(info.get("format", {}).get("size", 0))
            return {
                "duration": duration,
                "size_bytes": size,
                "size_mb": round(size / (1024 * 1024), 1),
                "duration_formatted": f"{int(duration // 60)}:{int(duration % 60):02d}",
            }
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
        pass

    # Fallback: just get file size
    return {
        "duration": 0,
        "size_bytes": os.path.getsize(file_path),
        "size_mb": round(os.path.getsize(file_path) / (1024 * 1024), 1),
        "duration_formatted": "未知",
    }


def extract_audio_pcm(file_path: str, output_path: str = None) -> str:
    """
    Extract audio from video as PCM 16kHz 16-bit mono (required format for ASR).
    Returns the path to the extracted audio file.
    """
    if output_path is None:
        output_path = os.path.join(
            UPLOAD_DIR,
            f"audio_{os.path.basename(file_path)}.pcm"
        )

    win_path = _to_win_path(file_path)
    cmd = [
        _FFMPEG_BIN, "-y", "-i", win_path,
        "-vn",                    # No video
        "-acodec", "pcm_s16le",   # PCM 16-bit signed little-endian
        "-ar", "16000",           # 16kHz sample rate
        "-ac", "1",               # Mono
        "-f", "s16le",            # Raw PCM format
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        raise Exception(f"音频提取失败: {result.stderr}")

    return output_path


def extract_audio_wav(file_path: str, output_path: str = None) -> str:
    """
    Extract audio from video as WAV 16kHz mono.
    Used as alternative format for ASR.
    """
    if output_path is None:
        output_path = os.path.join(
            UPLOAD_DIR,
            f"audio_{os.path.basename(file_path)}.wav"
        )

    win_path = _to_win_path(file_path)
    cmd = [
        _FFMPEG_BIN, "-y", "-i", win_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        raise Exception(f"音频提取失败: {result.stderr}")

    return output_path


def extract_keyframes(file_path: str, output_dir: str = None, frame_interval: float = 2.0, max_frames: int = 30) -> list[str]:
    """
    Extract keyframes from video at regular intervals.
    Returns list of paths to extracted frame images.
    """
    if output_dir is None:
        output_dir = os.path.join(UPLOAD_DIR, f"frames_{os.path.basename(file_path)}")
        os.makedirs(output_dir, exist_ok=True)

    # Get video duration first
    info = get_video_info(file_path)
    duration = info.get("duration", 60)

    # Calculate interval to get approximately max_frames
    if duration > 0:
        actual_interval = max(frame_interval, duration / max_frames)
    else:
        actual_interval = frame_interval

    output_pattern = os.path.join(output_dir, "frame_%03d.jpg")

    win_path = _to_win_path(file_path)
    cmd = [
        _FFMPEG_BIN, "-y", "-i", win_path,
        "-vf", f"fps=1/{actual_interval},scale=640:-1",
        "-q:v", "5",  # Good quality JPEG
        output_pattern
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        raise Exception(f"关键帧提取失败: {result.stderr}")

    # Collect frame paths
    frames = sorted([
        os.path.join(output_dir, f)
        for f in os.listdir(output_dir)
        if f.endswith(".jpg")
    ])[:max_frames]

    return frames


def split_video(file_path: str, segment_time: int = 120, output_dir: str = None) -> list[str]:
    """
    Split a large video into segments of specified duration.
    Returns list of segment file paths.
    """
    if output_dir is None:
        output_dir = os.path.join(UPLOAD_DIR, f"segments_{os.path.basename(file_path)}")
        os.makedirs(output_dir, exist_ok=True)

    output_pattern = os.path.join(output_dir, "segment_%d.mp4")

    win_path = _to_win_path(file_path)
    cmd = [
        _FFMPEG_BIN, "-y", "-i", win_path,
        "-c", "copy",  # Copy codec (fast, no re-encoding)
        "-f", "segment",
        "-segment_time", str(segment_time),
        "-reset_timestamps", "1",
        output_pattern
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

    if result.returncode != 0:
        raise Exception(f"视频分割失败: {result.stderr}")

    segments = sorted([
        os.path.join(output_dir, f)
        for f in os.listdir(output_dir)
        if f.endswith(".mp4")
    ])

    return segments


def check_ffmpeg() -> bool:
    """Check if ffmpeg is available."""
    try:
        subprocess.run([_FFMPEG_BIN, "-version"], capture_output=True, timeout=5)
        return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
