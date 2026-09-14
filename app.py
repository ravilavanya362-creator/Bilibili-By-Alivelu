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
  
        #legalModal {
            display: none;
            position: fixed;
            top: 0; left: 0; width: 100vw; height: 100vh;
            background: rgba(15, 23, 42, 0.75);
            backdrop-filter: blur(6px);
            z-index: 999999;
            align-items: center;
            justify-content: center;
            padding: 16px;
            box-sizing: border-box;
        }
        .legal-modal-card {
            background: #ffffff;
            width: 100%;
            max-width: 580px;
            max-height: 82vh;
            border-radius: 20px;
            box-shadow: 0 25px 50px rgba(0,0,0,0.35);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        .legal-modal-header {
            padding: 16px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #e2e8f0;
            background: #f8fafc;
        }
        .legal-modal-header h3 {
            margin: 0; font-size: 17px; font-weight: 800; color: #0f172a;
        }
        .legal-modal-close {
            background: #e2e8f0; border: none; width: 32px; height: 32px;
            border-radius: 50%; font-size: 20px; color: #334155; cursor: pointer;
            display: flex; align-items: center; justify-content: center;
        }
        .legal-modal-body {
            padding: 20px; overflow-y: auto; font-size: 14px;
            line-height: 1.7; color: #475569; text-align: left;
        }
        .legal-modal-body h4 {
            color: #0f172a; font-size: 15px; margin: 12px 0 4px;
        }
        .footer-nav-btns {
            display: flex; flex-wrap: wrap; gap: 14px 22px; justify-content: center; margin-bottom: 16px;
        }
        .legal-btn {
            background: none; border: none; padding: 0; color: #94a3b8;
            font-size: 13.5px; font-weight: 600; cursor: pointer; text-decoration: none; font-family: inherit;
        }
        .legal-btn:hover { color: #ffffff; text-decoration: underline; }

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
          resDiv.innerHTML = `<a class="dl-btn" href="${data.download_url}">⚡ High-Speed Download (MP4)</a>`;
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




<div id="legalModal" style="display:none;position:fixed;top:0;left:0;width:100vw;height:100vh;background:rgba(15,23,42,0.75);backdrop-filter:blur(6px);z-index:9999999;align-items:center;justify-content:center;padding:16px;box-sizing:border-box;" onclick="if(event.target === this) closeLegal()">
    <div style="background:#ffffff;width:100%;max-width:580px;max-height:82vh;border-radius:20px;box-shadow:0 25px 50px rgba(0,0,0,0.35);display:flex;flex-direction:column;overflow:hidden;border:1px solid #e2e8f0;">
        <div style="padding:16px 20px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #e2e8f0;background:#f8fafc;">
            <h3 id="modalTitle" style="margin:0;font-size:17px;font-weight:800;color:#0f172a;">Information</h3>
            <button type="button" onclick="closeLegal()" style="background:#e2e8f0;border:none;width:32px;height:32px;border-radius:50%;font-size:18px;color:#334155;cursor:pointer;display:flex;align-items:center;justify-content:center;font-weight:700;">&times;</button>
        </div>
        <div id="modalContent" style="padding:20px;overflow-y:auto;font-size:14px;line-height:1.7;color:#475569;text-align:left;"></div>
    </div>
</div>

<script>
var legalData = {
    about: {
        title: "About BiliSave",
        content: "<h4 style='color:#0f172a;margin-top:0;'>Welcome to BiliSave</h4><p>BiliSave is an ultrafast web utility developed by <strong>Dharshan Studio</strong>. It empowers students, researchers, animators, and digital creators to effortlessly archive public Bilibili videos and audio streams up to 1080p without quality degradation or adware.</p>"
    },
    contact: {
        title: "Contact Support",
        content: "<h4 style='color:#0f172a;margin-top:0;'>Dharshan Studio Support</h4><p>We are here to assist with any technical issues, feedback, or integration questions.</p><p><strong>Official Email:</strong> <a href='mailto:pavanibevara045@gmail.com' style='color:#0284c7;font-weight:bold;'>pavanibevara045@gmail.com</a></p><p>You can also reach out via our Instagram or Threads social channels above.</p>"
    },
    privacy: {
        title: "Privacy Policy",
        content: "<h4 style='color:#0f172a;margin-top:0;'>Privacy & Data Protection</h4><p>1. <strong>No Personal Logs:</strong> We do not require account registration or store personal user records.</p><p>2. <strong>Direct Proxy Delivery:</strong> Video requests are processed dynamically in real-time memory buffer pipelines and never stored permanently on our disks.</p><p>3. <strong>Zero Cookies:</strong> We do not track your cross-site browsing activity or sell data to third parties.</p>"
    },
    terms: {
        title: "Terms of Service",
        content: "<h4 style='color:#0f172a;margin-top:0;'>Service Terms</h4><p>By using BiliSave, you agree that:</p><p>1. The tool is solely for personal, non-commercial offline study, educational review, and archiving.</p><p>2. Users remain responsible for adhering to applicable copyright laws and intellectual property rights.</p>"
    },
    dmca: {
        title: "DMCA & Copyright Policy",
        content: "<h4 style='color:#0f172a;margin-top:0;'>DMCA Notice</h4><p>BiliSave operates with strict adherence to copyright laws and does not host or republish video content. All streams are routed directly from third-party public CDNs.</p><p>If you are a copyright owner wishing to request a domain block or exclusion for specific URLs, email our designated agent at: <a href='mailto:pavanibevara045@gmail.com' style='color:#0284c7;font-weight:bold;'>pavanibevara045@gmail.com</a>. Inquiries are handled within 24-48 business hours.</p>"
    },
    disclaimer: {
        title: "Disclaimer",
        content: "<h4 style='color:#0f172a;margin-top:0;'>Service Disclaimer</h4><p><strong>BiliSave is an independent tool and is NOT affiliated with or endorsed by Bilibili Inc.</strong> All trademarks, logos, and brand names are properties of their respective owners.</p>"
    }
};

function openLegal(key) {
    var data = legalData[key];
    if (data) {
        document.getElementById('modalTitle').innerText = data.title;
        document.getElementById('modalContent').innerHTML = data.content;
        document.getElementById('legalModal').style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }
}

function closeLegal() {
    document.getElementById('legalModal').style.display = 'none';
    document.body.style.overflow = 'auto';
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
            return jsonify({"error": "Direct media link not found"}), 404

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
    
    safe_ascii = re.sub(r'[^a-zA-Z0-9_-]', '_', raw_title)[:50].strip('_')
    if not safe_ascii:
        safe_ascii = f"bilibili_{key}"
    
    encoded_utf8 = urllib.parse.quote(raw_title)

    upstream_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com/"
    }

    range_header = request.headers.get("Range")
    if range_header:
        upstream_headers["Range"] = range_header

    try:
        session = requests.Session()
        r = session.get(target_url, headers=upstream_headers, stream=True, timeout=30)

        # 4MB High-Speed buffer chunking
        def generate():
            for chunk in r.iter_content(chunk_size=1024 * 1024 * 4):
                if chunk:
                    yield chunk

        resp = Response(generate(), status=r.status_code, content_type="video/mp4")
        resp.headers["Content-Disposition"] = f'attachment; filename="{safe_ascii}.mp4"; filename*=UTF-8\'\'{encoded_utf8}.mp4'
        resp.headers["Accept-Ranges"] = "bytes"

        if "content-length" in r.headers:
            resp.headers["Content-Length"] = r.headers["content-length"]
        if "content-range" in r.headers:
            resp.headers["Content-Range"] = r.headers["content-range"]

        return resp
    except Exception as e:
        return f"Stream error: {str(e)}", 502

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
