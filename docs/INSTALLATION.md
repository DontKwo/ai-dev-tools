# Desktop Installation Guide

Install and launch the `AI-Dev-Tools` Setup Assistant on your computer without Python or terminal commands.

## Safety & Authenticity Warning

- **Official `main` Releases Only**: Download `AI-Dev-Tools` exclusively from [DontKwo/ai-dev-tools Releases](https://github.com/DontKwo/ai-dev-tools/releases/latest).
- **Fork Warning**: Never download executables from forked repositories unless you have verified the source code yourself and know they do not contain malware. Only official `main` releases are maintained by the author, and I make no promises.
- **Bypassing Security Prompts**: Because independent open-source executables do not carry paid commercial signing certificates, Windows and macOS will warn that the app is unrecognized or potentially unsafe. Bypassing these warnings is strictly at your own discretion, and the software is provided "AS IS" with zero liability.

---

## Platform Installation Instructions

### Windows

1. Download `adt-setup-Windows.exe` from [Latest Releases](https://github.com/DontKwo/ai-dev-tools/releases/latest).
2. Double-click `adt-setup-Windows.exe` to open the Setup Assistant.
3. If **Microsoft Defender SmartScreen** displays *"Windows protected your PC"*:
   - Click **More info**.
   - Confirm the file came from `DontKwo/ai-dev-tools`, then click **Run anyway** at your own discretion.
4. Alternative unblock method: Right-click `adt-setup-Windows.exe` -> **Properties** -> check **Unblock** under Security -> click **Apply** and **OK** -> launch normally.

### macOS

1. Download `adt-setup-macOS.zip` from [Latest Releases](https://github.com/DontKwo/ai-dev-tools/releases/latest).
2. Double-click the `.zip` archive to extract the executable (and move to **Applications** if desired).
3. On macOS Sonoma and Sequoia, approve an independently distributed app in **System Settings**:
   - Double-click the extracted app once so macOS shows the blocked notice, then click **OK** (or **Done**).
   - Open **System Settings** -> **Privacy & Security** -> scroll to the **Security** section.
   - Next to the blocked notice, click **Open Anyway** and confirm with your password or Touch ID.
4. Developer Terminal Alternative: run `xattr -cr <path-to-app>` in Terminal, then open it normally.

### Linux

1. Download `adt-setup-Linux.tar.gz` from [Latest Releases](https://github.com/DontKwo/ai-dev-tools/releases/latest).
2. Extract the archive in your file manager (or run `tar -xzf adt-setup-Linux.tar.gz`).
3. Ensure execute permission (`chmod +x adt-setup-Linux`) and launch the application.

---

## Related Documentation

- [Project Overview](../README.md)
- [User Guide](USER_GUIDE.md)
- [Everyday Quickstart](user/quickstart.md)
- [Developer Guide](DEVELOPMENT.md)
- [Security Policy](../SECURITY.md)
- [MIT License](../LICENSE)
