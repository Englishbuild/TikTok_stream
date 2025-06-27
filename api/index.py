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
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

# --- NEW API Endpoint for SRT Subtitles ---
@app.route('/srt')
def get_srt_endpoint():
    tiktok_url = request.args.get('url')
    # Allow specifying language, default to English ('en')
    lang = request.args.get('lang', 'en')

    if not tiktok_url:
        return jsonify({"error": "Missing 'url' query parameter"}), 400

    try:
        # Command to get auto-captions, convert to SRT, and print to stdout
        command = [
            sys.executable, '-m', 'yt_dlp',
            '--write-auto-subs',    # Get automatically generated captions
            '--sub-lang', lang,       # Specify the language
            '--skip-download',      # Don't download the video
            '--sub-format', 'srt',     # Specify SRT format
            '--output', '-',          # Pipe output to stdout
            tiktok_url
        ]

        # Use Popen to run the command
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Use communicate() to get all output once the process finishes
        stdout, stderr = process.communicate()
        
        srt_content = stdout.decode('utf-8', 'ignore')
        stderr_output = stderr.decode('utf-8', 'ignore')

        # Check if we actually got SRT content
        if srt_content.strip():
            # Return the SRT content as plain text
            return Response(srt_content, mimetype='text/plain; charset=utf-8')
        else:
            # If no content, it means no subtitles were found
            print(f"SRT generation failed for {tiktok_url}. Stderr: {stderr_output}")
            return jsonify({"error": f"Subtitles not found for language '{lang}'."}), 404

    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred while fetching subtitles: {str(e)}"}), 500

# --- Root Endpoint (Updated for clarity) ---
@app.route('/')
def home():
    return "TikTok Streaming & Subtitle API v6 is running."
