# VoidCat Tether - Setup & Security Guide

## Overview

VoidCat Tether is a Flutter-based mobile application that acts as a remote "Control Pad" for the Sovereign Spirit middleware. It allows you to trigger pulses, wake agents, and monitor the internal monologue stream.

## Prerequisites

- **Flutter SDK**: Installed and configured (run `flutter doctor`).
- **Java JDK 1.8**: Configured via `JAVA_HOME`.
- **Android Device**: Connected via USB.
- **Sovereign Middleware**: Running locally (port 8020).

## 0. Configure Java JDK (One-time)

Android builds require Java 8. Ensure your environment is set:

```powershell
# Verify Java version
java -version

# If not found, ensure JAVA_HOME points to your installation:
$env:JAVA_HOME = "C:\Users\Wykeve\.jdks\java-1.8.0-openjdk-1.8.0.392-1.b08.redhat.windows.x86_64"
$env:PATH += ";$env:JAVA_HOME\bin"
```

## 1. Prepare your Android Device (Critical)

Before you can run the app, you must enable **USB Debugging**:

1.  **Enable Developer Mode**:
    -   Go to **Settings > About Phone**.
    -   Tap **Build Number** 7 times until you see "You are now a developer!".

2.  **Enable USB Debugging**:
    -   Go to **Settings > System > Developer Options**.
    -   Toggle **USB Debugging** to **ON**.

3.  **Authorize Computer**:
    -   Plug your phone into the PC.
    -   Unlock your phone.
    -   Look for a popup: *"Allow USB debugging?"*
    -   Check "Always allow from this computer" and tap **Allow**.

## 2. Verify Connection

Open a terminal and check if your device is recognized:

```powershell
# You may need to use the full path if adb is not in PATH
& "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe" devices
```

You should see:

```text
List of devices attached
XXXXXXXX    device
```

If it says `unauthorized`, check your phone screen again.

## 3. Set Up Port Forwarding (Recommended)

This magic command allows your phone to access your PC's `localhost:8020` directly.

```powershell
& "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe" reverse tcp:8020 tcp:8020
```

## 4. Security Configuration (Middleware)

Ensure your `.env` file has:

```env
SOVEREIGN_API_KEY_ENABLED=true
SOVEREIGN_API_KEY=voidcat-secure-handshake-2026
```

## 5. Running the App

1.  Navigate to the directory:
    ```powershell
    cd voidcat_tether
    ```

2.  Run on your device:
    ```powershell
    flutter run -d <device-id>
    ```
    *(If only one device is connected, just `flutter run` works)*

## 6. The Handshake Protocol (First Launch)

Upon first launch, the app will detect a missing configuration and present the **"Connect to Sovereign Spirit"** dialog.

- **Hub URL**:
  - If you ran the `adb reverse` command in Step 3, use: `http://localhost:8020`
  - Otherwise, use your PC's LAN IP (e.g., `http://192.168.1.100:8020`).
- **API Key**: Enter the value from your `.env` (e.g., `voidcat-secure-handshake-2026`).

Click **CONNECT**.

## Troubleshooting

- **No Devices Found**: Check your USB cable (some are charge-only). ensure USB Debugging is ON.
- **Connection Refused**: Did you run `adb reverse`? If not, `localhost` on the phone refers to the phone itself, not the PC.
- **Auth Error (403)**: Double-check that your API Key matches the `.env` value exactly.
