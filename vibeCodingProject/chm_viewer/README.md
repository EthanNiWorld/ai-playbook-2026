# 📖 CHM Web Viewer

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python)](https://www.python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Linux-lightgrey)]()

A lightweight, zero-dependency web viewer for reading `.chm` files in your browser.

**Single-file Python app — no `pip install` needed.**

---

## ✨ Features

| Feature | Details |
|---------|---------|
| 📤 **Upload** | Drag & drop or click to select `.chm` files |
| 📑 **TOC Navigation** | Auto-parsed directory tree with collapsible folders |
| 🖼️ **Gallery Mode** | Auto-aggregated image viewer with keyboard / swipe / scroll navigation |
| 🔍 **Zoom** | Click to enlarge, scroll to zoom, drag to pan, pinch on touch devices |
| ▶️ **Autoplay** | 2.5s interval slideshow with pause control |
| 🌐 **Zero Deps** | Pure Python standard library — no pip packages required |

## 📸 Screenshots

```
┌─────────────────────────────────────┐
│         CHM Web Viewer              │
│                                     │
│    ┌─────────────────────────┐      │
│    │  📁 Click or drag to    │      │
│    │     upload .chm file    │      │
│    └─────────────────────────┘      │
│                                     │
│    📚 Previously opened books       │
│     📕 yandorr.chm    504 files     │
└─────────────────────────────────────┘
         ↓ Upload & Extract
┌─────────────────────────────────────┐
│ 📁 yandorr.chm                      │
│ 504 files, 12 folders               │
│                                     │
│ 🖼️ Gallery Mode (128 images)        │
│  📁 Folder A                        │
│    📄 page1.htm                     │
│    🖼️ photo1.jpg                    │
│  📁 Folder B                        │
└─────────────────────────────────────┘
         ↓ Gallery Mode
┌─────────────────────────────────────┐
│ ‹              3 / 128            › │
│         ┌──────────────┐            │
│         │              │            │
│         │   [ Image ]  │            │
│         │              │            │
│         └──────────────┘            │
│ [thumb][thumb][thumb][thumb]...     │
└─────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

The only system dependency is `chmlib` (provides the `extract_chmLib` command):

```bash
# macOS
brew install chmlib

# Ubuntu / Debian
sudo apt install libchm-bin

# CentOS / RHEL / Fedora
sudo yum install chmlib

# Arch Linux
sudo pacman -S chmlib
```

### Run

```bash
# Clone and run — that's it
git clone https://github.com/YOUR_USERNAME/chm_viewer.git
cd chm_viewer
python3 chm_viewer.py
```

The browser will auto-open at `http://127.0.0.1:8899`. Upload a `.chm` file to start reading.

## 📝 CLI Options

```bash
python3 chm_viewer.py [--port PORT]
```

| Argument | Default | Description |
|----------|---------|-------------|
| `--port` | `8899`  | HTTP server port |

## ⌨️ Keyboard Shortcuts

### Gallery Mode

| Key | Action |
|-----|--------|
| `←` `→` `↑` `↓` | Previous / Next image |
| `Space` | Next image |
| `Enter` / `z` | Open zoom view |

### Zoom Mode

| Key | Action |
|-----|--------|
| `+` / `-` | Zoom in / out |
| `0` | Reset zoom to fit |
| `Esc` | Close zoom view |
| Scroll wheel | Zoom at cursor position |
| Double-click | Toggle 2× / fit-to-screen |
| Drag | Pan image |

### Touch Gestures

| Gesture | Action |
|---------|--------|
| Swipe left / right | Previous / Next image |
| Pinch | Zoom in / out |
| Tap image | Open zoom view |

## 🏗️ Architecture

```
chm_viewer.py (single file, ~850 lines)
│
├── Backend (Python stdlib only)
│   ├── http.server          — Local HTTP server
│   ├── email.parser         — Multipart upload parsing
│   ├── subprocess            — Calls extract_chmLib
│   └── tempfile             — Temporary extraction directory
│
└── Frontend (inline HTML/CSS/JS, no frameworks)
    ├── Landing page         — File upload + book list
    ├── TOC page             — Collapsible directory tree
    ├── Gallery mode         — Swipe/keyboard/scroll viewer
    └── Zoom overlay         — Pan/zoom/pinch lightbox
```

**Key design decisions:**
- **No npm/pip dependencies** — everything runs on Python standard library
- **No Node.js, no build step** — just `python3 chm_viewer.py`
- **Temp directory cleanup** — extracted files are automatically removed on exit
- **Local-only** — binds to `127.0.0.1`, never exposed to network

## 📂 Project Structure

```
chm_viewer/
├── chm_viewer.py       # Main application (single file)
├── requirements.txt    # Dependency notes (no pip packages needed)
├── README.md           # This file
├── LICENSE             # MIT License
└── .gitignore          # Git ignore rules
```

## ⚠️ Notes

- Extracted files are stored in the system temp directory and **auto-cleaned on exit**
- Max upload size: **500MB**
- Binds to **127.0.0.1 only** — not accessible from other machines
- CHM files with non-UTF-8 encoding may display garbled text in some edge cases

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| `extract_chmLib: command not found` | Install chmlib: `brew install chmlib` (macOS) or `sudo apt install libchm-bin` (Linux) |
| Port 8899 already in use | Use `--port` flag: `python3 chm_viewer.py --port 9000` |
| Python version error | Requires Python 3.8+ (`python3 --version` to check) |
| Chinese filenames garbled | Known issue with some CHM files; content is still readable |

## 📄 License

[MIT](LICENSE) — free for personal and commercial use.
