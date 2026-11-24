# Android APK Installation Guide

Install the standalone Android app directly on your Android phone or tablet (Android 8 through Android 15, including Pixel and Samsung Galaxy One UI).

---

## Step 1: Download the Official APK

1. Open [DontKwo/<Repo> Releases](https://github.com/DontKwo/<Repo>/releases/latest) on your phone's browser.
2. Tap `<AppName>-Android.apk` to download it.
3. If your browser asks *"File might be harmful. Download anyway?"*, confirm the URL shows `github.com/DontKwo/<Repo>` and tap **Download anyway**.

---

## Step 2: Samsung Galaxy Only (Disable Auto Blocker Temporarily)

Samsung phones running **One UI 6 or newer** turn on **Auto Blocker** by default, which overrides standard sideload permissions and blocks APK installs:

1. Open **Settings** -> **Security and privacy**.
2. Tap **Auto Blocker**.
3. Toggle **Auto Blocker** to **Off** temporarily (you will turn it back on after installation finishes).

---

## Step 3: Allow "Install Unknown Apps" for Your Browser or File Manager

Android grants APK installation permission per opener app (for example **Chrome**, **Firefox**, **Samsung Internet**, **Files by Google**, or **Samsung My Files**):

- **Pixel / Stock Android (Android 8-15)**:
  1. Open **Settings** -> **Apps** -> **Special app access** -> **Install unknown apps**.
  2. Tap your browser (or file manager) and turn on **Allow from this source**.
- **Samsung Galaxy**:
  1. Open **Settings** -> **Security and privacy** -> **More security settings** -> **Install unknown apps**.
  2. Tap your browser (or **My Files**) and turn on **Allow from this source**.

---

## Step 4: Install & Handle Google Play Protect Warnings

1. Tap the completed `<AppName>-Android.apk` notification or open it in **Files** / **My Files** -> **Downloads**.
2. Tap **Install**.
3. If **Google Play Protect** displays a warning dialog (*"Unsafe app blocked"* or *"Play Protect doesn't recognize this app's developer"*):
   - Tap **More details** (or the small arrow next to the warning).
   - Tap **Install anyway** at your own discretion.
4. If Play Protect blocks installation without an **Install anyway** button:
   - Open **Google Play Store** -> tap your **Profile icon** (top right) -> **Play Protect** -> **Settings gear** (top right).
   - Temporarily switch **Scan apps with Play Protect** to **Off**, install the APK, and immediately return to turn **Scan apps with Play Protect** back **On**.

---

## Step 5: Android 13-15 "Restricted Settings" (If Needed Later)

On Android 13, 14, and 15, sideloaded apps may show *"For your security, this setting is currently unavailable"* for sensitive permissions:

1. Trigger the permission request inside `<AppName>` once so Android registers the request.
2. Open **Settings** -> **Apps** -> **See all apps** -> **`<AppName>`**.
3. Tap the **three-dot menu** in the top-right corner -> **Allow restricted settings** -> confirm with your PIN, pattern, or fingerprint.
4. Grant the requested permission inside App Info -> **Permissions**.

---

## Step 6: Re-Enable Device Protections

After `<AppName>` finishes installing:

1. Turn **Allow from this source** back **Off** for your browser or file manager.
2. Confirm **Google Play Protect** scanning is **On**.
3. On Samsung Galaxy devices, turn **Auto Blocker** back **On**.

---

## Safety & Authenticity Warning

- **Security Prompts Are Expected**: Your phone will likely tell you the app is unrecognized, unverified, or potentially unsafe because this `.apk` is distributed directly from GitHub outside the Google Play Store.
- **Official `main` Releases Only**: Only `.apk` files published on the official [DontKwo/<Repo> Releases](https://github.com/DontKwo/<Repo>/releases/latest) page (`main` branch) are maintained by the author.
- **Fork Warning**: Never download forked `.apk` releases unless you are completely sure they do not contain malware. Only official `main` releases have no malware to the best of the author's knowledge, and I still make no promises.
- **Your Discretion & Zero Liability**: Bypassing Android security prompts is strictly at your own discretion. This software is provided "AS IS" under the [MIT License](../LICENSE) with zero warranty or liability.

---

## Related Documentation

- [Project Overview](../README.md)
- [Desktop Installation Guide](INSTALLATION.md)
- [User Guide](USER_GUIDE.md)
- [Developer Guide](DEVELOPMENT.md)
- [Security Policy](../SECURITY.md)
- [MIT License](../LICENSE)
