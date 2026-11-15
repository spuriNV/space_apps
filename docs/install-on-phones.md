# Installing CropLytics on a phone

## iPhone (free, needs a Mac and a cable)

iPhone apps can't be sent as a file. Without the paid Apple Developer Program, the app is installed from a Mac over a cable, and it stops opening after **7 days** (re-run step 6 to refresh it).

1. **Check versions.** On the iPhone: Settings → General → About → iOS Version. The Mac needs an Xcode that supports that iOS version (iOS 18 needs Xcode 16 or newer; iOS 26 needs Xcode 26). Install or update Xcode from the Mac App Store.
2. **Get the code** (in Terminal on the Mac):
   ```
   git clone https://github.com/spuriNV/space_apps.git
   open space_apps/apps/ios/CropLytics.xcodeproj
   ```
3. **Sign in to Xcode:** Xcode → Settings → Accounts → **+** → Apple ID. Any normal Apple ID works; it's free.
4. **Set signing:** click the CropLytics project → target **CropLytics** → **Signing & Capabilities**.
   - Tick **Automatically manage signing**.
   - Set **Team** to your name (Personal Team).
   - If Xcode says the bundle ID is taken, change `app.croplytics` to something unique, like `app.croplytics.yourname`.
5. **Prepare the iPhone.**
   - Plug it into the Mac and tap **Trust** on the phone.
   - Turn on **Settings → Privacy & Security → Developer Mode**, and restart when asked.
6. **Install:** pick the iPhone as the run destination in Xcode's top bar, then press **▶ Run**.
7. **Trust the developer:** the first time it opens, iOS blocks it. On the iPhone: Settings → General → **VPN & Device Management** → your Apple ID → **Trust**. Then open CropLytics.

**Without a cable or the 7-day limit:** that's TestFlight. It needs the paid Apple Developer Program. Then we upload the build and invite testers by email, and they install Apple's **TestFlight** app and tap the invite.

## Android (APK, sideload)

1. Get the signed APK onto the phone, using any of these:
   - the file sent in the Claude chat;
   - Google Drive;
   - email;
   - a USB cable.

   Use the `-arm64` APK for modern phones, such as the Galaxy S25.
2. Open it on the phone. Android asks to **allow installs from this app** (Chrome, Gmail, My Files and so on). Allow it.
3. Tap **Install**. A Play Protect notice may appear because the app isn't from the Play Store. Tap **Install anyway**.

A Google Play internal-testing link replaces this once the Play Console account is verified.
