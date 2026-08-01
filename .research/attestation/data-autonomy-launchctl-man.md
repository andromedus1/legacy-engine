---
source_handle: data-autonomy-launchctl-man
fetched: 2026-07-31
source_path: .research/reference/data-autonomy-upstream/launchctl-man.txt
provenance: source-direct
source_class: man-page
version: Darwin 25.3.0 (macOS)
---

# launchctl(1) man page — domain targets and operational subcommands

## Summary

Captured verbatim from `man launchctl` on the target machine. Load-bearing facts for
operating LaunchAgents: per-user GUI jobs live in the `gui/<uid>` domain (the
convenient form of the login domain — the right target for a job that should run while
the maintainer is logged in); `kickstart` runs a loaded service immediately regardless of its
schedule (the manual "run it now" and post-outage catch-up verb, with `-k` to restart a
running instance); `print` inspects a domain or service's state including last exit
status (the debugging verb). Modern bootstrap/bootout subcommands take these
domain-target specifiers.

## Key passages

> gui/<uid>/[service-name] Another form of the login specifier. Rather than specifying a user-login domain by its ASID, this specifier targets the domain based on which user it is associated with and is generally more convenient. — domain specifiers

> kickstart [-kp] service-target Instructs launchd to run the specified service immediately, regardless of its configured launch conditions. -k If the service is already running, kill the running instance before restarting the service. — subcommands

> print domain-target | service-target Prints information about the specified service or domain. … Service output includes various properties of the service, including information about its origin on-disk, its current state, execution context, and last exit status. — subcommands

## Structural metadata

Full man page saved to the source_path above (`man launchctl | col -b`, Darwin 25.3.0).
