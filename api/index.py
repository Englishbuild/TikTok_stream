from flask import Flask, Response, request, stream_with_context, jsonify
import yt_dlp
import requests

app = Flask(__name__)

def get_tiktok_info(video_url: str):
    """Uses yt-dlp to get video metadata, including necessary request headers."""
    # We need to tell yt-dlp to keep the http_headers it uses
    ydl_opts = {
        'quiet': True,
        'noplaylist': True,
        'format': 'best[ext=mp4]',
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(video_url, download=False)
    except Exception as e:
        print(f"Error fetching info from yt-dlp: {e}")
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

    # 1. Get the video info, which includes the stream URL and required headers
    info = get_tiktok_info(tiktok_url)
    if not info or 'url' not in info:
        return jsonify({"error": "Could not retrieve video stream URL from yt-dlp"}), 500
    
    direct_video_url = info['url']
    
    # -- THIS IS THE CRITICAL FIX --
    # Use the headers that yt-dlp determined were necessary to access the URL.
    # If http_headers are not present, fall back to a generic User-Agent.
    headers = info.get('http_headers', {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })

    # 2. Make a request to the direct URL that allows streaming
    try:
        req = requests.get(direct_video_url, stream=True, headers=headers)
        req.raise_for_status() 
    except requests.exceptions.RequestException as e:
        # This will now give a more accurate error message if it still fails
        return jsonify({"error": f"Failed to connect to TikTok's video server: {e}"}), 502

    # 3. Stream the content back to the client
    return Response(stream_with_context(req.iter_content(chunk_size=4096)),
                    content_type=req.headers['content-type'])

# Optional: A root endpoint to confirm the API is running
@app.route('/')
def home():
    return "TikTok Streaming API v2 is running."
