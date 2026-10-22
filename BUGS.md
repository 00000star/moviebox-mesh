# MovieBox Cosmic - Bug Ledger & Root Cause Analyses

This living ledger documents identified defects, root cause analyses,
remediations, and verification states.

---

## BUG-001: Peer Stream URL Relative Path Resolution

- **Severity**: High (Playback Failure)
- **Status**: `VERIFIED FIXED`
- **Symptom**: When browsing from the phone or PC, media items hosted
  on the remote peer failed to load or returned 404 when clicked.
- **Root Cause**: The catalog aggregator merged peer items directly into
  the combined media array without rewriting relative endpoints
  (e.g., `/stream/media?path=...`). The client browser resolved this
  relative URL against the local node instead of the remote peer holding
  the actual file.
- **Fix**: In `mesh_node.py` (`do_GET`), catalog federation inspects all
  peer media entries and prepends `http://<peer_ip>:<peer_port>` to
  `stream_url`, `thumb_url`, `live_url`, and `url`.
- **Verification**: Verified cross-node streaming between phone and
  Dell Latitude E7450 peer node.

---

## BUG-002: Modal Bleed-Through on Initial Web Load

- **Severity**: Medium (Cosmetic / UX Glitch)
- **Status**: `VERIFIED FIXED`
- **Symptom**: During initial page load or when CSS rendering was
  delayed, the Cinema Player modal, Music Player bar, and Arcade modal
  briefly flashed or occupied screen space before JavaScript initialized.
- **Root Cause**: Modal container HTML tags (`#player-modal`,
  `#arcade-modal`, `#music-player-bar`) in `index.html` lacked inline
  `style="display: none;"` definitions, relying entirely on deferred CSS
  classes.
- **Fix**: Added inline `style="display: none;"` directly to the HTML
  markup in both `web/index.html` and `static/index.html`.
- **Verification**: Clean instant page rendering confirmed with zero
  modal flicker or element displacement.

---

## BUG-003: Local IP Detection Fallback to 127.0.0.1

- **Severity**: High (Network Isolation)
- **Status**: `VERIFIED FIXED`
- **Symptom**: Node IP reported as `127.0.0.1` in the catalog and beacon,
  preventing peer nodes from discovering or accessing media streams.
- **Root Cause**: `socket.gethostbyname(socket.gethostname())` on Android
  often returns `127.0.0.1` or `127.0.1.1` instead of the active Wi-Fi or
  hotspot interface IP (`192.168.x.x` or `10.42.x.x`).
- **Fix**: Updated `get_local_ip()` in `mesh_node.py` to create a dummy
  UDP connection to a public DNS IP (`8.8.8.8:80`) to inspect the kernel
  routing table's chosen interface. Added fallback scan over `wlan0`,
  `ap0`, and `rndis0` interfaces via system commands if socket creation
  fails.
- **Verification**: Node accurately detects and broadcasts LAN IP
  (`10.42.0.70`).

---

## BUG-004: Daemon Restart Port Collision (Address In Use)

- **Severity**: High (Service Unavailability)
- **Status**: `VERIFIED FIXED`
- **Symptom**: Restarting `mesh_node.py` failed with `[Errno 98] Address
  already in use` on port 8080.
- **Root Cause**: Python's `ThreadingHTTPServer` socket remained in
  `TIME_WAIT` state, or a previous instance had not fully released the
  socket before the new process attempted `bind()`.
- **Fix**:
  1. Configured `allow_reuse_address = True` on `ThreadingHTTPServer`.
  2. Updated restart runbook and `mb-mesh.sh` to enforce `pkill -9`
     with a 1-second delay before spawning the new daemon process.
- **Verification**: Clean restarts confirmed with zero bind failures.
