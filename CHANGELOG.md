# Changelog

The development section records the latest successful development build, with
all changes since the latest stable release. GitHub Actions updates this file
and the rolling development release together. Release notes show the highlights
below and link here for the full history. Earlier build snapshots remain
in this file's Git history. Automated changelog commits are omitted from the
change list.

## Highlights since v0.1.0

- **Faster development builds:** Reuse unchanged components and rebuild only the
  affected parts, avoiding repeated export and compression of the Debian runtime.
- **Apps and Settings toggles:** Tap either button again to close its open menu.
- **Better cache reuse:** Preserve Trash packages and remote Docker layers, and
  include the keyboard layout in its compiler inputs.
- **Recorded release history:** Successful development builds automatically
  record all changes since the latest stable release in this changelog.

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
