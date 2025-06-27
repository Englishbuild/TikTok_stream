import subprocess
from flask import Flask, Response, request, jsonify
import yt_dlp

app = Flask(__name__)

# --- API Endpoint for Caption (No changes needed here) ---
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

# --- NEW AND IMPROVED API Endpoint for Streaming ---
@app.route('/stream')
def stream_video_endpoint():
    tiktok_url = request.args.get('url')
    if not tiktok_url:
        return jsonify({"error": "Missing 'url' query parameter"}), 400

    # Command to execute: yt-dlp <URL> -f best[ext=mp4] -o -
    # -f best[ext=mp4] ensures we get a streamable MP4 format.
    # -o - tells yt-dlp to pipe the final video data to standard output.
    # -q silences logs so only video data is sent to stdout.
    command = [
        'yt-dlp',
        '--format', 'best[ext=mp4]/best', # Prioritize MP4, but have a fallback
        '--output', '-',
        '--quiet',
        tiktok_url
    ]

    try:
        # Use Popen to start the process and get control of its output stream
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Generator function to stream the content chunk by chunk
        def generate_stream():
            try:
                while True:
                    # Read a chunk of data from the yt-dlp process's output
                    chunk = process.stdout.read(4096)
                    if not chunk:
                        # If there's no more data, the stream is finished
                        break
                    # Yield the chunk to the response
                    yield chunk
                
                # Check for any errors that yt-dlp might have printed to stderr
                stderr_output = process.stderr.read().decode('utf-8', 'ignore')
                if stderr_output:
                    print(f"yt-dlp stderr: {stderr_output}")

            except Exception as e:
                print(f"Error during streaming generation: {e}")
            finally:
                # Ensure the process is properly terminated
                if process.poll() is None:
                    process.terminate()
                print("Stream process finished.")

        # Return a streaming response. We explicitly set the mimetype.
        return Response(generate_stream(), mimetype='video/mp4')

    except FileNotFoundError:
        return jsonify({"error": "yt-dlp command not found in the Vercel environment."}), 500
    except Exception as e:
        return jsonify({"error": f"An error occurred while starting the stream process: {e}"}), 500

# Optional: A root endpoint to confirm the API is running
@app.route('/')
def home():
    return "TikTok Streaming API v3 (Subprocess) is running."
