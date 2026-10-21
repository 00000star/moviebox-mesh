#!/usr/bin/env python3
"""
MovieBox Mesh - Detached Background Sci-Fi Downloader & Auto-English Engine
Runs as a true POSIX daemon independent of Termux UI / window state.
Survives Termux being closed, app switching, and screen sleep via wakelock.
"""

import os
import sys
import time
import json
import re
import signal
import urllib.request
import urllib.parse
import subprocess
from concurrent.futures import ThreadPoolExecutor

BASE_DIR = "/storage/emulated/0/Movies/MovieBox/Movies"
PID_FILE = "/sdcard/Antigravity_Projects/moviebox-mesh/.downloader.pid"
LOG_FILE = "/sdcard/Antigravity_Projects/moviebox-mesh/downloader.log"
os.makedirs(BASE_DIR, exist_ok=True)

def sanitize_name(name):
    clean = re.sub(r'[\/*?:"<>|]', '', name)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean

SCIFI_CATALOG = [
    {
        "title": "Interstellar",
        "year": "2014",
        "imdb": "tt0816692",
        "direct_url": None
    },
    {
        "title": "Arrival",
        "year": "2016",
        "imdb": "tt2543164",
        "direct_url": None
    },
    {
        "title": "Blade Runner 2049",
        "year": "2017",
        "imdb": "tt1856101",
        "direct_url": "https://pixeldrain.dev/api/file/wX3n4ARf?download"
    },
    {
        "title": "Dune: Part One",
        "clean_title": "Dune Part One",
        "year": "2021",
        "imdb": "tt1160419",
        "direct_url": "https://pixeldrain.dev/api/file/PDua4TGu?download"
    },
    {
        "title": "Ex Machina",
        "year": "2014",
        "imdb": "tt0470752",
        "direct_url": "https://pixeldrain.dev/api/file/g9zpswZB?download"
    },
    {
        "title": "The Matrix",
        "year": "1999",
        "imdb": "tt0133093",
        "direct_url": "https://pixeldrain.dev/api/file/eLQHck7m?download"
    },
    {
        "title": "Inception",
        "year": "2010",
        "imdb": "tt1375666",
        "direct_url": "https://pixeldrain.dev/api/file/deYdTX4T?download"
    },
    {
        "title": "Dune: Part Two",
        "clean_title": "Dune Part Two",
        "year": "2024",
        "imdb": "tt15239678",
        "direct_url": "https://pixeldrain.dev/api/file/rQMJtTCY?download"
    },
    {
        "title": "Everything Everywhere All at Once",
        "year": "2022",
        "imdb": "tt6710474",
        "direct_url": "https://pixeldrain.dev/api/file/bDViahqV?download"
    },
    {
        "title": "District 9",
        "year": "2009",
        "imdb": "tt1136608",
        "direct_url": "https://pixeldrain.dev/api/file/pdtPN7K9?download"
    },
    {
        "title": "Edge of Tomorrow",
        "year": "2014",
        "imdb": "tt1631867",
        "direct_url": None
    }
]

def acquire_wakelock():
    try:
        subprocess.run(["termux-wake-lock"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

def promote_english_audio(fpath):
    cmd = ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index:stream_tags=language,LANGUAGE", "-of", "json", fpath]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if res.returncode != 0:
            return
        data = json.loads(res.stdout)
        streams = data.get("streams", [])
        if len(streams) >= 2:
            tags0 = streams[0].get("tags", {})
            tags1 = streams[1].get("tags", {})
            l0 = (tags0.get("language") or tags0.get("LANGUAGE") or "").lower()
            l1 = (tags1.get("language") or tags1.get("LANGUAGE") or "").lower()
            if "hin" in l0 and "eng" in l1:
                dirname = os.path.dirname(fpath)
                base = os.path.basename(fpath)
                temp_path = os.path.join(dirname, "temp_eng_" + base)
                swap_cmd = [
                    "ffmpeg", "-y", "-i", fpath,
                    "-map", "0:v:0", "-map", "0:a:1", "-map", "0:a:0",
                    "-disposition:a:0", "default", "-disposition:a:1", "none",
                    "-c", "copy", temp_path
                ]
                swap_res = subprocess.run(swap_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
                if swap_res.returncode == 0 and os.path.exists(temp_path) and os.path.getsize(temp_path) > 50*1024*1024:
                    os.replace(temp_path, fpath)
                    print(f"🔊 English promoted to Default for: {base}")
    except Exception:
        pass

class ResilientDownloader:
    def __init__(self, url, dest_path, num_workers=4):
        self.url = url
        self.dest_path = dest_path
        self.part_path = dest_path + ".part"
        self.meta_path = dest_path + ".meta.json"
        self.num_workers = num_workers
        self.total_size = 0
        self.downloaded = 0
        self.start_time = 0
        self.accepts_ranges = False
        self.running = False
        self.offsets = []

    def probe(self):
        req = urllib.request.Request(self.url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as res:
            self.total_size = int(res.headers.get("Content-Length", 0))
            self.accepts_ranges = res.headers.get("Accept-Ranges", "").lower() == "bytes"

    def load_meta(self):
        if os.path.exists(self.meta_path) and os.path.exists(self.part_path):
            try:
                with open(self.meta_path, "r") as f:
                    meta = json.load(f)
                    if meta.get("total_size") == self.total_size and len(meta.get("offsets", [])) == self.num_workers:
                        self.offsets = meta["offsets"]
                        self.downloaded = sum(meta.get("progress", [0] * self.num_workers))
                        print(f"🔄 Resuming from cached progress: {self.downloaded / (1024*1024):.1f} MB already downloaded")
                        return True
            except Exception:
                pass
        return False

    def save_meta(self, progress_arr):
        try:
            with open(self.meta_path, "w") as f:
                json.dump({
                    "total_size": self.total_size,
                    "offsets": self.offsets,
                    "progress": progress_arr,
                    "ts": time.time()
                }, f)
        except Exception:
            pass

    def download_slice(self, fd, slice_idx, start, end, progress_arr, max_retries=10):
        chunk_size = 256 * 1024
        cur_offset = self.offsets[slice_idx]
        for attempt in range(max_retries):
            if not self.running:
                break
            try:
                req = urllib.request.Request(self.url, headers={
                    "User-Agent": "Mozilla/5.0",
                    "Range": f"bytes={cur_offset}-{end}"
                })
                with urllib.request.urlopen(req, timeout=30) as res:
                    while cur_offset <= end and self.running:
                        buf = res.read(min(chunk_size, end - cur_offset + 1))
                        if not buf:
                            break
                        os.pwrite(fd, buf, cur_offset)
                        n = len(buf)
                        cur_offset += n
                        self.downloaded += n
                        progress_arr[slice_idx] += n
                        self.offsets[slice_idx] = cur_offset
                if cur_offset > end:
                    return True
            except Exception as e:
                if attempt < max_retries - 1 and self.running:
                    time.sleep(3.0 * (attempt + 1))
        return cur_offset > end

    def print_progress(self):
        while self.running and self.downloaded < self.total_size:
            time.sleep(1.0)
            elapsed = time.time() - self.start_time
            if elapsed <= 0 or self.total_size <= 0:
                continue
            speed = (self.downloaded / (1024 * 1024)) / elapsed
            pct = min((self.downloaded / self.total_size) * 100, 100.0)
            rem = max(self.total_size - self.downloaded, 0)
            eta_s = int(rem / (speed * 1024 * 1024)) if speed > 0 else 0
            eta_m, eta_sec = divmod(eta_s, 60)
            curr_mb = self.downloaded / (1024 * 1024)
            tot_mb = self.total_size / (1024 * 1024)
            
            bar_len = 10
            filled = int(bar_len * (pct / 100))
            bar = "=" * filled + ">" if filled < bar_len else "=" * bar_len
            bar = bar.ljust(bar_len)
            
            line = f"[{bar}] {pct:4.1f}% {curr_mb:.0f}/{tot_mb:.0f}MB {speed:.1f}MB/s ETA:{eta_m:02d}m{eta_sec:02d}s"
            sys.stdout.write(f"\r{line[:68]}")
            sys.stdout.flush()

    def start(self):
        self.probe()
        if self.total_size <= 0:
            print("✘ Error: Content-Length invalid or unavailable.")
            return False

        print(f"📦 Size: {self.total_size / (1024*1024):.1f} MB | Slices: {self.num_workers} parallel")
        
        slice_len = self.total_size // self.num_workers
        slices = []
        for i in range(self.num_workers):
            st = i * slice_len
            en = self.total_size - 1 if i == self.num_workers - 1 else (st + slice_len - 1)
            slices.append((st, en))

        progress_arr = [0] * self.num_workers
        resumed = self.load_meta()
        if not resumed:
            self.offsets = [st for st, _ in slices]
            fd = os.open(self.part_path, os.O_RDWR | os.O_CREAT | os.O_TRUNC)
            os.ftruncate(fd, self.total_size)
        else:
            fd = os.open(self.part_path, os.O_RDWR)

        try:
            self.start_time = time.time()
            self.running = True

            import threading
            prog_thread = threading.Thread(target=self.print_progress, daemon=True)
            prog_thread.start()

            futures = []
            with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
                for i in range(self.num_workers):
                    _, en = slices[i]
                    futures.append(executor.submit(self.download_slice, fd, i, self.offsets[i], en, progress_arr))
                for f in futures:
                    if not f.result():
                        self.running = False
                        self.save_meta(progress_arr)
                        print("\n✘ Slice stalled after retries; state saved for resume.")
                        return False

            self.running = False
            elapsed = max(time.time() - self.start_time, 0.001)
            avg_speed = (self.total_size / (1024 * 1024)) / elapsed
            print(f"\n✔ Done in {elapsed:.1f}s (Avg: {avg_speed:.2f} MB/s)")
            os.close(fd)
            fd = None

            if os.path.exists(self.meta_path):
                try: os.unlink(self.meta_path)
                except Exception: pass

            if os.path.exists(self.dest_path):
                os.unlink(self.dest_path)
            os.rename(self.part_path, self.dest_path)
            return True
        finally:
            self.running = False
            self.save_meta(progress_arr)
            if fd is not None:
                os.close(fd)

def daemonize():
    try:
        pid = os.fork()
        if pid > 0: sys.exit(0)
    except OSError: sys.exit(1)
    os.setsid()
    try:
        pid = os.fork()
        if pid > 0: sys.exit(0)
    except OSError: sys.exit(1)

    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    sys.stdout.flush()
    sys.stderr.flush()
    log = open(LOG_FILE, "a+", buffering=1)
    os.dup2(log.fileno(), sys.stdout.fileno())
    os.dup2(log.fileno(), sys.stderr.fileno())

def is_movie_present(title, clean_title):
    for c in [title, clean_title]:
        if not c: continue
        folder = os.path.join(BASE_DIR, c)
        if os.path.exists(folder):
            for f in os.listdir(folder):
                if f.lower().endswith((".mp4", ".mkv")) and not f.endswith(".part"):
                    fp = os.path.join(folder, f)
                    if os.path.getsize(fp) > 100 * 1024 * 1024:
                        return fp
    return None

def run_download_queue():
    acquire_wakelock()
    print("=" * 64)
    print("🎬 MOVIEBOX MESH - DETACHED RESILIENT DOWNLOADER ACTIVE")
    print(f"⏰ Started: {time.ctime()} (PID: {os.getpid()})")
    print("=" * 64)

    for item in SCIFI_CATALOG:
        title = item["title"]
        clean_title = item.get("clean_title") or sanitize_name(title)

        existing = is_movie_present(title, clean_title)
        if existing:
            sz = os.path.getsize(existing) / (1024 * 1024)
            print(f"✔ Ready: {title} ({sz:.1f} MB)")
            continue

        url = item.get("direct_url")
        if not url:
            continue

        movie_dir = os.path.join(BASE_DIR, clean_title)
        os.makedirs(movie_dir, exist_ok=True)
        dest_file = os.path.join(movie_dir, f"{clean_title}.mkv")

        print(f"\n⚡ Downloading: {title} ({item['year']})")
        downloader = ResilientDownloader(url, dest_file, num_workers=4)
        try:
            success = downloader.start()
            if success:
                print(f"🎉 Saved to: {dest_file}")
                promote_english_audio(dest_file)
        except Exception as e:
            print(f"\n✘ Download error for {title}: {e}")
            time.sleep(5)

    print("\n🏁 Queue processing finished.")
    if os.path.exists(PID_FILE):
        try: os.unlink(PID_FILE)
        except Exception: pass

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "stop":
        if os.path.exists(PID_FILE):
            with open(PID_FILE, "r") as f:
                pid = int(f.read().strip())
            try:
                os.kill(pid, signal.SIGTERM)
                print(f"Stopped background downloader (PID: {pid})")
            except Exception as e:
                print(f"Error stopping PID {pid}: {e}")
            try: os.unlink(PID_FILE)
            except Exception: pass
        else:
            print("No active downloader daemon found.")
        sys.exit(0)

    if len(sys.argv) > 1 and sys.argv[1] == "status":
        if os.path.exists(PID_FILE):
            with open(PID_FILE, "r") as f:
                pid = f.read().strip()
            print(f"🟢 Background Downloader is RUNNING (PID: {pid})")
        else:
            print("⚪ Downloader is NOT running.")
        if os.path.exists(LOG_FILE):
            print("\nRecent Logs:")
            subprocess.run(["tail", "-n", "10", LOG_FILE])
        sys.exit(0)

    if "--daemon" in sys.argv:
        daemonize()

    run_download_queue()

if __name__ == "__main__":
    main()
