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
        return jsonify({"error": f"Could not retrieve info: {str(e)}"}), 500

# --- Streaming Endpoint (No changes) ---
@app.route('/stream')
def stream_video_endpoint():
    tiktok_url = request.args.get('url')
    if not tiktok_url:
        return jsonify({"error": "Missing 'url' query parameter"}), 400

    try:
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
            finally:
                if process.poll() is None:
                    process.terminate()
                print("Stream process finished.")

        return Response(generate_stream(), mimetype='video/mp4')

    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

# --- UPDATED API Endpoint for SRT Subtitles with Cookie Support ---
@app.route('/srt')
def get_srt_endpoint():
    tiktok_url = request.args.get('url')
    cookie_string = request.args.get('cookie') # New: Get cookie from query params
    lang = request.args.get('lang', 'en')

    if not tiktok_url:
        return jsonify({"error": "Missing 'url' query parameter"}), 400

    try:
        # Base command for getting subtitles
        command = [
            sys.executable, '-m', 'yt_dlp',
            '--write-auto-subs',
            '--sub-lang', lang,
            '--skip-download',
            '--sub-format', 'srt',
            '--output', '-',
            '--quiet' # Add quiet to prevent yt-dlp's own messages from interfering
        ]

        # --- THIS IS THE CRITICAL CHANGE ---
        # If a cookie is provided, add it as a header to the command
        if cookie_string:
            print("Using provided cookie for authentication.")
            command.extend(['--add-header', f"Cookie: {cookie_string}"])
        else:
            print("No cookie provided, making an anonymous request.")
            
        # The last argument must be the URL
        command.append(tiktok_url)

        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        
        srt_content = stdout.decode('utf-8', 'ignore')

        if srt_content.strip():
            return Response(srt_content, mimetype='text/plain; charset=utf-8')
        else:
            # Provide more debug info if it fails
            error_message = stderr.decode('utf-8', 'ignore')
            print(f"SRT generation failed for {tiktok_url}. Stderr: {error_message}")
            return jsonify({"error": f"Subtitles not found for language '{lang}'."}), 404

    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

# --- Root Endpoint (Updated for clarity) ---
@app.route('/')
def home():
    return "TikTok Streaming & Subtitle API v7 (Cookie Auth) is running."
