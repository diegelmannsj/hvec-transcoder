import errno
import importlib.machinery
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / ",hvec"


def load_hvec():
    loader = importlib.machinery.SourceFileLoader("hvec_under_test", str(SCRIPT_PATH))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


hvec = load_hvec()


class FilenameTests(unittest.TestCase):
    def test_generated_filename_is_sanitized(self):
        result = hvec.generate_output_filename("My Movie (2025)", False, False, False)
        self.assertEqual(result, "My.Movie.2025.CONV.mkv")

    def test_generated_filename_includes_requested_suffixes(self):
        result = hvec.generate_output_filename("Movie.x264", False, True, True, rename_x264=True)
        self.assertEqual(result, "Movie.x265.CONV.NORM.CHAPTERS.mkv")

    def test_working_paths_differ_for_same_basename_in_different_directories(self):
        first = hvec.get_unique_working_output("/tmp", "/media/a/movie.mkv", "/media/a/movie.mp4")
        second = hvec.get_unique_working_output("/tmp", "/media/b/movie.mkv", "/media/b/movie.mp4")
        self.assertNotEqual(first, second)
        self.assertTrue(first.endswith(".mkv"))


class StreamSelectionTests(unittest.TestCase):
    def test_commentary_title_is_read_from_ffprobe_tags(self):
        streams = [
            {"index": 0, "codec_type": "video"},
            {"index": 1, "codec_type": "audio", "tags": {"language": "fra", "title": "Director Commentary"}},
            {"index": 2, "codec_type": "audio", "tags": {"language": "fra"}},
        ]
        kept, removed = hvec.plan_stream_selection(streams)
        self.assertEqual([stream["index"] for stream in kept], [0, 1])
        self.assertEqual([stream["index"] for stream in removed], [2])


class VerificationTests(unittest.TestCase):
    def test_rejects_wrong_transcode_codec(self):
        source = {"format": {"duration": "60"}, "streams": [{"codec_type": "video", "codec_name": "h264"}]}
        output = {"format": {"duration": "60"}, "streams": [{"codec_type": "video", "codec_name": "h264"}]}
        with mock.patch.object(hvec, "probe_media", side_effect=[source, output]):
            valid, reason = hvec.verify_output_file("source", "output", expect_hevc=True)
        self.assertFalse(valid)
        self.assertIn("expected HEVC", reason)

    def test_rejects_large_duration_difference(self):
        source = {"format": {"duration": "600"}, "streams": [{"codec_type": "video", "codec_name": "h264"}]}
        output = {"format": {"duration": "500"}, "streams": [{"codec_type": "video", "codec_name": "hevc"}]}
        with mock.patch.object(hvec, "probe_media", side_effect=[source, output]):
            valid, reason = hvec.verify_output_file("source", "output", expect_hevc=True)
        self.assertFalse(valid)
        self.assertIn("duration differs", reason)

    def test_accepts_valid_hevc_output(self):
        source = {"format": {"duration": "600"}, "streams": [{"codec_type": "video", "codec_name": "h264"}]}
        output = {"format": {"duration": "599.5"}, "streams": [{"codec_type": "video", "codec_name": "hevc"}]}
        with mock.patch.object(hvec, "probe_media", side_effect=[source, output]):
            valid, reason = hvec.verify_output_file("source", "output", expect_hevc=True)
        self.assertTrue(valid)
        self.assertIsNone(reason)


class FinalizationTests(unittest.TestCase):
    def test_direct_finalization_replaces_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            working = root / "working"
            destination = root / "destination"
            working.write_text("encoded")
            destination.write_text("original")
            hvec.finalize_sync_output(str(working), str(destination))
            self.assertEqual(destination.read_text(), "encoded")
            self.assertFalse(working.exists())

    def test_cross_device_finalization_stages_before_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            working = root / "working"
            destination = root / "destination"
            working.write_text("encoded")
            destination.write_text("original")
            real_replace = hvec.os.replace
            calls = 0

            def replace(source, target):
                nonlocal calls
                calls += 1
                if calls == 1:
                    raise OSError(errno.EXDEV, "simulated cross-device move")
                return real_replace(source, target)

            with mock.patch.object(hvec.os, "replace", side_effect=replace):
                hvec.finalize_sync_output(str(working), str(destination))
            self.assertEqual(destination.read_text(), "encoded")
            self.assertFalse(working.exists())
            self.assertEqual(list(root.glob(".*.hvec-*")), [])

    def test_finalization_failure_preserves_source_and_working_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            working = root / "working"
            destination = root / "destination"
            working.write_text("encoded")
            destination.write_text("original")
            with mock.patch.object(hvec.os, "replace", side_effect=PermissionError("denied")):
                with self.assertRaises(PermissionError):
                    hvec.finalize_sync_output(str(working), str(destination))
            self.assertEqual(destination.read_text(), "original")
            self.assertEqual(working.read_text(), "encoded")


class ArtifactTests(unittest.TestCase):
    def test_cleanup_removes_registered_files(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "caption.srt"
            artifact.write_text("temporary")
            manager = hvec.TemporaryArtifacts()
            manager.add(str(artifact))
            manager.cleanup()
            self.assertFalse(artifact.exists())


class ProcessTests(unittest.TestCase):
    def test_termination_escalates_after_timeout(self):
        class FakeProcess:
            pid = 4321

            def __init__(self):
                self.wait_calls = 0

            def poll(self):
                return None

            def wait(self, timeout):
                self.wait_calls += 1
                if self.wait_calls == 1:
                    raise subprocess.TimeoutExpired("ffmpeg", timeout)
                return 0

        process = FakeProcess()
        with mock.patch.object(hvec.os, "killpg") as killpg:
            hvec.terminate_process(process, timeout=0.01)
        self.assertEqual(killpg.call_args_list, [
            mock.call(process.pid, hvec.signal.SIGTERM),
            mock.call(process.pid, hvec.signal.SIGKILL),
        ])


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg and FFprobe are required")
class SyntheticMediaTests(unittest.TestCase):
    def create_source(self, path, duration="1"):
        subprocess.run([
            "ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=black:size=64x64:rate=10",
            "-t", duration, "-c:v", "mpeg4", str(path)
        ], check=True)

    def test_real_ffprobe_duration_validation(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as directory:
            root = Path(directory)
            source = root / "source.mkv"
            matching = root / "matching.mkv"
            short = root / "short.mkv"
            subprocess.run([
                "ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=black:size=64x64:rate=10",
                "-t", "8", "-c:v", "mpeg4", str(source)
            ], check=True)
            shutil.copy2(source, matching)
            subprocess.run([
                "ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=black:size=64x64:rate=10",
                "-t", "1", "-c:v", "mpeg4", str(short)
            ], check=True)

            valid, reason = hvec.verify_output_file(str(source), str(matching), expect_hevc=False)
            self.assertTrue(valid, reason)
            valid, reason = hvec.verify_output_file(str(source), str(short), expect_hevc=False)
            self.assertFalse(valid)
            self.assertIn("duration differs", reason)

    def test_script_dry_run_does_not_create_temp_directory(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as directory:
            root = Path(directory)
            source = root / "source.mkv"
            missing_temp = root / "not-created"
            subprocess.run([
                "ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=black:size=64x64:rate=10",
                "-t", "1", "-c:v", "mpeg4", str(source)
            ], check=True)
            result = subprocess.run([
                str(SCRIPT_PATH), "--no-nice", "--dry-run", "--sync-filename",
                "--temp-dir", str(missing_temp), "-i", str(source)
            ], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(result.stdout.startswith(",hvec Transcoder v"))
            self.assertFalse(missing_temp.exists())

    def test_script_remuxes_and_verifies_synthetic_media(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as directory:
            root = Path(directory)
            source = root / "source.mkv"
            output = root / "output.mkv"
            subprocess.run([
                "ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=black:size=64x64:rate=10",
                "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
                "-t", "1", "-c:v", "mpeg4", "-c:a", "aac", str(source)
            ], check=True)
            result = subprocess.run([
                str(SCRIPT_PATH), "--no-nice", "--quiet", "--remux",
                "--output", str(output), "-i", str(source)
            ], input="n\n", capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output.exists())
            valid, reason = hvec.verify_output_file(str(source), str(output), expect_hevc=False)
            self.assertTrue(valid, reason)

    def test_progress_mode_completes_without_pipe_deadlock(self):
        from tqdm import tqdm as tqdm_impl

        with tempfile.TemporaryDirectory(dir="/tmp") as directory:
            root = Path(directory)
            source = root / "source.mkv"
            output = root / "output.mkv"
            subprocess.run([
                "ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=black:size=64x64:rate=10",
                "-t", "1", "-c:v", "mpeg4", str(source)
            ], check=True)
            command = [
                "ffmpeg", "-y", "-nostdin", "-v", "error", "-progress", "-", "-nostats",
                "-i", str(source), "-c", "copy", str(output)
            ]
            hvec.tqdm = tqdm_impl
            success = hvec.run_ffmpeg_command(
                command, str(source), delete_source=False, expect_hevc=False,
                total_frames=10
            )
            self.assertTrue(success)
            self.assertTrue(output.exists())

    def test_failed_verification_preserves_source(self):
        from tqdm import tqdm as tqdm_impl

        with tempfile.TemporaryDirectory(dir="/tmp") as directory:
            root = Path(directory)
            source = root / "source.mkv"
            output = root / "output.mkv"
            self.create_source(source)
            hvec.tqdm = tqdm_impl
            success = hvec.run_ffmpeg_command(
                ["ffmpeg", "-y", "-v", "error", "-i", str(source), "-c", "copy", str(output)],
                str(source), delete_source=True, expect_hevc=True
            )
            self.assertFalse(success)
            self.assertTrue(source.exists())
            self.assertFalse(output.exists())

    def test_verified_output_allows_requested_source_deletion(self):
        from tqdm import tqdm as tqdm_impl

        with tempfile.TemporaryDirectory(dir="/tmp") as directory:
            root = Path(directory)
            source = root / "source.mkv"
            output = root / "output.mkv"
            self.create_source(source)
            hvec.tqdm = tqdm_impl
            success = hvec.run_ffmpeg_command(
                ["ffmpeg", "-y", "-v", "error", "-i", str(source), "-c", "copy", str(output)],
                str(source), delete_source=True, expect_hevc=False
            )
            self.assertTrue(success)
            self.assertFalse(source.exists())
            self.assertTrue(output.exists())


class CliTests(unittest.TestCase):
    def test_version_is_first_and_requires_no_input(self):
        result = subprocess.run([str(SCRIPT_PATH), "--no-nice", "--version"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertTrue(result.stdout.startswith(",hvec Transcoder v"))

    def test_audio_bitrate_requires_codec(self):
        result = subprocess.run([
            str(SCRIPT_PATH), "--no-nice", "-i", str(SCRIPT_PATH), "--abitrate", "192k"
        ], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("--abitrate requires --acodec", result.stderr)


if __name__ == "__main__":
    unittest.main()
