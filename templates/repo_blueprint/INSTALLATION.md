# Desktop Installation Guide

Install and launch `<AppName>` on your computer without Python, Node.js, or developer tools.

## Safety & Authenticity Warning

- **Official `main` Releases Only**: Download `<AppName>` exclusively from [DontKwo/<Repo> Releases](https://github.com/DontKwo/<Repo>/releases/latest).
- **Fork Warning**: Never download builds from forked repositories unless you have verified the source code yourself and know they do not contain malware. Only official `main` releases are maintained by the author, and I make no promises.
- **Bypassing Security Prompts**: Because independent open-source executables do not carry paid commercial signing certificates, Windows and macOS will warn that the app is unrecognized or potentially unsafe. Bypassing these warnings is strictly at your own discretion, and the software is provided "AS IS" with zero liability.

---

## Platform Installation Instructions

### Windows

1. Download `<AppName>-Windows.exe` from [Latest Releases](https://github.com/DontKwo/<Repo>/releases/latest).
2. Double-click the downloaded `.exe` file to open `<AppName>`.
3. If **Microsoft Defender SmartScreen** displays *"Windows protected your PC"*:
   - Click **More info**.
   - Confirm the file came from `DontKwo/<Repo>`, then click **Run anyway** at your own discretion.
4. Alternative unblock method: Right-click `<AppName>-Windows.exe` -> **Properties** -> check **Unblock** near the bottom under Security -> click **Apply** and **OK** -> open the file normally.

### macOS

1. Download `<AppName>-macOS.zip` (or `.dmg`) from [Latest Releases](https://github.com/DontKwo/<Repo>/releases/latest).
2. Double-click the archive to unpack it (or open the `.dmg`) and drag **`<AppName>.app`** into your **Applications** folder.
3. On macOS Sonoma and Sequoia, approve an independently distributed app in **System Settings**:
   - Double-click `<AppName>.app` once so macOS shows the blocked notice, then click **OK** (or **Done**).
   - Open **System Settings** -> **Privacy & Security** -> scroll to the **Security** section.
   - Next to `"<AppName>.app was blocked"`, click **Open Anyway** and confirm with your password or Touch ID.
4. Developer Terminal Alternative (when working locally): run `xattr -cr /Applications/<AppName>.app` in Terminal, then open `<AppName>.app` normally.

### Linux

1. Download `<AppName>-Linux.tar.gz` from [Latest Releases](https://github.com/DontKwo/<Repo>/releases/latest).
2. Extract the archive in your file manager (or run `tar -xzf <AppName>-Linux.tar.gz`).
3. Make the extracted binary executable (right-click -> **Properties** -> **Permissions** -> allow executing as program, or run `chmod +x <AppName>`).
4. Double-click `<AppName>` (or run `./install.sh` if included in the archive) to launch.

---

## Related Documentation

- [Project Overview](../README.md)
- [User Guide](USER_GUIDE.md)
- [Developer Guide](DEVELOPMENT.md)
- [Security Policy](../SECURITY.md)
- [MIT License](../LICENSE)
