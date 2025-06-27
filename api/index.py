import subprocess
from flask import Flask, Response, request, jsonify
import yt_dlp
import sys
import os

app = Flask(__name__)

# --- API Endpoint for Caption ---
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

# --- FINAL AND MOST ROBUST Streaming Endpoint ---
@app.route('/stream')
def stream_video_endpoint():
    tiktok_url = request.args.get('url')
    if not tiktok_url:
        return jsonify({"error": "Missing 'url' query parameter"}), 400

    try:
        # --- THE CRITICAL FIX ---
        # Find the directory where the Python executable is located.
        # In a virtual environment, scripts like yt-dlp are in the same directory.
        python_executable_dir = os.path.dirname(sys.executable)
        # Construct the full, absolute path to the yt-dlp command.
        yt_dlp_path = os.path.join(python_executable_dir, 'yt-dlp')

        # Check if the executable actually exists at that path.
        if not os.path.exists(yt_dlp_path):
            return jsonify({"error": f"yt-dlp executable not found at expected path: {yt_dlp_path}"}), 500

        # Now, use the full path in the command.
        command = [
            yt_dlp_path,
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
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500

# Root endpoint
@app.route('/')
def home():
    return "TikTok Streaming API v4 (Absolute Path) is running."
