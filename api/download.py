# api/download.py
import os
from pathlib import Path
from flask import Flask, request, send_file, abort

from yt_dlp import YoutubeDL

app = Flask(__name__)

# ========= FFMPEG PATH (ROOT MEIN ffmpeg file honi chahiye) =========
FFMPEG_PATH = str(Path(__file__).resolve().parents[1] / "ffmpeg")

if not os.path.isfile(FFMPEG_PATH):
    raise RuntimeError(f"ffmpeg binary not found at: {FFMPEG_PATH}")

# ========= TEMP FOLDER =========
TMP_DIR = "/tmp/yt_downloads"
os.makedirs(TMP_DIR, exist_ok=True)

def cleanup():
    for file in Path(TMP_DIR).glob("*"):
        try:
            if file.is_file():
                file.unlink()
        except:
            pass

def download_video(url: str, format_type: str):
    cleanup()

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "ffmpeg_location": FFMPEG_PATH,
        "outtmpl": os.path.join(TMP_DIR, "%(id)s.%(ext)s"),
    }

    if format_type == "mp3":
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

        if format_type == "mp3":
            filename = filename.rsplit(".", 1)[0] + ".mp3"

    return Path(filename)

# ========= ROUTE =========
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return "YouTube Downloader API – POST {url, type: 'mp4'|'mp3'}", 200

    try:
        data = request.get_json(force=True)
        url = data.get("url", "").strip()
        fmt = data.get("type", "mp4")

        if fmt not in ("mp4", "mp3"):
            abort(400, "type must be 'mp4' or 'mp3'")

        if not url:
            abort(400, "Missing 'url'")

        file_path = download_video(url, fmt)

        response = send_file(
            str(file_path),
            as_attachment=True,
            download_name=file_path.name,
            mimetype="video/mp4" if fmt == "mp4" else "audio/mpeg"
        )

        # Delete file after send
        @response.call_on_close
        def delete_file():
            try:
                file_path.unlink()
            except:
                pass

        return response

    except Exception as e:
        return f"Error: {str(e)}", 500
