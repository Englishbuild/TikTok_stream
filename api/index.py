import subprocess
from flask import Flask, Response, request, jsonify
import yt_dlp
import sys

app = Flask(__name__)

# --- API Endpoint for Caption (No changes) ---
@app.route('/info')
def get_info_endpoint():
    tiktok_url = request.args.get('url')
    if not tiktok_url:
        return jsonify({"error": "Missing 'url' query parameter"}), 400
    
    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'noplaylist': True}) as ydl:
            info = ydl.extract_info(tiktok_url, download=False)
            caption = info.get('description') or info.get('title', 'No caption found')
            return jsonify({"caption": caption})
    except Exception as e:
        return jsonify({"error": f"Could not retrieve info: {e}"}), 500

# --- FINAL, CORRECTED Streaming Endpoint ---
@app.route('/stream')
def stream_video_endpoint():
    tiktok_url = request.args.get('url')
    if not tiktok_url:
        return jsonify({"error": "Missing 'url' query parameter"}), 400

    try:
        # --- THE DEFINITIVE FIX ---
        # Instead of finding the 'yt-dlp' executable, we tell the Python
        # interpreter to run the 'yt_dlp' module directly.
        # This is the standard and most robust way to do this.
        # sys.executable ensures we use the same python that is running our app.
        command = [
            sys.executable, '-m', 'yt_dlp',
            '--format', 'best[ext=mp4]/best',
            '--output', '-',
            '--quiet',
            tiktok_url
        ]
        
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        def generate_stream():
            try:
                while True:
                    chunk = process.stdout.read(4096)
                    if not chunk:
                        break
                    yield chunk
                
                stderr_output = process.stderr.read().decode('utf-8', 'ignore')
                if stderr_output:
                    print(f"yt-dlp stderr: {stderr_output}")

            except Exception as e:
                print(f"Error during streaming generation: {e}")
            finally:
                if process.poll() is None:
                    process.terminate()
                print("Stream process finished.")

        return Response(generate_stream(), mimetype='video/mp4')

    except Exception as e:
        # This will catch any errors in starting the process itself.
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

# Root endpoint
@app.route('/')
def home():
    return "TikTok Streaming API v5 (Module Invocation) is running."
