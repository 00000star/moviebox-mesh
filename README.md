# 🎬 MovieBox Cosmic - Decentralized P2P Cinema, Music & Gaming Hub

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://python.org)
[![Dependencies: Zero](https://img.shields.io/badge/Dependencies-Zero%20(Pure%20StdLib)-success.svg)]()
[![P2P: UDP%20Mesh](https://img.shields.io/badge/P2P-UDP%20Beacon%20Mesh-cyan.svg)]()

> A sovereign, 100% dependency-free cross-platform Cinema, Audio, Webtoon and Gaming Hub designed for instant local-network streaming and P2P synchronization between phones, laptops, and PCs.

---

## 🌌 Overview & Architecture

MovieBox Cosmic transforms any local network or Wi-Fi hotspot into a high-performance, all-in-one entertainment mesh. It requires **zero external pip packages or npm modules**—operating entirely on the Python Standard Library and native Web standards.

```text
+-------------------------------------------------------------+
|               MOVIEBOX COSMIC TOPOLOGY & ARCHITECTURE       |
+-------------------------------------------------------------+
  [Phone Screen / Remote]          [PC Display / Big Screen]
  • Touch Virtual Gamepad =======> • 60 FPS HTML5 Canvas Arcade
  • Music Mini-Player              • FastStart Cinema Player
  • Vertical Webtoon Reader        • Permanent Movie Archive
         |                                     |
         +==== P2P Wi-Fi Hotspot Auto-Offload =+
         |    (40 MB/s high-speed local sync)  |
         +-------------------------------------+
```

---

## ✨ Features

- **🎬 Universal In-Browser Cinema Player**: Native HTML5 player with Fullscreen (`F`), 10s seeking (`←/→`), Play/Pause (`Space`), and live on-the-fly FFmpeg transmuxing for MKV/AC3 files (zero VLC required).
- **🚀 FastStart Stream Engine**: Relocates MP4 `moov` atom to file header for instant 100ms playback starts without pre-buffering full files.
- **📱 Phone-to-PC Auto-Offload**: Automatically detects PC peer when connecting to hotspot and syncs completed movie files over local Wi-Fi to preserve phone storage.
- **🎵 Music & Cosmic Radio**: Built-in audio library scanner and persistent floating music player with background audio playback and live web radio streams.
- **🎮 Cross-Device Gaming & P2P Gamepad**:
  - Built-in instant-play arcade (*Cosmic Starfighter*).
  - Virtual Touch Gamepad on phone that controls PC screen games wirelessly.
- **📖 Webtoon & Light Novel Readers**:
  - Vertical continuous scroll reader for Manhwa / Comics.
  - Distraction-free reader with font size controls for light novels.
- **📺 IPTV Live Channels**: Built-in M3U playlist parser indexing 300+ live sports, movies, and news channels.
- **📱 P2P Apps Vault**: Offline APK and installer distribution vault for connected devices without internet.

---

## ⚡ Quickstart

### 1. Clone & Run
```bash
git clone https://github.com/Starboy001/moviebox-mesh.git
cd moviebox-mesh
python3 mesh_node.py
```

### 2. Connect via Browser
Open your browser on any phone, laptop, or PC connected to the same Wi-Fi:
```text
http://<node-ip>:8080
```

---

## 🛠️ CLI Management

A POSIX service controller is included:
```bash
mb-mesh start    # Start background daemon
mb-mesh status   # Check server health & IP
mb-mesh stop     # Stop daemon
```

---

## 📄 License
Released under the [MIT License](LICENSE).
Built with ❤️ for decentralized, sovereign local media networks.
