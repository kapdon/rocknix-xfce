#!/bin/bash
# Download the versioned desktop bundle; never write the ROCKNIX root image.
set -Eeuo pipefail

VERSION=latest
REPOSITORY=kapdon/rocknix-desktop
ASSET=rocknix-desktop-rp6-arm64.tar.xz
BASE=/storage/rocknix-desktop/managed/host
WORKSPACE=/storage/rocknix-desktop
EXPERIMENTAL_DEVICE=0

fail() { printf 'Install failed: %s\n' "$*" >&2; exit 1; }

read_confirmation() {
  # stdin carries the installer itself when invoked as curl | bash.
  if ! read -r "$1" 2>/dev/null </dev/tty; then
    printf '\nConfirmation requires a terminal; cancelled.\n' >&2
    return 1
  fi
}

check_power() {
  # RP6 main battery only, never a connected controller's power supply.
  local battery=${1:-/sys/class/power_supply/battery} kind capacity
  kind=$(cat "$battery/type" 2>/dev/null) || fail 'cannot read device battery; restore telemetry and retry'
  capacity=$(cat "$battery/capacity" 2>/dev/null) || fail 'cannot read device battery; restore telemetry and retry'
  [ "$kind" = Battery ] && [[ "$capacity" =~ ^[0-9]{1,3}$ ]] ||
    fail 'invalid device battery telemetry; restore telemetry and retry'
  capacity=$((10#$capacity))
  [ "$capacity" -le 100 ] || fail 'invalid device battery percentage'
  [ "$capacity" -ge 10 ] || fail "battery is $capacity%; charge to at least 10%, even when plugged in"
}

select_installation_paths() {
  BASE="$WORKSPACE/managed/host"
  DATA="$WORKSPACE/data"
}

detect_installation() {
  local result
  select_installation_paths
  result=$(python3 "$STAGING/bundle/payload/bin/rocknix-install-state" --bundle "$STAGING/bundle") ||
    fail 'installation validation failed; no installation changes made'
  INSTALL_STATUS=$(jq -er '.status' <<<"$result")
  INSTALL_REASON=$(jq -er '.reason' <<<"$result")
  INSTALLED_REVISION=$(jq -r '.revision // empty' <<<"$result")
  case "$INSTALL_STATUS" in healthy|invalid|absent) ;; *) fail 'invalid installation classification' ;; esac
  if [ "$INSTALL_STATUS" = healthy ]; then
    [[ "$INSTALLED_REVISION" =~ ^[0-9a-f]{40}$ ]] || fail 'invalid installed revision'
  fi
}

confirm_action() {
  local action=$1 answer
  if [ "$action" = Install ]; then
    printf 'Install Desktop Mode? This replaces Desktop apps, home, profiles and settings. No recovery copy is kept. Shared files and native ROCKNIX stay untouched. [y/N] '
  else
    printf 'Update Desktop Mode? Replace the container system and installed packages. Home, user settings and shared files are preserved. [y/N] '
  fi
  if ! read_confirmation answer; then printf '\nCancelled.\n'; return 1; fi
  case "$answer" in y|Y|yes|YES) return 0 ;; *) printf 'Cancelled.\n'; return 1 ;; esac
}

confirm_untested_device() {
  local model=$1 answer
  printf '%s uses the supported SM8550 chipset family, but ROCKNIX Desktop has only been hardware-tested on Retroid Pocket 6. Features may not work on this device. Proceed at your own risk? [y/N] ' "$model"
  if ! read_confirmation answer; then printf '\nCancelled.\n'; return 1; fi
  case "$answer" in y|Y|yes|YES) return 0 ;; *) printf 'Cancelled.\n'; return 1 ;; esac
}

acquire_install_lock() {
  exec 9>/storage/.rocknix-desktop-install.lock
  flock -n 9 || fail 'another installation is running'
}

check_install_target() {
  [ ! -L "$WORKSPACE" ] || fail 'workspace must not be a symlink'
  if [ -e "$WORKSPACE" ]; then
    [ -d "$WORKSPACE" ] && [ "$(realpath "$WORKSPACE")" = "$WORKSPACE" ] || fail 'unsafe workspace path'
  fi
}

check_games_idle() {
  # This standalone downloader cannot use a bundled helper yet. Check before
  # and immediately after locking, rather than holding recovery off for a download.
  local journal=${1:-/run/rocknix-desktop-games/session.json} state unit
  [ ! -e "$journal" ] && [ ! -L "$journal" ] || fail 'finish Steam session recovery before maintenance'
  for unit in rocknix-desktop-games.service steam-bigpicture.scope; do
    state=$(systemctl show --property=ActiveState --value "$unit") || fail 'cannot inspect Steam state'
    case "$state" in
      inactive|failed) ;;
      *) fail 'Steam must be fully inactive before maintenance' ;;
    esac
  done
}

check_device() {
  [ "$(id -u)" = 0 ] || fail 'run as root on the ROCKNIX device'
  [ -r /etc/os-release ] || fail 'missing OS identification'
  . /etc/os-release
  [ "${OS_NAME:-}" = ROCKNIX ] || fail 'this installer requires ROCKNIX'
  [ "$(uname -m)" = aarch64 ] || fail 'only aarch64 is supported'
  [ "${HW_DEVICE:-}" = SM8550 ] && [ "${DISTRO_DEVICE:-}" = SM8550 ] ||
    fail 'this device is currently out of scope; only ROCKNIX SM8550/QCS8550 devices are being tested'
  local model
  model=$(tr -d '\000' </proc/device-tree/model 2>/dev/null || true)
  [ -n "$model" ] || fail 'missing device-tree identity'
  DEVICE_MODEL=$model
  EXPERIMENTAL_DEVICE=0
  [ "$model" = 'Retroid Pocket 6' ] || EXPERIMENTAL_DEVICE=1
  [ -d /storage ] && [ -w /storage ] || fail '/storage must be writable'
  for command in curl jq sha256sum tar xz df mktemp systemctl flock realpath find python3; do
    command -v "$command" >/dev/null || fail "missing command: $command"
  done
  check_install_target
  local state
  state=$(systemctl show --property=ActiveState --value rocknix-desktop.service) || fail 'cannot inspect Desktop state'
  [ "$state" = inactive ] || fail 'exit Desktop Mode before running the installer'
  check_games_idle
  if [ "${OPERATION:-auto}" != uninstall ]; then
    [ "$(df -Pk /storage | awk 'END {print $4}')" -ge 4194304 ] ||
      fail 'at least 4 GiB free on /storage is required'
  fi
}

validate_uninstall_helpers() {
  # Never execute a guest-writable helper as native host root.
  python3 - "$BASE/bin" <<'PY'
import os, stat, sys
from pathlib import Path
directory = Path(sys.argv[1])
for path in (*directory.parents, directory, *directory.iterdir()):
    info = path.lstat()
    if info.st_uid != 0 or info.st_mode & 0o022 or not (
            stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
        raise SystemExit('Unsafe installed host helper path: ' + str(path))
PY
}

uninstall_desktop() {
  local check=$1 yes=$2 answer
  select_installation_paths
  local helper="$BASE/bin/rocknix-lxc-uninstall"
  [ -f "$helper" ] || fail 'no installed LXC uninstaller found; no changes made'
  validate_uninstall_helpers
  python3 "$helper" --check
  [ "$check" != 1 ] || return 0
  if [ "$yes" != 1 ]; then
    printf 'Uninstall Desktop integration? Apps, home and settings are retained. Native ROCKNIX and shared files stay untouched. [y/N] '
    read_confirmation answer || return 0
    case "$answer" in y|Y|yes|YES) ;; *) printf 'Cancelled.\n'; return 0 ;; esac
  fi
  python3 "$helper" --yes
}

verify_bundle() {
  local directory=$1 expected actual
  expected=$(awk 'NR == 1 {print $1}' "$directory/$ASSET.sha256")
  [[ "$expected" =~ ^[0-9a-f]{64}$ ]] || fail 'invalid SHA-256 checksum'
  actual=$(sha256sum "$directory/$ASSET")
  [ "${actual%% *}" = "$expected" ] || fail 'bundle checksum mismatch'
}

record_release() {
  # The release record describes the exact downloaded and verified bundle.
  [ -x "$BASE/bin/rocknix-tools-metadata" ] || return 0
  [ ! -L "$BASE/release-info.json" ] || fail 'release metadata must not be a symlink'
  cp "$STAGING/latest.json" "$BASE/release-info.json"
  "$BASE/bin/rocknix-tools-metadata"
}

main() {
  local check=0 yes=0 requested=auto release_selected=0
  VERSION=latest
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --help|-h)
        printf 'Usage: bash install.sh [--dev | --release TAG] [--install | --update | --uninstall] [--check | --yes]\nDefault: latest published stable version. --dev selects rolling development; --release TAG selects a version. Update replaces the container system and packages, preserving home and shared files; Install replaces Desktop apps and home. Uninstall removes integration and retains data without downloading a bundle.\n--yes accepts the operation (including deletion for Install), but never skips an untested-device confirmation.\nOther SM8550/QCS8550 installs require confirmation; other chipsets are currently out of scope.\n--check validates prerequisites without changes; with --uninstall it validates installed removal.\n'
        return ;;
      --check) check=1; shift ;;
      --yes) yes=1; shift ;;
      --install|--update|--uninstall)
        [ "$requested" = auto ] || fail 'choose Install, Update or Uninstall'
        requested=${1#--}; shift ;;
      --dev)
        [ "$release_selected" = 0 ] || fail 'choose --dev or --release TAG'
        release_selected=1; VERSION=development; shift ;;
      --release)
        [ "$release_selected" = 0 ] || fail 'choose --dev or --release TAG'
        [ "$#" -ge 2 ] || fail 'missing release tag'
        [[ "$2" =~ ^v[0-9]+\.[0-9]+\.[0-9]+(-(alpha|beta|rc)\.[0-9]+)?$ ]] || fail 'invalid release tag'
        release_selected=1; VERSION=$2
        shift 2 ;;
      *) fail "unknown option: $1" ;;
    esac
  done
  [ "$check$yes" != 11 ] || fail 'choose --check or --yes'
  # Consent is supplied by the host installer, never by the writable guest.
  export ROCKNIX_UNTESTED_DEVICE_CONFIRMED=0
  OPERATION=$requested
  check_device
  if [ "$requested" = uninstall ]; then
    uninstall_desktop "$check" "$yes"
    return
  fi
  if [ "$check" = 1 ]; then
    [ "$EXPERIMENTAL_DEVICE" != 1 ] || printf 'Untested device: %s. Installation will require confirmation.\n' "$DEVICE_MODEL"
    printf 'Device checks passed. No changes made.\n'
    return
  fi
  if [ "$EXPERIMENTAL_DEVICE" = 1 ]; then
    confirm_untested_device "$DEVICE_MODEL" || return 0
    export ROCKNIX_UNTESTED_DEVICE_CONFIRMED=1
  fi
  # Lock before downloading, and recheck after acquiring it.
  acquire_install_lock
  check_device
  check_power
  select_installation_paths
  [ ! -L "$WORKSPACE" ] || fail 'workspace must not be a symlink'
  mkdir -p "$WORKSPACE"
  [ "$(realpath "$WORKSPACE")" = "$WORKSPACE" ] || fail 'invalid workspace path'
  STAGING=$(mktemp -d "$WORKSPACE/install.XXXXXX")
  trap 'rc=$?; if [ "$rc" = 0 ]; then rm -rf -- "$STAGING"; else
    printf "Installation stopped. Diagnostics/staging retained at %s\n" "$STAGING" >&2; fi' EXIT
  if [ "$VERSION" = latest ]; then
    curl --fail --location --proto '=https' --proto-redir '=https' --retry 3 \
      -H 'Accept: application/vnd.github+json' \
      "https://api.github.com/repos/$REPOSITORY/releases/latest" -o "$STAGING/latest-release.json" ||
      fail 'cannot determine the latest stable release'
    VERSION=$(jq -er 'if .draft == false and .prerelease == false then .tag_name else error("not a stable release") end' \
      "$STAGING/latest-release.json") || fail 'invalid latest release metadata'
    [[ "$VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || fail 'invalid latest release tag'
  fi
  local url="https://github.com/$REPOSITORY/releases/download/$VERSION"
  curl --fail --location --proto '=https' --proto-redir '=https' --retry 3 \
    --retry-all-errors "$url/latest.json" -o "$STAGING/latest.json"
  local revision expected
  revision=$(jq -er '.commit' "$STAGING/latest.json")
  expected=$(jq -er '.sha256' "$STAGING/latest.json")
  [[ "$revision" =~ ^[0-9a-f]{40}$ ]] || fail 'invalid build commit'
  [[ "$expected" =~ ^[0-9a-f]{64}$ ]] || fail 'invalid build checksum'
  ASSET=$(jq -er '.asset' "$STAGING/latest.json")
  local release_format
  release_format=$(jq -r '.format // 1' "$STAGING/latest.json")
  case "$release_format" in
    1) [[ "$ASSET" =~ ^rocknix-desktop-rp6-arm64-${revision}(-r[0-9]+a[0-9]+)?\.tar\.xz$ ]] || fail 'invalid build filename' ;;
    2) [[ "$ASSET" = "rocknix-desktop-components-${revision}-${expected}.json" ]] || fail 'invalid component manifest filename' ;;
    *) fail 'unsupported release format; update the installer' ;;
  esac
  check_power
  printf 'Downloading ROCKNIX Desktop (Sway) %s (%s)\n' "$VERSION" "$revision"
  curl --fail --location --proto '=https' --proto-redir '=https' --retry 3 \
    "$url/$ASSET" -o "$STAGING/$ASSET"
  printf '%s  %s\n' "$expected" "$ASSET" >"$STAGING/$ASSET.sha256"
  verify_bundle "$STAGING"
  if [ "$release_format" = 2 ]; then
    local helper helper_sha helper_size
    helper=$(jq -er '.bootstrap.asset' "$STAGING/latest.json")
    helper_sha=$(jq -er '.bootstrap.sha256' "$STAGING/latest.json")
    helper_size=$(jq -er '.bootstrap.size' "$STAGING/latest.json")
    [[ "$helper_sha" =~ ^[0-9a-f]{64}$ && "$helper" = "rocknix-components-${helper_sha}.py" &&
       "$helper_size" =~ ^[0-9]{1,7}$ ]] || fail 'invalid component bootstrap'
    [ "$helper_size" -le 1048576 ] || fail 'component bootstrap is too large'
    curl --fail --location --proto '=https' --proto-redir '=https' --retry 3 --max-filesize 1048576 \
      "$url/$helper" -o "$STAGING/component-installer.py"
    [ "$(wc -c <"$STAGING/component-installer.py")" -eq "$helper_size" ] || fail 'component bootstrap size mismatch'
    printf '%s  %s\n' "$helper_sha" "$STAGING/component-installer.py" | sha256sum -c -
    # Both actions use a complete new guest system; home lives outside it.
    python3 "$STAGING/component-installer.py" --manifest "$STAGING/$ASSET" \
      --repository "$REPOSITORY" --cache "$STAGING/components" --profile update --output "$STAGING/bundle"
  else
    mkdir "$STAGING/bundle"
    tar -xJf "$STAGING/$ASSET" -C "$STAGING/bundle"
  fi
  grep -Fxq "commit=$revision" "$STAGING/bundle/build-info" || fail 'bundle provenance mismatch'
  # Verify required integration before probing or changing installed data.
  [ -f "$STAGING/bundle/payload/systemd/rocknix-desktop.service" ] &&
    [ -f "$STAGING/bundle/rootfs/etc/rocknix-desktop-release" ] &&
    [ -f "$STAGING/bundle/payload/bin/rocknix-device-profile" ] ||
    fail 'bundle is missing required Desktop integration; no installation changes made'
  if ! python3 "$STAGING/bundle/payload/bin/rocknix-device-profile" \
      >"$STAGING/device-profile.json" 2>"$STAGING/device-check.log"; then
    cat "$STAGING/device-check.log" >&2
    fail "device profile rejected; see diagnostics in $STAGING. No Desktop data replaced"
  fi
  cat "$STAGING/device-profile.json"
  if [ -e "$BASE/state/upgrade-in-progress.json" ]; then
    # Let the checksum-bound updater recover its transaction; never offer a
    # destructive fresh install merely because replacement was interrupted.
    INSTALL_STATUS=healthy
    INSTALL_REASON='component update recovery required'
    INSTALLED_REVISION=
  else
    detect_installation
  fi
  printf 'Installed state: %s — %s\nAvailable: %s (%s)\n' "$INSTALL_STATUS" "$INSTALL_REASON" "$VERSION" "$revision"
  local action=Install
  [ "$INSTALL_STATUS" != healthy ] || action=Update
  [ "$requested" != install ] || action=Install
  if [ "$requested" = update ] && [ "$INSTALL_STATUS" != healthy ]; then
    fail 'Update is unavailable for an absent or invalid installation. Run Install to replace Desktop data.'
  fi
  if [ "$action" = Update ] && [ "$INSTALLED_REVISION" = "$revision" ] &&
     [ -f "$BASE/release-info.json" ] && [ ! -L "$BASE/release-info.json" ] &&
     jq -e --arg commit "$revision" --arg sha256 "$expected" \
       '.commit == $commit and .sha256 == $sha256' "$BASE/release-info.json" >/dev/null; then
    record_release
    printf 'Already up to date; release metadata refreshed.\n'
    return
  fi
  if [ "$yes" != 1 ]; then confirm_action "$action" || return 0; fi
  check_power
  if [ "$action" = Update ]; then
    # The upgrader acquires this same lock and revalidates the installation.
    # Close our descriptor first to avoid deadlocking the child process.
    flock -u 9
    exec 9>&-
    bash "$STAGING/bundle/upgrade.sh" --bundle "$STAGING/$ASSET" --sha256 "$expected" --assembled "$STAGING/bundle" --yes
  else
    bash "$STAGING/bundle/install-device.sh" --replace
  fi
  record_release
  printf '\nRefresh the EmulationStation game list, then open Tools > Desktop Mode.\n'
}

if [[ "${BASH_SOURCE[0]:-$0}" = "$0" ]]; then
  main "$@"
fi
