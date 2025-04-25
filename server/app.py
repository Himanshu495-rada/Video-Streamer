from flask import Flask, request, Response, send_file, jsonify
import os
import subprocess  # Still needed for ffprobe
import math
import json
from flask_cors import CORS, cross_origin


app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

# Directory where converted MP4 files are stored
# The server will ONLY look in this directory for video files.
CONVERTED_DIR = 'C:\\Users\\himan\\Videos\\Music videos'

# Ensure the converted directory exists (though the converter script should create it)
if not os.path.exists(CONVERTED_DIR):
    os.makedirs(CONVERTED_DIR)
    print(f"Created directory for converted videos: {CONVERTED_DIR}")


@app.route("/")
@cross_origin()
def hello():
    return "Application is running"


@app.route('/video/<filename>')
@cross_origin()
def stream_video(filename):
    """
    Streams MP4 video files from the converted directory using range requests.
    Assumes files in CONVERTED_DIR are already MP4.
    """
    # Ensure the requested file has an .mp4 extension
    if not filename.lower().endswith('.mp4'):
        # 415 Unsupported Media Type
        return "Only MP4 files are supported for streaming.", 415

    video_path = os.path.join(CONVERTED_DIR, filename)

    # Check if the converted MP4 file exists
    if not os.path.exists(video_path):
        # Provide a more informative error if the file isn't found in the converted directory
        # This might indicate the conversion script hasn't been run for the original file.
        return f"Converted file '{filename}' not found. Please ensure the original video has been converted.", 404

    range_header = request.headers.get('Range', None)
    file_size = os.path.getsize(video_path)

    # --- Streaming Logic (Handles Range Requests for MP4) ---
    if range_header:
        # Parse the Range header sent by the browser
        byte_range = range_header.replace('bytes=', '').split('-')
        start = int(byte_range[0])
        end = int(byte_range[1]) if len(
            byte_range) > 1 and byte_range[1] else file_size - 1

        chunk_size = end - start + 1

        try:
            with open(video_path, 'rb') as f:
                f.seek(start)
                data = f.read(chunk_size)

            response = Response(data, 206)  # 206 Partial Content
            response.headers['Content-Range'] = f'bytes {start}-{end}/{file_size}'
            response.headers['Content-Length'] = chunk_size
            response.headers['Content-Type'] = 'video/mp4'  # Always video/mp4
            response.headers['Accept-Ranges'] = 'bytes'
            return response

        except IOError:
            return "Error reading file chunk", 500
    else:
        # If no Range header, serve the whole file (or the beginning).
        response = send_file(video_path, mimetype='video/mp4')
        response.headers['Accept-Ranges'] = 'bytes'
        return response


@app.route('/video_info/<filename>')
@cross_origin()
def get_video_info(filename):
    """
    Gets video metadata (like duration) using ffprobe from the converted directory.
    Assumes files in CONVERTED_DIR are already MP4.
    """
    # Ensure the requested file has an .mp4 extension
    if not filename.lower().endswith('.mp4'):
        return jsonify({"error": "Only MP4 files are supported for info."}), 415

    video_path = os.path.join(CONVERTED_DIR, filename)

    if not os.path.exists(video_path):
        # Provide a more informative error if the file isn't found
        return jsonify({"error": f"Converted file '{filename}' not found. Please ensure the original video has been converted."}), 404

    try:
        # Use ffprobe to get the duration
        ffprobe_command = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            '-i', video_path  # Probe the file in the converted directory
        ]

        process = subprocess.run(
            ffprobe_command, capture_output=True, text=True, check=True)

        duration_str = process.stdout.strip()
        duration = float(duration_str)

        return jsonify({"duration": duration})

    except subprocess.CalledProcessError as e:
        print(f"ffprobe error (stdout): {e.stdout}")
        print(f"ffprobe error (stderr): {e.stderr}")
        return jsonify({"error": "Could not get video info", "details": e.stderr.strip()}), 500
    except FileNotFoundError:
        print("Error: ffprobe command not found.")
        print("Please ensure ffmpeg (which includes ffprobe) is installed and accessible in your system's PATH.")
        return jsonify({"error": "ffprobe command not found"}), 500
    except Exception as e:
        print(f"An error occurred getting video info: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500


if __name__ == '__main__':
    # Ensure the converted directory exists on server startup as well
    if not os.path.exists(CONVERTED_DIR):
        os.makedirs(CONVERTED_DIR)
        print(f"Created directory for converted videos: {CONVERTED_DIR}")

    # Run the Flask development server
    app.run(debug=True)
