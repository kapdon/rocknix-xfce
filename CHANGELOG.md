# Changelog

The development section records the latest successful development build, with
all changes since the latest stable release. GitHub Actions updates this file
and the rolling development release together. Earlier build snapshots remain
in this file's Git history. Automated changelog commits are omitted from the
change list.

<!-- development-changelog:start -->

## Unreleased

- Reuse independently built Desktop components, so configuration changes avoid
  rebuilding, exporting and compressing the large Debian runtime.
- Preserve package and remote image-layer caches across ordinary rebuilds.
- Toggle the Apps and Settings menus closed when tapped again.
- Generate cumulative development release notes from the latest stable release
  and record successful development builds here.

<!-- development-changelog:end -->

## [v0.1.0](https://github.com/kapdon/rocknix-desktop/releases/tag/v0.1.0) — 2026-10-02

Retroid Pocket 6 LXC Desktop release. Source:
[`8188d40`](https://github.com/kapdon/rocknix-desktop/commit/8188d4052daa3a1401cf48831e4c9772a7a718de).
