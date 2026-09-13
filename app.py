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
    if not url:
        return jsonify({"error": "URL missing"}), 400
    
    file_id = str(int(time.time()))
    out_template = f"{DOWNLOAD_DIR}/{file_id}.%(ext)s"
    
    cmd = [
        "yt-dlp",
        "--ffmpeg-location", FFMPEG_PATH,
        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "--referer", "https://www.bilibili.com/",
        "-f", "bestvideo+bestaudio/best",
        "--merge-output-format", "mp4",
        "--no-playlist",
        "-o", out_template,
        url
    ]
    
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=280)
        print("STDOUT:", res.stdout)
        print("STDERR:", res.stderr)
        
        matches = glob.glob(f"{DOWNLOAD_DIR}/{file_id}.*")
        valid_files = [f for f in matches if not f.endswith(".part")]
        
        if not valid_files:
            return jsonify({"error": res.stderr[-200:] if res.stderr else "Download failed"}), 500
            
        final_file = valid_files[0]
        ext = final_file.split(".")[-1]
        return jsonify({"title": "Video Ready", "download_url": f"/download-file/{file_id}/{ext}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/download-file/<file_id>/<ext>")
def download_file(file_id, ext):
    file_path = f"{DOWNLOAD_DIR}/{file_id}.{ext}"
    if not os.path.exists(file_path):
        return "File Not Found", 404
        
    @after_this_request
    def remove_file(response):
        def delete():
            time.sleep(30)
            if os.path.exists(file_path):
                try: os.remove(file_path)
                except: pass
        threading.Thread(target=delete).start()
        return response
        
    return send_file(file_path, as_attachment=True, download_name=f"bilibili_{file_id}.{ext}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
