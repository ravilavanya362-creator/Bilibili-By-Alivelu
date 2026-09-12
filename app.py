import os, glob, subprocess, threading, time
import imageio_ffmpeg
from flask import Flask, request, jsonify, render_template, send_file, after_this_request
from flask_cors import CORS

FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()

app = Flask(__name__)
CORS(app)
DOWNLOAD_DIR = "downloaded_files"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def cleanup_old_files():
    while True:
        time.sleep(300)
        now = time.time()
        for f in glob.glob(f"{DOWNLOAD_DIR}/*"):
            if os.stat(f).st_mtime < now - 600:
                try: os.remove(f)
                except: pass

threading.Thread(target=cleanup_old_files, daemon=True).start()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/get-video", methods=["POST"])
def get_video():
    data = request.json or {}
    url = data.get("url", "").strip()
    if not url: return jsonify({"error": "URL missing"}), 400
    file_id = str(int(time.time()))
    out_template = f"{DOWNLOAD_DIR}/{file_id}.%(ext)s"
    cmd = [
        "yt-dlp",
        "--ffmpeg-location", FFMPEG_PATH,
        "-f", "bv*+ba/b",
        "--merge-output-format", "mp4",
        "-o", out_template,
        url
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=240)
        if res.returncode != 0: return jsonify({"error": "Download failed"}), 500
        if not glob.glob(f"{DOWNLOAD_DIR}/{file_id}.mp4"): return jsonify({"error": "File processing error"}), 500
        return jsonify({"title": "Video Ready", "download_url": f"/download-file/{file_id}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/download-file/<file_id>")
def download_file(file_id):
    file_path = f"{DOWNLOAD_DIR}/{file_id}.mp4"
    if not os.path.exists(file_path): return "File Not Found", 404
    @after_this_request
    def remove_file(response):
        def delete():
            time.sleep(30)
            if os.path.exists(file_path): os.remove(file_path)
        threading.Thread(target=delete).start()
        return response
    return send_file(file_path, as_attachment=True, download_name=f"video_{file_id}.mp4")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
