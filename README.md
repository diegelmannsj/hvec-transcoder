# `,hvec` — Intel QSV HEVC Transcoder

`,hvec` is a command-line wrapper around FFmpeg for transcoding and remuxing video files. It is designed for media-library maintenance and uses Intel Quick Sync Video (QSV) to encode HEVC/H.265 quickly while retaining control over quality, audio, subtitles, chapters, and output naming.

The name comes from a typo of HEVC/HVEC. The leading comma is intentional.

## Features

- Transcode video to HEVC with Intel QSV hardware acceleration.
- Remux video into an MKV container without re-encoding the video.
- Process a single file, a directory, or a recursive directory tree.
- Select files interactively with a terminal UI.
- Skip files already encoded as HEVC.
- Adjust QSV quality and encoding preset.
- Copy audio, choose an audio codec and bitrate, or use smart audio conversion.
- Analyze and normalize audio to EBU R128 targets.
- Embed external subtitles and chapters.
- Extract embedded EIA-608 captions from `.ts` recordings.
- Interactively retain English audio and subtitle streams.
- Preserve source ownership and permissions on successful output files.
- Use upgrade and normalization profiles for common batch workflows.

## Requirements

Required:

- Python 3
- FFmpeg and FFprobe
- FFmpeg built with Intel QSV support
- Compatible Intel Quick Sync Video hardware and drivers
- Python packages `argcomplete` and `tqdm`

Install the Python dependencies with:

```bash
python3 -m pip install argcomplete tqdm
```

Some features use additional commands:

- `mediainfo` for MediaInfo display and more accurate frame counts
- `mkvpropedit` from MKVToolNix for chapter embedding
- `nice`, `ionice`, and `stdbuf` on Linux for background priority and progress reporting

The current script also uses the Unix `grp` module and is primarily intended for Linux or another compatible Unix-like system.

## Installation

Clone the repository, then make the script executable:

```bash
git clone https://github.com/diegelmannsj/hvec-transcoder.git hvec-project
cd hvec-project
chmod +x ,hvec
```

Optionally place it in your `PATH`:

```bash
sudo ln -s /path/to/hvec-project/,hvec /usr/local/bin/,hvec
```

## Basic usage

```text
,hvec -i INPUT [options]
,hvec --profile {upgrade,normalize} [-i INPUT]
,hvec --tui [-i DIRECTORY]
```

Without `--remux`, the default operation transcodes video to HEVC using `hevc_qsv`. Audio is copied unless an audio-processing option is selected. Generated output names normally end in `.CONV.mkv`; remuxed files normally end in `.REMUX.mkv`.

## Options

### Input and output

| Option | Description |
| --- | --- |
| `-i`, `--input PATH` | Input video file or directory. Defaults to the current directory for profiles and TUI mode. |
| `-o`, `--output FILE` | Explicit output MKV filename for a single input file. |
| `--out-dir DIR` | Batch output directory. Source subdirectory structure is preserved. |
| `-S`, `--sync-filename` | Match the output basename to the input and change the extension to `.mkv`. |
| `--temp-dir DIR` | Temporary directory used with `--sync-filename`. Default: `/storage/temp/`. |
| `-D`, `--delete` | Delete the source after the output has been created and verified. |
| `-R`, `--recursive` | Include video files in subdirectories. |

### Processing and quality

| Option | Description |
| --- | --- |
| `--profile upgrade` | Recursively transcode non-HEVC files, synchronize filenames, use smart audio, and delete sources. |
| `--profile normalize` | Remux while normalizing audio, synchronize filenames, and delete sources. |
| `-Q`, `--quality N` | QSV global quality. Intended range: 1–51; lower values produce higher quality. Default: 24. |
| `-p`, `--preset PRESET` | `veryfast`, `faster`, `fast`, `medium`, `slow`, `slower`, or `veryslow`. Default: `medium`. |
| `-H`, `--hvec` | Force HEVC transcoding, overriding `--remux`. |
| `-r`, `--remux` | Copy the video stream into MKV without transcoding it. |
| `--skip-hevc` | Skip files whose first detected video codec is already HEVC. |
| `--keep-title` | Preserve the global title metadata tag. |
| `--no-nice` | Disable automatic Linux background-priority adjustment. |

### Audio, subtitles, and chapters

| Option | Description |
| --- | --- |
| `--smart-audio` | Copy AAC, AC3, EAC3, and MP3; convert other audio codecs to EAC3 at 640 kbit/s. |
| `-N`, `--normalize [CSV]` | Normalize audio to EBU R128 (`-23 LUFS`) and optionally use the specified loudness-analysis CSV. |
| `--acodec CODEC` | Encode audio with a selected codec. Audio is copied when no audio option is supplied. |
| `--abitrate RATE` | Set the bitrate when re-encoding audio, such as `192k` or `384k`. |
| `-s`, `--subs FILE [FILE ...]` | Add one or more external subtitle files. |
| `-C`, `--chapters FILE` | Embed an external OGM/TXT or XML chapter file with `mkvpropedit`. |
| `-E`, `--english`, `-k` | Interactively keep video, English audio/subtitles, and detected commentary streams. |

### Interface and diagnostics

| Option | Description |
| --- | --- |
| `-T`, `--tui` | Open the interactive terminal file selector. |
| `-m`, `--mediainfo` | Display MediaInfo for a single input before processing. |
| `--dry-run` | Print the principal FFmpeg output command instead of executing that command. See the limitation below. |
| `-q`, `--quiet` | Suppress most FFmpeg output. |
| `-V`, `--verbose` | Print additional processing information. |
| `-Y`, `--assume-yes` | Automatically answer `yes` to interactive prompts. |
| `-v`, `--version` | Display the embedded version history. |
| `-h`, `--help` | Display command-line help. |

## Examples

Transcode one file with the default QSV settings:

```bash
,hvec -i "My Movie (2025).mp4"
```

The generated filename will normally be `My.Movie.2025.CONV.mkv`.

Transcode a directory recursively and skip existing HEVC files:

```bash
,hvec -i /path/to/videos -R --skip-hevc
```

Remux a file without re-encoding its video or audio:

```bash
,hvec -i movie.mp4 --remux
```

Transcode with external subtitles and chapters:

```bash
,hvec -i movie.mp4 --subs movie.en.srt --chapters chapters.txt
```

Normalize audio while remuxing:

```bash
,hvec -i movie.mkv --normalize --remux
```

Preview the principal FFmpeg output command:

```bash
,hvec -i movie.mp4 --dry-run
```

Launch the interactive selector for a directory tree:

```bash
,hvec --tui -i /path/to/videos --recursive
```

## Important safety notes

### Source deletion

`--delete`, `--profile upgrade`, and `--profile normalize` are destructive. The two profiles enable source deletion automatically. Review the selected files and ensure backups exist before using these options.

With the current implementation, synchronization mode writes the output to the temporary directory and may delete the source before moving the temporary output to its final destination. If that final move fails, manual recovery from `--temp-dir` may be necessary.

### Dry-run limitations

`--dry-run` prevents execution of the principal transcode/remux command and prevents source deletion. It is not currently a completely read-only mode: preparation may create output or temporary directories, run FFprobe, update the probe cache, perform loudness analysis, or attempt `.ts` caption extraction.

### Automatic priority adjustment

On Linux, the script normally relaunches itself with CPU nice level 19 and idle I/O priority. Use `--no-nice` to retain the current process priority.

## Cache and log files

The script stores persistent data under `~/.hvec`:

- `~/.hvec/probe.csv` caches detected video, audio, and subtitle codecs.
- `~/.hvec/audit_loudness.csv` stores loudness-analysis results when normalization is used without another CSV path.

If `audit_loudness.csv` exists in the current directory, normalization prefers that file over the default file in `~/.hvec`.
