# Wistia Video Downloader

A production-ready command-line tool for downloading Wistia videos with ease. This tool combines video ID extraction, single video downloads, and batch processing into one unified interface.

## Features

- 🎯 **Extract video IDs** from HTML content containing Wistia video links
- 📥 **Download single videos** by providing a video ID
- 📦 **Batch download** multiple videos from a list of IDs
- 🎬 **Quality selection** with support for multiple video qualities
- 📊 **Progress tracking** with detailed download statistics
- 🔄 **Retry logic** for handling network failures
- 📁 **Organized output** with customizable download directories
- 🚀 **Production-ready** with comprehensive error handling

## Installation

### Option 1: Direct Installation (Recommended)

```bash
# Install the package
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"
```

### Option 2: Manual Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Make the script executable
chmod +x wistia.py
```

## Usage

### Command Overview

```bash
wistia <command> [options]
```

### Available Commands

#### 1. Extract Video IDs

Extract video IDs from HTML files containing Wistia video links:

```bash
# Extract IDs from HTML file
wistia extract videos.txt

# Extract IDs and save to custom file
wistia extract videos.txt custom_ids.txt
```

#### 2. Download Single Video

Download a single video by its ID:

```bash
# Download with default quality (720p)
wistia download o1kvat5mfb

# Download with specific quality
wistia download o1kvat5mfb --quality 1080p

# Download to custom directory
wistia download o1kvat5mfb --output-dir /path/to/downloads
```

#### 3. Batch Download

Download multiple videos from a list of IDs:

```bash
# Download all videos from ID list
wistia batch video_ids.txt

# Batch download with custom quality
wistia batch video_ids.txt --quality 540p

# Batch download with custom settings
wistia batch video_ids.txt --quality 1080p --delay 2.0 --max-retries 5
```

#### 4. Extract and Download (One Command)

Extract video IDs from HTML and download them in one step:

```bash
# Extract and download all videos
wistia extract-and-download videos.txt

# Extract, save IDs, and download
wistia extract-and-download videos.txt --save-ids extracted_ids.txt --quality 720p
```

### Global Options

- `--output-dir, -o`: Output directory for downloaded videos (default: `downloads`)
- `--quality, -q`: Video quality preference (default: `720p`)
- `--max-retries`: Maximum number of retries for failed downloads (default: `3`)
- `--delay`: Delay between downloads in seconds (default: `1.0`)
- `--quiet`: Suppress non-error output

### Quality Options

Available video qualities (actual availability depends on the video):
- `Original File` - Original uploaded file
- `1080p` - Full HD
- `720p` - HD (default)
- `540p` - Standard definition
- `360p` - Low definition
- `224p` - Mobile quality

## Examples

### Basic Usage

```bash
# Extract video IDs from HTML file
wistia extract videos.txt

# Download a single video
wistia download abc123def

# Download multiple videos
wistia batch video_ids.txt
```

### Advanced Usage

```bash
# High-quality batch download with custom settings
wistia batch video_ids.txt \
    --quality 1080p \
    --output-dir /Users/me/WistiaVideos \
    --delay 2.0 \
    --max-retries 5

# Extract and download in one command with progress
wistia extract-and-download videos.txt \
    --quality 720p \
    --save-ids backup_ids.txt \
    --output-dir downloads/training-videos

# Quiet mode for automation
wistia batch video_ids.txt --quiet --output-dir /automated/downloads
```

## File Formats

### Input HTML File (videos.txt)

Your HTML file should contain Wistia video links with `wvideo=` parameters:

```html
<p><a href="https://example.com/video?wvideo=abc123def">Video 1</a></p>
<p><a href="https://example.com/video?wvideo=xyz789ghi">Video 2</a></p>
```

### Video ID List File (video_ids.txt)

One video ID per line:

```
abc123def
xyz789ghi
mno456pqr
```

## Output Structure

```
downloads/
├── Video-Title-1_720p.mp4
├── Video-Title-2_1080p.mp4
├── Another-Video_540p.mp4
└── failed_downloads.txt  # Created if any downloads fail
```

## Error Handling

The tool includes comprehensive error handling:

- **Network failures**: Automatic retry with exponential backoff
- **Invalid video IDs**: Logged and skipped
- **Missing files**: Clear error messages
- **Interrupted downloads**: Graceful handling of Ctrl+C
- **Failed downloads**: Logged to `failed_downloads.txt`

## Progress Tracking

- Real-time download progress for each video
- Overall batch progress with statistics
- Summary report at the end of batch operations
- Failed downloads are logged for retry

## Requirements

- Python 3.6 or higher
- Internet connection
- Sufficient disk space for video files

## Copyright Notice

⚠️ **Important**: Make sure you have the copyright or permission to download videos from Wistia. This tool is intended for downloading videos you own or have explicit permission to download. Users are responsible for ensuring they comply with Wistia's terms of service and applicable copyright laws.

## Dependencies

- `requests` - For HTTP requests
- Standard library modules (no additional dependencies)

## Development

### Running Tests

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests (when available)
pytest tests/
```

### Code Formatting

```bash
# Format code
black wistia.py

# Check code style
flake8 wistia.py
```

## Troubleshooting

### Common Issues

1. **"No video IDs found"**
   - Check that your HTML file contains `wvideo=` parameters
   - Verify the file encoding is UTF-8

2. **"Download failed"**
   - Check your internet connection
   - Verify the video ID is correct
   - Try increasing `--max-retries`

3. **"Permission denied"**
   - Check write permissions in the output directory
   - Try using `--output-dir` to specify a different directory

### Getting Help

```bash
# Show help for main command
wistia --help

# Show help for specific subcommand
wistia download --help
wistia batch --help
```

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## Changelog

### v1.0.0
- Initial production release
- Unified CLI interface
- Comprehensive error handling
- Progress tracking and statistics
- Batch processing capabilities
- Quality selection options