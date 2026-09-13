import os, json, subprocess, requests
from flask import Flask, request, jsonify, render_template_string, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width="device-width", initial-scale=1.0">
  <title>Bilibili Ultra Downloader</title>
  <style>
    body { background: #0d1117; color: #fff; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
    .box { background: #161b22; border: 1px solid #30363d; border-radius: 14px; padding: 30px 20px; width: 90%; max-width: 420px; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.6); }
    h2 { margin-top: 0; margin-bottom: 20px; font-size: 1.5rem; color: #58a6ff; }
    input { width: 100%; padding: 14px; margin-bottom: 16px; border-radius: 8px; border: 1px solid #30363d; background: #0d1117; color: #fff; box-sizing: border-box; font-size: 15px; outline: none; }
    input:focus { border-color: #58a6ff; }
    button { width: 100%; padding: 13px; background: #238636; color: #fff; border: none; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; transition: 0.2s; }
    button:hover { background: #2ea043; }
    button:disabled { background: #333; cursor: not-allowed; }
    #status { margin-top: 16px; font-size: 14px; color: #8b949e; word-break: break-word; }
    .dl-btn { display: inline-block; margin-top: 15px; padding: 13px 25px; background: #1f6feb; color: #fff; text-decoration: none; border-radius: 8px; font-weight: bold; width: 85%; }
  </style>
</head>
<body>
  <div class="box">
    <h2>Bilibili Downloader</h2>
    <input type="text" id="vurl" placeholder="Paste Bilibili link here...">
    <button id="btn" onclick="fetchDirectLink()">Get Download Link</button>
    <div id="status"></div>
    <div id="result"></div>
  </div>

  <script>
    async function fetchDirectLink() {
      const u = document.getElementById("vurl").value.trim();
      const st = document.getElementById("status");
      const b = document.getElementById("btn");
      const resDiv = document.getElementById("result");

      if (!u) { alert("Paste a valid link!"); return; }
      b.disabled = true;
      resDiv.innerHTML = "";
      st.innerText = "Extracting direct media streams...";

      try {
        const res = await fetch("/extract", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url: u })
        });
        const data = await res.json();
        if (res.ok && data.stream_url) {
          st.innerText = data.title || "Video Ready!";
          resDiv.innerHTML = `<a class="dl-btn" href="${data.stream_url}" target="_blank">⬇️ Download Video (MP4)</a>`;
        } else {
          st.innerText = "Error: " + (data.error || "Failed to fetch video");
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

@app.route("/extract", methods=["POST"])
def extract():
    data = request.get_json(force=True, silent=True) or {}
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    cmd = [
        "yt-dlp",
        "-j",
        "--no-playlist",
        "--no-check-certificates",
        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "--referer", "https://www.bilibili.com/",
        url
    ]

    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
        if proc.returncode != 0 or not proc.stdout.strip():
            return jsonify({"error": "Video link could not be parsed"}), 400

        info = json.loads(proc.stdout)
        title = info.get("title", "Bilibili_Video")
        
        target_url = None
        formats = info.get("formats", [])
        for f in reversed(formats):
            if f.get("vcodec") != "none" and f.get("acodec") != "none" and f.get("url"):
                target_url = f.get("url")
                break
                
        if not target_url and info.get("url"):
            target_url = info.get("url")

        if not target_url and formats:
            for f in reversed(formats):
                if f.get("url"):
                    target_url = f.get("url")
                    break

        if not target_url:
            return jsonify({"error": "Direct stream link not found"}), 404

        proxy_url = f"/stream?video_url={requests.utils.quote(target_url)}&title={requests.utils.quote(title)}"
        return jsonify({"title": title, "stream_url": proxy_url})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/stream")
def stream():
    vurl = request.args.get("video_url")
    title = request.args.get("title", "video")
    if not vurl:
        return "Missing URL", 400

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com/"
    }

    req = requests.get(vurl, headers=headers, stream=True)
    def generate():
        for chunk in req.iter_content(chunk_size=1024 * 1024):
            if chunk:
                yield chunk

    response = Response(generate(), content_type=req.headers.get("content-type", "video/mp4"))
    response.headers["Content-Disposition"] = f"attachment; filename={title}.mp4"
    return response

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
