#!/bin/bash
# Records shot 5 (the phone fly-in) from Safari in the iOS Simulator (iPhone 15, iOS 17.5).
# Builds a tiny XCUITest driver (phone-driver/, via xcodegen) that taps the Colusa rice card.
# Output: video/raw/rec/s05_phone.mp4 (+ a 24 fps copy) and s05_phone.marks (tap time, epoch seconds).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/../raw/rec"; mkdir -p "$OUT"
UDID="${UDID:-A0DCD560-FD02-4975-963B-E1F0F40DF841}"   # iPhone 15, iOS 17.5
DD="${DERIVED:-${TMPDIR:-/tmp}/croplytics-simdriver}"
URL="${APP_URL:-https://croplytics-app.onrender.com/}"

xcrun simctl boot "$UDID" 2>/dev/null || true
xcrun simctl bootstatus "$UDID" -b >/dev/null
xcrun simctl ui "$UDID" appearance light
xcrun simctl status_bar "$UDID" override --time 9:41 --batteryLevel 100 --batteryState charged --cellularBars 4 --wifiBars 3 --dataNetwork wifi

cd "$HERE/phone-driver"
xcodegen generate >/dev/null
xcodebuild build-for-testing -project SimDriver.xcodeproj -scheme DriverUITests -destination "platform=iOS Simulator,id=$UDID" -derivedDataPath "$DD" -quiet

# fresh page: the pick list over California
xcrun simctl terminate "$UDID" com.apple.mobilesafari 2>/dev/null || true
xcrun simctl openurl "$UDID" "$URL"
sleep 12

rm -f "$OUT/s05_phone.mp4"
xcrun simctl io "$UDID" recordVideo --codec h264 --force "$OUT/s05_phone.mp4" & REC=$!
sleep 1; python3 -c 'import time;print("rec_start", time.time())' > "$OUT/s05_phone.marks"
PRE_WAIT=2 FLY_WAIT=${FLY_WAIT:-6} xcodebuild test-without-building -project SimDriver.xcodeproj -scheme DriverUITests -destination "platform=iOS Simulator,id=$UDID" -derivedDataPath "$DD" 2>&1 | grep -E "MARK|error|Test Suite .* (passed|failed)" | tee -a "$OUT/s05_phone.marks"
pkill -INT -f "recordVideo.*s05_phone" || true; wait $REC || true
# the simulator writes variable-frame-rate video; a 24 fps copy gives the edit stable times
ffmpeg -v error -y -i "$OUT/s05_phone.mp4" -vf fps=24 -c:v libx264 -crf 12 -preset fast "$OUT/s05_phone_cfr.mp4"
echo "wrote $OUT/s05_phone.mp4 and s05_phone_cfr.mp4 (pick the cut points in build.mjs PHONE_PIECES)"
