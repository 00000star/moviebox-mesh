# MovieBox Cosmic - Project State

## System Status
- **Current Version**: v1.4.1 (Cosmic Edition)
- **Node**: TECNO KM4k (Host: Android 15 / Termux)
- **Primary Peer**: Dell Latitude E7450 (10.204.123.211:8080)
- **Mesh Status**: Active & Linked (UDP port 9999, HTTP port 8080)
- **Dependencies**: Zero external packages (Pure Python 3.10+ stdlib)

## Active Catalog Inventory
- **Movies**: 32 verified items (1080p Sci-Fi & Action collection)
- **Live IPTV**: 300 channels (parsed M3U8 streams)
  - Movies: 60 channels
  - Sports: 61 channels
  - News: 59 channels
  - General Entertainment: 120 channels
- **Music & Radio**:
  - Local Audio: 2 tracks (/sdcard/Music)
  - Cosmic Radio: 17 live curated web radio streams
  - Floating Player: Persistent background playback bar
- **E-Reading**:
  - Webtoons / Manhwa: 1 vertical continuous image reader
  - Light Novels: 1 distraction-free reader
- **Offline Apps Vault**: 1 Android package distribution
- **Gaming Subsystem**:
  - HTML5 Arcade: Cosmic Starfighter (60 FPS Canvas)
  - Wireless Controller: Virtual touch gamepad with PC sync

## Key Operating Endpoints
- Web UI: `http://127.0.0.1:8080` (or `http://<node-ip>:8080`)
- Catalog API: `GET /api/catalog`
- Direct Streaming: `GET /stream/media?path=<path>`
- Direct Download / PC Save: `GET /stream/download?path=<path>`
- Live FFmpeg Transmuxer: `GET /play/live/<media_id>`
- Gamepad Relay: `POST /api/gamepad/input` & `GET /api/gamepad/state`
- Apps Distribution: `GET /api/apps` & `/api/apps/download/<file>`
