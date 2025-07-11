#!/usr/bin/env python3
"""
Wistia Video Downloader CLI Tool
A production-ready command-line interface for downloading Wistia videos.

Features:
- Extract video IDs from HTML content
- Download single videos by ID
- Batch download multiple videos
- Quality selection
- Progress tracking
- Error handling and retry logic
"""

import argparse
import requests
import json
import re
import os
import sys
import time
import logging
from pathlib import Path
from urllib.parse import urlparse
from typing import List, Dict, Optional, Tuple
import threading
from queue import Queue
import signal


class WistiaDownloader:
    """Main Wistia downloader class with comprehensive functionality"""

    def __init__(
        self,
        output_dir: str = "downloads",
        quality: str = "720p",
        max_retries: int = 3,
        delay: float = 1.0,
        quiet: bool = False,
    ):
        self.output_dir = Path(output_dir)
        self.quality = quality
        self.max_retries = max_retries
        self.delay = delay
        self.quiet = quiet
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        )

        # Create output directory
        self.output_dir.mkdir(exist_ok=True)

        # Setup logging
        logging.basicConfig(
            level=logging.INFO if not quiet else logging.WARNING,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)

        # Statistics
        self.stats = {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "failed_ids": [],
        }

    def extract_video_ids(self, input_file: str, output_file: str = None) -> List[str]:
        """Extract video IDs from HTML content"""
        input_path = Path(input_file)

        if not input_path.exists():
            raise FileNotFoundError(f"Input file '{input_file}' not found")

        with open(input_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Pattern to match wvideo= followed by the video ID
        pattern = r"wvideo=([a-zA-Z0-9]+)"
        matches = re.findall(pattern, content)

        if not matches:
            self.logger.warning("No video IDs found in the input file")
            return []

        # Remove duplicates while preserving order
        seen = set()
        unique_video_ids = []
        for video_id in matches:
            if video_id not in seen:
                seen.add(video_id)
                unique_video_ids.append(video_id)

        self.logger.info(
            f"Found {len(matches)} video ID(s) ({len(unique_video_ids)} unique)"
        )

        # Write to output file if specified
        if output_file:
            output_path = Path(output_file)
            with open(output_path, "w", encoding="utf-8") as f:
                for video_id in unique_video_ids:
                    f.write(f"{video_id}\n")
            self.logger.info(f"Video IDs written to '{output_file}'")

        return unique_video_ids

    def get_embed_data(self, video_id: str) -> Dict:
        """Fetch embed data from Wistia iframe"""
        embed_url = f"https://fast.wistia.net/embed/iframe/{video_id}"

        for attempt in range(self.max_retries):
            try:
                response = self.session.get(embed_url, timeout=30)
                response.raise_for_status()

                content = response.text
                pattern = r"W\.iframeInit\((.*?)\);"
                match = re.search(pattern, content, re.DOTALL)

                if not match:
                    raise ValueError("Could not find video data in embed page")

                full_match = match.group(1).strip()

                # Find the balanced braces for the JSON object
                brace_count = 0
                json_end = 0

                for i, char in enumerate(full_match):
                    if char == "{":
                        brace_count += 1
                    elif char == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break

                if json_end == 0:
                    raise ValueError("Could not find complete JSON object")

                json_str = full_match[:json_end]
                data = json.loads(json_str)
                return data

            except (requests.RequestException, json.JSONDecodeError, ValueError) as e:
                if attempt < self.max_retries - 1:
                    self.logger.warning(
                        f"Attempt {attempt + 1} failed for video {video_id}: {e}"
                    )
                    time.sleep(self.delay * (attempt + 1))
                else:
                    raise Exception(
                        f"Failed to fetch embed data after {self.max_retries} attempts: {e}"
                    )

    def extract_video_urls(self, embed_data: Dict) -> List[Dict]:
        """Extract video URLs from embed data"""
        if "assets" not in embed_data:
            raise ValueError("No assets found in embed data")

        video_assets = []

        for asset in embed_data["assets"]:
            if asset.get("type") in [
                "original",
                "hd_mp4_video",
                "md_mp4_video",
                "mp4_video",
                "iphone_video",
            ]:
                video_assets.append(
                    {
                        "quality": asset.get("display_name")
                        or asset.get("slug")
                        or "unknown",
                        "url": asset.get("url"),
                        "width": asset.get("width"),
                        "height": asset.get("height"),
                        "size": asset.get("size"),
                        "bitrate": asset.get("bitrate"),
                        "ext": asset.get("ext", "mp4"),
                    }
                )

        # Sort by quality (highest first)
        video_assets.sort(key=lambda x: x["bitrate"] or 0, reverse=True)

        return video_assets

    def select_quality(
        self, video_urls: List[Dict], quality_preference: str = None
    ) -> Dict:
        """Select video quality based on preference"""
        if not video_urls:
            raise ValueError("No video URLs available")

        if quality_preference is None:
            quality_preference = self.quality

        # Try exact match first
        quality_lower = quality_preference.lower()
        for video in video_urls:
            if video["quality"] and video["quality"].lower() == quality_lower:
                return video

        # Try partial match
        for video in video_urls:
            if video["quality"] and quality_lower in video["quality"].lower():
                return video

        # Default to highest quality
        self.logger.warning(
            f"Quality '{quality_preference}' not found, using highest quality"
        )
        return video_urls[0]

    def download_video(self, url: str, filename: str, video_info: Dict) -> bool:
        """Download video from URL with progress tracking"""
        try:
            if not self.quiet:
                print(
                    f"Downloading {video_info['quality']} ({video_info['width']}x{video_info['height']})..."
                )

            response = self.session.get(url, stream=True, timeout=30)
            response.raise_for_status()

            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0

            with open(filename, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        if total_size > 0 and not self.quiet:
                            progress = (downloaded / total_size) * 100
                            print(f"\rProgress: {progress:.1f}%", end="", flush=True)

            if not self.quiet:
                print(f"\nDownload completed: {filename}")

            return True

        except Exception as e:
            self.logger.error(f"Download failed: {e}")
            return False

    def download_single_video(self, video_id: str, quality: str = None) -> bool:
        """Download a single video by ID"""
        try:
            self.logger.info(f"Fetching video data for ID: {video_id}")
            embed_data = self.get_embed_data(video_id)

            video_title = embed_data.get("name", f"wistia_{video_id}")
            video_urls = self.extract_video_urls(embed_data)

            if not video_urls:
                self.logger.error("No video URLs found")
                return False

            selected_video = self.select_quality(video_urls, quality)

            # Create safe filename
            safe_title = re.sub(r"[^\w\s-]", "", video_title).strip()
            safe_title = re.sub(r"[-\s]+", "-", safe_title)
            filename = (
                self.output_dir
                / f"{safe_title}_{selected_video['quality']}.{selected_video['ext']}"
            )

            # Skip if file already exists
            if filename.exists():
                self.logger.info(f"File already exists, skipping: {filename}")
                return True

            return self.download_video(selected_video["url"], filename, selected_video)

        except Exception as e:
            self.logger.error(f"Error downloading video {video_id}: {e}")
            return False

    def download_batch(self, video_ids: List[str], quality: str = None) -> Dict:
        """Download multiple videos"""
        self.stats["total"] = len(video_ids)

        if not self.quiet:
            print(f"Starting batch download of {len(video_ids)} videos...")
            print(f"Quality: {quality or self.quality}")
            print(f"Output directory: {self.output_dir}")
            print("-" * 50)

        for i, video_id in enumerate(video_ids, 1):
            if not self.quiet:
                print(f"\n[{i}/{len(video_ids)}] Processing video ID: {video_id}")

            success = self.download_single_video(video_id, quality)

            if success:
                self.stats["successful"] += 1
                self.logger.info(f"✓ Successfully downloaded: {video_id}")
            else:
                self.stats["failed"] += 1
                self.stats["failed_ids"].append(video_id)
                self.logger.error(f"✗ Failed to download: {video_id}")

            # Delay between downloads
            if i < len(video_ids) and self.delay > 0:
                time.sleep(self.delay)

        return self.stats

    def print_summary(self):
        """Print download summary"""
        if self.quiet:
            return

        print("\n" + "=" * 50)
        print("DOWNLOAD SUMMARY")
        print("=" * 50)
        print(f"Total videos: {self.stats['total']}")
        print(f"Successful: {self.stats['successful']}")
        print(f"Failed: {self.stats['failed']}")
        print(f"Skipped: {self.stats['skipped']}")

        if self.stats["failed_ids"]:
            print(f"\nFailed video IDs:")
            for failed_id in self.stats["failed_ids"]:
                print(f"  - {failed_id}")

            # Write failed IDs to file
            failed_file = self.output_dir / "failed_downloads.txt"
            with open(failed_file, "w") as f:
                for failed_id in self.stats["failed_ids"]:
                    f.write(f"{failed_id}\n")
            print(f"\nFailed IDs written to: {failed_file}")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Wistia Video Downloader - Download Wistia videos with ease",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract video IDs from HTML file
  python wistia.py extract videos.txt

  # Download single video
  python wistia.py download o1kvat5mfb

  # Download with specific quality
  python wistia.py download o1kvat5mfb --quality 1080p

  # Batch download from ID list
  python wistia.py batch video_ids.txt

  # Extract and download in one command
  python wistia.py extract-and-download videos.txt --quality 720p

Available qualities: 1080p, 720p, 540p, 360p, 224p, "Original File"
        """,
    )

    # Global options
    parser.add_argument(
        "--output-dir",
        "-o",
        default="downloads",
        help="Output directory for downloaded videos (default: downloads)",
    )
    parser.add_argument(
        "--quality",
        "-q",
        default="720p",
        help="Video quality preference (default: 720p)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum number of retries for failed downloads (default: 3)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between downloads in seconds (default: 1.0)",
    )
    parser.add_argument(
        "--quiet", action="store_true", help="Suppress non-error output"
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Extract command
    extract_parser = subparsers.add_parser(
        "extract", help="Extract video IDs from HTML file"
    )
    extract_parser.add_argument("input_file", help="HTML file containing video links")
    extract_parser.add_argument(
        "output_file",
        nargs="?",
        default="video_ids.txt",
        help="Output file for video IDs (default: video_ids.txt)",
    )

    # Download command
    download_parser = subparsers.add_parser(
        "download", help="Download single video by ID"
    )
    download_parser.add_argument("video_id", help="Wistia video ID")
    download_parser.add_argument(
        "--quality", "-q", help="Video quality preference (overrides global setting)"
    )

    # Batch command
    batch_parser = subparsers.add_parser(
        "batch", help="Download multiple videos from ID list"
    )
    batch_parser.add_argument(
        "ids_file", help="File containing video IDs (one per line)"
    )
    batch_parser.add_argument(
        "--quality", "-q", help="Video quality preference (overrides global setting)"
    )

    # Extract and download command
    extract_download_parser = subparsers.add_parser(
        "extract-and-download", help="Extract IDs and download videos"
    )
    extract_download_parser.add_argument(
        "input_file", help="HTML file containing video links"
    )
    extract_download_parser.add_argument(
        "--save-ids", help="Save extracted IDs to file"
    )
    extract_download_parser.add_argument(
        "--quality", "-q", help="Video quality preference (overrides global setting)"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Initialize downloader
    downloader = WistiaDownloader(
        output_dir=args.output_dir,
        quality=args.quality or "720p",
        max_retries=args.max_retries,
        delay=args.delay,
        quiet=args.quiet,
    )

    try:
        if args.command == "extract":
            video_ids = downloader.extract_video_ids(args.input_file, args.output_file)
            if not args.quiet:
                print(f"\nExtracted {len(video_ids)} unique video IDs")
                for i, video_id in enumerate(video_ids, 1):
                    print(f"{i}. {video_id}")

        elif args.command == "download":
            success = downloader.download_single_video(args.video_id, args.quality)
            if success:
                print("Download completed successfully!")
                return 0
            else:
                print("Download failed!")
                return 1

        elif args.command == "batch":
            # Read video IDs from file
            ids_file = Path(args.ids_file)
            if not ids_file.exists():
                print(f"Error: File '{args.ids_file}' not found")
                return 1

            with open(ids_file, "r") as f:
                video_ids = [line.strip() for line in f if line.strip()]

            if not video_ids:
                print("No video IDs found in file")
                return 1

            stats = downloader.download_batch(video_ids, args.quality)
            downloader.print_summary()

            return 0 if stats["failed"] == 0 else 1

        elif args.command == "extract-and-download":
            # Extract IDs
            video_ids = downloader.extract_video_ids(args.input_file, args.save_ids)

            if not video_ids:
                print("No video IDs found to download")
                return 1

            # Download videos
            stats = downloader.download_batch(video_ids, args.quality)
            downloader.print_summary()

            return 0 if stats["failed"] == 0 else 1

    except KeyboardInterrupt:
        print("\nDownload interrupted by user")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
