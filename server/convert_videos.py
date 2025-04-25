import os
import subprocess
import sys
import time
import threading
import tempfile

# Directory where your original video files are stored
VIDEO_DIR = 'C:\\Users\\himan\\Videos\\Movies\\New folder'
# Directory to store converted MP4 files
CONVERTED_DIR = 'C:\\Users\\himan\\Videos\\Movies'

# Ensure the directories exist
if not os.path.exists(VIDEO_DIR):
    os.makedirs(VIDEO_DIR)
    print(f"Created directory for original videos: {VIDEO_DIR}")

if not os.path.exists(CONVERTED_DIR):
    os.makedirs(CONVERTED_DIR)
    print(f"Created directory for converted videos: {CONVERTED_DIR}")

# Supported input file extensions for conversion (add more if needed)
SUPPORTED_INPUT_EXTENSIONS = ['.mkv', '.webm', '.avi', '.mov']


def get_video_duration(file_path):
    """
    Gets the duration of a video file in seconds using ffprobe.
    Returns duration in seconds or None if an error occurs.
    """
    try:
        # ffprobe command to get duration
        ffprobe_command = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            '-i', file_path
        ]
        # Use text=True for string output, check=True to raise exception on error
        process = subprocess.run(
            ffprobe_command, capture_output=True, text=True, check=True)
        duration_str = process.stdout.strip()
        return float(duration_str)
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError) as e:
        # Print error to stderr
        print(
            f"\nError getting duration for {os.path.basename(file_path)}: {e}", file=sys.stderr)
        return None


def monitor_ffmpeg_progress(progress_filepath, total_duration, stop_event):
    """
    Monitors the FFmpeg progress file and updates the console loading bar.
    Runs in a separate thread to avoid blocking the main process while FFmpeg runs.
    """
    # Give FFmpeg a moment to start and create the file
    time.sleep(0.5)

    try:
        # Open the progress file for reading with line buffering
        with open(progress_filepath, 'r', buffering=1) as f:
            # Seek to the beginning initially
            f.seek(0)
            # Keep track of the last reported percentage, -1 to ensure initial print
            last_percentage = -1

            # Loop until the stop event is set (meaning FFmpeg finished)
            while not stop_event.is_set():
                line = f.readline()  # Read one line at a time
                if not line:
                    # If no line was read, we are at the end of the file.
                    # Wait a bit before trying again.
                    # Shorter sleep for more responsive updates
                    time.sleep(0.05)
                    continue  # Go back to the start of the while loop

                # Process the line
                if line.startswith('out_time_ms='):
                    try:
                        # Extract time in milliseconds and convert to seconds
                        elapsed_time_ms = int(line.split('=')[1].strip())
                        elapsed_time_sec = elapsed_time_ms / 1000.0

                        if total_duration and total_duration > 0:
                            percentage = (elapsed_time_sec /
                                          total_duration) * 100
                            # Clamp between 0 and 100
                            percentage = max(0, min(100, percentage))

                            # Only update the display if the percentage has changed significantly
                            # or if it's 100%
                            if percentage - last_percentage >= 0.1 or percentage == 100:  # Update if >= 0.1% change
                                bar_length = 50  # Length of the progress bar in characters
                                filled_length = int(
                                    bar_length * percentage // 100)
                                bar = '█' * filled_length + '-' * \
                                    (bar_length - filled_length)

                                # Print the progress bar dynamically on the same line
                                # \r returns cursor to the beginning of the line
                                sys.stdout.write(
                                    f'\rProgress: [{bar}] {percentage:.1f}% ')
                                sys.stdout.flush()  # Ensure the output is immediately visible

                                last_percentage = percentage  # Update last reported percentage

                    except (ValueError, IndexError):
                        # Ignore lines that don't parse as expected
                        pass
                # Add other progress indicators if needed (e.g., 'frame=', 'speed=')

            # After the loop finishes (stop_event is set), read any remaining lines
            # to ensure we capture the final 100% if the thread stopped before reading it.
            while True:
                line = f.readline()
                if not line:
                    break  # No more lines
                # Re-process the line to ensure final 100% is displayed
                if line.startswith('out_time_ms='):
                    try:
                        elapsed_time_ms = int(line.split('=')[1].strip())
                        elapsed_time_sec = elapsed_time_ms / 1000.0
                        if total_duration and total_duration > 0:
                            percentage = (elapsed_time_sec /
                                          total_duration) * 100
                            percentage = max(0, min(100, percentage))
                            bar_length = 50
                            filled_length = int(bar_length * percentage // 100)
                            bar = '█' * filled_length + '-' * \
                                (bar_length - filled_length)
                            sys.stdout.write(
                                f'\rProgress: [{bar}] {percentage:.1f}% ')
                            sys.stdout.flush()
                    except (ValueError, IndexError):
                        pass

            # Ensure a newline is printed at the very end to move to the next line
            sys.stdout.write('\n')
            sys.stdout.flush()

    except FileNotFoundError:
        print(
            f"\nError: FFmpeg progress file not found at {progress_filepath}", file=sys.stderr)
    except Exception as e:
        print(
            f"\nAn error occurred while monitoring progress: {e}", file=sys.stderr)


def convert_to_mp4(input_path, output_path):
    """
    Converts a video file to MP4 format using ffmpeg with progress monitoring.
    Returns True on success, False on failure.
    """
    input_filename = os.path.basename(input_path)
    output_filename = os.path.basename(output_path)

    print(f"Converting '{input_filename}'...")

    # Get the total duration using ffprobe
    total_duration = get_video_duration(input_path)
    if total_duration is None:
        print(
            f"Could not get duration for '{input_filename}'. Conversion will proceed without a progress bar.", file=sys.stderr)
        show_progress = False
    else:
        print(f"Duration: {total_duration:.2f} seconds")
        show_progress = True

    # Create a temporary file for FFmpeg progress output
    temp_progress_file = None
    progress_filepath = None
    if show_progress:
        try:
            # delete=False so the file is not deleted immediately when closed
            temp_progress_file = tempfile.NamedTemporaryFile(
                delete=False, suffix=".progress")
            progress_filepath = temp_progress_file.name
            # IMPORTANT: Close the file handle immediately so FFmpeg can write to it
            temp_progress_file.close()
        except Exception as e:
            print(
                f"\nWarning: Could not create temporary progress file: {e}. Conversion will proceed without a progress bar.", file=sys.stderr)
            show_progress = False

    # FFmpeg command to convert to MP4
    ffmpeg_command = [
        'ffmpeg',
        '-i', input_path,
        # Use libx264 for H.264 encoding. REQUIRES FFmpeg built with libx264 support.
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-vf', 'format=yuv420p',  # Ensure YUV 4:2:0 pixel format
        '-movflags', '+faststart',
        '-y',  # Overwrite output file without asking
        '-loglevel', 'error',  # Suppress verbose ffmpeg output, only show errors
    ]

    # Add the progress flag if we are showing progress
    if show_progress and progress_filepath:
        ffmpeg_command.extend(['-progress', progress_filepath])
        # If using -progress, ffmpeg sends progress to the file and other messages
        # might still go to stderr. We suppress most output with -loglevel error.
    else:
        # If not showing progress, capture stderr for error reporting in case of failure
        pass  # capture_output=True will be handled by subprocess.run args

    # Add the output file path
    ffmpeg_command.append(output_path)

    # Event to signal the progress monitoring thread to stop
    stop_event = threading.Event()
    progress_thread = None

    try:
        # Start the progress monitoring thread if showing progress
        if show_progress and progress_filepath:
            progress_thread = threading.Thread(target=monitor_ffmpeg_progress, args=(
                progress_filepath, total_duration, stop_event))
            progress_thread.start()

        # Execute the ffmpeg command
        # Capture output only if NOT showing progress, otherwise let stderr pass through
        # (suppressed by -loglevel error)
        if show_progress:
            # Let stderr go to console for real errors (suppressed by -loglevel error)
            # stdout is typically not used by ffmpeg for regular output when converting
            # check=True raises CalledProcessError on non-zero exit code
            process = subprocess.run(ffmpeg_command, check=True)
        else:
            # Capture stdout/stderr for error reporting if progress is not shown
            process = subprocess.run(
                ffmpeg_command, capture_output=True, text=True, check=True)

        # If we reach here, ffmpeg finished successfully
        # The progress monitor thread should have printed the final 100% and a newline
        # If progress wasn't shown, print a simple success message
        if not show_progress:
            # Print success if no progress bar was shown
            print(f"Successfully converted '{input_filename}'.")

        return True

    except subprocess.CalledProcessError as e:
        print(f"\nError converting '{input_filename}'.", file=sys.stderr)
        if not show_progress:  # Only print captured output if not showing progress bar
            print(f"ffmpeg stdout: {e.stdout}", file=sys.stderr)
            print(f"ffmpeg stderr: {e.stderr}", file=sys.stderr)
        # Clean up the partially created output file if conversion failed
        if os.path.exists(output_path):
            os.remove(output_path)
        return False
    except FileNotFoundError:
        print(f"\nError: ffmpeg command not found.", file=sys.stderr)
        print("Please ensure ffmpeg is installed and accessible in your system's PATH.", file=sys.stderr)
        return False
    except Exception as e:
        print(
            f"\nAn unexpected error occurred during conversion of '{input_filename}': {e}", file=sys.stderr)
        if os.path.exists(output_path):
            os.remove(output_path)
        return False
    finally:
        # Signal the progress thread to stop and wait for it to finish
        if progress_thread and progress_thread.is_alive():
            stop_event.set()
            progress_thread.join(timeout=5)  # Join with a timeout

        # Clean up the temporary progress file
        if progress_filepath and os.path.exists(progress_filepath):
            try:
                os.remove(progress_filepath)
            except OSError as e:
                print(
                    f"\nWarning: Could not delete temporary progress file {progress_filepath}: {e}", file=sys.stderr)


def main():
    """
    Finds video files in VIDEO_DIR, lists those needing conversion,
    and converts them to MP4 in CONVERTED_DIR one by one with a progress bar
    for the current file.
    """
    print("Starting video conversion process...")

    files_to_convert = []
    skipped_count = 0

    # First pass: Identify files that need conversion and count them
    print("Scanning for videos to convert...")
    for root, _, files in os.walk(VIDEO_DIR):
        for filename in files:
            original_path = os.path.join(root, filename)
            filename_base, file_extension = os.path.splitext(filename)
            file_extension = file_extension.lower()

            # Determine the output path in the converted directory
            converted_filename = f"{filename_base}.mp4"
            converted_path = os.path.join(CONVERTED_DIR, converted_filename)

            # Skip if it's already an MP4 in the original directory
            if file_extension == '.mp4':
                skipped_count += 1
                continue

            # Check if the file extension is supported for conversion
            if file_extension not in SUPPORTED_INPUT_EXTENSIONS:
                skipped_count += 1
                continue

            # Check if the converted MP4 file already exists
            if os.path.exists(converted_path):
                skipped_count += 1
                continue

            # If none of the skip conditions met, add to the list to convert
            files_to_convert.append((original_path, converted_path, filename))

    total_videos_to_convert = len(files_to_convert)
    print(f"Found {total_videos_to_convert} video(s) needing conversion.")
    if skipped_count > 0:
        print(
            f"Skipped {skipped_count} file(s) (already MP4 or unsupported format or already converted).")

    if total_videos_to_convert == 0:
        print("No videos to convert. Exiting.")
        return

    print("\nStarting conversions:")
    converted_count = 0
    error_count = 0

    # Second pass: Perform the conversions one by one
    for i, (original_path, converted_path, filename) in enumerate(files_to_convert):
        current_video_number = i + 1
        print(
            f"\n--- Converting file {current_video_number} of {total_videos_to_convert}: '{filename}' ---")

        if convert_to_mp4(original_path, converted_path):
            # Print success message after the progress bar line
            print(f"Finished converting '{filename}'.")
            converted_count += 1
        else:
            # Error message already printed by convert_to_mp4
            print(f"Failed to convert '{filename}'.", file=sys.stderr)
            error_count += 1

    print("\nConversion process finished.")
    print(f"Total videos processed: {total_videos_to_convert}")
    print(f"Converted successfully: {converted_count}")
    print(f"Failed conversions: {error_count}")
    print(f"Files skipped (already processed or unsupported): {skipped_count}")


if __name__ == "__main__":
    # Check if ffmpeg and ffprobe are available before starting
    try:
        subprocess.run(['ffmpeg', '-version'],
                       capture_output=True, check=True, text=True)
        subprocess.run(['ffprobe', '-version'],
                       capture_output=True, check=True, text=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: ffmpeg or ffprobe not installed or not in your system's PATH.", file=sys.stderr)
        print("Please ensure ffmpeg (which includes ffprobe) is installed and accessible.", file=sys.stderr)
        sys.exit(1)  # Exit if ffmpeg/ffprobe is not found

    main()
