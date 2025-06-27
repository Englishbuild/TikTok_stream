from flask import Flask, Response, request, stream_with_context, jsonify
import yt_dlp
import requests

# Vercel will look for this 'app' variable
app = Flask(__name__)

def get_tiktok_info(video_url: str):
    """Uses yt-dlp to get video metadata."""
    ydl_opts = {
        'quiet': True,
        'noplaylist': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(video_url, download=False)
    except Exception as e:
        print(f"Error fetching info: {e}")
        return None

# --- API Endpoint for Caption ---
@app.route('/info')
def get_info_endpoint():
    tiktok_url = request.args.get('url')
    if not tiktok_url:
        return jsonify({"error": "Missing 'url' query parameter"}), 400
        
    info = get_tiktok_info(tiktok_url)
    if not info:
        return jsonify({"error": "Could not retrieve info from TikTok"}), 500

    caption = info.get('description') or info.get('title', 'No caption found')
    return jsonify({"caption": caption})

# --- API Endpoint for Streaming ---
@app.route('/stream')
def stream_video_endpoint():
    tiktok_url = request.args.get('url')
    if not tiktok_url:
        return jsonify({"error": "Missing 'url' query parameter"}), 400

    # 1. Get the direct, temporary video URL from TikTok
    info = get_tiktok_info(tiktok_url)
    if not info or 'url' not in info:
        return jsonify({"error": "Could not retrieve video stream URL"}), 500
    
    direct_video_url = info['url']

    # 2. Make a request to the direct URL that allows streaming
    # stream=True is essential. It doesn't download the whole file at once.
    try:
        req = requests.get(direct_video_url, stream=True, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        # Check if the request to TikTok's server was successful
        req.raise_for_status() 
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Failed to connect to TikTok's video server: {e}"}), 502

    # 3. Stream the content back to the client (your Android app)
    return Response(stream_with_context(req.iter_content(chunk_size=4096)),
                    content_type=req.headers['content-type'])

# Optional: A root endpoint to confirm the API is running
@app.route('/')
def home():
    return "TikTok Streaming API is running."
