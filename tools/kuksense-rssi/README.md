# KukSense RSSI MVP

This is the first hardware-free KukSense experiment. It uses the WiFi adapter already present in a Windows laptop and watches changes in nearby access-point signal strength.

## What it can do

- continuously scan nearby WiFi BSSIDs
- record signal percentage and estimated dBm
- calculate rolling signal variance
- output a basic RF activity score
- classify the environment as `calibrating`, `quiet`, `possible-movement`, or `high-activity`
- save all measurements to CSV for later model training

## What it cannot do

This prototype does not provide CSI. It cannot reliably identify a person, count people, estimate pose, detect breathing or heart rate, or make medical or safety claims. It detects RF disturbance only.

## Run on Windows

Open PowerShell in this directory and run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\windows\kuksense-rssi.ps1
```

Optional parameters:

```powershell
.\windows\kuksense-rssi.ps1 -IntervalSeconds 2 -WindowSize 20 -MovementThreshold 4.0 -OutputPath .\session.csv
```

## Test procedure

1. Keep the laptop and router in fixed positions.
2. Run the script for five minutes in an empty, quiet room.
3. Run it for five minutes while one person walks through the room.
4. Repeat with door movement, fan movement, and nearby-device traffic.
5. Compare `RollingStdDev` and `ActivityScore` in the CSV.
6. Tune `MovementThreshold` for the room before treating any state as useful.

## MVP path

1. Validate whether RSSI variance separates quiet and active sessions.
2. Add baseline calibration and adaptive thresholds.
3. Aggregate multiple BSSIDs instead of relying on one signal.
4. Add a local Rust service and WebSocket stream.
5. Connect the stream to the existing Tauri desktop frontend.
6. Add session labelling and a small classifier trained on the user's own room data.

The ESP32/CSI pipeline remains available in the parent repository for a later hardware-assisted version.
