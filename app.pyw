from __future__ import annotations

import argparse
import json
import os
import queue
import re
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk
import tkinter as tk
import threading


APP_TITLE = "Wistia Downloader GUI"
DEFAULT_QUALITY = "Original File"
QUALITY_OPTIONS = [
    "Original File",
    "1080p",
    "720p",
    "540p",
    "360p",
    "224p",
]
WISTIA_ID_PATTERNS = [
    re.compile(r"wvideo=([A-Za-z0-9]+)", re.IGNORECASE),
    re.compile(r"/iframe/([A-Za-z0-9]+)", re.IGNORECASE),
]
DIRECT_ID_PATTERN = re.compile(r"^(?=.*\d)[A-Za-z0-9]{8,20}$")


def default_output_dir() -> str:
    downloads_dir = Path.home() / "Downloads"
    if downloads_dir.exists():
        return str(downloads_dir)
    return str(Path.home())


def settings_path() -> Path:
    appdata = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    return appdata / "WistiaDownloaderGUI" / "settings.json"


def load_settings() -> dict[str, str]:
    path = settings_path()
    if not path.exists():
        return {}

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_settings(data: dict[str, str]) -> None:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def unique_ids_from_text(raw_text: str) -> list[str]:
    seen: set[str] = set()
    results: list[str] = []

    def add_candidate(candidate: str) -> None:
        if candidate and candidate not in seen:
            seen.add(candidate)
            results.append(candidate)

    for pattern in WISTIA_ID_PATTERNS:
        for match in pattern.findall(raw_text):
            add_candidate(match)

    for token in re.split(r"[\s,;]+", raw_text):
        cleaned = token.strip().strip("\"'()[]{}<>")
        if DIRECT_ID_PATTERN.fullmatch(cleaned):
            add_candidate(cleaned)

    return results


def resolve_downloader_class():
    try:
        from wistia import WistiaDownloader
    except ImportError as exc:  # pragma: no cover - environment-specific
        raise ImportError(
            "Could not import the installed `wistia-downloader` package. "
            "Reinstall it with `py -m pip install --user --upgrade git+https://github.com/aladagemre/wistia-downloader.git`."
        ) from exc

    return WistiaDownloader


class WistiaGui:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("920x780")
        self.root.minsize(840, 640)
        self.root.configure(bg="#edf2fb")

        self.settings = load_settings()
        self.log_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self.worker_thread: threading.Thread | None = None
        self.stop_requested = False
        self.active_downloader = None
        self.last_failed_ids: list[str] = []
        self.total_items = 0
        self.completed_items = 0

        self.output_dir_var = tk.StringVar(value=self.settings.get("output_dir", default_output_dir()))
        self.quality_var = tk.StringVar(value=self.settings.get("quality", DEFAULT_QUALITY))
        self.status_var = tk.StringVar(value="Ready")
        self.count_var = tk.StringVar(value="0 IDs ready")
        self.progress_text_var = tk.StringVar(value="Progress: 0 / 0")
        self.progress_var = tk.DoubleVar(value=0.0)

        self._configure_styles()
        self._build_layout()
        self._update_count()
        self.root.after(150, self._poll_log_queue)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _configure_styles(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", font=("Segoe UI", 10))
        style.configure("App.TFrame", background="#edf2fb")
        style.configure("Card.TFrame", background="#ffffff")
        style.configure("Header.TLabel", background="#edf2fb", foreground="#13203a", font=("Segoe UI Semibold", 20))
        style.configure("SubHeader.TLabel", background="#edf2fb", foreground="#4c5d79", font=("Segoe UI", 10))
        style.configure("CardTitle.TLabel", background="#ffffff", foreground="#1a2950", font=("Segoe UI Semibold", 11))
        style.configure("Hint.TLabel", background="#ffffff", foreground="#66758f", font=("Segoe UI", 9))
        style.configure("Status.TLabel", background="#edf2fb", foreground="#4c5d79", font=("Segoe UI", 9))
        style.configure("Accent.TButton", font=("Segoe UI Semibold", 10))

    def _build_layout(self) -> None:
        outer = ttk.Frame(self.root, style="App.TFrame", padding=18)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(5, weight=1)

        ttk.Label(outer, text=APP_TITLE, style="Header.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            outer,
            text="Paste Wistia IDs or links, pick a folder and quality, then download in one click.",
            style="SubHeader.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(4, 14))

        settings_card = ttk.Frame(outer, style="Card.TFrame", padding=16)
        settings_card.grid(row=2, column=0, sticky="ew")
        settings_card.columnconfigure(1, weight=1)

        ttk.Label(settings_card, text="Download Settings", style="CardTitle.TLabel").grid(
            row=0, column=0, columnspan=5, sticky="w"
        )
        ttk.Label(
            settings_card,
            text="Your last used folder and quality are remembered automatically.",
            style="Hint.TLabel",
        ).grid(row=1, column=0, columnspan=5, sticky="w", pady=(2, 14))

        ttk.Label(settings_card, text="Download folder").grid(row=2, column=0, sticky="w", padx=(0, 12))
        ttk.Entry(settings_card, textvariable=self.output_dir_var).grid(row=2, column=1, sticky="ew")
        ttk.Button(settings_card, text="Browse", command=self._choose_folder).grid(row=2, column=2, padx=8)
        ttk.Button(settings_card, text="Open Folder", command=self._open_output_folder).grid(row=2, column=3)

        ttk.Label(settings_card, text="Quality").grid(row=3, column=0, sticky="w", padx=(0, 12), pady=(12, 0))
        ttk.Combobox(
            settings_card,
            textvariable=self.quality_var,
            values=QUALITY_OPTIONS,
            state="readonly",
            width=18,
        ).grid(row=3, column=1, sticky="w", pady=(12, 0))

        ids_card = ttk.Frame(outer, style="Card.TFrame", padding=16)
        ids_card.grid(row=3, column=0, sticky="nsew", pady=(14, 0))
        ids_card.columnconfigure(0, weight=1)
        ids_card.rowconfigure(2, weight=1)
        outer.rowconfigure(3, weight=1)

        ttk.Label(ids_card, text="Video IDs", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            ids_card,
            text="Paste one ID per line, comma-separated IDs, or Wistia links/HTML and the app will extract IDs.",
            style="Hint.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 10))

        self.ids_text = scrolledtext.ScrolledText(
            ids_card,
            height=14,
            wrap="word",
            font=("Consolas", 10),
            bd=0,
            relief="flat",
            padx=10,
            pady=10,
        )
        self.ids_text.grid(row=2, column=0, sticky="nsew")
        self.ids_text.bind("<<Modified>>", self._on_text_modified)

        controls = ttk.Frame(ids_card, style="Card.TFrame")
        controls.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        controls.columnconfigure(1, weight=1)

        ttk.Button(controls, text="Paste Clipboard", command=self._paste_clipboard).grid(row=0, column=0, sticky="w")
        ttk.Label(controls, textvariable=self.count_var, style="Hint.TLabel").grid(row=0, column=1, sticky="w", padx=12)
        ttk.Button(controls, text="Clear", command=self._clear_ids).grid(row=0, column=2, padx=(8, 0))

        actions = ttk.Frame(outer, style="App.TFrame")
        actions.grid(row=4, column=0, sticky="ew", pady=(14, 0))
        actions.columnconfigure(1, weight=1)

        buttons = ttk.Frame(actions, style="App.TFrame")
        buttons.grid(row=0, column=0, sticky="w")
        self.download_button = ttk.Button(
            buttons, text="Download Videos", command=self._start_download, style="Accent.TButton"
        )
        self.download_button.grid(row=0, column=0, padx=(0, 8))
        self.retry_button = ttk.Button(
            buttons,
            text="Retry Failed IDs",
            command=self._retry_failed_ids,
            state="disabled",
        )
        self.retry_button.grid(row=0, column=1, padx=(0, 8))
        self.stop_button = ttk.Button(buttons, text="Stop After Current Video", command=self._stop_download, state="disabled")
        self.stop_button.grid(row=0, column=2)

        progress_frame = ttk.Frame(actions, style="App.TFrame")
        progress_frame.grid(row=0, column=1, sticky="ew", padx=(18, 0))
        progress_frame.columnconfigure(0, weight=1)
        ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100).grid(row=0, column=0, sticky="ew")
        ttk.Label(progress_frame, textvariable=self.progress_text_var, style="Status.TLabel").grid(
            row=1, column=0, sticky="w", pady=(4, 0)
        )

        ttk.Label(actions, textvariable=self.status_var, style="Status.TLabel").grid(row=0, column=2, sticky="e", padx=(18, 0))

        log_card = ttk.Frame(outer, style="Card.TFrame", padding=16)
        log_card.grid(row=5, column=0, sticky="nsew", pady=(14, 0))
        log_card.columnconfigure(0, weight=1)
        log_card.rowconfigure(1, weight=1)

        ttk.Label(log_card, text="Download Log", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        self.log_text = scrolledtext.ScrolledText(
            log_card,
            height=12,
            wrap="word",
            font=("Consolas", 10),
            bg="#0f172a",
            fg="#d8e2ff",
            insertbackground="#d8e2ff",
            bd=0,
            relief="flat",
            padx=10,
            pady=10,
        )
        self.log_text.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        self.log_text.configure(state="disabled")
        self._append_log("Ready. Paste IDs or Wistia links to begin.")

    def _choose_folder(self) -> None:
        chosen = filedialog.askdirectory(initialdir=self.output_dir_var.get() or default_output_dir())
        if chosen:
            self.output_dir_var.set(chosen)

    def _open_output_folder(self) -> None:
        path = Path(self.output_dir_var.get().strip() or default_output_dir())
        path.mkdir(parents=True, exist_ok=True)
        os.startfile(path)

    def _paste_clipboard(self) -> None:
        try:
            clipboard_text = self.root.clipboard_get()
        except tk.TclError:
            messagebox.showinfo(APP_TITLE, "Your clipboard is empty or unavailable right now.")
            return

        self.ids_text.delete("1.0", "end")
        self.ids_text.insert("1.0", clipboard_text)
        self._update_count()

    def _clear_ids(self) -> None:
        self.ids_text.delete("1.0", "end")
        self._update_count()

    def _on_text_modified(self, _event: tk.Event | None = None) -> None:
        if self.ids_text.edit_modified():
            self.ids_text.edit_modified(False)
            self._update_count()

    def _update_count(self) -> None:
        ids = unique_ids_from_text(self.ids_text.get("1.0", "end"))
        noun = "ID" if len(ids) == 1 else "IDs"
        self.count_var.set(f"{len(ids)} unique {noun} ready")

    def _append_log(self, message: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message.rstrip() + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _set_running_state(self, running: bool) -> None:
        self.download_button.configure(state="disabled" if running else "normal")
        self.stop_button.configure(state="normal" if running else "disabled")
        if running:
            self.retry_button.configure(state="disabled")
        else:
            self.retry_button.configure(state="normal" if self.last_failed_ids else "disabled")

    def _set_progress(self, completed: int, total: int) -> None:
        self.completed_items = completed
        self.total_items = total
        percent = (completed / total * 100) if total else 0
        self.progress_var.set(percent)
        self.progress_text_var.set(f"Progress: {completed} / {total}")

    def _start_download(self) -> None:
        if self.worker_thread and self.worker_thread.is_alive():
            return

        raw_text = self.ids_text.get("1.0", "end")
        video_ids = unique_ids_from_text(raw_text)
        if not video_ids:
            messagebox.showwarning(APP_TITLE, "Paste at least one valid Wistia video ID or link before downloading.")
            return

        self._begin_download(video_ids, "Starting download")

    def _begin_download(self, video_ids: list[str], intro_message: str) -> None:
        if self.worker_thread and self.worker_thread.is_alive():
            return

        output_dir = Path(self.output_dir_var.get().strip() or default_output_dir())
        output_dir.mkdir(parents=True, exist_ok=True)
        quality = self.quality_var.get().strip() or DEFAULT_QUALITY

        try:
            downloader_class = resolve_downloader_class()
        except ImportError as exc:
            messagebox.showerror(APP_TITLE, str(exc))
            return

        save_settings({"output_dir": str(output_dir), "quality": quality})

        self.stop_requested = False
        self.last_failed_ids = []
        self.active_downloader = downloader_class(
            output_dir=str(output_dir),
            quality=quality,
            max_retries=3,
            delay=1.0,
            quiet=True,
        )
        self._set_progress(0, len(video_ids))
        self._set_running_state(True)
        self.status_var.set(f"Downloading {len(video_ids)} video(s)...")
        self._append_log("")
        self._append_log(f"{intro_message} for {len(video_ids)} video(s)")
        self._append_log(f"Output folder: {output_dir}")
        self._append_log(f"Quality: {quality}")

        self.worker_thread = threading.Thread(
            target=self._run_download_worker,
            args=(video_ids, quality),
            daemon=True,
        )
        self.worker_thread.start()

    def _run_download_worker(self, video_ids: list[str], quality: str) -> None:
        successful = 0
        failed_ids: list[str] = []

        try:
            total = len(video_ids)
            for index, video_id in enumerate(video_ids, start=1):
                if self.stop_requested:
                    break

                self.log_queue.put(("log", f"[{index}/{total}] Downloading {video_id}"))
                success = self.active_downloader.download_single_video(video_id, quality)
                if success:
                    successful += 1
                    self.log_queue.put(("log", f"Completed: {video_id}"))
                else:
                    failed_ids.append(video_id)
                    self.log_queue.put(("log", f"Failed: {video_id}"))

                self.log_queue.put(("progress", {"completed": index, "total": total}))

            summary = {
                "total": len(video_ids),
                "completed": successful + len(failed_ids),
                "successful": successful,
                "failed_ids": failed_ids,
                "stopped": self.stop_requested,
            }
            self.log_queue.put(("done", summary))
        except Exception as exc:  # pragma: no cover - safety net
            self.log_queue.put(("log", f"Unexpected worker error: {exc}"))
            self.log_queue.put(
                (
                    "done",
                    {
                        "total": len(video_ids),
                        "completed": successful + len(failed_ids),
                        "successful": successful,
                        "failed_ids": failed_ids,
                        "stopped": self.stop_requested,
                    },
                )
            )

    def _poll_log_queue(self) -> None:
        while True:
            try:
                event, payload = self.log_queue.get_nowait()
            except queue.Empty:
                break

            if event == "log":
                self._append_log(str(payload))
            elif event == "progress":
                progress = payload if isinstance(payload, dict) else {}
                self._set_progress(int(progress.get("completed", 0)), int(progress.get("total", 0)))
            elif event == "done":
                self._finish_download(payload if isinstance(payload, dict) else {})

        self.root.after(150, self._poll_log_queue)

    def _finish_download(self, summary: dict[str, object]) -> None:
        self._set_running_state(False)
        self.active_downloader = None

        total = int(summary.get("total", 0))
        completed = int(summary.get("completed", 0))
        successful = int(summary.get("successful", 0))
        failed_ids = list(summary.get("failed_ids", []))
        stopped = bool(summary.get("stopped", False))

        self._set_progress(completed, total)
        self.last_failed_ids = failed_ids

        if stopped:
            self.status_var.set("Stopped after current video")
            self._append_log("Stop requested. The batch was stopped.")
            self.retry_button.configure(state="normal" if self.last_failed_ids else "disabled")
            return

        if not failed_ids and successful == total:
            self.status_var.set("Download complete")
            self._append_log("All downloads completed successfully.")
            messagebox.showinfo(APP_TITLE, f"Download complete.\n\nSuccessful: {successful}")
        else:
            self.status_var.set("Download finished with errors")
            self._append_log("Download finished with errors.")
            if failed_ids:
                self._append_log("Failed IDs: " + ", ".join(failed_ids))
            messagebox.showwarning(
                APP_TITLE,
                f"Download finished.\n\nSuccessful: {successful}\nFailed: {len(failed_ids)}",
            )

        self.retry_button.configure(state="normal" if self.last_failed_ids else "disabled")

    def _retry_failed_ids(self) -> None:
        if not self.last_failed_ids:
            messagebox.showinfo(APP_TITLE, "There are no failed IDs ready to retry.")
            self.retry_button.configure(state="disabled")
            return

        self._begin_download(list(self.last_failed_ids), "Retrying failed IDs")

    def _stop_download(self) -> None:
        if not self.worker_thread or not self.worker_thread.is_alive():
            return

        self.stop_requested = True
        self.status_var.set("Stopping after current video...")
        self._append_log("Stop requested. Waiting for the current video to finish...")
        if self.active_downloader is not None:
            try:
                self.active_downloader.session.close()
            except Exception:
                pass

    def _on_close(self) -> None:
        if self.worker_thread and self.worker_thread.is_alive():
            should_close = messagebox.askyesno(
                APP_TITLE, "A download is still running. Do you want to stop it after the current video and close the app?"
            )
            if not should_close:
                return
            self._stop_download()

        self.root.after(150, self.root.destroy)


def run_smoke_test() -> int:
    downloader_class = resolve_downloader_class()
    downloader = downloader_class(
        output_dir=default_output_dir(),
        quality=DEFAULT_QUALITY,
        max_retries=1,
        delay=0.0,
        quiet=True,
    )
    payload = {
        "downloader_class": downloader_class.__name__,
        "settings_path": str(settings_path()),
        "sample_id_parse_count": len(unique_ids_from_text("o1kvat5mfb https://example.com?v=1&wvideo=abc123def")),
        "default_output_dir": default_output_dir(),
        "default_quality": DEFAULT_QUALITY,
        "downloader_has_session": hasattr(downloader, "session"),
    }
    print(json.dumps(payload, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--smoke-test", action="store_true")
    args, _unknown = parser.parse_known_args()

    if args.smoke_test:
        return run_smoke_test()

    root = tk.Tk()
    WistiaGui(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
