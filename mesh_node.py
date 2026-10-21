#!/usr/bin/env python3
"""
MovieBox Mesh - Decentralized P2P Cinema, Music, Webtoon, Novel & Gaming Hub
100% Python Standard Library (Zero External Dependencies)
Version: 1.4.0 (Cosmic Edition)
"""

import os
import sys
import json
import time
import socket
import select
import shutil
import mimetypes
import threading
import subprocess
import re
import hashlib
import zipfile
import urllib.parse
import urllib.request
from urllib.parse import urlparse, parse_qs, unquote
from http.server import HTTPServer, BaseHTTPRequestHandler
import socketserver

# Configuration Defaults
VERSION = "1.4.0"
PORT = 8080
DISCOVERY_PORT = 9999
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
WEB_DIR = os.path.join(BASE_DIR, "web")
APPS_DIR = os.path.join(BASE_DIR, "apps")
LIVE_DIR = os.path.join(BASE_DIR, "live")
MANHWA_DIR = os.path.join(BASE_DIR, "manhwa")
NOVELS_DIR = os.path.join(BASE_DIR, "novels")
MUSIC_DIR = "/sdcard/Music" if os.path.exists("/sdcard/Music") else os.path.join(BASE_DIR, "music")
THUMBS_DIR = os.path.join(BASE_DIR, ".thumbs")
MOVIES_DIR = "/sdcard/Movies/MovieBox/Movies" if os.path.exists("/sdcard/Movies/MovieBox/Movies") else (
    "/sdcard/Movies/MovieBox" if os.path.exists("/sdcard/Movies/MovieBox") else os.path.join(BASE_DIR, "movies")
)
FALLBACK_MOVIES_DIR = "/sdcard/Movies" if os.path.exists("/sdcard") else os.path.join(os.path.expanduser("~"), "Videos")
PROGRESS_FILE = os.path.join(BASE_DIR, "progress.json")
WISHLIST_FILE = os.path.join(BASE_DIR, "wishlist.json")
OFFLOAD_MANIFEST = os.path.join(BASE_DIR, "offload_manifest.json")

# Ensure required directories exist
for d in [STATIC_DIR, WEB_DIR, APPS_DIR, LIVE_DIR, MANHWA_DIR, NOVELS_DIR, THUMBS_DIR, MOVIES_DIR, MUSIC_DIR]:
    os.makedirs(d, exist_ok=True)

# Code Fingerprinting for Mesh Auto-Update
def get_code_fingerprint():
    max_ts = 0
    try:
        if os.path.exists(__file__):
            max_ts = max(max_ts, os.path.getmtime(__file__))
    except Exception:
        pass
    for directory in [STATIC_DIR, WEB_DIR]:
        if os.path.exists(directory):
            try:
                for root, _, files in os.walk(directory):
                    for f in files:
                        fp = os.path.join(root, f)
                        try:
                            max_ts = max(max_ts, os.path.getmtime(fp))
                        except Exception:
                            pass
            except Exception:
                pass
    return int(max_ts) if max_ts > 0 else int(time.time())

LOCAL_CODE_TS = get_code_fingerprint()

# Node Identification
def get_node_name():
    try:
        model = subprocess.check_output(["getprop", "ro.product.model"], stderr=subprocess.DEVNULL).decode().strip()
        if model:
            return model
    except Exception:
        pass
    return socket.gethostname() or "Mesh-Node"

def get_local_ip():
    for ifname in ['wlan0', 'wlan1', 'rndis0', 'eth0', 'rmnet_data0']:
        try:
            import fcntl, struct
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            ip = socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s', ifname[:15].encode('utf-8')))[20:24])
            s.close()
            if ip and not ip.startswith('127.'):
                return ip
        except Exception:
            pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('10.42.0.1', 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith('127.'):
            return ip
    except Exception:
        pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith('127.'):
            return ip
    except Exception:
        pass
    return '127.0.0.1'

NODE_NAME = get_node_name()
LOCAL_IP = get_local_ip()

# In-memory mesh peer registry
PEERS = {}
PEERS_LOCK = threading.Lock()

# Cross-Device Gamepad State Relay (Phone -> PC)
GAMEPAD_STATE = {
    "dpad_up": False, "dpad_down": False, "dpad_left": False, "dpad_right": False,
    "btn_a": False, "btn_b": False, "btn_x": False, "btn_y": False,
    "start": False, "select": False, "timestamp": 0
}
GAMEPAD_LOCK = threading.Lock()

def format_size(bytes_size):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} PB"

def is_unmetered_wifi():
    try:
        out = subprocess.check_output(
            ["cmd", "connectivity", "is-active-network-metered"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        return out.lower() == "false"
    except Exception:
        try:
            out = subprocess.check_output(["ip", "route"], stderr=subprocess.DEVNULL).decode()
            if "wlan0" in out and "rmnet" not in out:
                return True
        except Exception:
            pass
    return False

# --- Media Metadata & Thumbnailing ---

def parse_media_metadata(filename):
    base = os.path.splitext(filename)[0]
    year_match = re.search(r'\b(19\d\d|20\d\d)\b', base)
    year = year_match.group(1) if year_match else ""

    res_match = re.search(r'\b(2160p|4k|1080p|720p|480p|576p|hdr|bluray|web-?dl|hdrip)\b', base, re.I)
    resolution = res_match.group(1).upper() if res_match else "1080p"

    audio_match = re.search(r'\b(5\.1|7\.1|atmos|dts|ddp?5\.1|aac|ac3|dual\s*audio|hindi|eng)\b', base, re.I)
    audio = audio_match.group(1).upper() if audio_match else "English 5.1"

    clean = re.sub(r'\b(19\d\d|20\d\d|2160p|4k|1080p|720p|480p|bluray|web-?dl|x264|x265|hevc|aac|dts|hdrip|yify|rarbg|eztv)\b.*', '', base, flags=re.I)
    clean = clean.replace(".", " ").replace("_", " ").replace("-", " ").strip()
    clean_title = clean.title() if clean else base

    lower_name = filename.lower()
    if any(k in lower_name for k in ['arrival', 'alien', 'space', 'star', 'matrix', 'future', 'sci-fi', 'scifi', 'cyber', 'interstellar', 'avatar', 'blade runner', 'terminator', 'dune', 'galaxy', 'machina']):
        category = "Sci-Fi"
    elif any(k in lower_name for k in ['spider', 'action', 'war', 'fight', 'john wick', 'mission', 'fast', 'furious', 'die hard', 'batman', 'marvel', 'avengers', 'bond', 'sniper', 'gun', 'fury']):
        category = "Action"
    elif any(k in lower_name for k in ['cartoon', 'animated', 'anime', 'pixar', 'disney', 'shrek', 'toy story', 'spider-verse', 'dragon']):
        category = "Animation"
    elif any(k in lower_name for k in ['horror', 'conjuring', 'dead', 'evil', 'zombie', 'scary', 'halloween', 'saw', 'exorcist', 'insidious']):
        category = "Horror"
    elif any(k in lower_name for k in ['comedy', 'funny', 'hangover', 'ted', 'parody', 'dumb', 'holiday']):
        category = "Comedy"
    else:
        category = "Drama"

    return clean_title, year, resolution, audio, category

def extract_thumbnail(filepath, thumb_path):
    if os.path.exists(thumb_path) and os.path.getsize(thumb_path) > 1024:
        return True
    try:
        cmd = ["ffmpeg", "-y", "-ss", "00:05:00", "-i", filepath, "-vframes", "1", "-vf", "scale=480:-1", "-q:v", "3", thumb_path]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=12)
        if res.returncode == 0 and os.path.exists(thumb_path) and os.path.getsize(thumb_path) > 1024:
            return True
        cmd[3] = "00:00:30"
        res2 = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=8)
        return res2.returncode == 0 and os.path.exists(thumb_path) and os.path.getsize(thumb_path) > 1024
    except Exception:
        return False

class ThumbnailWorker(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.queue = []
        self.lock = threading.Lock()

    def add(self, filepath, thumb_path):
        with self.lock:
            if (filepath, thumb_path) not in self.queue:
                self.queue.append((filepath, thumb_path))

    def run(self):
        while True:
            item = None
            with self.lock:
                if self.queue:
                    item = self.queue.pop(0)
            if item:
                filepath, thumb_path = item
                extract_thumbnail(filepath, thumb_path)
                time.sleep(0.2)
            else:
                time.sleep(2)

THUMB_WORKER = ThumbnailWorker()
THUMB_WORKER.start()

def load_offload_manifest():
    if os.path.exists(OFFLOAD_MANIFEST):
        try:
            with open(OFFLOAD_MANIFEST, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_offload_manifest(data):
    try:
        with open(OFFLOAD_MANIFEST, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

def scan_local_media():
    items = []
    user_home = os.path.expanduser("~")
    scan_paths = [
        MOVIES_DIR,
        "/sdcard/Movies/MovieBox/Movies",
        "/sdcard/Movies/MovieBox",
        FALLBACK_MOVIES_DIR,
        "/sdcard/Download",
        os.path.join(BASE_DIR, "movies"),
        os.path.join(user_home, "Videos"),
        os.path.join(user_home, "Movies"),
        os.path.join(user_home, "Downloads"),
        os.path.join(user_home, "moviebox-mesh", "movies")
    ]
    valid_exts = {'.mp4', '.mkv', '.webm', '.avi', '.mov', '.ts', '.m4v'}
    seen_files = set()
    offloaded_map = load_offload_manifest()

    for folder in scan_paths:
        if not os.path.exists(folder):
            continue
        for root, _, files in os.walk(folder):
            for f in sorted(files):
                ext = os.path.splitext(f)[1].lower()
                if ext in valid_exts:
                    full_path = os.path.join(root, f)
                    if full_path in seen_files:
                        continue
                    seen_files.add(full_path)
                    try:
                        stat = os.stat(full_path)
                        item_id = f"mov_{abs(hash(full_path))}"
                        clean_title, year, res, audio, category = parse_media_metadata(f)
                        
                        thumb_file = os.path.join(THUMBS_DIR, f"{item_id}.jpg")
                        if not os.path.exists(thumb_file):
                            THUMB_WORKER.add(full_path, thumb_file)

                        is_offloaded = offloaded_map.get(item_id, {}).get("synced", False)
                        is_pc_node = ("laptop" in NODE_NAME.lower() or "pc" in NODE_NAME.lower() or "dell" in NODE_NAME.lower() or LOCAL_IP == "10.42.0.1")

                        items.append({
                            "id": item_id,
                            "title": clean_title,
                            "raw_title": f,
                            "filename": f,
                            "path": full_path,
                            "size": format_size(stat.st_size),
                            "size_bytes": stat.st_size,
                            "year": year,
                            "resolution": res,
                            "audio": audio,
                            "category": category,
                            "type": "movie",
                            "node": NODE_NAME,
                            "ip": LOCAL_IP,
                            "is_pc": is_pc_node,
                            "offloaded": is_offloaded or is_pc_node,
                            "thumb_url": f"/api/thumb/{item_id}",
                            "stream_url": f"/stream/media?path={urllib.parse.quote(full_path)}",
                            "live_url": f"/play/live/{item_id}",
                            "url": f"/stream/media?path={urllib.parse.quote(full_path)}",
                            "from_peer": False
                        })
                    except Exception:
                        continue
    return items

# --- Music & Cosmic Radio Scanner ---

def scan_local_music():
    tracks = []
    seen = set()
    valid_exts = {'.mp3', '.flac', '.m4a', '.wav', '.ogg', '.aac'}
    scan_paths = [
        MUSIC_DIR,
        "/sdcard/Music",
        "/sdcard/Download",
        os.path.join(BASE_DIR, "music"),
        os.path.join(os.path.expanduser("~"), "Music")
    ]
    for folder in scan_paths:
        if not os.path.exists(folder):
            continue
        for root, _, files in os.walk(folder):
            for f in sorted(files):
                ext = os.path.splitext(f)[1].lower()
                if ext in valid_exts:
                    full_p = os.path.join(root, f)
                    if full_p in seen:
                        continue
                    seen.add(full_p)
                    stat = os.stat(full_p)
                    title = os.path.splitext(f)[0].replace("_", " ").replace(".", " ").title()
                    tracks.append({
                        "id": f"mus_{abs(hash(full_p))}",
                        "title": title,
                        "filename": f,
                        "format": ext.lstrip('.').upper(),
                        "size": format_size(stat.st_size),
                        "stream_url": f"/stream/media?path={urllib.parse.quote(full_p)}"
                    })
    return tracks

def get_radio_stations():
    stations = []
    radio_m3u = os.path.join(LIVE_DIR, "radio.m3u")
    if os.path.exists(radio_m3u):
        try:
            with open(radio_m3u, "r", encoding="utf-8", errors="ignore") as fp:
                name = None
                for line in fp:
                    line = line.strip()
                    if line.startswith("#EXTINF"):
                        parts = line.split(",", 1)
                        name = parts[1].strip() if len(parts) > 1 else "Cosmic Radio"
                    elif line and not line.startswith("#") and name:
                        stations.append({
                            "id": f"rad_{abs(hash(line))}",
                            "title": name,
                            "url": line,
                            "type": "radio"
                        })
                        name = None
        except Exception:
            pass
    if not stations:
        stations.append({
            "id": "rad_cosmic",
            "title": "Cosmic Ambient Radio",
            "url": "https://ice6.somafm.com/groovesalad-128-mp3",
            "type": "radio"
        })
    return stations

# --- Live TV Playlists Parser ---

def get_live_tv_channels():
    channels = []
    seen_urls = set()
    categories = ["Movies", "Sports", "News", "General"]

    search_dirs = [
        LIVE_DIR,
        "/sdcard/Antigravity_Projects/moviebox-tui/live",
        os.path.join(BASE_DIR, "live")
    ]

    for s_dir in search_dirs:
        if not os.path.exists(s_dir):
            continue
        for root, _, files in os.walk(s_dir):
            for f in sorted(files):
                if f.lower().endswith((".m3u", ".m3u8")) and not "radio" in f.lower():
                    m3u_path = os.path.join(root, f)
                    try:
                        with open(m3u_path, "r", encoding="utf-8", errors="ignore") as fp:
                            name = None
                            logo = ""
                            group = "Movies" if "movie" in f.lower() else ("Sports" if "sport" in f.lower() else ("News" if "news" in f.lower() else "General"))
                            for line in fp:
                                line = line.strip()
                                if line.startswith("#EXTINF"):
                                    logo_match = re.search(r'tvg-logo="([^"]+)"', line)
                                    logo = logo_match.group(1) if logo_match else ""
                                    group_match = re.search(r'group-title="([^"]+)"', line)
                                    if group_match:
                                        raw_group = group_match.group(1).lower()
                                        if any(k in raw_group for k in ['sport', 'football', 'espn', 'racing']):
                                            group = "Sports"
                                        elif any(k in raw_group for k in ['news', 'cnn', 'bbc', 'aljazeera']):
                                            group = "News"
                                        elif any(k in raw_group for k in ['movie', 'cinema', 'hbo']):
                                            group = "Movies"
                                        else:
                                            group = "General"
                                    parts = line.split(",", 1)
                                    name = parts[1].strip() if len(parts) > 1 else "Live Channel"
                                elif line and not line.startswith("#") and name:
                                    if line not in seen_urls:
                                        seen_urls.add(line)
                                        channels.append({
                                            "id": f"tv_{abs(hash(line))}",
                                            "title": name,
                                            "url": line,
                                            "logo": logo,
                                            "category": group,
                                            "node": "MovieBox Live"
                                        })
                                    name = None
                                    logo = ""
                    except Exception:
                        pass

    grouped = {cat: [] for cat in categories}
    for ch in channels:
        cat = ch.get("category", "General")
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append(ch)

    return {
        "categories": categories,
        "total": len(channels),
        "channels": channels,
        "grouped": grouped
    }

# --- Manhwa & Novels Readers ---

def scan_manhwa():
    series = []
    if not os.path.exists(MANHWA_DIR):
        return series
    for item in sorted(os.listdir(MANHWA_DIR)):
        ipath = os.path.join(MANHWA_DIR, item)
        if os.path.isdir(ipath):
            pages = sorted([f for f in os.listdir(ipath) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))])
            series.append({
                "id": f"mhw_{abs(hash(item))}",
                "title": item.replace("_", " ").title(),
                "folder": item,
                "pages_count": len(pages),
                "cover": f"/api/manhwa/cover/{urllib.parse.quote(item)}" if pages else None
            })
    return series

def scan_novels():
    books = []
    if not os.path.exists(NOVELS_DIR):
        return books
    for item in sorted(os.listdir(NOVELS_DIR)):
        if item.lower().endswith(('.txt', '.epub', '.md')):
            full_path = os.path.join(NOVELS_DIR, item)
            stat = os.stat(full_path)
            books.append({
                "id": f"nov_{abs(hash(item))}",
                "title": os.path.splitext(item)[0].replace("_", " ").title(),
                "filename": item,
                "size": format_size(stat.st_size)
            })
    return books

# --- Apps Vault Scanner ---

def scan_local_apps():
    items = []
    if not os.path.exists(APPS_DIR):
        return items
    for f in sorted(os.listdir(APPS_DIR)):
        ext = os.path.splitext(f)[1].lower()
        if ext in ('.apk', '.xapk', '.deb', '.exe', '.sh', '.zip'):
            full_path = os.path.join(APPS_DIR, f)
            try:
                stat = os.stat(full_path)
                title = os.path.splitext(f)[0].replace(".", " ").replace("_", " ").title()
                if ext in ('.apk', '.xapk'):
                    platform = "TV / Mobile" if any(k in f.lower() for k in ['tv', 'leanback', 'atv']) else "Mobile"
                elif ext in ('.exe',):
                    platform = "PC (Windows)"
                elif ext in ('.deb', '.sh'):
                    platform = "PC (Linux)"
                else:
                    platform = "Cross-Platform"

                items.append({
                    "id": f"app_{abs(hash(full_path))}",
                    "title": title,
                    "filename": f,
                    "path": full_path,
                    "size": format_size(stat.st_size),
                    "size_bytes": stat.st_size,
                    "platform": platform,
                    "type": "app",
                    "node": NODE_NAME,
                    "ip": LOCAL_IP,
                    "url": f"/api/apps/download/{urllib.parse.quote(f)}"
                })
            except Exception:
                continue
    return items

def get_wishlist():
    if os.path.exists(WISHLIST_FILE):
        try:
            with open(WISHLIST_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def save_wishlist(data):
    try:
        with open(WISHLIST_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

# --- UDP Beacon & Peer Discovery ---

class MeshBeacon(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def run(self):
        listener = threading.Thread(target=self.listen_for_peers, daemon=True)
        listener.start()

        while True:
            try:
                media_count = len(scan_local_media())
                apk_count = len(scan_local_apps())
                payload = json.dumps({
                    "node": NODE_NAME,
                    "ip": LOCAL_IP,
                    "port": PORT,
                    "version": VERSION,
                    "code_ts": LOCAL_CODE_TS,
                    "media_count": media_count,
                    "apk_count": apk_count,
                    "ts": time.time()
                }).encode('utf-8')
                self.sock.sendto(payload, ('255.255.255.255', DISCOVERY_PORT))
            except Exception:
                pass
            time.sleep(5)

    def listen_for_peers(self):
        recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        recv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            recv_sock.bind(('', DISCOVERY_PORT))
        except Exception:
            return

        while True:
            try:
                data, addr = recv_sock.recvfrom(4096)
                peer_info = json.loads(data.decode('utf-8'))
                peer_ip = peer_info.get("ip") or addr[0]
                if peer_ip != LOCAL_IP:
                    with PEERS_LOCK:
                        PEERS[peer_ip] = {
                            "name": peer_info.get("node", "Peer"),
                            "port": peer_info.get("port", PORT),
                            "version": peer_info.get("version", "1.0.0"),
                            "code_ts": peer_info.get("code_ts", 0),
                            "media_count": peer_info.get("media_count", 0),
                            "apk_count": peer_info.get("apk_count", 0),
                            "last_seen": time.time()
                        }
            except Exception:
                pass

# --- HTTP Request Handler ---

class MeshHTTPHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, DELETE")
        self.send_header("Access-Control-Allow-Headers", "Range, Content-Type, Accept")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/setup":
            script = f"""#!/usr/bin/env bash
echo "=== MovieBox Cosmic Sync & Launch ==="
HOST="{LOCAL_IP}:{PORT}"
echo "Connected to Cinema Hub at http://$HOST"
which xdg-open >/dev/null 2>&1 && xdg-open "http://$HOST" || which sensible-browser >/dev/null 2>&1 && sensible-browser "http://$HOST" || echo "Please open http://$HOST in your browser"
"""
            body = script.encode('utf-8')
            self.send_response(200)
            self.send_cors_headers()
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        # 1. API: Catalog
        if path == "/api/catalog":
            local_media = scan_local_media()
            local_apks = scan_local_apps()
            live_data = get_live_tv_channels()
            manhwa_data = scan_manhwa()
            novels_data = scan_novels()
            music_data = scan_local_music()
            radio_data = get_radio_stations()
            wishlist = get_wishlist()

            active_peers = []
            now = time.time()
            with PEERS_LOCK:
                for ip, info in list(PEERS.items()):
                    if now - info["last_seen"] < 15:
                        active_peers.append({"ip": ip, **info})

            combined_media = list(local_media)
            if not query.get("peer") and active_peers:
                seen_ids = {m.get("id") for m in combined_media}
                for peer in active_peers:
                    p_ip = peer.get("ip")
                    p_port = peer.get("port", PORT)
                    p_base = f"http://{p_ip}:{p_port}"
                    try:
                        req = urllib.request.Request(
                            f"{p_base}/api/catalog?peer=1",
                            headers={"User-Agent": "MovieBox-Mesh"}
                        )
                        with urllib.request.urlopen(req, timeout=1.5) as resp:
                            if resp.status == 200:
                                p_data = json.loads(resp.read().decode('utf-8'))
                                for item in p_data.get("media", []):
                                    if item.get("id") not in seen_ids:
                                        seen_ids.add(item.get("id"))
                                        item_copy = dict(item)
                                        item_copy["from_peer"] = True
                                        for key in ["stream_url", "thumb_url", "live_url", "url"]:
                                            if key in item_copy and item_copy[key] and not str(item_copy[key]).startswith("http"):
                                                item_copy[key] = f"{p_base}{item_copy[key]}"
                                        combined_media.append(item_copy)
                    except Exception:
                        pass

            self.send_json({
                "version": VERSION,
                "code_ts": LOCAL_CODE_TS,
                "self": {"name": NODE_NAME, "ip": LOCAL_IP, "port": PORT, "version": VERSION, "code_ts": LOCAL_CODE_TS},
                "peers": active_peers,
                "unmetered_wifi": is_unmetered_wifi(),
                "media": combined_media,
                "apks": local_apks,
                "manhwa": manhwa_data,
                "novels": novels_data,
                "music": music_data,
                "radio": radio_data,
                "live_tv": live_data.get("channels", []),
                "live_tv_grouped": live_data.get("grouped", {}),
                "wishlist": wishlist
            })
            return

        # 2. API: Music & Radio
        if path == "/api/music":
            self.send_json({
                "tracks": scan_local_music(),
                "radio": get_radio_stations()
            })
            return

        # 3. API: Gamepad Input State (PC polls gamepad controls)
        if path == "/api/gamepad/state":
            with GAMEPAD_LOCK:
                self.send_json(GAMEPAD_STATE)
            return

        # 4. API: Live TV
        if path == "/api/livetv/channels":
            self.send_json(get_live_tv_channels())
            return

        # 5. API: Thumbnails
        if path.startswith("/api/thumb/"):
            thumb_id = path.replace("/api/thumb/", "").replace(".jpg", "").strip()
            thumb_file = os.path.join(THUMBS_DIR, f"{thumb_id}.jpg")
            if not os.path.exists(thumb_file):
                for m in scan_local_media():
                    if m["id"] == thumb_id:
                        extract_thumbnail(m["path"], thumb_file)
                        break

            if os.path.exists(thumb_file):
                self.serve_static_file(thumb_file, "image/jpeg", cache_seconds=86400)
            else:
                svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="480" height="270" viewBox="0 0 480 270">
                    <rect width="100%" height="100%" fill="#060913"/>
                    <circle cx="240" cy="135" r="40" fill="#00a8ff" opacity="0.8"/>
                    <polygon points="232,120 256,135 232,150" fill="#ffffff"/>
                    <text x="240" y="210" font-family="sans-serif" font-size="16" fill="#38bdf8" text-anchor="middle">MovieBox Cosmic</text>
                </svg>'''
                body = svg.encode('utf-8')
                self.send_response(200)
                self.send_cors_headers()
                self.send_header("Content-Type", "image/svg+xml")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            return

        # 6. Stream Media
        if path == "/stream/media":
            file_path = query.get("path", [None])[0]
            if not file_path or not os.path.exists(file_path):
                self.send_error(404, "Media file not found")
                return
            self.serve_file_range(file_path)
            return

        # 7. In-Browser Live Transmuxer
        if path.startswith("/play/live/"):
            media_id = path.replace("/play/live/", "").strip()
            target_path = None
            for m in scan_local_media():
                if m["id"] == media_id:
                    target_path = m["path"]
                    break
            if not target_path or not os.path.exists(target_path):
                self.send_error(404, "Media item not found for live transmux")
                return
            self.serve_live_transmux(target_path)
            return

        # 8. API: Apps
        if path == "/api/apps":
            self.send_json({"apps": scan_local_apps()})
            return

        if path.startswith("/api/apps/download/"):
            filename = unquote(path.replace("/api/apps/download/", "").strip())
            file_path = os.path.join(APPS_DIR, os.path.basename(filename))
            if not os.path.exists(file_path):
                self.send_error(404, "App file not found")
                return
            self.serve_file_range(file_path, as_attachment=True, download_name=os.path.basename(filename))
            return

        # 9. Manhwa & Novels
        if path == "/api/manhwa":
            self.send_json({"manhwa": scan_manhwa()})
            return

        if path == "/api/novels":
            self.send_json({"novels": scan_novels()})
            return

        # 10. Wishlist
        if path == "/api/wishlist":
            self.send_json({"wishlist": get_wishlist()})
            return

        # 11. Mesh Bundle
        if path == "/api/mesh/bundle":
            bundle_files = {}
            mesh_node_file = os.path.join(BASE_DIR, "mesh_node.py")
            if os.path.exists(mesh_node_file):
                try:
                    with open(mesh_node_file, "r", encoding="utf-8") as f:
                        bundle_files["mesh_node.py"] = f.read()
                except Exception:
                    pass
            for root_dir in [STATIC_DIR, WEB_DIR]:
                if os.path.exists(root_dir):
                    for root, _, files in os.walk(root_dir):
                        for f in files:
                            full_f = os.path.join(root, f)
                            rel_f = os.path.relpath(full_f, BASE_DIR)
                            try:
                                with open(full_f, "r", encoding="utf-8", errors="ignore") as sf:
                                    bundle_files[rel_f] = sf.read()
                            except Exception:
                                pass
            self.send_json({
                "version": VERSION,
                "code_ts": LOCAL_CODE_TS,
                "files": bundle_files
            })
            return

        # 12. Static Web UI files
        if path == "/" or path == "/index.html":
            static_file = os.path.join(WEB_DIR, "index.html")
            if not os.path.exists(static_file):
                static_file = os.path.join(STATIC_DIR, "index.html")
            self.serve_static_file(static_file, "text/html")
            return

        rel_static = path.lstrip("/")
        for candidate_dir in [WEB_DIR, STATIC_DIR]:
            candidate = os.path.join(candidate_dir, rel_static)
            if os.path.exists(candidate) and os.path.isfile(candidate):
                mime, _ = mimetypes.guess_type(candidate)
                self.serve_static_file(candidate, mime or "application/octet-stream")
                return

        self.send_error(404, "Page Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # Gamepad Input Relay (Phone sends touch button states)
        if path == "/api/gamepad/input":
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len).decode('utf-8') if content_len > 0 else "{}"
            try:
                data = json.loads(body)
                with GAMEPAD_LOCK:
                    GAMEPAD_STATE.update(data)
                    GAMEPAD_STATE["timestamp"] = time.time()
                self.send_json({"status": "received", "time": GAMEPAD_STATE["timestamp"]})
                return
            except Exception as e:
                self.send_json({"error": str(e)}, status=400)
                return

        # Wishlist Management
        if path == "/api/wishlist":
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len).decode('utf-8') if content_len > 0 else "{}"
            try:
                data = json.loads(body)
            except Exception:
                data = {}
            action = data.get("action", "add")
            wishlist = get_wishlist()
            if action == "add":
                title = data.get("title", "").strip()
                if not title:
                    self.send_json({"status": "error", "message": "Title required"}, status=400)
                    return
                item = {
                    "id": f"wish_{int(time.time()*1000)}",
                    "title": title,
                    "year": data.get("year", "").strip(),
                    "notes": data.get("notes", "").strip(),
                    "status": data.get("status", "Wanted"),
                    "added_by": NODE_NAME,
                    "added_at": int(time.time())
                }
                wishlist.append(item)
                save_wishlist(wishlist)
                self.send_json({"status": "success", "item": item})
                return

        self.send_error(404, "Endpoint not found")

    def serve_live_transmux(self, filepath):
        try:
            self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except Exception:
            pass

        cmd = [
            "ffmpeg", "-re", "-i", filepath,
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-f", "mp4",
            "-movflags", "frag_keyframe+empty_moov+default_base_moof",
            "pipe:1"
        ]

        self.send_response(200)
        self.send_cors_headers()
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()

        proc = None
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=64 * 1024)
            while True:
                chunk = proc.stdout.read(64 * 1024)
                if not chunk:
                    break
                self.wfile.write(chunk)
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            if proc:
                proc.terminate()
                try: proc.wait(timeout=2)
                except: proc.kill()

    def serve_file_range(self, file_path, as_attachment=False, download_name=None):
        try:
            file_size = os.path.getsize(file_path)
            range_header = self.headers.get('Range')

            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                if file_path.endswith('.mkv'):
                    mime_type = "video/x-matroska"
                elif file_path.endswith('.mp4'):
                    mime_type = "video/mp4"
                else:
                    mime_type = "application/octet-stream"

            try:
                self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            except Exception:
                pass

            if range_header:
                range_match = range_header.strip().replace("bytes=", "").split("-")
                start = int(range_match[0]) if range_match[0] else 0
                max_chunk = 4 * 1024 * 1024
                requested_end = int(range_match[1]) if len(range_match) > 1 and range_match[1] else None
                end = min(start + max_chunk - 1, file_size - 1) if requested_end is None else min(requested_end, file_size - 1)

                if start >= file_size or end >= file_size or start > end:
                    self.send_error(416, "Requested Range Not Satisfiable")
                    return

                length = end - start + 1
                self.send_response(206)
                self.send_cors_headers()
                self.send_header("Content-Type", mime_type)
                self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                self.send_header("Content-Length", str(length))
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Cache-Control", "public, max-age=3600")
                if as_attachment:
                    self.send_header("Content-Disposition", f'attachment; filename="{download_name or os.path.basename(file_path)}"')
                self.end_headers()

                with open(file_path, "rb") as f:
                    f.seek(start)
                    remaining = length
                    chunk_size = 256 * 1024
                    while remaining > 0:
                        read_bytes = min(remaining, chunk_size)
                        chunk = f.read(read_bytes)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        remaining -= len(chunk)
            else:
                self.send_response(200)
                self.send_cors_headers()
                self.send_header("Content-Type", mime_type)
                self.send_header("Content-Length", str(file_size))
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Cache-Control", "public, max-age=3600")
                if as_attachment:
                    self.send_header("Content-Disposition", f'attachment; filename="{download_name or os.path.basename(file_path)}"')
                self.end_headers()

                with open(file_path, "rb") as f:
                    shutil.copyfileobj(f, self.wfile, length=256 * 1024)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            pass

    def send_json(self, data, status=200):
        body = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def serve_static_file(self, file_path, mime_type, cache_seconds=3600):
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_cors_headers()
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", f"public, max-age={cache_seconds}")
            self.end_headers()
            self.wfile.write(content)
        except Exception:
            self.send_error(500, "Error reading static file")

class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True

def main():
    print("=" * 60)
    print(f"🎬 MOVIEBOX COSMIC HUB v{VERSION} - NODE: {NODE_NAME}")
    print(f"📡 Local IP: http://{LOCAL_IP}:{PORT}")
    print(f"🍿 Movies: {MOVIES_DIR}")
    print(f"🎵 Music:  {MUSIC_DIR}")
    print(f"🎮 Games:  Arcade & P2P Gamepad Active")
    print("=" * 60)

    beacon = MeshBeacon()
    beacon.start()

    server = ThreadedHTTPServer(('0.0.0.0', PORT), MeshHTTPHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()

if __name__ == "__main__":
    main()
