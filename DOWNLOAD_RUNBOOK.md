# MovieBox High-Speed Download & Self-Healing Runbook

## 1. Unified Fast Execution
Download any movie or series at maximum speed via the global CLI:
```bash
mb-dl "<Movie Title or IMDb ID>" [--quality 720p|1080p] [--force]
```
- Example: `mb-dl "Dune Part Two" --quality 720p --force`
- Check library & downloads: `mb-dl --status`

---

## 2. Speed Optimization Architecture
* **4-Way Concurrent HTTP Range Slicing**: Slices files into 4 parallel 
  streams to saturate available mobile bandwidth.
* **Direct POSIX `os.pwrite`**: Zero intermediate temporary files, zero 
  stitching overhead. Writes straight to exact disk offsets.
* **Pre-Allocated Storage**: Pre-allocates files with `os.ftruncate` 
  to eliminate disk fragmentation on Android storage.
* **Direct CDN Prioritization**: Automatically prioritizes high-speed 
  Pixeldrain API streams over slow web interstitials.

---

## 3. Self-Healing Diagnostic & Recovery Matrix

| Issue / Failure Point | Root Cause | Automated Remedy |
| :--- | :--- | :--- |
| **`Errno 1: Operation not permitted`** | Colons (`:`) or illegal characters in Android FUSE directory/file names. | `sanitize_name()` automatically strips `[:/*?"<>|]` before creating paths. |
| **Addon HTTP 429 / 500 / Offline** | Free Stremio cloud workers rate-limiting or failing. | 3-tier fallback: queries HdHub (Pixeldrain) -> Hyper -> Cinemeta. |
| **Broken Slice / Connection Drop** | Cellular handover, signal fluctuation. | Each slice retries 3 times with exponential backoff; other slices continue uninterrupted. |
| **"Destination outside download directory"** | Rust canonicalization mismatch (`/sdcard` vs `/storage/emulated/0`). | Canonical path `/storage/emulated/0/Movies/MovieBox/Movies` enforced globally. |
| **Corrupted / Truncated Video File** | Premature socket close or partial stream. | Container magic-byte validation (EBML/MKV `0x1A45DFA3` or MP4 `ftyp`) before rename. |
| **Hotspot Device Can't Connect** | Android `netd` firewall blocking tethered traffic. | Auto-configured via `iptables -I INPUT -p tcp --dport 8080 -j ACCEPT`. |

---

## 4. Storage Structure & Mesh Synchronization
* Storage Root: `/storage/emulated/0/Movies/MovieBox/Movies/<Title>/`
* Mesh Portal: `http://10.0.19.174:8080` (or `http://127.0.0.1:8080`)
* Any file downloaded via `mb-dl` or `moviebox-tui` is immediately 
  indexed and playable across all connected phones and laptops.
