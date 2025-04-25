import os
import json

# Directory where your converted MP4 video files are stored
CONVERTED_DIR = 'C:\\Users\\himan\\Videos\\Music videos'
# Path to the output JSON file
OUTPUT_JSON_FILE = './videos.json'
# Base path for poster images (relative to the static directory served by Flask)
POSTER_BASE_PATH = '/static/posters/'
# Default poster image filename if a specific one doesn't exist (optional)
# You might want to create a default_poster.jpg in your static/posters directory
DEFAULT_POSTER = 'poster.jpg'


def generate_video_list_json(converted_dir, output_json_file, poster_base_path, default_poster=None):
    """
    Scans the converted video directory, collects video details,
    and saves them to a JSON file.
    """
    video_list = []

    print(f"Scanning directory: {converted_dir}")

    # Check if the converted directory exists
    if not os.path.exists(converted_dir):
        print(f"Error: Converted directory '{converted_dir}' not found.")
        print("Please run the conversion script first.")
        return

    # Walk through the converted directory
    for root, _, files in os.walk(converted_dir):
        for filename in files:
            # Only process MP4 files (since the server is set to stream only MP4)
            # if filename.lower().endswith('.mp4'):
            file_path = os.path.join(root, filename)
            # Create a simple ID (can be improved for uniqueness if needed)
            # Use filename without extension as ID
            video_id = f"video{files.index(filename) + 1}"

            # Create a simple title from the filename (replace underscores/dashes with spaces)
            title = os.path.splitext(filename)[0].replace(
                '_', ' ').replace('-', ' ').title()

            # Generate poster path - assumes a poster image with the same base name exists
            # in the static/posters directory. Falls back to default poster if specified.
            poster_filename = "poster.jpg"  # Assuming poster is a JPG
            poster_path = os.path.join(poster_base_path, poster_filename)

            # If a default poster is specified, you could add logic here to check
            # if the specific poster file exists on the filesystem and use the
            # default if it doesn't. For simplicity here, we just construct the path.
            # The frontend's onerror handler on the <img> tag will handle missing images.

            video_details = {
                "id": video_id,
                "title": title,
                # Path relative to the web server's root (handled by Flask static)
                "poster": poster_path,
                "filename": filename  # The actual filename in the converted directory
            }
            video_list.append(video_details)

    # Write the video list to the JSON file
    try:
        with open(output_json_file, 'w', encoding='utf-8') as f:
            json.dump(video_list, f, indent=2, ensure_ascii=False)
        print(f"\nSuccessfully generated video list in: {output_json_file}")
        print(f"Found {len(video_list)} MP4 video(s).")
    except IOError as e:
        print(
            f"\nError writing to JSON file {output_json_file}: {e}", file=sys.stderr)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}", file=sys.stderr)


if __name__ == "__main__":
    # Ensure the converted directory exists before scanning
    if not os.path.exists(CONVERTED_DIR):
        print(f"Creating missing directory: {CONVERTED_DIR}")
        os.makedirs(CONVERTED_DIR)
        print("Please place your converted MP4 files in this directory.")

    # Ensure the static/posters directory exists (where posters are expected)
    static_posters_dir = './static/posters'
    if not os.path.exists(static_posters_dir):
        print(f"Creating missing directory: {static_posters_dir}")
        os.makedirs(static_posters_dir)
        print("Please place your poster images in this directory.")
        # Optionally create a placeholder default poster if you specified one
        if DEFAULT_POSTER and not os.path.exists(os.path.join(static_posters_dir, DEFAULT_POSTER)):
            print(
                f"Consider adding a default poster image named '{DEFAULT_POSTER}' to {static_posters_dir}")

    generate_video_list_json(
        CONVERTED_DIR, OUTPUT_JSON_FILE, POSTER_BASE_PATH, DEFAULT_POSTER)
