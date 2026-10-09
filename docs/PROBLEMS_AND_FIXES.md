# Problems and fixes

A record of what went wrong while turning the hackathon prototype into a working system, what caused it, and what was done. Numbers are referenced from [ARCHITECTURE.md](ARCHITECTURE.md). Entries marked **Open** are not solved yet and are tracked in [PLAN.md](PLAN.md).

Test video used for most findings: an 11-second portrait phone clip (478x850, 25 fps) of two workers clearing a garbage-choked drain.

---

## Part 1: Results that were not real

The first review found that much of the "AI" output was scripted. These were the most serious problems, because a municipal tool that reports invented hazards is worse than no tool.

### 1. Fallback detector invented hazards

**Symptom.** Any video, including a clean road, was reported to contain a "choked storm drain" (severity 4, 92% confidence) and an "illegal debris accumulation" (88%).
**Cause.** When Gemini failed or found nothing, `_detect_optical_hazards()` returned those two fixed issues.
**Fix.** Removed. Upload or Pass A failure now fails the job with the error; "no issues found" is a valid result. Test: `test_upload_failure_fails_job_instead_of_inventing_hazards`.

### 2. Scores followed a script, not the video

**Symptom.** Every evidence video showed drainage risk falling from 94.8% "CHOKED" through "RAPID JETTING" to "DRAIN RESTORED" at 58% of the clip's length, whatever it showed.
**Cause.** `get_temporal_telemetry()` computed the numbers from playback position alone. The CCTV page's JavaScript player repeated the same script for one 11.16-second demo clip.
**Fix.** Both removed. Scores are computed once from observed evidence (`compute_observed_hazard_scores`), and the page shows the real values and their sources.

### 3. "Object detection" was brightness thresholding

**Symptom.** Boxes drifted over bright and dark regions labelled as garbage and drains.
**Cause.** `detect_frame_objects()` called bright pixels garbage and dark pixels drains, then fed them to a Kalman tracker seeded from Gemini's single box.
**Fix.** Replaced by a real segmentation model and tracker (YOLOE + BoT-SORT; see Part 3).

### 4. Hard-coded inputs to the scores

**Symptom.** Water depth was always 28 cm when a drain issue existed (10 cm otherwise); scores were derived from severity guesses.
**Fix.** Depth is no longer reported, because it cannot be measured from video. Drainage is scored from Gemini's drain assessment (Pass C), or shown as "Not assessed". Garbage uses detector coverage or Gemini's severity, and `score_sources` says which.

### 5. Alerts were never sent

**Symptom.** Email, Telegram and webhook settings existed, but `app/notify/` was empty.
**Fix.** Wrote `app/notify/alerts.py`. Hazards alert immediately; violations only after officer approval; every attempt is logged in `alert_logs`. If no channel is configured, the UI says so instead of claiming success.

### 6. Real violations never reached officers

**Symptom.** The Priority Queue showed only hard-coded demo incidents. Violations found in uploaded videos were stored but never displayed.
**Fix.** Added a review section that reads pending violations from the database, shows the evidence and has Approve/Reject buttons that require an officer's name.

### 7. Vehicle and plate photos were never saved

**Symptom.** Gemini returned vehicle and plate boxes, but only the person was cropped.
**Fix.** Person, vehicle and plate crops are all saved; plate text is validated against Indian formats.

### 8. Clean videos would have crashed the job

**Symptom.** Found after removing the fake detections: a video with no incidents raised an integrity error.
**Cause.** The annotated-video `Evidence` row used `created_incidents[0].id if created_incidents else None`, but `incident_id` is not nullable. The fake detections had hidden this, because there was always an incident.
**Fix.** The row is only written when an incident exists; the video path is also stored in `result.json`.

---

## Part 2: Environment and tooling

### 9. OpenCV 5 silently disabled violator detection

**Symptom.** Pass B always logged "skipped" and produced no violations.
**Cause.** `pyproject.toml` allowed any OpenCV `>= 4.8`, so a fresh install got 5.0, which removed `cv2.CascadeClassifier` (used for bystander face blurring). The exception was caught, so the whole pass disappeared quietly.
**Fix.** Pinned `opencv-python>=4.8,<5`. Pass B failures are now also shown in the progress log.

### 10. `pip install -e .` failed

**Cause.** setuptools' flat-layout discovery found `app`, `data` and `scripts` as competing top-level packages.
**Fix.** `[tool.setuptools.packages.find] include = ["app*"]`, plus package data for the tracker YAML.

### 11. Evidence videos would not play in browsers

**Symptom.** Blank video player.
**Cause.** OpenCV's H.264 (`avc1`) writer needs the OpenH264 DLL, which is missing on Windows, so it fell back to `mp4v`, which browsers do not play.
**Fix.** After writing, the video is transcoded to H.264 (`libx264`, `yuv420p`, `+faststart`) with the ffmpeg binary bundled in `imageio-ffmpeg`.

### 12. Gemini free-tier quota ran out repeatedly

**Symptom.** `429 RESOURCE_EXHAUSTED` part-way through jobs.
**Cause.** The free tier allows 20 requests per model per day, per project. Each video uses about 5 requests, and the key was apparently shared (quota ran out faster than this work used it).
**Fix.** A longer `FALLBACK_MODELS` chain (3.8, 3.7, 3.6 and 3.5 Flash, 3 Flash preview, Flash latest, 3.5 and 3.1 Flash-Lite). A 429 skips straight to the next model; a 503 is retried with backoff first. Steps that are not essential degrade instead of failing.
**Open.** A paid key, or caching Gemini responses per video, is needed for regular use.

### 13. Ultralytics dependency conflicts and runtime installs

**Symptom.** Ultralytics requires `opencv-python`, which conflicts with `opencv-python-headless` (both provide `cv2`). On first use it also installed `lap` and `clip` by itself at runtime.
**Fix.** Switched the project to `opencv-python<5` and declared `ultralytics`, `lap` and `clip` (from Ultralytics' fork) in `pyproject.toml`, so nothing installs at runtime.

### 14. Slow first load of the detector

**Symptom.** The first load took about 7 minutes and downloaded a 242 MB text encoder (MobileCLIP2-B).
**Fix.** `build_detector_model()` sets the text classes once and saves a "baked" model (`data/models/civiceye-yoloe-26s-seg-<hash>.pt`). Later loads take 0.2 s and need no text encoder. `scripts/prepare_detector.py` does this ahead of a demo. The hash changes when the class list changes, so the model is rebuilt automatically.

### 15. Windows-specific issues

- **Locked DLL.** `pip` could not replace `cv2.pyd` while Streamlit was running. Stop the server before changing OpenCV.
- **Console encoding.** Printing progress messages containing emoji to a `cp1252` console raised `UnicodeEncodeError` (test scripts only; Streamlit was unaffected). Use `PYTHONIOENCODING=utf-8`.
- **Relative paths.** `DATA_DIR=data` in `.env` resolved against the current folder, so starting the app from another directory created a second database. Relative storage paths now resolve against the project root.

### 16. Streamlit did not reload edited modules

**Symptom.** A layout fix appeared not to work in the browser.
**Cause.** On this setup Streamlit does not hot-reload imported modules under `app/ui/views`; the running server kept the old code.
**Fix.** Restart the server after code changes. (Diagnosed by measuring the rendered DOM: the video was not inside the new column at all.)

### 17. TomTom traffic requests fail with an SSL error (**Open**)

**Symptom.** Every TomTom call fails with `CERTIFICATE_VERIFY_FAILED: self-signed certificate in certificate chain`.
**Cause.** Something on the network or machine (typically antivirus web scanning or a proxy) intercepts HTTPS. Python's `urllib` rejects the substituted certificate. Gemini calls work because they go through a different HTTP stack, and WeatherAPI works only because it is called over plain `http://`.
**Planned fix.** Use the OS certificate store (`truststore`) so verification stays on, and move WeatherAPI to `https://` (its API key currently travels in plain text).

---

## Part 3: Making detection real

### 18. Text prompts cannot see real garbage

**Symptom.** On the drain clip, which is mostly garbage, the detector outlined people and water but no garbage at all.
**Investigation.** With 20 garbage prompts ("garbage", "trash", "litter", "plastic waste", "pile of trash" and others) and the confidence threshold dropped to 3%, the best garbage score was 0.07. The large model (YOLOE-26l) did no better. Without garbage in view, the "construction rubble" prompt fired on a brick wall and reported 99% construction debris.
**Fix.** Visual prompting. Gemini, which recognised the scene correctly, boxes garbage on 4 keyframes. Those boxes become YOLOE visual prompts, so the detector looks for things that *look like this video's garbage*. Text garbage classes were removed entirely; without examples, garbage is reported as not measured.
**Result.** Garbage was found in 46% of analysed frames instead of none.

### 19. The large model was slower and worse

YOLOE-26l took 97 s against 40 s for 26s on the same clip, and painted water as garbage. The small model is the default.

### 20. Garbage heaps cannot be tracked as objects

**Symptom.** Garbage masks covered up to 64% of the frame, yet almost no garbage survived as a tracked object; track IDs passed 200 in 11 seconds.
**Cause.** A heap has no stable boundary. The detector splits and merges it differently every frame, so IoU-based tracking starts a new track almost every time.
**Fix.** Garbage is measured as area: the union of masks per frame (on a 160-px raster so overlaps are not double-counted), a 90th-percentile coverage that one bad frame cannot drive, the share of frames with garbage, and area share per waste stream. Tracking is kept for countable objects.

### 21. One person, many track IDs

**Symptom.** 12 to 15 "people" reported. The clip actually shows two workers, one bystander and 2-3 distant people during the opening pan.
**Cause.** Handheld camera, fast pans and workers bending over and overlapping.
**Fixes tried.**
- BoT-SORT with sparse optical-flow camera-motion compensation, a 40-frame buffer and 10 analysed fps. This helped somewhat.
- Dropping tracks shorter than 0.5 s, which removed flicker.
- Re-identification (`with_reid`) using the detector's own features. This had no effect, because those features are only produced inside Ultralytics' own tracking loop, not on plain `predict()` calls. Turned off.
**Fix shipped.** Report `peak_in_frame` (the most people visible at once, 5 here), and caption the track table to say one person can have several IDs.
**Open.** A dedicated ReID model would reduce ID switches.

### 22. Long straight lines across garbage outlines

**Symptom.** Garbage outlines had straight strokes slicing across the frame.
**Cause.** Ultralytics' `Masks.xy` merges all pieces of one mask into a single polygon by joining them with connecting segments.
**Fix.** `mask_contours()` finds contours on each mask bitmap, keeps every piece separate, scales them to the original frame and drops pieces under 30 px.

### 23. Gemini's garbage boxes are coarse (**Open**)

Boxes sometimes include the workers standing in the garbage, and every region on the test clip was labelled "mixed". Mixed is accurate for unsorted heaps, but it means the waste-stream breakdown has not yet been shown to separate streams on real footage.

### 24. Water masks spill over garbage (**Open**)

In some frames the "stagnant water" mask covers floating garbage, and that garbage goes uncounted. Both coverage numbers are underestimates in those frames.

---

## Part 4: Front end

### 25. Interface looked generated

**Symptom.** Emojis in every heading, "Real-Time AI" and similar hype copy, fake REC/FPS overlays, a fake search bar, bell and avatar, and a deploy message claiming "Alerted via SMS & Radio" when nothing was sent.
**Fix.** Redesigned: a light theme with design tokens, one accent colour, Space Grotesk / Inter / JetBrains Mono, SVG line icons, a fixed top bar with a pop-up command-palette menu, plain wording, and honest placeholders ("No stream connected").

### 26. Portrait videos were too tall to view

**Symptom.** The 478x850 clip was stretched to the full content width, about 2,000 px tall, so it could only be seen by scrolling.
**Fix.** The video sits in a centre column sized from its aspect ratio, capped at 70% of the viewport height. Measured at 315x561 px in a 1920x950 window.

---

## Part 5: Process

### 27. Opening the pull request

The GitHub CLI is not installed on the development machine, and the in-app browser was not signed in to GitHub, so the PR from `utkarsh` to `main` has to be opened by hand. The description is in `PR_DESCRIPTION.md` next to the repository folder.

### 28. Not yet verified

- Live email, Telegram and webhook delivery: no channel credentials were configured. Channel failures are covered by tests with mocks.
- The officer approve/reject flow after the redesign: it was clicked through before the redesign, but no violation was pending afterwards.
- Accuracy on a labelled set of videos: only one real clip has been analysed so far.
