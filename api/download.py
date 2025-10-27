# api/download.py
import os
import json
import shutil
from flask import Flask, request, send_file, abort
from yt_dlp import YoutubeDL
from pathlib import Path

app = Flask(__name__)

# ---- ffmpeg location -------------------------------------------------
FFMPEG_PATH = str(Path(__file__).resolve().parents[1] / "ffmpeg")
if not os.path.isfile(FFMPEG_PATH):
    raise RuntimeError(f"ffmpeg binary missing at {FFMPEG_PATH}")
# ---------------------------------------------------------------------

TMP = "/tmp/yt_downloader"
os.makedirs(TMP, exist_ok=True)

def cleanup():
    for f in Path(TMP).glob("*"):
        try:
            if f.is_file(): f.unlink()
        except: pass

def download_yt(url: str, out_type: str):
    cleanup()

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "ffmpeg_location": FFMPEG_PATH,
        "outtmpl": os.path.join(TMP, "%(id)s.%(ext)s"),
    }

    if out_type == "mp3":
        ydl_opts.update({
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        })
    else:  # mp4
        ydl_opts.update({
            "format": "bestvideo+bestaudio/best",
            "merge_output_format": "mp4",
        })

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        if out_type == "mp3":
            filename = filename.rsplit(".", 1)[0] + ".mp3"
    return Path(filename)

@app.route("/", methods=["POST"])
def download():
    try:
        data = request.get_json(force=True)
        url = data.get("url", "").strip()
        out_type = data.get("type", "mp4")
        if out_type not in ("mp4", "mp3"):
            abort(400, "type must be mp4 or mp3")
        if not url:
            abort(400, "url missing")

        file_path = download_yt(url, out_type)

        response = send_file(
            str(file_path),
            as_attachment=True,
            download_name=file_path.name,
            mimetype="video/mp4" if out_type == "mp4" else "audio/mpeg"
        )

        @response.call_on_close
        def _cleanup():
            try: file_path.unlink()
            except: pass

        return response

    except Exception as e:
        return str(e), 500
