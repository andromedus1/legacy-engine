---
source_handle: data-autonomy-launchd-plist-man
fetched: 2026-07-31
source_path: .research/reference/data-autonomy-upstream/launchd-plist-man.txt
provenance: source-direct
source_class: man-page
version: Darwin 25.3.0 (macOS)
---

# launchd.plist(5) man page — scheduling keys (captured from Darwin 25.3.0)

## Summary

The authoritative reference for LaunchAgent job definitions, captured verbatim from
`man launchd.plist` on the target machine (the maintainer's Mac, Darwin 25.3.0) into the
reference corpus. Load-bearing keys for the scheduled-refresh design:
`StartCalendarInterval` (crontab-like calendar firing; and unlike cron, jobs missed
while the Mac sleeps run once on wake, coalesced), `StartInterval` (every-N-seconds,
but intervals that fire during sleep are *missed*, not coalesced — wrong tool for a
laptop/desktop), `ThrottleInterval` (default: jobs won't respawn more than once per 10
seconds), `RunAtLoad` (launch once at load; discouraged), `StandardOutPath` /
`StandardErrorPath` (map stdout/stderr to files, auto-created), `WorkingDirectory`
(chdir before exec), and `EnvironmentVariables`. The sleep/wake asymmetry between
StartCalendarInterval and StartInterval is the decisive fact: calendar-based scheduling
is the only variant that self-heals across sleep on a personal machine.

## Key passages

> Unlike cron which skips job invocations when the computer is asleep, launchd will start the job the next time the computer wakes up. If multiple intervals transpire before the computer is woken, those events will be coalesced into one event upon wake from sleep. — StartCalendarInterval

> StartInterval <integer> This optional key causes the job to be started every N seconds. If the system is asleep during the time of the next scheduled interval firing, that interval will be missed due to shortcomings in kqueue(3). — StartInterval

> The value is in seconds, and by default, jobs will not be spawned more than once every 10 seconds. — ThrottleInterval

> RunAtLoad <boolean> This optional key is used to control whether your job is launched once at the time the job is loaded. The default is false. This key should be avoided, as speculative job launches have an adverse effect on system-boot and user-login scenarios. — RunAtLoad

> StandardOutPath <string> This optional key specifies that the given path should be mapped to the job's stdout(4) … If the file does not exist, it will be created with writable permissions and ownership reflecting the user and/or group — StandardOutPath

> WorkingDirectory <string> This optional key is used to specify a directory to chdir(2) to before running the job. — WorkingDirectory

> StartCalendarInterval <dictionary of integers or array of dictionaries of integers> This optional key causes the job to be started every calendar interval as specified. Missing arguments are considered to be wildcard. The semantics are similar to crontab(5) — StartCalendarInterval

## Structural metadata

Full man page saved to the source_path above (`man launchd.plist | col -b`, 738 lines,
Darwin 25.3.0). Passages quoted with their key names as anchors.
