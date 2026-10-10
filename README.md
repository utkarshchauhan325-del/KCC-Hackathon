# FloodGuard – Priority Queue Redesign Spec

Target file: `app/ui/views/priority_queue.py` (styles in `app/ui/components/styles.py`)
Reference design: the "Priority Queue – Desktop" artboard (open the design link, export PNG, and keep it as `docs/queue_design.png`).

## Problems with the current queue
1. Every card repeats the same chrome (severity, source, category, risk, action, evidence), so scanning 6+ incidents is slow.
2. Key frames are small and the bounding box is hard to read; there is no way to see the other frames Gemini captured.
3. A long single column forces endless scrolling; there is no selected state or detail view.
4. "Mark resolved" is the only action. Dispatch is hidden inside a collapsed "Crew for this site" row.
5. Sensor-only incidents show a large empty "No camera frame" box.
6. Filters are limited to one "All sources" dropdown.

## New layout (desktop, master-detail)
1. **Top nav**: unchanged (navy `#0B132B`, active tab underlined in teal).
2. **Header**: eyebrow "OPERATIONS", title, one-line help, buttons `Export log` and `Upload video`.
3. **KPI strip**: 4 compact cards with a coloured left border (red open, teal key frames, amber violations, green crews).
4. **Toolbar**: tab chips (Open / Violations / Crews), then filter chips (Severity, Source, Zone, Sort by risk) and a search box.
5. **Left column: incident list.** Each card = key frame thumbnail (208x132, red bounding box + label, video timestamp badge) + severity badge, source badge, mono ID and age, location and incident type, one-line summary, circular risk-score ring, category, confidence, buttons `Resolve` (ghost) and `Dispatch crew` (primary teal).
6. **Right column: sticky detail panel for the selected card.** Large key frame with boxes, a 4-frame filmstrip (frames Gemini captured, with timestamps), AI observation, risk score, garbage area %, suggested action, crew picker, `Dispatch crew` and `Mark resolved`.
7. **Sensor-only cards**: hatched placeholder, grey "Sensor" badge, no frame in the detail panel.
8. **Violations to review tab**: same card, but the actions become `Approve and send to PMC` and `Reject`, plus the evidence triplet (scene, suspect crop with blurred bystanders, vehicle and plate crop) and a required "Reviewing officer" field. Never auto-approve.

## Design tokens
| Token | Value |
|---|---|
| Nav / ink | `#0B132B` / `#0F1B2D` |
| Page bg / card | `#F3F5F9` / `#FFFFFF`, border `#E1E6EE`, radius 12px |
| Primary (teal) | `#0E7C86` |
| Severity 5 | text `#B71C1C` on `#FDECEC` |
| Severity 4 | text `#9A4A00` on `#FFF1DC` |
| Muted text | `#5B6B80` |
| Fonts | Space Grotesk (UI), JetBrains Mono (IDs, timestamps) |
| Bounding box | 2px `#FF3B30`, mono 10px label |

## Behaviour
- Default sort: risk score descending, then severity. First card selected on load.
- Clicking a card (or its frame) selects it and fills the detail panel (`st.session_state["queue_selected"]`).
- Clicking a filmstrip thumbnail swaps the large frame.
- Dispatch moves the incident to "Crews in the field" and updates the KPI counters and nav label `Queue (n)`.
- Resolved incidents leave the list with a short success toast.
- Empty state: "All clear. No open incidents." with an icon.
- Mobile (<900px): the detail panel becomes an expander under the selected card.

## Accessibility
Real buttons only, 44px targets on touch, text contrast 4.5:1, severity never conveyed by colour alone (badge text "Severity 5/5").
