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
