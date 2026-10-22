# MovieBox Cosmic - Technical Debt & Architectural Constraints

This document details known platform constraints, hardware limitations,
and technical debt items requiring maintenance or future refactoring.

## 1. Android Socket Routing & Multicast/Broadcast Quirks

### Issue
On Android 15 (TECNO KM4k host), UDP broadcast packets (`255.255.255.255`)
on port 9999 can occasionally be dropped or filtered by the Linux kernel
when Wi-Fi hotspot mode is enabled or when switching between mobile data
and Wi-Fi interfaces.

### Current Mitigation
- The beacon sender iterates over multiple target broadcast addresses:
  `255.255.255.255`, subnet-directed broadcast (`192.168.43.255`,
  `10.42.0.255`), and explicit peer unicast if a peer was previously
  discovered.

### Future Architecture
- Introduce a lightweight multicast DNS (mDNS / SSDP) responder or direct
  subnet TCP ping discovery to supplement UDP broadcast.

---

## 2. Dell Latitude E7450 Hardware Decoding Limitations

### Hardware Profile
- **CPU**: Intel Core i5-5300U (2 cores / 4 threads, 2.3 GHz).
- **GPU**: Intel HD Graphics 5500 (Broadwell GT2).
- **Supported Codecs**: H.264 / AVC 8-bit hardware decode; VP8.
- **Unsupported Codecs**: H.265 / HEVC 10-bit hardware decode, AV1.

### Impact on Playback
- 10-bit HEVC (H.265 Main 10) high-bitrate video causes 100% CPU spikes
  and stuttering when played in web browsers on the Dell Latitude E7450.
- 8-bit H.264 (AVC) plays smoothly at 1080p with near-zero CPU load.

### Mitigation & Guidance
- Standardize downloads and library conversions on 1080p H.264 (AVC)
  AAC MP4 with `moov` atom at the front (`-movflags faststart`).
- When streaming MKV/HEVC to the PC node, trigger the live transmuxer
  or offload raw files directly to disk via "⬇️ Save to PC" for playback
  in MPV or VLC with multithreaded software decode.

---

## 3. Background Daemon Keepalive on Android 15

### Issue
Android 15 uses aggressive battery optimization and OEM state management
(`Hiber/stateManager`) which terminates background Termux processes or
drops listening sockets when the device enters deep sleep.

### Current Mitigation
- `mb-mesh.sh` tracks process IDs in `.mesh.pid` and launches via
  `nohup ... &`.
- Termux wake-lock (`termux-wake-lock`) should be enabled during active
  media streaming sessions.

### Future Architecture
- Add an optional Android foreground notification service wrapper via
  Termux:API or a lightweight native Android companion service.
