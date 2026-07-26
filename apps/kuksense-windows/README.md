# KukSense Windows v0.1.0

Native desktop test build for hardware-free Wi-Fi RF activity experiments.

## Included
- Native Windows GUI with Start/Stop sensing
- Nearby SSID/BSSID scanning through built-in Windows `netsh wlan`
- Per-BSSID rolling variance and adaptive activity score
- Quiet / possible movement / high activity classification
- Room calibration from collected quiet-room samples
- Live activity graph and nearby-network table
- Automatic local CSV session history under Documents/KukSense/sessions
- Manual CSV export
- No cloud account and no data upload

## Test correctly
Keep laptop and router fixed. Start sensing for 1–2 minutes in an empty quiet room, press **Calibrate room**, then walk through the room and compare the activity score. Repeat tests because normal laptop RSSI is noisy.

## Limitations
This build measures ordinary Wi-Fi RSSI changes, not CSI. It cannot reliably identify people, count people, locate a person, see through walls, detect falls, breathing, heart rate, or provide medical/safety guarantees. Accuracy depends heavily on the Windows Wi-Fi adapter, driver, router placement, interference and scan refresh behavior.

## Build
GitHub Actions creates `KukSense.exe` with PyInstaller on `windows-latest`, validates that the EXE is larger than 1 MB, computes SHA-256, packages it with this README, and uploads the ZIP artifact.
