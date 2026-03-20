from flask import Flask, request, jsonify, send_file, send_from_directory, Response
from flask_cors import CORS
import yt_dlp
import os, uuid, threading, time, subprocess

app = Flask(__name__, static_folder='frontend', static_url_path='')
CORS(app, resources={r"/*": {"origins": "*"}})

BASE         = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE, 'downloads')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

download_progress = {}

def keep_alive():
    """Ping self every 10 mins to prevent sleep"""
    import urllib.request
    time.sleep(60)
    while True:
        try:
            url = os.environ.get('RAILWAY_STATIC_URL') or os.environ.get('RENDER_EXTERNAL_URL', '')
            if url:
                urllib.request.urlopen(f'https://{url}/api/health', timeout=10)
        except: pass
        time.sleep(600)

threading.Thread(target=keep_alive, daemon=True).start()



def cleanup_file(path, delay=600):
    def _del():
        time.sleep(delay)
        try:
            if os.path.exists(path): os.remove(path)
        except: pass
    threading.Thread(target=_del, daemon=True).start()

def has_ffmpeg():
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=5)
        return True
    except: return False

@app.route('/')
def index():
    return send_from_directory('frontend', 'index.html')

@app.route('/<path:path>')
def catch_all(path):
    if path.startswith('api/'):
        return jsonify({'error': 'Not found'}), 404
    fp = os.path.join(BASE, 'frontend', path)
    if os.path.isfile(fp):
        return send_from_directory('frontend', path)
    return send_from_directory('frontend', 'index.html')

@app.route('/api/download', methods=['POST'])
def download_reel():
    data = request.get_json()
    url  = (data or {}).get('url', '').strip()
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
    if 'instagram.com' not in url and 'instagr.am' not in url:
        return jsonify({'error': 'Invalid Instagram URL'}), 400

    job_id = str(uuid.uuid4())
    download_progress[job_id] = {'status': 'starting', 'percent': 0}

    def do_download():
        try:
            out = os.path.join(DOWNLOAD_DIR, f'{job_id}.mp4')

            def hook(d):
                if d['status'] == 'downloading':
                    raw = d.get('_percent_str', '0%').strip().replace('%', '')
                    try:
                        download_progress[job_id] = {
                            'status': 'downloading', 'percent': float(raw)
                        }
                    except: pass
                elif d['status'] == 'finished':
                    download_progress[job_id] = {'status': 'processing', 'percent': 95}

            fmt = ('bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best'
                   if has_ffmpeg() else 'best[ext=mp4]/best')

            with yt_dlp.YoutubeDL({
                'outtmpl': out, 'format': fmt,
                'merge_output_format': 'mp4',
                'progress_hooks': [hook],
                'quiet': True, 'no_warnings': True,
            }) as ydl:
                ydl.download([url])

            actual = out
            for f in os.listdir(DOWNLOAD_DIR):
                if f.startswith(job_id):
                    actual = os.path.join(DOWNLOAD_DIR, f); break

            download_progress[job_id] = {
                'status': 'done', 'percent': 100, 'file_id': job_id
            }
            cleanup_file(actual, delay=600)

        except Exception as e:
            download_progress[job_id] = {'status': 'error', 'error': str(e)}

    threading.Thread(target=do_download, daemon=True).start()
    return jsonify({'job_id': job_id})

@app.route('/api/progress/<job_id>')
def get_progress(job_id):
    return jsonify(download_progress.get(job_id, {'status': 'not_found'}))

@app.route('/api/video/<job_id>')
def serve_video(job_id):
    job_id   = os.path.basename(job_id)
    filepath = None
    for f in os.listdir(DOWNLOAD_DIR):
        if f.startswith(job_id):
            filepath = os.path.join(DOWNLOAD_DIR, f); break
    if not filepath or not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404

    size = os.path.getsize(filepath)
    rng  = request.headers.get('Range')
    if rng:
        parts  = rng.replace('bytes=', '').split('-')
        start  = int(parts[0])
        end    = int(parts[1]) if parts[1] else size - 1
        length = end - start + 1
        with open(filepath, 'rb') as fh:
            fh.seek(start); data = fh.read(length)
        rv = Response(data, 206, mimetype='video/mp4')
        rv.headers['Content-Range']  = f'bytes {start}-{end}/{size}'
        rv.headers['Accept-Ranges']  = 'bytes'
        rv.headers['Content-Length'] = str(length)
        rv.headers['Access-Control-Allow-Origin'] = '*'
        return rv
    return send_file(filepath, mimetype='video/mp4', conditional=True)

@app.route('/api/convert', methods=['POST'])
def convert_to_mp4():
    if 'video' not in request.files:
        return jsonify({'error': 'No video file'}), 400
    job_id  = str(uuid.uuid4())
    webm_in = os.path.join(DOWNLOAD_DIR, f'{job_id}_in.webm')
    mp4_out = os.path.join(DOWNLOAD_DIR, f'{job_id}_out.mp4')
    request.files['video'].save(webm_in)
    try:
        r = subprocess.run([
            'ffmpeg', '-y', '-i', webm_in,
            '-c:v', 'libx264', '-preset', 'fast',
            '-crf', '18', '-c:a', 'aac',
            '-movflags', '+faststart', mp4_out
        ], capture_output=True, timeout=300)
        if r.returncode != 0:
            raise Exception(r.stderr.decode())
        cleanup_file(webm_in, delay=10)
        cleanup_file(mp4_out, delay=120)
        return send_file(mp4_out, mimetype='video/mp4',
                         as_attachment=True, download_name='reel_1080x1920.mp4')
    except Exception as e:
        if os.path.exists(webm_in): os.remove(webm_in)
        return jsonify({'error': str(e)}), 500

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'ffmpeg': has_ffmpeg()})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"\n🎬  ReelForge on port {port}\n")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
