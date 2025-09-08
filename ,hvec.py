#!/usr/bin/env python3

import argparse
import subprocess
import sys
import os
import json
import math
import argcomplete

# --- Version History ---
# 1.7: Made transcoding command more robust by explicitly mapping streams.
# 1.8: Added a -q/--quiet flag to suppress warnings and progress output from FFmpeg.
__version__ = "1.8"

# --- PERFORMANCE CONSTANT ---
ESTIMATED_FPS = 85

def main():
    """
    Parses arguments and either displays media info or runs FFmpeg for transcoding.
    """
    parser = argparse.ArgumentParser(
        description="Transcodes a video to HEVC (QSV) or displays media info.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Examples:
  # Get info and estimated transcode time for a video
  ,hvec.py -i movie.mp4

  # Transcode a video verbosely (default)
  ,hvec.py -i movie.mp4 -o movie.mkv

  # Transcode a video quietly (hides progress and warnings)
  ,hvec.py -i movie.mp4 -o movie.mkv --quiet
"""
    )
    parser.add_argument("-i", "--input", required=True, help="Input video file")
    parser.add_argument("-o", "--output", help="Output MKV file. If omitted, script will display info about the input file.")
    parser.add_argument("-s", "--subs", help="(Optional) Subtitle file to embed. Only used for transcoding.")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress FFmpeg warnings and progress updates (quieter output).")
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")
    
    argcomplete.autocomplete(parser)
    print(f"--- hvec Transcoder v{__version__} ---")
    args = parser.parse_args()
    
    if not args.output:
        # ...(Info-mode is unchanged)...
        if not os.path.exists(args.input):
            print(f"Error: Input file not found at '{args.input}'", file=sys.stderr)
            sys.exit(1)
        print(f"\n--- Media Information for: {os.path.basename(args.input)} ---\n")
        try:
            subprocess.run(['ffprobe', '-hide_banner', args.input], check=True)
            estimate_transcode_time(args.input)
        except FileNotFoundError:
            print("Error: 'ffprobe' not found. Is FFmpeg installed correctly?", file=sys.stderr)
            sys.exit(1)
        except subprocess.CalledProcessError:
            print("\nError: ffprobe failed to analyze the file.", file=sys.stderr)
            sys.exit(1)
        sys.exit(0)

    # --- MODE 2: Transcoding (if output file is specified) ---
    if not os.path.exists(args.input):
        print(f"Error: Input file not found at '{args.input}'", file=sys.stderr)
        sys.exit(1)
    if args.subs and not os.path.exists(args.subs):
        print(f"Error: Subtitle file not found at '{args.subs}'", file=sys.stderr)
        sys.exit(1)

    # --- Build the FFmpeg command ---
    ffmpeg_cmd = ['ffmpeg']
    
    # Add the -loglevel error flag if --quiet is used
    if args.quiet:
        ffmpeg_cmd.extend(['-loglevel', 'error'])
        
    ffmpeg_cmd.extend(['-hwaccel', 'qsv', '-c:v', 'h264_qsv', '-i', args.input])
    
    encoding_params = ['-c:v', 'hevc_qsv', '-preset', 'medium', '-global_quality', '24', '-c:a', 'copy']
    
    if args.subs:
        ffmpeg_cmd.extend(['-i', args.subs, '-map', '0:v:0', '-map', '0:a', '-map', '1:s'])
        ffmpeg_cmd.extend(['-c:s', 'copy', '-metadata:s:s:0', 'language=eng'])
    else:
        ffmpeg_cmd.extend(['-map', '0:v:0', '-map', '0:a?'])

    ffmpeg_cmd.extend(encoding_params)
    ffmpeg_cmd.append(args.output)
    
    run_ffmpeg_command(ffmpeg_cmd)

# ...(The rest of the functions: estimate_transcode_time and run_ffmpeg_command are unchanged)...
def estimate_transcode_time(input_file):
    print("\n--- Transcode Estimate (for this hardware) ---")
    ffprobe_cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', input_file]
    try:
        result = subprocess.run(ffprobe_cmd, check=True, capture_output=True, text=True)
        media_info = json.loads(result.stdout)
        video_stream = next((s for s in media_info['streams'] if s['codec_type'] == 'video'), None)
        if not video_stream:
            print("Could not find a video stream to analyze.")
            return

        total_frames_str = video_stream.get('nb_frames')
        if total_frames_str and total_frames_str.isdigit():
            total_frames = int(total_frames_str)
        else:
            duration = float(video_stream.get('duration', media_info['format'].get('duration', '0')))
            rate_num, rate_den = map(int, video_stream.get('avg_frame_rate', '0/1').split('/'))
            frame_rate = rate_num / rate_den if rate_den != 0 else 0
            total_frames = math.ceil(duration * frame_rate)

        if total_frames > 0 and ESTIMATED_FPS > 0:
            estimated_seconds = total_frames / ESTIMATED_FPS
            mins, secs = divmod(estimated_seconds, 60)
            hours, mins = divmod(mins, 60)
            print(f"Estimated time to transcode: {int(hours):02d}:{int(mins):02d}:{int(secs):02d}")
            print(f"(Based on an estimated {ESTIMATED_FPS} FPS for QSV HEVC encoding on this hardware)")
        else:
            print("Could not determine video length to provide an estimate.")
    except Exception as e:
        print(f"Could not analyze video to provide an estimate: {e}")

def run_ffmpeg_command(cmd):
    print("\nExecuting FFmpeg command:")
    print(' '.join(f'"{arg}"' if ' ' in arg else arg for arg in cmd))
    print("\n------------------------- FFmpeg Output -------------------------")
    try:
        subprocess.run(cmd, check=True)
        print("-----------------------------------------------------------------")
        print(f"\nSuccessfully created '{cmd[-1]}'.")
    except FileNotFoundError:
        print("\nError: 'ffmpeg' not found. Is FFmpeg installed and in your PATH?", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print("-----------------------------------------------------------------")
        print(f"\nError: FFmpeg failed with exit code {e.returncode}.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()