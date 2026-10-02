# GitHub component benchmark — 2026-10-02

The Apps/Settings tap-to-close fix was reverted on the isolated
`codex/component-builds-github-test` branch, built with the component workflow,
and then replayed exactly. All three runs succeeded on fresh
`ubuntu-24.04-arm` GitHub-hosted runners. No compression settings were changed.

| Run | Source | Job execution | Queue | Components built / reused |
| --- | --- | ---: | ---: | --- |
| [First build without toggle fix](https://github.com/kapdon/rocknix-desktop/actions/runs/37050212287) | `6cf85d6` | 44m29s | 8s | 10 / 0 |
| [Warm baseline without toggle fix](https://github.com/kapdon/rocknix-desktop/actions/runs/37055238310) | `6cf85d6` | 44s | 10s | 0 / 10 |
| [Exact toggle fix replayed](https://github.com/kapdon/rocknix-desktop/actions/runs/37055517092) | `7051355` | 47s | 6s | 1 / 9 |

Job execution runs from the job's `startedAt` through `completedAt`, including
runner setup, checkout, artifact resolution, dependency setup, source tests,
component build, component publication, timing upload and cleanup. Queue time
is separate. Including the queue, the warm and replay runs took 54s and 53s.

The first run populated an empty native artifact store. It spent 42m26s in the
build step and 63s publishing components; that cold initialization cost is not
a warm-build speed claim. The largest component costs were Trash (670.564s),
guest base (855.306s), host runtime (419.045s) and MPV media (372.169s).

## Actual change and reuse

The replay changed only `rootfs-overlay/usr/local/bin/rocknix-launcher`, restoring
the 12 inserted and two removed lines from merge `dca1b28` (first parent).
The restored tree exactly matched implementation revision `361cd62`.

The warm baseline reused all ten exact component descriptors from the seed run.
The replay reused nine descriptors byte-for-byte and changed only
`guest-integration`. Both runs skipped builder setup and cache-service setup.
The initial resolver recognized this before any Docker setup.

| Measured stage | Warm baseline | Toggle fix replay |
| --- | ---: | ---: |
| Resolve component references | 7s | 5s |
| Install fakeroot support | 10s | 9s |
| Source checks | 16s | 16s |
| Component build function | 3.054s | 4.863s |
| Guest integration packing/compression | skipped | 0.040s |
| Verify/publish component assets | 3s | 6s |

The changed compressed archive was **17,412 bytes** (baseline 17,292 bytes).
The Debian base, Trash transaction, trusted host runtime, private media,
Fuzzel, keyboard, host integration and host theme were reused. No large image
export or compression ran for the menu change. The remaining time was dominated
by test/setup and GitHub metadata requests.

Both published integration archives were downloaded with digest and size
verification. Their actual `rocknix-launcher` contents matched their source
commits exactly: the baseline omitted tap-to-close and the replay contained it.
This checks the published payload as well as the resolver plan.

## Comparison and limits

The [previous monolithic run](https://github.com/kapdon/rocknix-desktop/actions/runs/37010279368)
at `dca1b28` took 16m34s of job execution, including 13m42s in its main build step
and 73s publishing the bundle. The 47-second component benchmark used roughly
**95.3% less job execution time**, about **21.1 times faster** in this comparison.
One warm baseline and one real-change run demonstrate reuse; these are not a
statistical distribution or a guarantee for arbitrary changes.

These runs used `benchmark=true`: reusable component artifacts were genuinely
published, but the development channel manifest, `latest.json`, release notes
and tag were not advanced. Normal channel promotion is an additional small
publication path whose time was not measured here. The before/after release
metadata, asset identities, sizes and digests were verified unchanged; remote
`dev` remained `c1a1aec8e89b6ddeef3c9b78e58b132be5805599`.

The toggle fix is restored on the test branch. Nothing was merged into `dev`.
RP6 installation, retained-update and interruption acceptance remain separate
from this build-performance test.

Evidence is available in each run's `component-build-timings` artifact and in
local `dist/github-benchmark/` (run metadata, plans, timing JSON, manifests,
verification results and the two small published integration archives).
Full baseline commit: `6cf85d6e19c9e0a696a9eb5934dc918c523c5c8a`.
Full replay commit: `70513557bd886d70bd57f83713fb626319683d05`.
