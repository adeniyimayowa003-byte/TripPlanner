# TripPlanner submission review — 6 November 2026

**Decision:** The core application and presentation materials are available for a classroom demonstration. Final sign-off remains conditional on the actual hosted restart/redeploy persistence check and a rehearsal on the presentation device. This review does not claim every acceptance criterion or an unseen marking rubric has been satisfied.

## Verified today

- [Public website](https://tripplanner-mayowa.onrender.com/) loads over HTTPS and `/healthz` returns HTTP 200 with `{"status":"ok"}`. Free hosting can sleep, so allow about a minute for the first visit.
- A real browser journey selected Paris, three days, EUR 300 and food/history; it produced seven explained matches, a seven-of-nine-slot itinerary and EUR 135 scheduled estimates.
- A rehearsal trip was saved through the actual form, appeared in Saved trips and reopened with the same preferences, suggestions and estimates. Keyboard submission succeeded. An earlier automation click did not submit and was not counted as success.
- Light and Dark were checked on the live site; ten images loaded on the saved page. The browser's original Use device setting preference was restored. [Dark-mode proof](images/tripplanner-online-saved-dark.jpg) records the successful save.
- A separate HTTP visitor without the saved browser's cookie received HTTP 404 for that saved trip. Its body exactly matched the response for a nonexistent trip, and contained no rehearsal title.
- The [latest recorded GitHub CI run](https://github.com/adeniyimayowa003-byte/TripPlanner/actions/runs/41381620794) passed Windows, Linux and PostgreSQL jobs. The complete local run has **1,688 passed**, zero failures/errors/skips, recorded on 2 November. Application code has not changed in this review; this is not a claim of rerunning the entire suite today.
- All six existing SHA256 sidecars matched their files: Windows ZIP, Android APK, two historical source ZIPs, PowerPoint and Word guide.

## Submission items

| Item | Where to get it | Status |
| --- | --- | --- |
| Public website | https://tripplanner-mayowa.onrender.com/ | Live, with free-tier sleep/usage limits |
| Current source | https://github.com/adeniyimayowa003-byte/TripPlanner | Published; includes hosting, tests, spec and plans |
| Updated source ZIP | `dist/release/TripPlanner-submission-source-2026-11-06.zip` and checksum | Prepared from reviewed current source; check its sidecar |
| Windows demo | `dist/release/TripPlanner-0.8.0-demo.2-windows-x64.zip` | Recorded Windows 11 journey; checksum matched |
| Android demo | `dist/release/TripPlanner-0.8.0-demo.2-android-demo.apk` | Emulator verified; physical phone untested; debug-signed |
| PowerPoint | `dist/presentation/TripPlanner-Presentation.pptx` | 17 slides with notes/photos/screenshots; checksum matched |
| Word guide | `dist/presentation/TripPlanner-Presentation-Guide.docx` | 16 rendered/reviewed pages; checksum matched |

Local binaries and presentation files are assignment attachments under `dist`, which is excluded from source commits. They have not been published as GitHub Release downloads. The older `complete-source.zip` is the earlier native classroom checkpoint and omits subsequent hosting work; use the dated current source ZIP or GitHub for the latest source. The PowerPoint/Word files retain their original local-release evidence; [presentation guidance](presentation-walkthrough.md) supplies the current online link and verification update.

## Still open

1. **Actual cloud restart/redeploy:** Reopen the same saved collection with unchanged secret/storage, compare saved snapshot bytes/fingerprints and confirm visitor isolation. Local tests, browser reload, or the fact that a free host slept do not substitute for this check. The Render dashboard currently requires user sign-in before the operator action can be checked.
2. **Presentation-device rehearsal:** Open the deck, guide and selected demo on the actual laptop/phone used for class. A physical Android handset and arbitrary Office versions are not covered by the recorded emulator/rendering results.
3. **Assignment packaging:** Submit the source plus the PPTX, DOCX and whichever native demo the teacher requests. Read the teacher's actual upload/rubric requirements; they have not been supplied here. A public source repository alone does not include the ignored downloadable binaries.

## What to explain honestly

The AI uses explainable matching scores and greedy scheduling, with six curated cities and illustrative per-person activities/food estimates. It has no trained language model, autonomous agent, live prices, bookings, full route optimization or cross-device account sync. Shared-browser cookie limits and native/cloud storage differences are documented. Original code is MIT; photos and dependencies retain their own licenses.

No app-store publication, production-scale reliability, paid hosting or physical-phone verification is claimed. See [the full local release evidence](final-release-checks.md) and [free hosting evidence](phase-09-free-implementation.md).
