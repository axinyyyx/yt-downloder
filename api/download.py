# api/download.py  (पूरा कोड – कॉपी-पेस्ट करो)

import os
from pathlib import Path
from flask import Flask, request, send_file, abort
from yt_dlp import YoutubeDL

app = Flask(__name__)

# FFMPEG PATH – root में ffmpeg file होनी चाहिए
FFMPEG_PATH = str(Path(__file__).resolve().parents[1] / "ffmpeg")

if not os.path.isfile(FFMPEG_PATH):
    raise RuntimeError(f"ffmpeg not found at {FFMPEG_PATH} – add ffmpeg binary in root!")

TMP_DIR = "/tmp/yt_downloads"
os.makedirs(TMP_DIR, exist_ok=True)

def cleanup():
    for f in Path(TMP_DIR).glob("*"):
        try: f.unlink()
        except: pass

def download_yt(url: str, fmt: str):
    cleanup()
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "ffmpeg_location": FFMPEG_PATH,
        "outtmpl": os.path.join(TMP_DIR, "%(id)s.%(ext)s"),
    }
    if fmt == "mp3":
        ydl_opts.update({
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        })
    else:
        ydl_opts.update({
            "format": "bestvideo+bestaudio/best",
            "merge_output_format": "mp4",
        })

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        fname = ydl.prepare_filename(info)
        if fmt == "mp3":
            fname = fname.rsplit(".", 1)[0] + ".mp3"
    return Path(fname)

@app.route("/", methods=["GET", "POST"])
def main():
    if request.method == "GET":
        return "POST {url, type: 'mp4'|'mp3'} to /api/download", 200

    try:
        data = request.get_json(force=True)
        url = data.get("url", "").strip()
        typ = data.get("type", "mp4")
        if typ not in ("mp4", "mp3"):
            abort(400, "type must be mp4 or mp3")
        if not url:
            abort(400, "url required")

        file_path = download_yt(url, typ)

        resp = send_file(
            str(file_path),
            as_attachment=True,
            download_name=file_path.name,
            mimetype="video/mp4" if typ == "mp4" else "audio/mpeg"
        )
        @resp.call_on_close
        def _(): 
            try: file_path.unlink()
            except: pass
        return resp
    except Exception as e:
        return f"Error: {str(e)}", 500
