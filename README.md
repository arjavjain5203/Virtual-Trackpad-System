# Virtual Trackpad System

A Linux background daemon that turns your webcam into a virtual trackpad using hand gestures.

## Features
- **Gesture Control**: Move, Click, Scroll, and Switch states.
- **Low Latency**: Uses Kalman Filtering and Adaptive Smoothing.
- **System Integration**: Runs as a systemd service with uinput integration.
- **Privacy**: Processed locally, no data stored or sent.

### Prerequisites

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install python3-venv python3-pip libopencv-dev
# For uinput support
sudo usermod -aG input $USER
```

#### Windows
- Install [Python 3.10+](https://www.python.org/downloads/windows/)
- No special drivers needed (uses `pyautogui`).

### Installation
1.  Clone the repository.
2.  Run the setup:
    - **Linux**: `./scripts/install.sh`
    - **Windows**:
        ```powershell
        python -m venv venv
        .\venv\Scripts\activate
        pip install -r requirements.txt
        ```

## Usage

### Two-Handed Interaction System
The system uses a **Left Hand = Mode**, **Right Hand = Action** paradigm.

**1. Left Hand (Mode Selector)**
| Mode | Hand Pose | Description |
| :--- | :--- | :--- |
| **NEUTRAL** | Fist / Closed | System OFF (Safety) |
| **ARMED** | Open Palm | **Cursor Move** enabled |
| **CLICK** | Thumb Up | **Click/Tap** enabled |
| **DRAG** | OK Sign (Index+Thumb circle) | **Drag** enabled |
| **SCROLL** | Two Fingers (Index+Middle) | **Scroll** enabled |
| **SYSTEM** | Three Fingers | (Reserved for shortcuts) |

**2. Right Hand (Executor)**
| Action | Hand Pose | Effect (Dependent on Mode) |
| :--- | :--- | :--- |
| **CURSOR** | Index Finger | Moves Cursor (in ARMED/CLICK/DRAG) |
| **CLICK** | **Fist (Close Hand)** | **Left Click** (in ARMED Mode) |
| **TAP**| Pinch (Thumb + Index) | Left Click (in CLICK Mode) |
| **DRAG** | Pinch (Thumb + Index) | Holds Click (in DRAG Mode) |
| **SCROLL** | Index Finger (Vertical) | Scrolls Page (in SCROLL Mode) |
| **CANCEL** | Fist | Stops all actions (in other modes) |

### Running
- **Linux**: `sudo ./venv/bin/python src/main.py`
- **Windows**: `python src/main.py`

### Running as Service (Linux Only)
```bash
sudo systemctl start virtual-trackpad
sudo systemctl enable virtual-trackpad
```
Check logs:
```bash
journalctl -u virtual-trackpad -f
```

## Configuration
Edit `src/config.py` to tune:
- `SENSITIVITY_X / Y`: Cursor speed.
- `FILTER_BETA`: Smoothing amount (Lower = Smoother/Slower, Higher = Faster/Rougher).
- `CAMERA_ID`: If you have multiple cameras.

## Troubleshooting

### MediaPipe Issues
If you see `AttributeError: module 'mediapipe' has no attribute 'solutions'`, ensure you have the correct package installed:
```bash
pip uninstall mediapipe
pip install mediapipe
```

### Permission Denied
If you get `Permission denied: '/dev/uinput'`:
1. Check udev rules: `ls -l /dev/uinput` should show root:input or root:yourgroup.
2. Ensure you are in the group: `groups`.
3. Reboot if udev rules didn't apply.

### No Camera
Ensure your user has access to `/dev/video0` (usually `video` group).
# Virtual-Trackpad-System
