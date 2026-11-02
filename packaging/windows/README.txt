TripPlanner 0.8.0-demo.2 — Windows x64 portable demonstration

1. Extract the WHOLE ZIP into a folder. Do not run an executable inside the ZIP.
2. Open TripPlanner.exe. Keep its _internal and licenses folders beside it.
3. Choose a city, enter preferences, view ideas, build an itinerary, and save it.

No separately installed Python, editor, or development server is needed.
Microsoft Edge WebView2 Runtime and the normal Windows .NET Framework are
prerequisites. Use Microsoft's official runtime instructions if it is absent:
https://developer.microsoft.com/microsoft-edge/webview2/

This is an unsigned class-project demo, not a signed public production release.
Follow your Windows/organization policy for unsigned software. This document
does not instruct you to bypass SmartScreen, antivirus, or certificate warnings.

Your saved trips, appearance, and browser profile live separately under your
Windows account's local application-data folder, normally:
%LOCALAPPDATA%\TripPlanner
Replacing this app folder does not reset that profile. Keep your own backup
before repairing or deleting data. Sharing the same Windows profile shares its
local collection. There are no private accounts or application-level encryption.

Advanced/QA: TripPlanner.exe --data-dir C:\your-own-absolute-profile-folder
Use a separate empty folder for demonstration tests. Close the existing window
before opening another app against the same profile.

Core planning, bundled pictures, and local saves use local data. Google Maps,
venue sources, license deeds, and photographer links open in your normal system
browser and need internet. The app covers six curated cities, not live worldwide
search. Costs and time slots are illustrative, not bookings or current prices.

Keep LICENSE, PHOTO_CREDITS.md, THIRD_PARTY_NOTICES.md, CODE_LICENSE.md, and licenses/ when
redistributing this whole folder. build-info.json identifies actual versions;
artifact-inventory.json records bundled-file hashes. The adjacent ZIP SHA-256
file lets you compare the download's checksum.

If startup fails, read the message. Do not delete your database as a workaround.
Check WebView2 availability and writable profile permissions, then close/retry.
