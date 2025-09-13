#!/usr/bin/env python3

import argparse
import subprocess
import sys
import os
import json
import math
import argcomplete

# --- Version History ---
__version__ = "2.8"

VERSION_HISTORY = f"""
,hvec Transcoder v{__version__}
---------------------------------
v2.8: Corrected a major bug in Transcode mode that incorrectly forced the input
      decoder to H.264 (h264_qsv), causing errors with non-H.264 source files
      like H.265. The script now correctly allows FFmpeg to auto-detect the
      input codec for hardware decoding.
v2.7: Fixed subtitle embedding (--subs) to correctly map streams, preventing conflicts with existing/incompatible subtitle tracks in the source file.
v2.6: Changed behavior to default the output filename if -o is not specified,
      replacing the previous "info-only" mode for a faster workflow.
v2.5: Changed subtitle handling to automatically convert to SRT when the
      output container is MKV, improving remux compatibility.
v2.4: Added --convert-subs flag to handle incompatible embedded subtitles.
v2.3: Improved --remux mode to intelligently ignore incompatible tracks.
v2.2: Added -r/--remux mode for lossless stream copying.
v2.1: Added --less-noise flag for periodic progress updates.
v2.0: Reworked argument parsing to correctly handle --version flag.
v1.9: Display full version history with --version flag.
v1.8: Added -q/--quiet flag to suppress FFmpeg warnings and progress.
v1.7: Made transcoding more robust by explicitly mapping desired streams.
v1.6: Moved version print to run before argument parsing.
v1.5: Always print version number on execution.
v1.4: Added argcomplete hook for shell autocompletion.
v1.3: Added transcode time estimation to info-only mode.
v1.2: Added info-only mode when only -i is provided.
v1.1: Added --version flag.
v1.0: Initial release.
"""

# --- PERFORMANCE CONSTANT ---
ESTIMATED_FPS = 85

def main():
    """
    Parses arguments and performs media operations: transcode or remux.
    """
    # --- Manually check for --version flag BEFORE argparse ---
    if '-v' in sys.argv or '--version' in sys.argv:
        print(VERSION_HISTORY)
        sys.exit(0)

    # --- Set up the Argument Parser ---
    parser = argparse.ArgumentParser(
        description="A tool to transcode, remux, or inspect video files.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Examples:
  # Transcode movie.mp4 to movie.mkv (output name is automatic)
  ,hvec.py -i movie.mp4

  # Remux a video, converting subtitles, with automatic output name
  ,hvec.py -i movie.m4v --remux

  # Remux a movie while replacing its subtitles with an external SRT file
  ,hvec.py -i movie.mkv -o movie_new.mkv --subs new.srt --remux
"""
    )
    parser.add_argument("-i", "--input", required=True, help="Input video file")
    parser.add_argument("-o", "--output", help="Output MKV file. If omitted, it's generated from the input name.")
    parser.add_argument("-s", "--subs", help="(Optional) Subtitle file to embed.")
    parser.add_argument("-r", "--remux", action="store_true", help="Perform a lossless remux (stream copy) instead of transcoding.")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress all warnings and progress. Overrides --less-noise.")
    parser.add_argument("--less-noise", action="store_true", help="Show progress updates only every 30 seconds.")
    parser.add_argument("--convert-subs", action="store_true", help="Convert subtitle tracks to a compatible format (srt) instead of copying.")
    parser.add_argument("-v", "--version", action="store_true", help="Show the version history and exit.")
    
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    
    print(f"--- hvec Transcoder v{__version__} ---")
    
    if not os.path.exists(args.input):
        print(f"Error: Input file not found at '{args.input}'", file=sys.stderr)
        sys.exit(1)

    # Check for output file and create a default if not provided
    if not args.output:
        base_name, _ = os.path.splitext(args.input)
        args.output = base_name + ".mkv"
        print(f"\nInfo: No output file specified. Defaulting to '{args.output}'")
    
    # --- MODE: Output Mode ---
    if args.subs and not os.path.exists(args.subs):
        print(f"Error: Subtitle file not found at '{args.subs}'", file=sys.stderr)
        sys.exit(1)
    
    subtitle_codec = 'srt' if args.convert_subs or args.output.lower().endswith('.mkv') else 'copy'
    
    if args.remux:
        # --- SUB-MODE: Remux ---
        print("\nMode: Lossless Remux")
        ffmpeg_cmd = ['ffmpeg', '-i', args.input]

        if args.subs:
            ffmpeg_cmd.extend(['-i', args.subs])
            # Map video and audio from input 0, subtitles from input 1
            ffmpeg_cmd.extend(['-map', '0:v', '-map', '0:a?', '-map', '1:s'])
            ffmpeg_cmd.extend(['-c:v', 'copy', '-c:a', 'copy', '-c:s', subtitle_codec])
        else: # Original logic for files without external subs
            ffmpeg_cmd.extend(['-map', '0:v:0', '-map', '0:a?', '-map', '0:s?'])
            ffmpeg_cmd.extend(['-c:v', 'copy', '-c:a', 'copy', '-c:s', subtitle_codec])
        
        ffmpeg_cmd.append(args.output)
    else:
        # --- SUB-MODE: Transcode ---
        print("\nMode: QSV Transcode")
        ffmpeg_cmd = ['ffmpeg']
        if args.quiet:
            ffmpeg_cmd.extend(['-loglevel', 'error'])
        elif args.less_noise:
            ffmpeg_cmd.extend(['-stats_period', '30'])
        
        # --- THE FIX IS HERE ---
        # Set global hwaccel but do NOT force an input codec.
        # FFmpeg will auto-detect the correct one (h264_qsv, hevc_qsv, etc.)
        ffmpeg_cmd.extend(['-hwaccel', 'qsv'])
        ffmpeg_cmd.extend(['-i', args.input])

        encoding_params = ['-c:v', 'hevc_qsv', '-preset', 'medium', '-global_quality', '24', '-c:a', 'copy']
        
        if args.subs:
            ffmpeg_cmd.extend(['-i', args.subs])
            # Map video and audio from input 0, subtitles from input 1
            ffmpeg_cmd.extend(['-map', '0:v', '-map', '0:a?', '-map', '1:s'])
            ffmpeg_cmd.extend(['-c:s', subtitle_codec])
        else: # Original logic for files without external subs
            ffmpeg_cmd.extend(['-map', '0:v:0', '-map', '0:a?', '-map', '0:s?'])
            ffmpeg_cmd.extend(['-c:s', subtitle_codec])

        ffmpeg_cmd.extend(encoding_params)
        ffmpeg_cmd.append(args.output)

    run_ffmpeg_command(ffmpeg_cmd)

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
    # A helper to print the command in a copy-pasteable format
    cmd_str = ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in cmd)
    print(cmd_str)
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