#!/usr/bin/env python3
"""
mb-dl: High-Speed Resilient Media Downloader & Stream Engine
Unified downloader for MovieBox Mesh with auto-resolution, 
multi-segment Range acceleration, filesystem sanitization,
and self-healing fault recovery.
"""

import os
import sys
import time
import json
import re
import struct
import urllib.request
import urllib.parse
import subprocess
from concurrent.futures import ThreadPoolExecutor

BASE_DIR = "/storage/emulated/0/Movies/MovieBox/Movies"
os.makedirs(BASE_DIR, exist_ok=True)

CINEMETA_SEARCH = "https://v3-cinemeta.strem.io/catalog/movie/top/search={query}.json"
HDHUB_TEMPLATE = "https://hdhub.thevolecitor.qzz.io/eyJ0b3Jib3giOiJ1bnNldCIsInF1YWxpdGllcyI6IjIxNjBwLDEwODBwLDcyMHAiLCJzb3J0IjoiZGVzYyJ9/stream/movie/{imdb_id}.json"
HYPER_TEMPLATE = "https://hyper.stravo.site/local/stream/movie/{imdb_id}.json"

def sanitize_name(name):
    """Strip illegal Android FAT/FUSE characters"""
    clean = re.sub(r'[\/*?:"<>|]', '', name)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean

def is_unmetered_wifi():
    try:
        out = subprocess.check_output(
            ["su", "-c", "cmd connectivity is-active-network-metered"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        return out.lower() == "false"
    except Exception:
        return False

def search_imdb(query):
    """Resolve a movie title to IMDb ID via Cinemeta"""
    if query.startswith("tt") and query[2:].isdigit():
        return query, query
    q = urllib.parse.quote(query)
    url = CINEMETA_SEARCH.format(query=q)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.load(r)
            metas = data.get("metas", [])
            if metas:
                best = metas[0]
                return best.get("id"), best.get("name", query)
    except Exception:
        pass
    return None, query

def resolve_streams(imdb_id, preferred_quality="720p"):
    """
    Tiered stream resolver:
    Tier 1: HdHub direct Pixeldrain API
    Tier 2: HdHub other direct streams
    Tier 3: Hyper streams
    """
    candidates = []
    
    # 1. Query HdHub
    url = HDHUB_TEMPLATE.format(imdb_id=imdb_id)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.load(r)
            for s in data.get("streams", []):
                u = s.get("url", "")
                if not u.startswith("http"):
                    continue
                desc = (str(s.get("name") or "") + " " + str(s.get("title") or "")).lower()
                
                score = 0
                if "pixeldrain" in u:
                    score += 50
                if preferred_quality.lower() in desc:
                    score += 30
                elif "720" in desc:
                    score += 20
                elif "1080" in desc:
                    score += 10
                
                candidates.append({
                    "url": u,
                    "desc": desc[:40],
                    "score": score,
                    "provider": "HdHub"
                })
    except Exception:
        pass

    # 2. Query Hyper if candidates empty or low score
    if not candidates or max(c["score"] for c in candidates) < 30:
        h_url = HYPER_TEMPLATE.format(imdb_id=imdb_id)
        try:
            req = urllib.request.Request(h_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.load(r)
                for s in data.get("streams", []):
                    u = s.get("url", "")
                    if not u.startswith("http"):
                        continue
                    desc = (str(s.get("name") or "") + " " + str(s.get("title") or "")).lower()
                    score = 10
                    if preferred_quality.lower() in desc:
                        score += 30
                    candidates.append({
                        "url": u,
                        "desc": desc[:40],
                        "score": score,
                        "provider": "Hyper"
                    })
        except Exception:
            pass

    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates

def validate_media_file(filepath):
    """Validate container magic bytes to guarantee video integrity"""
    if not os.path.exists(filepath):
        return False
    size = os.path.getsize(filepath)
    if size < 5 * 1024 * 1024: # Smaller than 5MB is suspect for a movie
        return False
    try:
        with open(filepath, "rb") as f:
            header = f.read(128)
            # Check MKV (EBML \x1a\x45\xdf\xa3) or MP4 (ftyp)
            if b"\x1a\x45\xdf\xa3" in header:
                return True
            if b"ftyp" in header or b"moov" in header or b"mdat" in header:
                return True
    except Exception:
        pass
    return False

class FastDownloader:
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

    def probe(self):
        req = urllib.request.Request(self.url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as res:
            self.total_size = int(res.headers.get("Content-Length", 0))
            self.accepts_ranges = res.headers.get("Accept-Ranges", "").lower() == "bytes"

    def download_slice(self, fd, start, end, max_retries=3):
        chunk_size = 256 * 1024
        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(self.url, headers={
                    "User-Agent": "Mozilla/5.0",
                    "Range": f"bytes={start}-{end}"
                })
                with urllib.request.urlopen(req, timeout=30) as res:
                    offset = start
                    while offset <= end:
                        buf = res.read(min(chunk_size, end - offset + 1))
                        if not buf:
                            break
                        os.pwrite(fd, buf, offset)
                        offset += len(buf)
                        self.downloaded += len(buf)
                return True
            except Exception as e:
                time.sleep(1.0 * (attempt + 1))
        return False

    def print_progress(self):
        while self.downloaded < self.total_size:
            time.sleep(0.5)
            elapsed = time.time() - self.start_time
            if elapsed <= 0 or self.total_size <= 0:
                continue
            speed = (self.downloaded / (1024 * 1024)) / elapsed
            pct = min((self.downloaded / self.total_size) * 100, 100.0)
            remaining_bytes = max(self.total_size - self.downloaded, 0)
            eta_sec = int(remaining_bytes / (speed * 1024 * 1024)) if speed > 0 else 0
            eta_m, eta_s = divmod(eta_sec, 60)
            
            curr_mb = self.downloaded / (1024 * 1024)
            tot_mb = self.total_size / (1024 * 1024)
            
            bar_len = 10
            filled = int(bar_len * (pct / 100))
            bar = "=" * filled + ">" if filled < bar_len else "=" * bar_len
            bar = bar.ljust(bar_len)
            
            line = f"[{bar}] {pct:4.1f}% {curr_mb:.0f}/{tot_mb:.0f}MB {speed:.1f}MB/s ETA:{eta_m:02d}m{eta_s:02d}s"
            sys.stdout.write(f"\r{line[:68]}")
            sys.stdout.flush()

    def start(self):
        self.probe()
        if self.total_size <= 0:
            print("✘ Error: Content-Length invalid or server offline.")
            return False

        print(f"📦 Size: {self.total_size / (1024*1024):.1f} MB | Slices: {self.num_workers} parallel")
        fd = os.open(self.part_path, os.O_RDWR | os.O_CREAT | os.O_TRUNC)
        try:
            os.ftruncate(fd, self.total_size)
            self.start_time = time.time()

            import threading
            prog_thread = threading.Thread(target=self.print_progress, daemon=True)
            prog_thread.start()

            if self.accepts_ranges and self.num_workers > 1:
                slice_len = self.total_size // self.num_workers
                futures = []
                with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
                    for i in range(self.num_workers):
                        start = i * slice_len
                        end = self.total_size - 1 if i == self.num_workers - 1 else (start + slice_len - 1)
                        futures.append(executor.submit(self.download_slice, fd, start, end))
                    for f in futures:
                        if not f.result():
                            print("\n✘ A download slice failed after retries.")
                            return False
            else:
                if not self.download_slice(fd, 0, self.total_size - 1):
                    return False

            elapsed = max(time.time() - self.start_time, 0.001)
            avg_speed = (self.total_size / (1024 * 1024)) / elapsed
            print(f"\n✔ Done in {elapsed:.1f}s (Avg: {avg_speed:.2f} MB/s)")
            os.close(fd)
            fd = None

            # Validate header integrity before final rename
            if not validate_media_file(self.part_path):
                print("✘ Error: Downloaded file failed media header integrity verification!")
                return False

            if os.path.exists(self.dest_path):
                os.unlink(self.dest_path)
            os.rename(self.part_path, self.dest_path)
            return True
        finally:
            if fd is not None:
                os.close(fd)

def get_existing_movie(title):
    clean = sanitize_name(title)
    for folder_name in [title, clean]:
        fpath = os.path.join(BASE_DIR, folder_name)
        if os.path.exists(fpath):
            for f in os.listdir(fpath):
                if f.lower().endswith((".mp4", ".mkv")) and not f.endswith(".part"):
                    full = os.path.join(fpath, f)
                    if os.path.getsize(full) > 50 * 1024 * 1024:
                        return full
    return None

def download_movie(query, quality="720p", force=False):
    unmetered = is_unmetered_wifi()
    if not unmetered and not force:
        print("⚠️  Warning: Active connection is METERED MOBILE DATA.")
        print("Pass --force to authorize download.")
        return False

    existing = get_existing_movie(query)
    if existing:
        sz = os.path.getsize(existing) / (1024 * 1024)
        print(f"✔ Already exists: {os.path.basename(existing)} ({sz:.1f} MB)")
        return True

    print(f"🔍 Searching: {query}...")
    imdb_id, display_name = search_imdb(query)
    if not imdb_id:
        print(f"✘ Could not resolve IMDb ID for: {query}")
        return False

    print(f"🎬 Resolved: {display_name} ({imdb_id})")
    clean_title = sanitize_name(display_name)
    
    print(f"📡 Resolving streams ({quality})...")
    candidates = resolve_streams(imdb_id, quality)
    if not candidates:
        print(f"✘ No streams found for {display_name}.")
        return False

    movie_dir = os.path.join(BASE_DIR, clean_title)
    os.makedirs(movie_dir, exist_ok=True)
    dest_path = os.path.join(movie_dir, f"{clean_title}.mkv")

    # Self-healing stream failover loop
    for idx, cand in enumerate(candidates[:3]):
        print(f"\n⚡ Trying stream {idx+1}/{min(len(candidates), 3)} via {cand['provider']}...")
        downloader = FastDownloader(cand["url"], dest_path, num_workers=4)
        try:
            if downloader.start():
                print(f"🎉 Saved to: {dest_path}")
                return True
        except Exception as e:
            print(f"✘ Stream {idx+1} failed: {e}")
            if os.path.exists(downloader.part_path):
                try: os.unlink(downloader.part_path)
                except Exception: pass

    print("✘ All candidate streams failed.")
    return False

def show_status():
    print("=" * 64)
    print("🎬 MOVIEBOX MESH - LIBRARY & SYSTEM STATUS")
    print("=" * 64)
    print(f"📁 Storage: {BASE_DIR}")
    if os.path.exists(BASE_DIR):
        folders = sorted(os.listdir(BASE_DIR))
        print(f"📚 Movies Available ({len(folders)}):")
        for f in folders:
            sub = os.path.join(BASE_DIR, f)
            if os.path.isdir(sub):
                for mf in os.listdir(sub):
                    if mf.lower().endswith((".mp4", ".mkv")) and not mf.endswith(".part"):
                        fp = os.path.join(sub, mf)
                        sz = os.path.getsize(fp) / (1024 * 1024)
                        print(f"  ✔ {f}: {mf} ({sz:.1f} MB)")
                    elif mf.endswith(".part"):
                        fp = os.path.join(sub, mf)
                        sz = os.path.getsize(fp) / (1024 * 1024)
                        print(f"  ⏳ {f}: IN PROGRESS ({sz:.1f} MB)")

def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage:")
        print("  mb-dl \"<title or imdb_id>\" [--quality 720p|1080p] [--force]")
        print("  mb-dl --status")
        sys.exit(0)

    if sys.argv[1] in ("--status", "status"):
        show_status()
        sys.exit(0)

    query = sys.argv[1]
    quality = "720p"
    force = "--force" in sys.argv
    for arg in sys.argv[2:]:
        if arg in ("720p", "1080p", "480p"):
            quality = arg
        elif arg.startswith("--quality="):
            quality = arg.split("=", 1)[1]

    download_movie(query, quality, force)

if __name__ == "__main__":
    main()
