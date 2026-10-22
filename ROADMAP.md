# MovieBox Cosmic - Strategic Roadmap

This document outlines planned capabilities, architecture milestones,
and future enhancements for MovieBox Cosmic.

---

## 🎯 Phase 1: High-Priority Enhancements (Next Release)

### 1. Automated Wi-Fi Background Folder Sync
- **Objective**: Automatically transfer completed downloads from the
  phone's `/sdcard/Download/` to the PC's permanent storage library
  whenever both devices connect to the same local Wi-Fi or hotspot.
- **Implementation**: Background sync worker comparing file hashes,
  transferring over HTTP chunked upload, and cleaning phone disk space
  upon verified receipt.

### 2. Embedded Subtitle Extraction Pipeline
- **Objective**: Render embedded subtitles from MKV and MP4 files
  directly in the HTML5 browser cinema player.
- **Implementation**: Fast extraction endpoint (`/stream/subtitles/<id>`)
  using `ffmpeg -i <file> -map 0:s:0 -f webvtt pipe:1` to stream WebVTT
  tracks directly to `<track>` elements in the video player.

### 3. Debrid Stream & Torrent Caching
- **Objective**: Integrate sovereign premium cloud torrent caching
  (Real-Debrid / Torbox / AllDebrid) for instant streaming of magnets
  without local downloading.
- **Implementation**: Lightweight Python resolver adding cloud stream
  links into the local catalog alongside offline files.

---

## 🚀 Phase 2: Platform & Ecosystem Expansion

### 4. ZeroConf mDNS & SSDP Discovery
- Augment UDP beacon with RFC-compliant mDNS (`moviebox.local`) so
  users can connect by typing `http://moviebox.local:8080` without
  needing to check IP addresses.

### 5. Progressive Web App (PWA) Offline Caching
- Implement a Service Worker and `manifest.json` enabling the web client
  to be installed to home screens with offline caching for UI assets,
  audio tracks, and downloaded reading material.

### 6. Hardware Transcode Profiles
- Add client device detection to dynamically select between copy transmux
  (`-c:v copy`) and hardware-accelerated 720p transcode for low-powered
  smartphones or older PCs.
