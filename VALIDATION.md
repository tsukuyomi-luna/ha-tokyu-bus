# Prototype validation — 2026-09-29

- 8 offline normalization/time tests passed; compileall passed.
- HA Core 2026.9.3 actual config flow created an entry, state loaded.
- Four entities populated from live upstream data; tracking NEXT parsed, unknown congestion retained.
- Entry reload succeeded with same entity IDs and updated estimate.
- A new standalone stock-entities dashboard was saved and read back through HA WebSocket API. Browser/iPhone rendering not yet verified.
- Initial form used vol.Match, which the installed HA form serializer rejected. Changed UI types to str and validated codes in the submit handler; actual config-flow retry passed.
- No Live Activity push has been sent; example only.
- HA startup and setup/unload exercised on real HA. Failure injection and automated full HA framework tests remain outstanding.
- Not validated: special-day schedules, automatic boarding detection, all routes, display-route aggregation, automatic route selection, phone delivery, long-duration operation.

- HACS custom repository registration and main-branch download succeeded on the same HA; installed=true. Installed Python file SHA256 values match the published source.
- GitHub CI passed. This is not a HACS default-store listing or approval.

## 0.2.0

- Ruff format/lint, oxfmt, ESLint, 22 Python tests and Chromium card checks passed.
- Card checks cover 320/390/800px, populated/empty/stale states, script buttons, HTML injection safety and timer cleanup. Native HA/mobile rendering remains a separate check.
- HA options flow saved poll_seconds=30. Two successive successful retrieval timestamps were 30.007 seconds apart.
- Dedicated dashboard resource and card config saved/read back. Start/stop/test scripts registered through HA's config API.
- Bounded 2-minute phone test started. API acceptance is not proof of iPhone display; owner confirmation is pending.
- Normal Live Activity updates are separate from API polling, at most every 2 minutes on changes, with a 30-minute session limit.
