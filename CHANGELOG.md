# Changelog

The generated Development section records the latest successful development
build, with all changes since the latest stable release. GitHub Actions updates
that section and the rolling development release together. The curated highlights
also cover committed development work; the dated backfill below distinguishes
changes beyond the recorded build from published artifacts. Release notes use
these highlights and link here for the full history. Earlier build snapshots
remain in this file's Git history. Automated changelog commits are omitted from
the change list.

## Highlights since v0.1.0

- **Guest Gamescope cleanup:** Contain each launch in an unprivileged service,
  clear detached Wine helpers on exit or compositor loss, and keep the shared
  FEX server outside individual game lifetimes. RP6 preview checks passed;
  the upstream compositor abort and final bundle acceptance remain separate.

- **Gamescope app picker:** Keep “Launch with Gamescope” first in the initial
  Apps list, reuse installed app entries and display settings, and show a gamepad
  icon for both it and Steam games.
- **Gamescope display fitting:** Default nested games to the current Sway
  content area, with an option to use the full monitor resolution and a shared launcher for
  LXC X11/Wine games. Keep the game resolution stable while Gamescope scales
  window changes. Native DRM launching remains unchanged. RP6 probes and the
  user's PD2 Gamescope launch passed; broader input/gameplay acceptance remains.
- **Component replacement:** Replace the system container on update while preserving
  home data and metadata; installed system packages and password changes reset.
  Legacy-export migration and interrupted replacement were tested on RP6.
- **Guest X11 and controllers:** Supply patched Xwayland, publish Sway work areas,
  expose the native virtual gamepad, and provide an always-available one-tap
  Desktop/Game override with secondary Gamescope detection.
- **Scoped host providers:** Add opt-in native graphics reuse with narrow read-only
  mounts. Packaged providers remain the default; native codecs remain diagnostic.
- **Faster development builds:** Reuse unchanged components and rebuild only the
  affected parts, avoiding repeated export and compression of the Debian runtime.
- **Apps and Settings toggles:** Tap either button again to close its open menu.
- **Better cache reuse:** Preserve Trash packages and remote Docker layers, and
  include the keyboard layout in its compiler inputs.
- **Recorded release history:** Successful development builds automatically
  record all changes since the latest stable release in this changelog; release
  pages show curated highlights and link to the full history.
- **Native Steam games:** Launch installed ROCKNIX Steam shortcuts with a choice
  to close Desktop or keep it running, reusing the native Steam scope and shared
  library. Keep mode adds controller focus switching and a touch override.
- **Steam session recovery:** Handle Steam's update/restart request in Keep mode
  and block installation or maintenance until session recovery finishes.
- **Desktop file chooser:** Include the GTK portal backend and preserve its
  configuration through managed component updates. This does not fix native
  Steam's separate Browse dialog.

Current release gaps and evidence boundaries: [0.2.0 readiness](docs/release-readiness-0.2.0.md).

## Committed development changes through `c128035` — 2026-10-03

Backfill audited against `origin/dev` at
`c128035dc786f2dbec8b4c6a7131f1025017936e`. These changes are committed but are
not included in the recorded development build `3a32508` below. The rolling
release still identified that build when checked on 2026-10-03; this backfill
does not record a new build or publication. Coverage is the Git ancestry range
`3a32508..c128035`, including work merged from the Steam branch and `[skip ci]`
commits. Dates below are the commits' author dates. The automated changelog
record and merge-only bookkeeping are omitted.

### 2026-10-03

- Reuse ROCKNIX's native `steam-bigpicture.scope` for Steam sessions, supervise
  Desktop transitions separately, and retain recovery state when cleanup fails.
  Document the compatibility choice to run native Steam as host root, the trust
  implications of shared writable game files, and remaining external-launch race
  limits. ([9c9ea88](https://github.com/kapdon/rocknix-desktop/commit/9c9ea88ac0d33f78b9e8fd8ca24886e3f84a34f6))
- Restart Keep mode on Steam's update/restart exit code 42 while allowing normal
  exits, compositor failures and stop signals to end the session. Guard standalone
  installation before downloads and across lock acquisition; resolve maintenance
  guards from the copied updater's trusted helper directory. Regression evidence
  for these changes is local fixtures, not new device qualification. ([c128035](https://github.com/kapdon/rocknix-desktop/commit/c128035dc786f2dbec8b4c6a7131f1025017936e))

### 2026-10-02

- Add native Steam game launching with persistent Close Desktop / Keep Desktop
  settings, stop/recovery handling and an available-memory guard. Close mode uses
  ROCKNIX's installed `runemu.sh` and DRM launcher; Keep mode uses nested Wayland
  Gamescope. Read installed game entries from ROCKNIX's `.desktop` shortcuts.
  ([728ed03](https://github.com/kapdon/rocknix-desktop/commit/728ed0311b6a62241bf547db583c8403da72b2c2), [b74f905](https://github.com/kapdon/rocknix-desktop/commit/b74f9055aad1f6a4bccc406547484eb3958de5ae), [916a9c5](https://github.com/kapdon/rocknix-desktop/commit/916a9c55ffb8e9981d11f065b15d7077e4394e39))
- Switch Keep-mode InputPlumber profiles with Steam window focus, expose a touch
  override for Desktop or game controls, and restore Desktop controls on recovery.
  ([3344a25](https://github.com/kapdon/rocknix-desktop/commit/3344a25d6766aa028107ce83f70aebec80c54fcb))
- Apply a common SDR presentation baseline with the optional Gamescope WSI bypass
  disabled in both Steam launch modes; document HDR/timing exclusions and possible
  performance differences. ([c42f9c9](https://github.com/kapdon/rocknix-desktop/commit/c42f9c9bd161707b30e0d63f0c35188d64e472a6))
- Add `xdg-desktop-portal` and its GTK backend for LXC Desktop file choosers, and
  include the portal configuration in managed component updates. Native Steam's
  separate Browse-dialog limitation remains. ([5a1f6ab](https://github.com/kapdon/rocknix-desktop/commit/5a1f6abeba7c735495ea8df73438998e5700598b), [7092c27](https://github.com/kapdon/rocknix-desktop/commit/7092c27cf6da55bce113e898ec4c86983b0883a3))
- Generate concise development-release highlights from this file and link the
  release page to the complete changelog. ([b23ee56](https://github.com/kapdon/rocknix-desktop/commit/b23ee5670273b589b157867f2d527f0962dc6032))
- Record Steam reuse research, offline path discovery, shared-path and launch
  exclusion experiments, descendant-cgroup checks, lease/crash recovery fixtures,
  containment review and ELF dependency parsing. These are research and validation
  artifacts, not a shipped in-LXC Steam runtime. ([7057431](https://github.com/kapdon/rocknix-desktop/commit/70574317b73b49e63c1e131c404c29b1b6e13beb), [3bd0994](https://github.com/kapdon/rocknix-desktop/commit/3bd0994f20131100b81683bcee4de2fb210e6828), [5d0a0d0](https://github.com/kapdon/rocknix-desktop/commit/5d0a0d0e66f01cfb3d2bd2183a8e140a4129f9bc), [9ff5c30](https://github.com/kapdon/rocknix-desktop/commit/9ff5c305e34d016c4a9254923d205588639c0d32), [3c16eb3](https://github.com/kapdon/rocknix-desktop/commit/3c16eb39f0e3239bc30468837d0c9215cc0778e4), [e182657](https://github.com/kapdon/rocknix-desktop/commit/e182657a4c8f9ce9fa6898cee67acfca6f200fbf), [32ff7eb](https://github.com/kapdon/rocknix-desktop/commit/32ff7eb79840a7ed555ff8243419f565904ac56c), [acd470d](https://github.com/kapdon/rocknix-desktop/commit/acd470d82fa3d60754c7bec153f2556063554ee3))
- Record installed-RP6 inventory, idmap/nested-runtime experiments, partial
  Satisfactory startup and recovery results, and the native Gamescope investigation.
  Preserve their documented limitations; the LXC game experiment is not a gameplay
  pass. See the [Steam evidence index](experiments/steam-lxc/README.md) and
  [native integration validation boundaries](docs/native-steam.md#validation-boundaries).
  ([857cd47](https://github.com/kapdon/rocknix-desktop/commit/857cd47aeafae029562ddec50838c60d31301a3e), [beaebdc](https://github.com/kapdon/rocknix-desktop/commit/beaebdcdcbbf86e9710f406356f5e8d3ec38dd0e), [711fc0c](https://github.com/kapdon/rocknix-desktop/commit/711fc0c053ed157404ddd93167806c9db694d401), [8fa06a2](https://github.com/kapdon/rocknix-desktop/commit/8fa06a20210c98ad375105280e2763e23104065c))

[Backfill comparison](https://github.com/kapdon/rocknix-desktop/compare/3a32508bd92d184e4d961c83a8469ef510a290f5...c128035dc786f2dbec8b4c6a7131f1025017936e)

<!-- development-changelog:start -->

## Development

Commit: `3a32508bd92d184e4d961c83a8469ef510a290f5`
Built: 2026-10-02T20:17:20Z

Rolling dev pre-release. The installer selects the latest successful build.

## Changes since v0.1.0

Compared with the latest stable release, not the previous development build.

- docs: clarify ROCKNIX project independence ([a70f578](https://github.com/kapdon/rocknix-desktop/commit/a70f578d935f2f073b713b3ab43c5e27b21c838f))
- fix: toggle Apps and Settings menus on repeated taps ([bef1135](https://github.com/kapdon/rocknix-desktop/commit/bef1135540ea28832ac8a3f2a04452b008cec364))
- perf: retain dependency layers across desktop overlay changes ([e146ce1](https://github.com/kapdon/rocknix-desktop/commit/e146ce17f4efdd02abae4f43d75899a765dd86aa))
- perf: compress release bundles with parallel fast xz ([8fb9fe8](https://github.com/kapdon/rocknix-desktop/commit/8fb9fe802f4115c5962d9a58f769897c283af5d8))
- perf: restore original release compression ([ee0c169](https://github.com/kapdon/rocknix-desktop/commit/ee0c1698c932d6844c0d6266198901876dc68de8))
- perf: isolate stable dependencies from mutable build inputs ([2f15fe8](https://github.com/kapdon/rocknix-desktop/commit/2f15fe81f10d6bb19756b790823db652dde288c2))
- fix: include keyboard symbols in compiler inputs ([4034218](https://github.com/kapdon/rocknix-desktop/commit/40342182b75601c88c1469847ac35f39a4702ac4))
- fix: integrate Apps and Settings menu toggles ([dca1b28](https://github.com/kapdon/rocknix-desktop/commit/dca1b28caffd5dc4c52d43d5d66e1445133c8996))
- feat: generate development notes since the latest stable release ([c1a1aec](https://github.com/kapdon/rocknix-desktop/commit/c1a1aec8e89b6ddeef3c9b78e58b132be5805599))
- fix: preserve cache reuse for packages and remote image layers ([7476ca8](https://github.com/kapdon/rocknix-desktop/commit/7476ca8ec156460e638f5ab1d13faa3792c4ab57))
- Build and publish reusable Desktop release components ([c3e9aa1](https://github.com/kapdon/rocknix-desktop/commit/c3e9aa1f2edc0e4edc45cfc05aac99ff982d0064))
- Reuse verified package artifacts for base-only rebuilds ([bcd3999](https://github.com/kapdon/rocknix-desktop/commit/bcd3999504bfb37ec1fb6e17afd7b49e9b82da09))
- Preserve component prefixes in extended tar headers ([aae9465](https://github.com/kapdon/rocknix-desktop/commit/aae9465933a5541ec1ea877d4532dd241c53b238))
- Give integration components exclusive ownership of managed defaults ([15d68ba](https://github.com/kapdon/rocknix-desktop/commit/15d68ba46fe4deb5784427b93dfcba7cabea710c))
- Keep component input keys stable across Python versions ([cb02f8d](https://github.com/kapdon/rocknix-desktop/commit/cb02f8df2edb0653a93acdcfaca65cdccf0e47be))
- Add repeatable local component build benchmarks ([07467c1](https://github.com/kapdon/rocknix-desktop/commit/07467c1eeb15ac582ad84e0acf4fca9fe9af8ed4))
- Record local component architecture validation and timings ([3ea8522](https://github.com/kapdon/rocknix-desktop/commit/3ea8522b2d7c0cd9d70c1f1819aa1a14d90a4c40))
- Allow component benchmarks on development branches ([361cd62](https://github.com/kapdon/rocknix-desktop/commit/361cd62e0fd89d15adac0000cc7c8212b95c167d))
- Record native GitHub component cache benchmark results ([d847854](https://github.com/kapdon/rocknix-desktop/commit/d8478545939d04f2ee9958d9b86afa0eccc520ea))
- Record successful development builds in the changelog ([d102001](https://github.com/kapdon/rocknix-desktop/commit/d10200103967eea1a908c5644b92ac7be3e89ccc))
- Merge pull request #2 from kapdon/codex/component-builds ([3a32508](https://github.com/kapdon/rocknix-desktop/commit/3a32508bd92d184e4d961c83a8469ef510a290f5))

[Full comparison](https://github.com/kapdon/rocknix-desktop/compare/v0.1.0...3a32508bd92d184e4d961c83a8469ef510a290f5)

<!-- development-changelog:end -->

## [v0.1.0](https://github.com/kapdon/rocknix-desktop/releases/tag/v0.1.0) — 2026-10-02

Retroid Pocket 6 LXC Desktop release. Source:
[`8188d40`](https://github.com/kapdon/rocknix-desktop/commit/8188d4052daa3a1401cf48831e4c9772a7a718de).
