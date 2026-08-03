import tempfile
import unittest
from inspect import signature
from pathlib import Path
from unittest.mock import patch

from shorts_generator.local.downloader import (
    _existing_download,
    _extract_remote_video_id,
    _resolve_local_path,
)
from shorts_generator.pipeline import _is_bilibili_url, generate_shorts
from shorts_generator.local.clipper import _ratio


class BilibiliUrlTests(unittest.TestCase):
    def test_recognizes_bilibili_hosts(self):
        self.assertTrue(_is_bilibili_url("https://www.bilibili.com/video/BV1ttTX6JED2/"))
        self.assertTrue(_is_bilibili_url("https://b23.tv/abc123"))
        self.assertFalse(_is_bilibili_url("https://example.com/video/BV1ttTX6JED2"))

    def test_extracts_bilibili_video_id(self):
        self.assertEqual(
            _extract_remote_video_id("https://www.bilibili.com/video/BV1ttTX6JED2/?p=2"),
            "BV1ttTX6JED2",
        )
        self.assertEqual(
            _extract_remote_video_id("https://www.bilibili.com/video/?bvid=BV1ttTX6JED2"),
            "BV1ttTX6JED2",
        )

    @patch("shorts_generator.pipeline._run_local")
    def test_bilibili_defaults_to_local_mode(self, run_local):
        run_local.return_value = {"mode": "local"}

        result = generate_shorts("https://www.bilibili.com/video/BV1ttTX6JED2/")

        self.assertEqual(result["mode"], "local")
        run_local.assert_called_once()


class LocalPathTests(unittest.TestCase):
    def test_resolves_direct_and_file_urls(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            media = Path(tmp_dir) / "测试 video.mp4"
            media.touch()

            self.assertEqual(_resolve_local_path(str(media)), str(media.resolve()))
            self.assertEqual(_resolve_local_path(media.as_uri()), str(media.resolve()))

    def test_finds_bilibili_part_cache(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            cached = Path(tmp_dir) / "source_BV1HkK26QEub_p1.mp4"
            cached.touch()

            self.assertEqual(
                _existing_download(tmp_dir, "BV1HkK26QEub"),
                str(cached),
            )


class AspectRatioTests(unittest.TestCase):
    def test_default_output_is_horizontal(self):
        self.assertEqual(signature(generate_shorts).parameters["aspect_ratio"].default, "16:9")
        self.assertAlmostEqual(_ratio("16:9"), 16 / 9)

    def test_invalid_ratio_falls_back_to_horizontal(self):
        self.assertAlmostEqual(_ratio("invalid"), 16 / 9)


if __name__ == "__main__":
    unittest.main()
