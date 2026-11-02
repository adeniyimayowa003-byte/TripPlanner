# Presentation handoff

**Public website follow-up:** Phase 9 is an approved extension, separate from the packaged classroom checkpoint described below. Production code and operator instructions are being checked; no public URL has been deployed. Read the [hosting guide](public-hosting.md). Until actual deployment acceptance is recorded, demonstrate the verified local apps and describe online hosting as pending. The existing PowerPoint/Word binaries retain their original release evidence and have not been regenerated to claim a public deployment.

The classroom materials are local editable files under `dist/presentation/`:

- `TripPlanner-Presentation.pptx`: 17 slides with speaker notes, travel photography, actual web/Windows/Android screenshots, the specification and development method, code responsibilities, AI scoring, scheduling, money/saves, privacy, platform evidence, testing, and the live-demo sequence.
- `TripPlanner-Presentation-Guide.docx`: 16 pages explaining the project, summarized specifications/plans, beginner programming concepts, platform limits, a rehearsal script, probable teacher questions, and image credits.

Keep these files locally available for the presentation. They are release artifacts rather than ordinary GitHub source files. `dist/` remains ignored. The slide deck uses editable text and embedded pictures, with source/photograph credits in its notes. The Word guide is editable and includes its own attribution appendix. They are intended for roughly a 9–12 minute explanation/demo, adjustable to the actual class time limit.

## Rehearse a predictable journey

1. Open the extracted Windows demo before connecting the projector.
2. Choose Paris, three days, EUR 300 activities/food allowance per person, food and history, and no pace/family preference.
3. Explain one matching reason and the equal daily allowance.
4. Show the itinerary: seven of nine suggested slots, EUR 135 scheduled, EUR 165 unallocated. Explain a gap and the missing-meals notice.
5. Save with a clear name, select Dark, close/reopen, and open the saved trip. Explain the frozen snapshot and remembered appearance.
6. When internet is available, open Luxembourg Gardens externally in Maps and return. The app uses no Maps API key.
7. If the live demo is interrupted, slides 3 and 10 show the recorded Windows journey. Slide 14 shows the actual Android emulator app. Use the Word guide to continue explaining the same tested behavior.

No fixed weekly timeline applies. Describe the four SDD steps separately from the functional product increments. The AI is explainable rule-based matching and greedy scheduling. The release contains no trained model or autonomous agent. Be precise about the six-city dataset, illustrative costs, missing meals, and platform/device verification limits.

Read [final release checks](final-release-checks.md), the [Windows guide](windows-download.md), and the [Android guide](android-download.md) before presenting. A physical Android phone has not been tested, and the current packages are classroom demos rather than app-store releases. The source and CI setup are ready for local review; no GitHub repository was uploaded by this task.
