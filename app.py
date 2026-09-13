import os, json, subprocess, time, re
import urllib.parse
import requests
from flask import Flask, request, jsonify, render_template_string, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Bilibili Video Downloader</title>
  <style>
    body { background: #0d1117; color: #fff; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
    .box { background: #161b22; border: 1px solid #30363d; border-radius: 14px; padding: 25px 20px; width: 90%; max-width: 420px; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.6); }
    h2 { margin-top: 0; margin-bottom: 20px; font-size: 1.5rem; color: #58a6ff; }
    input { width: 100%; padding: 14px; margin-bottom: 16px; border-radius: 8px; border: 1px solid #30363d; background: #0d1117; color: #fff; box-sizing: border-box; font-size: 15px; outline: none; }
    input:focus { border-color: #58a6ff; }
    button { width: 100%; padding: 13px; background: #238636; color: #fff; border: none; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; }
    button:disabled { background: #333; cursor: not-allowed; }
    #status { margin-top: 16px; font-size: 13px; color: #8b949e; word-break: break-word; }
    .dl-btn { display: inline-block; margin-top: 15px; padding: 14px 20px; background: #1f6feb; color: #fff; text-decoration: none; border-radius: 8px; font-weight: bold; width: 85%; font-size: 16px; }
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
      st.innerText = "Extracting video link...";

      try {
        const res = await fetch("/extract", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url: u })
        });
        const data = await res.json();
        if (res.ok && data.download_url) {
          st.innerText = data.title || "Video Ready!";
          resDiv.innerHTML = `<a class="dl-btn" href="${data.download_url}">⬇️ Download Video (MP4)</a>`;
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

URL_CACHE = {}

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
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=40)
        if proc.returncode != 0 or not proc.stdout.strip():
            return jsonify({"error": "Could not parse video link"}), 400

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

        key = str(int(time.time() * 1000))
        URL_CACHE[key] = {"url": target_url, "title": title}

        return jsonify({"title": title, "download_url": f"/stream/{key}"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/stream/<key>")
def stream_file(key):
    item = URL_CACHE.get(key)
    if not item:
        return "Download link expired. Please click Get Download Link again.", 404

    target_url = item["url"]
    raw_title = item.get("title", "video")
    
    # Safe ASCII filename for HTTP Header compatibility
    safe_ascii = re.sub(r'[^a-zA-Z0-9_-]', '_', raw_title)[:50].strip('_')
    if not safe_ascii:
        safe_ascii = f"bilibili_{key}"
    
    encoded_utf8 = urllib.parse.quote(raw_title)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com/"
    }

    try:
        r = requests.get(target_url, headers=headers, stream=True, timeout=30)
        def generate():
            for chunk in r.iter_content(chunk_size=1024 * 512):
                if chunk:
                    yield chunk

        resp = Response(generate(), content_type="video/mp4")
        # Uses safe ASCII filename + UTF-8 fallback for browser compatibility
        resp.headers["Content-Disposition"] = f'attachment; filename="{safe_ascii}.mp4"; filename*=UTF-8\'\'{encoded_utf8}.mp4'
        if "content-length" in r.headers:
            resp.headers["Content-Length"] = r.headers["content-length"]
        return resp
    except Exception as e:
        return f"Stream error: {str(e)}", 502

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
