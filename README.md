# ,hvec - A QSV HEVC Transcoder

A simple yet powerful command-line wrapper for FFmpeg to simplify transcoding video files to the modern HEVC (H.265) codec, using Intel's Quick Sync Video (QSV) for fast, hardware-accelerated performance.

This script is designed for media library management, allowing for easy, high-quality conversions to save space while maintaining visual fidelity.

## Features

- **Hardware Acceleration:** Leverages Intel QSV for both decoding and encoding, ensuring high performance on compatible hardware.
- **Batch Processing:** Transcode entire directories of video files with a single command.
- **Recursive Mode:** Can scan and process video files in subdirectories.
- **Smart Transcoding:** Intelligently skips files that are already in the target HEVC format to save time.
- **Quality & Speed Control:** Optional flags to adjust video quality (`--quality`) and encoding speed/compression (`--preset`).
- **Advanced Audio Control:** Copy audio streams losslessly (default) or re-encode them to other formats like AAC to save space.
- **Subtitle Embedding:** Embed external SRT subtitle files during transcoding or remuxing.
- **Dry Run Mode:** Preview the `ffmpeg` command that will be executed without running it, perfect for testing.
- **Remuxing:** A lossless mode to quickly copy streams into a new MKV container without re-encoding.

## Requirements

- **Python 3**
- **FFmpeg:** Must be installed and available in your system's PATH. A version compiled with QSV support is required.
- **Intel CPU with Quick Sync Video (QSV):** The host machine must have compatible hardware.

## Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/diegelmannsj/hvec-transcoder.git
    cd hvec-project
    ```
2.  Make the script executable:
    ```bash
    chmod +x ,hvec
    ```
3.  (Optional but Recommended) Place the script in your PATH for easy access from any directory.
    ```bash
    sudo ln -s $PWD/,hvec /usr/local/bin/,hvec
    ```

## Usage

The script is controlled via command-line flags. You can see all available options by running:
```bash
,hvec --help
```

### Examples

**1. Basic Transcode of a Single File**
This will transcode `movie.mp4` to `movie.mkv` using the default quality and preset settings.
```bash
,hvec -i movie.mp4
```

**2. Transcode with Higher Quality**
Use the `-Q` (quality) and `-p` (preset) flags to get a higher quality, more efficiently compressed file. This will be slower.
```bash
,hvec -i movie.mp4 -Q 20 -p slow
```

**3. Transcode an Entire Directory**
This finds all video files in the `input_folder` and saves the new HEVC files to `output_folder`.
```bash
,hvec -i /path/to/input_folder --out-dir /path/to/output_folder
```

**4. The "Power User" Batch Command**
This command recursively scans a library, skips any files that are already H.265, re-encodes the audio to AAC at 192k to save space, and saves the new files to a different directory.
```bash
,hvec -i /media/library -R --skip-hevc --acodec aac --abitrate 192k --out-dir /media/library_HEVC
```

**5. Perform a Dry Run**
See the command that *would* be executed for the "Power User" example above, without actually running it.
```bash
,hvec -i /media/library -R --skip-hevc --acodec aac --abitrate 192k --out-dir /media/library_HEVC --dry-run
```

**6. Remux a File**
Quickly copy all streams into a new, clean MKV container without re-encoding.
```bash
,hvec -i corrupt_container.mp4 --remux
```
