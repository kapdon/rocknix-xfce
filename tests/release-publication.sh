#!/bin/bash
# Exercise release invariants against local Git and a fake GitHub client.
set -Eeuo pipefail
cd "$(dirname "$0")/.."
scratch=$(mktemp -d)
trap 'rm -rf -- "$scratch"' EXIT
mkdir -p "$scratch/repo/scripts" "$scratch/repo/dist" "$scratch/bin"
cp scripts/publish-release.sh "$scratch/repo/scripts/"
cp scripts/publish-development.sh scripts/development-release-notes.py "$scratch/repo/scripts/"
cp scripts/prune-development-assets.sh "$scratch/repo/scripts/"
cp CHANGELOG.md "$scratch/repo/"
printf 'dist/\n' >"$scratch/repo/.gitignore"
git init -q --initial-branch=dev "$scratch/repo"
git -C "$scratch/repo" config user.name 'Release fixture'
git -C "$scratch/repo" config user.email 'fixture@example.invalid'
git -C "$scratch/repo" add .
git -C "$scratch/repo" commit -qm 'Release fixture'
git init -q --bare "$scratch/remote"
git -C "$scratch/repo" remote add origin "$scratch/remote"
git -C "$scratch/repo" push -q origin dev
revision=$(git -C "$scratch/repo" rev-parse HEAD)
mkdir "$scratch/archive"
printf 'commit=%s\nbuilt=2026-09-30T11:00:00Z\n' "$revision" >"$scratch/archive/build-info"
tar -cJf "$scratch/repo/dist/rocknix-desktop-rp6-arm64.tar.xz" -C "$scratch/archive" .
cat >"$scratch/bin/gh" <<'STUB'
#!/bin/bash
set -Eeuo pipefail
printf '%s\n' "$*" >>"$PUBLISH_LOG"
if [ "$1" = api ]; then
  case "$2" in
    */releases/latest)
      [ "${PUBLISH_FAIL_NOTES:-0}" != 1 ] || exit 1
      printf '{"tag_name":"v0.1.0"}\n' ;;
    */compare/*)
      jq -n '[{total_commits:2,commits:[{sha:"2222222222222222222222222222222222222222",html_url:"https://example.invalid/one",commit:{message:"fix: first change"}}]},
              {total_commits:2,commits:[{sha:"3333333333333333333333333333333333333333",html_url:"https://example.invalid/two",commit:{message:"fix: second change"}}]}]' ;;
    */git/tags) printf '1111111111111111111111111111111111111111\n' ;;
    */git/refs/*) ;;
    */releases/assets/*) ;;
    *)
      if [[ "$*" = *'--jq .assets' ]]; then
        asset=$(jq -r .asset "$PUBLISH_POINTER")
        jq -n --arg asset "$asset" --arg other_family "${PUBLISH_OTHER_FAMILY:-desktop}" '[
          {id:1,name:"latest.json",state:"uploaded"},
          {id:2,name:$asset,state:"uploaded"},
          {id:3,name:($asset + ".sha256"),state:"uploaded"},
          {id:4,name:("rocknix-" + $other_family + "-rp6-arm64-0000000000000000000000000000000000000000.tar.xz"),state:"uploaded"},
          {id:5,name:("rocknix-" + $other_family + "-rp6-arm64-0000000000000000000000000000000000000000.tar.xz.sha256"),state:"uploaded"}]'
      else printf '2026-09-30T12:00:00Z\n'; fi ;;
  esac
fi
if [ "$1 $2" = 'release list' ]; then printf 'development\n'; fi
if [ "$1 $2" = 'release view' ]; then printf '2026-09-30T12:00:00Z\n'; fi
if [ "$1 $2" = 'release upload' ] && [ "${PUBLISH_FAIL_UPLOAD:-0}" = 1 ]; then exit 1; fi
if [ "$1 $2" = 'release upload' ] && [[ "$*" = *'dist/latest.json'* ]]; then
  [ "${PUBLISH_FAIL_POINTER:-0}" != 1 ] || exit 1
  cp dist/latest.json "$PUBLISH_POINTER"
fi
if [ "$1 $2" = 'release download' ]; then
  while [ "$#" -gt 0 ]; do
    if [ "$1" = --dir ]; then cp "$PUBLISH_POINTER" "$2/latest.json"; break; fi
    shift
  done
fi
STUB
chmod +x "$scratch/bin/gh"
export PATH="$scratch/bin:$PATH" PUBLISH_LOG="$scratch/calls" PUBLISH_POINTER="$scratch/pointer.json"
for tag in v0.1.0-alpha.1 v0.1.0; do
  : >"$PUBLISH_LOG"
  bash "$scratch/repo/scripts/publish-release.sh" "$tag" >/dev/null
  grep -q '^release view .*--json assets' "$PUBLISH_LOG"
  if grep -q '/releases/tags/v0.1.0' "$PUBLISH_LOG"; then exit 1; fi
  grep -q '^release create .*--draft' "$PUBLISH_LOG"
  grep -Fxq -- 'Built: 2026-09-30T11:00:00Z' "$PUBLISH_LOG"
  grep -qF -- "$(printf 'Commit: `%s`' "$revision")" "$PUBLISH_LOG"
  grep -q '^release upload .*latest.json' "$PUBLISH_LOG"
  grep -q '^release edit .*--draft=false' "$PUBLISH_LOG"
  if [[ "$tag" = *-* ]]; then grep -q -- '--prerelease' "$PUBLISH_LOG";
  elif grep -q -- '--prerelease' "$PUBLISH_LOG"; then exit 1; fi
  if [[ "$tag" = *-* ]]; then grep -q -- '--latest=false' "$PUBLISH_LOG";
  else grep -q -- '--latest=true' "$PUBLISH_LOG"; fi
  jq -e --arg revision "$revision" --arg tag "$tag" \
    '.commit == $revision and .version == $tag and .released_at == "2026-09-30T12:00:00Z" and .built_at == "2026-09-30T11:00:00Z"' \
    "$scratch/repo/dist/latest.json" >/dev/null
done
for attempt in 1 2; do
  GITHUB_RUN_ID=123 GITHUB_RUN_ATTEMPT="$attempt" \
    bash "$scratch/repo/scripts/publish-development.sh" >/dev/null
  jq -e --arg id "r123a$attempt" '.build_id == $id' \
    "$scratch/repo/dist/latest.json" >/dev/null
  test -f "$scratch/repo/dist/rocknix-desktop-rp6-arm64-$revision-r123a$attempt.tar.xz"
done
grep -qF "compare/v0.1.0...$revision?per_page=100 --paginate --slurp" "$PUBLISH_LOG"
grep -qF '[Full changelog](https://github.com/kapdon/rocknix-desktop/blob/dev/CHANGELOG.md)' "$scratch/repo/dist/development-notes.md"
if grep -Eq 'fix: (first|second) change' "$scratch/repo/dist/development-notes.md"; then exit 1; fi
grep -qF -- '--notes-file dist/development-notes.md' "$PUBLISH_LOG"
grep -q '/releases/assets/4 --method DELETE' "$PUBLISH_LOG"
grep -q '/releases/assets/5 --method DELETE' "$PUBLISH_LOG"
if grep -Eq '/releases/assets/[123] --method DELETE' "$PUBLISH_LOG"; then exit 1; fi
awk '/release upload development dist\/latest.json/ {ready=1} /--method DELETE/ {if (!ready) exit 1}' "$PUBLISH_LOG"
jq -e '.built_at == "2026-09-30T11:00:00Z"' "$scratch/repo/dist/latest.json" >/dev/null
grep -q 'git/refs/tags/development --method PATCH' "$PUBLISH_LOG"
grep -q '^release edit development .*--prerelease --latest=false' "$PUBLISH_LOG"
# Release lookup failure must stop before any publication mutation.
: >"$PUBLISH_LOG"
if PUBLISH_FAIL_NOTES=1 bash "$scratch/repo/scripts/publish-development.sh" >/dev/null 2>&1; then exit 1; fi
if grep -Eq '^release (upload|edit|create)|--method (POST|PATCH|DELETE)' "$PUBLISH_LOG"; then exit 1; fi
# Unknown asset families refuse the entire inventory before any deletion.
: >"$PUBLISH_LOG"
if PUBLISH_OTHER_FAMILY=unexpected bash "$scratch/repo/scripts/prune-development-assets.sh" \
  "$(jq -r .asset "$PUBLISH_POINTER")" >/dev/null 2>&1; then exit 1; fi
if grep -q -- '--method DELETE' "$PUBLISH_LOG"; then exit 1; fi
: >"$PUBLISH_LOG"
if PUBLISH_FAIL_POINTER=1 GITHUB_RUN_ID=123 GITHUB_RUN_ATTEMPT=3 \
  bash "$scratch/repo/scripts/publish-development.sh" >/dev/null 2>&1; then exit 1; fi
if grep -q -- '--method DELETE' "$PUBLISH_LOG"; then exit 1; fi
: >"$PUBLISH_LOG"
if PUBLISH_FAIL_UPLOAD=1 bash "$scratch/repo/scripts/publish-release.sh" v0.1.0-beta.1 >/dev/null 2>&1; then exit 1; fi
if grep -q '^release edit ' "$PUBLISH_LOG"; then exit 1; fi
git -C "$scratch/repo" tag v0.1.0
git -C "$scratch/repo" push -q origin refs/tags/v0.1.0
if bash "$scratch/repo/scripts/publish-release.sh" v0.1.0 >/dev/null 2>&1; then exit 1; fi
git -C "$scratch/repo" switch -qc candidate
git -C "$scratch/repo" commit --allow-empty -qm 'Untested candidate'
if bash "$scratch/repo/scripts/publish-release.sh" v0.2.0 >/dev/null 2>&1; then exit 1; fi
git -C "$scratch/repo" push -q origin HEAD:refs/heads/dev
git -C "$scratch/repo" switch -q --detach "$revision"
if bash "$scratch/repo/scripts/publish-release.sh" v0.2.0 >/dev/null 2>&1; then exit 1; fi
printf 'PASS: exact dev provenance, immutable versioned tags, latest-only dev assets and complete-before-retirement\n'
