# Contributing

## Maintainer workflow

Keep implementation and docs changes on focused branches targeting `dev`.
This does not authorize a push, merge, tag change or publication; obtain the
owner's authorization for those actions. Documentation-only work needs link
and source-claim checks, not a device reinstall or fresh runtime build.

Validate locally **before pushing**: run `bash tests/check.sh`, commit locally,
then run `bash build-rootfs.sh` from that clean commit and verify the manifest/component checksums
and assembled `build-info`. Test affected installation, desktop and uninstall behavior on
the RP6 with that local bundle when changing those paths. Preserve user data
unless the owner explicitly authorizes disposable test data. Record what was actually tested and any remaining gaps.

Keep iterative edits, commits and builds local. Before publishing a candidate,
validate runtime changes in its local bundle end to end on the RP6: install, launch from Tools,
display/touch/controller/keyboard behavior, return to EmulationStation, and
uninstall/reinstall as appropriate.
Only push the validated candidate to `dev` when ready for the final GitHub build
and download-path test. Batch changes rather than pushing every small fix.
The manually dispatched GitHub bundle workflow is the publication step,
not a substitute for local testing. Afterwards, verify the raw GitHub installer and rolling bundle URLs end
to end. Never use remote builds as the normal edit/test loop.

Keep temporary diagnostics out of the product tree. Attach exact revision/bundle
evidence to the review or release
and preserve required third-party attribution. Published
versioned tags/assets must stay immutable; the rolling dev policy is below.

## Branches and pull requests

The following is the default workflow for external contributions:

Create your branch from an up-to-date `dev` and open the pull request against `dev`.
Use descriptive branch names such as `fix/keyboard-toggle`. Do not push directly
to `dev` for routine changes.

Keep each commit **under 300 added lines** (`git show --numstat`). Split large
changes into cohesive, reviewable steps, not arbitrary fragments. Keep PRs focused;
aim for under 300 additions per PR too. Explain unavoidable generated-file or
large-test exceptions in the PR. Never commit built runtimes or release binaries.

Commit messages must use this form:

```text
type: short description
```

Common types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `style`.
Use the imperative mood and keep the first line under 72 characters, for example
`fix: restore the frontend after desktop logout`. Explain the reason in the body
when it is not obvious. Do not rewrite another contributor's branch without consent.

Include in each PR:

- What changed and why; link an issue if relevant.
- Commands/tests run and their actual results; identify checks not performed.
- Device model, ROCKNIX build, graphics mode and rollback steps for device changes.
- Screenshots or physical-device confirmation for visible/input behavior changes.

Wait for review and passing checks. Do not merge your own PR automatically. Prefer
squash merging small PRs; ensure the final title follows the commit-message format.

## Safety and code style

Use Bash strict mode, quote expansions, fail closed on unsupported devices, and
keep device-specific checks explicit. Never assume ROCKNIX has apt or a writable
root image. Keep persistent changes under `/storage`; preserve user homes and
require explicit confirmation before replacing Desktop data.

Preserve EmulationStation boot and return behavior. Test normal logout, failed
startup, controls, touch and session cleanup when changing lifecycle code.
Do not claim hardware acceleration solely from a capability flag.

Run `bash tests/check.sh` before submitting. Use ShellCheck when available.
Run upstream suites only for sufficiently relevant changes or when explicitly
required; they are not a default build gate. Record executed and skipped
checks honestly, including cached results and their original revision. Keep
the existing artifact and source checks and test affected RP6 behavior;
source fixtures alone do not establish hardware success.
Keep secrets, private device addresses and local logs out of
commits. Retain required third-party copyright/license notices. Do not add a new
device to the support table without testing on that physical hardware.

## Releases

`dev` is the default development branch; target contribution PRs at `dev`.
Manually run **Development bundle** on `dev` after local and relevant
hardware validation. Eligible non-RP6 devices receive an automatic, default-No
warning and use the narrow [SM8550 profile](docs/devices.md).
This applies to development and versioned releases; `--yes` cannot bypass the
device warning. Do not claim support from profile eligibility or
synthetic tests. Pushes run checks but do not publish a bundle.

Dev publication is **latest-only**: the `development`
pre-release retains the current bundle, its checksum and `latest.json`; release
notes identify source commit, build time and all commits ahead of the latest
stable GitHub release. The comparison is regenerated on every development
publication, so no previous-development baseline needs tracking. Dev assets may be replaced or
removed on the next successful publication. Record installed provenance from
`build-info` / `rocknix-version`; use a versioned release when a fixed public
snapshot is needed. Update the pointer only after the bundle/checksum upload
succeeds. Devices do not update automatically.

Distinct commit-and-run-qualified filenames let the new bundle/checksum upload
finish before `latest.json` changes. The publisher then validates the complete
current asset set and removes superseded dev assets. The pointer includes
`built_at`; release notes show the source commit and build time. Publication
fixture tests cover pointer-failure retention and deletion order. The rolling
`development` tag is mutable; versioned tags are not.

Manually run **Versioned release** on the tested `dev` commit with the chosen
version. The publisher requires the exact current remote `dev` commit.
`vX.Y.Z` publishes a normal release; alpha,
beta and RC tags publish pre-releases. The workflow makes the release public
only after all installer assets are uploaded. Never move a versioned tag or replace its
assets. Installation defaults to the latest published stable version;
`--dev` selects development and `--release TAG` pins a version. Publication
does not automatically update users' devices.

See [build requirements and cache behavior](docs/build.md).

Build from a clean, tested commit. Validate fresh-device installation, update,
uninstall and lifecycle before a normal release. Keep the README installation
commands synchronized with published versions. Review dependency
license/source-distribution obligations before distributing runtime binaries.
