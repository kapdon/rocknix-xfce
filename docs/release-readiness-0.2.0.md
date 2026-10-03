# 0.2.0 readiness audit — 2026-10-03

Status: target version proposed, not release-approved. Latest published stable is
`v0.1.0` (`8188d4`). No open GitHub issues or PRs were returned during this audit;
that does not mean the recorded local findings are resolved. This is a worktree,
evidence and release-path audit, not a new comprehensive code or hardware review.

## Integrated candidate

Local `dev` fast-forwarded from current `origin/dev` (`e7f4870`) to `3dd0816`,
including all 36 host-provider, component replacement, Xwayland, controller,
work-area and Gamescope commits. Old local `dev` had unrelated pre-LXC history;
with owner approval it was realigned, preserving `39fa395` under
`codex/legacy-chroot`. No remote branch, release, tag or workflow was changed.

The built manifest identifies `3dd0816`. Full RP6 installation was previously
`fd0c7c2`; the five menu/picker files from `3dd0816` were applied as a live preview.
Do not describe that preview as a full candidate installation. The local bundle
has `local_override: true` and cannot be published by the release tools.

## Open findings and release checks

| Finding | Evidence and next action |
| --- | --- |
| Gamescope teardown abort | Debian guest Gamescope aborted after a clean probe exit. The guest teardown preview now contains launches in per-app services, with real PD2 exit and abrupt compositor-loss cleanup verified. The upstream abort itself is not repaired; final bundle validation remains. See [teardown evidence](gamescope-teardown.md). |
| Publishable candidate missing | Build without the local Trash override; verify all component hashes, metadata and source/license payloads. Install the complete candidate on RP6. Previous locally audited inputs do not qualify the normal release build. |
| Delivery and replacement | Earlier RP6 legacy-to-component, component replacement and process-kill recovery passed. Repeat the final candidate's fresh install, upgrade, retained-home checks, uninstall/reinstall and Gaming return as appropriate. Downloaded release/bootstrap verification must follow authorized publication. Physical power-loss recovery is not established. |
| Input and lifecycle acceptance | Controller enumeration and injected checks passed. Recheck physical buttons/axes, held-button mode transitions, touch alignment, audible output and Steam overlay in both launch modes on the final candidate. Gamepad ACL normal-exit restoration passed; crash cleanup remains fixture evidence. |
| Steam restart and recovery | Exit-code-42 restart and maintenance exclusion were corrected in `c128035`, now included. Their regression evidence is local fixtures, not a live Steam updater/recovery test. |
| Release notes | The versioned component publisher currently emits commit/build metadata and a generic installation sentence. Prepare user-facing 0.2.0 highlights and explain system replacement, preserved home data and system-package/password reset before publication. |

Historical checks and exact evidence are in the
[component replacement ledger](component-replacement-validation.md),
[native launch record](../experiments/steam-lxc/NATIVE-FPS.md), and
[upgrade policy](upgrades.md). Older acceptance entries remain revision-specific.
Main-menu launch checks are not gameplay FPS or long-duration stability tests.

## Known boundaries, not forgotten merges

- Native host Steam runs in ROCKNIX's root scope by the owner's accepted
  compatibility decision. Shared writable executable content does not provide
  strong guest-to-host isolation. The [trust tradeoff](native-steam.md#accepted-trust-tradeoff)
  remains deliberate; this audit does not reopen a privileged-helper redesign.
- Host graphics reuse remains protected opt-in. Native codecs failed required
  playback lifecycle checks and stay diagnostic-only; packaged corrected codecs
  remain the default. See [native providers](native-providers.md).
- The user confirmed PD2 fullscreen through the virtual-display wrapper works.
  Ordinary D2GL windowed rendering still fails to follow accepted client resizes;
  its renderer handoff remains separate. Virtual display dimensions are sampled
  at launch and scaled during later outer-window changes, not dynamically reset.
- Generic Gamescope launching targets X11/Wine. Existing single-instance apps
  can receive launches outside the wrapper; close them first. Native Steam's
  separate non-Steam Browse-dialog limitation remains documented.
- RP6 is the only hardware-tested device. Suspend/resume, future firmware
  compatibility and offline full-data restore remain unqualified. Firefox PiP
  matching is English-title dependent. These were already documented limits.

## Local repository cleanup

Twenty redundant branch names were removed only after verifying each tip was
reachable from a retained branch. The clean `codex/steam-lifecycle-p2` worktree
was removed; its changes are in `dev`. No stash or dirty source was discarded.
Legacy XFCE/Sway tarballs and their checksum files were removed from the main
checkout's `dist/` directory (593,231,004 logical bytes). Current component
artifacts, older diagnostic/recovery inputs and credentials were preserved.
`.env.local` is now ignored. Exact pre-cleanup refs and artifact hashes are
recorded in the local audit evidence outside the source repository.

Remaining worktrees:

| Checkout | Reason retained |
| --- | --- |
| Main `dev` | Integrated development checkout |
| `codex/host-library-reuse` | Exact tested feature revision and current component build/cache |
| `codex/steam-lxc-reuse` | Current chat checkout; all commits are already in `dev` |

Remaining archival refs are `codex/legacy-chroot`, `codex/legacy-bubblewrap`, and
`codex/beta-release-validation`. The last preserves the old LXC acceptance and
research ledger from before history reconstruction; it is not a feature to merge
wholesale. The retained `codex/component-builds-github-test` matches its remote:
its two extra commits are a revert/reapply pair with no net tree change from
their common base. There is no additional identified feature waiting to merge.
No remote branch or historical tag was deleted.

Post-merge `bash tests/check.sh` and `git diff --check` passed. All eleven
retained `3dd0816` component sizes and SHA-256 hashes were verified again.
These are local checks; no new RP6 test or build was run during this audit.

Recommendation: finish the candidate checks above, then release `v0.2.0`.
If publishing before those checks are complete is deliberately chosen, use an
explicit prerelease and retain the limitations; do not claim stable acceptance.
