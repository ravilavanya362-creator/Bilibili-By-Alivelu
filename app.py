import os, glob, subprocess, threading, time
import imageio_ffmpeg
from flask import Flask, request, jsonify, render_template_string, send_file, after_this_request
from flask_cors import CORS

FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()

app = Flask(__name__)
CORS(app)
DOWNLOAD_DIR = "/tmp/downloaded_files"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Bilibili Downloader</title>
  <style>
    body { background: #0d1117; color: #fff; font-family: sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
    .box { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 25px; width: 90%; max-width: 400px; text-align: center; }
    input { width: 100%; padding: 12px; margin-bottom: 15px; border-radius: 8px; border: 1px solid #30363d; background: #0d1117; color: #fff; box-sizing: border-box; font-size: 16px; }
    button { width: 100%; padding: 12px; background: #0070f3; color: #fff; border: none; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; }
    button:disabled { background: #444; }
    #status { margin-top: 15px; font-size: 13px; color: #58a6ff; word-break: break-all; white-space: pre-wrap; }
    .dl-btn { display: inline-block; margin-top: 15px; padding: 12px 20px; background: #238636; color: #fff; text-decoration: none; border-radius: 8px; font-weight: bold; }
  </style>
</head>
<body>
  <div class="box">
    <h3>Bilibili Downloader</h3>
    <input type="text" id="vurl" placeholder="Paste Bilibili link...">
    <button id="btn" onclick="downloadVid()">Download</button>
    <div id="status"></div>
    <div id="btnContainer"></div>
  </div>

  <script>
    async function downloadVid() {
      const u = document.getElementById("vurl").value.trim();
      const st = document.getElementById("status");
      const b = document.getElementById("btn");
      const cont = document.getElementById("btnContainer");

      if (!u) { alert("Please enter a link!"); return; }
      b.disabled = true;
      cont.innerHTML = "";
      st.innerText = "Processing video on server (1-2 mins)...";

      try {
        const res = await fetch("/get-video", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url: u })
        });
        const data = await res.json();
        if (res.ok && data.download_url) {
          st.innerText = "Completed!";
          cont.innerHTML = `<a class="dl-btn" href="${data.download_url}">Save Video to Phone</a>`;
        } else {
          st.innerText = "Error: " + (data.error || "Failed");
        }
      } catch (err) {
        st.innerText = "Network Error: " + err.message;
      } finally {
        b.disabled = false;
      }
    }
  </script>
</body>
</html>"""

@app.route("/")
def home():
    return render_template_string(HTML_PAGE)

@app.route("/get-video", methods=["POST"])
def get_video():
    data = request.get_json(force=True, silent=True) or {}
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    file_id = str(int(time.time()))
    out_template = f"{DOWNLOAD_DIR}/{file_id}.%(ext)s"

    cmd = [
        "yt-dlp",
        "--ffmpeg-location", FFMPEG_PATH,
        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "--referer", "https://www.bilibili.com/",
        "-f", "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "--no-playlist",
        "--no-check-certificates",
        "-o", out_template,
        url
    ]

    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=280)
        matches = glob.glob(f"{DOWNLOAD_DIR}/{file_id}.*")
        valid = [f for f in matches if not f.endswith(".part")]
        
        if not valid:
            err_output = res.stderr if res.stderr else res.stdout
            return jsonify({"error": err_output[-300:] if err_output else "Download processing failed"}), 500
        
        ext = valid[0].split(".")[-1]
        return jsonify({"download_url": f"/download-file/{file_id}/{ext}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/download-file/<file_id>/<ext>")
def download_file(file_id, ext):
    file_path = f"{DOWNLOAD_DIR}/{file_id}.{ext}"
    if not os.path.exists(file_path):
        return "File not found", 404
    @after_this_request
    def remove_file(response):
        def cleanup():
            time.sleep(30)
            try: os.remove(file_path)
            except: pass
        threading.Thread(target=cleanup).start()
        return response
    return send_file(file_path, as_attachment=True, download_name=f"bilibili_{file_id}.{ext}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
