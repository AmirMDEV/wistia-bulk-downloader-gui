# Wistia Downloader GUI

Quick Windows GUI for the installed `wistia` downloader.

## What it does

- Paste video IDs in bulk
- Accept direct IDs, Wistia links, or pasted HTML containing `wvideo=...`
- Choose the download folder
- Pick the quality
- Start downloads with one button
- Retry only the failed IDs from the last batch
- Show a live log while the batch runs
- Show overall progress while the batch runs

## Defaults

- Download folder: `T:\Amir\Property`
- Quality: `Original File`

The app remembers your last used folder and quality automatically.

## Launch

Double-click:

- [Launch Wistia Downloader GUI.cmd](C:\Users\Amir Mansaray\Documents\Github\wistia-downloader-gui\Launch%20Wistia%20Downloader%20GUI.cmd)
- Desktop shortcut: [Wistia Downloader GUI.lnk](C:\Users\Amir Mansaray\Desktop\Wistia%20Downloader%20GUI.lnk)

Or run:

```powershell
pyw .\app.pyw
```

## Smoke test

```powershell
py .\app.pyw --smoke-test
```

## Notes

- The GUI uses the installed Python `wistia-downloader` package directly for a cleaner Windows workflow.
- If `wistia-downloader` is missing, the GUI will show an error when you try to start a batch.
