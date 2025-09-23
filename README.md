# ,hvec - A QSV HEVC Transcoder

A simple yet powerful command-line wrapper for FFmpeg to simplify transcoding video files to the modern HEVC (H.265) codec, using Intel's Quick Sync Video (QSV) for fast, hardware-accelerated performance. And yes, the name of the script (,hvec) is from a typo of HVEC (and the comma is intentional, as I use it for all of my scripts)

This script is designed for media library management, allowing for easy, high-quality conversions to save space while maintaining visual fidelity.
## Features

- **Hardware Acceleration:** Leverages Intel QSV for both decoding and encoding.
- **Automatic Filename Cleaning:** Removes parentheses and replaces spaces with periods for cleaner, command-line friendly output names.
- **Batch Processing:** Transcode entire directories of video files with a single command, automatically adding a `.CONV` suffix to new files.
- **Recursive Mode:** Can scan and process video files in subdirectories.
- **Smart Transcoding:** Intelligently skips files that are already in the target HEVC format.
- **Destructive Mode:** Optional flag (`--delete`) to automatically delete the source file upon a successful conversion.
- **Quality & Speed Control:** Flags to adjust video quality (`--quality`) and encoding speed/compression (`--preset`).
- **Advanced Audio Control:** Copy audio streams losslessly (default) or re-encode them.
- **Subtitle Embedding:** Embed external SRT subtitle files during transcoding or remuxing.
- **Dry Run Mode:** Preview the `ffmpeg` command that will be executed without running it.
- **Remuxing:** A lossless mode to quickly copy streams into a new MKV container without re-encoding.
- **HEVC Override:** A flag (`--hvec`) to force an HEVC transcode, even when other modes like `--remux` are specified.
## Requirements

- **Python 3**
- **FFmpeg:** Must be installed and available in your system's PATH. A version compiled with QSV support is required.
- **Intel CPU with Quick Sync Video (QSV):** The host machine must have compatible hardware.

## Installation

1.  Clone the repository or download the script.
2.  Make the script executable:
    ```bash
    chmod +x ,hvec
    ```
3.  (Optional but Recommended) Place the script in your PATH for easy access from any directory, for example:
    ```bash
    # This path may vary depending on your system
    sudo ln -s /path/to/your/script/,hvec /usr/local/bin/,hvec
    ```

## Usage
usage: blah [-h] -i INPUT [-o OUTPUT] [-D] [--out-dir OUT_DIR] [-R] [-s SUBS]
            [-H] [-Q QUALITY]
            [-p {veryfast,faster,fast,medium,slow,slower,veryslow}]
            [--acodec ACODEC] [--abitrate ABITRATE] [--skip-hevc] [--dry-run]
            [-r] [-q] [--less-noise] [-v]

A tool to transcode or remux video files using Intel QSV.

options:
  -h, --help            show this help message and exit
  -i, --input INPUT     Input video file or directory.
  -o, --output OUTPUT   Output MKV file. If specified, name sanitization is skipped.
  -D, --delete          Delete the original input file after a successful transcode.
  --out-dir OUT_DIR     Output directory for batch processing. Preserves source folder structure.
  -R, --recursive       Process files in subdirectories when -i is a directory.
  -s, --subs SUBS       (Optional) External subtitle file to embed (single file mode only).
  -H, --hvec            Force output to be HEVC/H.265. Overrides --remux.
  -Q, --quality QUALITY
                        Set QSV quality for video (1-51, lower is better). Default: 24.
  -p, --preset {veryfast,faster,fast,medium,slow,slower,veryslow}
                        Set QSV encoding preset. Slower presets offer better compression. Default: medium.
  --acodec ACODEC       Re-encode audio to a specific codec (e.g., aac, ac3). Default: copy.
  --abitrate ABITRATE   Set audio bitrate when re-encoding (e.g., 192k, 384k).
  --skip-hevc           In batch mode, skip transcoding files that are already H.265/HEVC.
  --dry-run             Print the FFmpeg commands without executing them.
  -r, --remux           Perform a lossless remux instead of transcoding.
  -q, --quiet           Suppress most FFmpeg output. Overrides --less-noise.
  --less-noise          Show progress updates only every 30 seconds.
  -v, --version         Show the version history and exit.

### Examples
```bash
# Transcode a single file with default settings and auto-name-cleaning
```bash
# "My Movie (2025).mp4" -> "My.Movie.2025.mkv"
  ,hvec -i "My Movie (2025).mp4"

```bash
# Transcode a file and delete the original upon success
  ,hvec -i "My Movie.mp4" -D
```

```bash
# Transcode all videos in a folder and delete the originals
  ,hvec -i /path/to/videos/ -D
```
