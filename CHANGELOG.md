# MovieBox Cosmic - Changelog

All notable changes to the MovieBox Cosmic project will be documented
in this file.

## [v1.4.1] - 2026-10-22

### Added
- **Direct Save to PC / Offload Feature**:
  - Implemented `/stream/download` endpoint with RFC 7233 range support
    and `Content-Disposition: attachment`.
  - Added dedicated "⬇️ Save to PC" button on movie cards to trigger
    direct file preservation to PC local disk.
- **Directory Synchronization**:
  - Completely synchronized `static/` with `web/` assets to eliminate
    stale cache and modal bleed bugs in fallback scenarios.
- **System Governance Documentation**:
  - Added `PROJECT_STATE.md`, `ARCHITECTURE.md`, `CHANGELOG.md`,
    `TECH_DEBT.md`, `BUGS.md`, and `ROADMAP.md`.

## [v1.4.0] - 2026-10-22

### Fixed
- **Peer Catalog Federation**:
  - Resolved missing peer movie list by federating peer catalog objects
    into the primary catalog API response.
  - Rewrote relative stream URLs to point to remote peer IPs.
- **Modal Bleed-Through Bug**:
  - Added explicit inline `style="display: none;"` to music, video,
    and arcade modals to prevent initial flash on page load.
- **LAN IP Resolution**:
  - Fixed fallback to `127.0.0.1` by probing active gateway interfaces
    across Wi-Fi hotspot and tethering subnets.
- **Transmuxer Pipeline**:
  - Resolved MKV container browser playback errors via real-time
    fragmented MP4 remuxing (`/play/live/<id>`).

## [v1.3.0] - 2026-10-21

### Added
- **Webtoon & Manhwa Reader**:
  - Vertical continuous-scroll image reader for comics and webtoons.
- **Light Novel Reader**:
  - Distraction-free typography reader with adjustable font sizes.
- **HTML5 Arcade & Wireless Gamepad**:
  - Integrated 60 FPS *Cosmic Starfighter* canvas arcade.
  - Dual-mode mobile touch gamepad relay to control PC games.
- **Offline Apps Vault**:
  - Distribution point for APK packages across offline LAN devices.

## [v1.2.0] - 2026-10-21

### Added
- **Cosmic Glassmorphism UI**:
  - Modern dark-themed cyberpunk UI with responsive grid cards.
- **IPTV Engine**:
  - Integrated M3U playlist parser indexing 300 live TV streams.
- **Music & Radio Subsystem**:
  - Added local audio scanner and 17 live streaming cosmic radio stations.
  - Added persistent floating bottom audio player.

## [v1.1.0] - 2026-10-20

### Added
- **P2P UDP Beacon**:
  - Automated node discovery across Wi-Fi networks on UDP port 9999.
  - Heartbeat exchange and peer table management.

## [v1.0.0] - 2026-10-20

### Added
- Initial standalone HTTP media server on Python standard library.
- FastStart stream engine with HTTP byte-range request support.
