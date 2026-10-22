# MovieBox Cosmic - System Architecture

## Architecture Overview

MovieBox Cosmic operates as a decentralized, zero-dependency P2P
media hub. Any node (Android phone, Linux laptop, Windows PC) running
`mesh_node.py` simultaneously behaves as an HTTP content server and a
P2P mesh peer.

## Network Topology & Data Flow

```text
+-------------------------------------------------------+
|                 LOCAL WI-FI / HOTSPOT                 |
+-------------------------------------------------------+
        |                                       |
+-------------------+                   +-------------------+
|    PHONE NODE     |   UDP Beacon      |     PC NODE       |
|    (TECNO KM4k)   |<=================>|  (Dell Latitude)  |
|    Port 8080      |   Port 9999       |    Port 8080      |
+-------------------+                   +-------------------+
        |                                       |
        |--- Federated Catalog Polling -------->|
        |<-- Direct Media Stream / Download ----|
        |--- Touch Gamepad Input (HTTP/WS) ---->|
```

## Subsystem Details

### 1. P2P Mesh UDP Beacon (Port 9999)
- Every node runs a background UDP broadcast daemon sending a JSON
  announcement packet every 5 seconds.
- Payload contains `node_name`, `ip`, `port`, `version`, and `code_ts`.
- Inbound listener maintains a dynamic peer table with automatic
  timeout pruning for dead nodes after 15 seconds.

### 2. Multithreaded HTTP Server (Port 8080)
- Built on Python's `http.server.ThreadingHTTPServer`.
- Implements RFC 7233 partial content range requests (`bytes=start-end`)
  allowing instant scrubbing and resume without full buffer download.
- Supports `GET /stream/download` with `Content-Disposition: attachment`
  for direct PC offloading and file preservation.

### 3. Federated Catalog Engine
- When `/api/catalog` is requested, the node scans its local media
  directories and queries known peer nodes asynchronously.
- Peer media objects are federated into a single unified catalog,
  rewriting relative stream URLs to point directly to the host peer IP.

### 4. Real-Time FFmpeg Transmuxer Pipeline
- For video containers (MKV, AVI) or audio codecs (AC3, DTS, EAC3)
  that browsers cannot decode natively, `/play/live/<media_id>`
  spawns a subprocess pipeline:
  `ffmpeg -i <file> -c:v copy -c:a aac -f mp4 -movflags frag_keyframe+empty_moov pipe:1`
- Pipes streaming fragmented MP4 directly to the browser response
  without writing intermediate files to disk.

### 5. Wireless Gamepad Relay
- Mobile client exposes a dual-mode touch virtual gamepad.
- Button presses and joystick vectors are posted to
  `/api/gamepad/input`.
- The PC arcade window polls `/api/gamepad/state` to drive in-browser
  60 FPS canvas gameplay wirelessly across devices.
