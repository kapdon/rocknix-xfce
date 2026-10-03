#!/bin/bash
# Standalone installer refuses game recovery before downloading while locked.
set -Eeuo pipefail
cd "$(dirname "$0")/.."
source ./install.sh
scratch=$(mktemp -d)
trap 'rm -rf -- "$scratch"' EXIT
journal="$scratch/session.json"
fixture_unit=rocknix-desktop-games.service
fixture_state=inactive
fixture_error=0
systemctl() {
  [ "$*" = "show --property=ActiveState --value $4" ] || return 99
  [ "$fixture_error" = 0 ] || return 1
  if [ "$4" = "$fixture_unit" ]; then printf '%s\n' "$fixture_state"; else printf 'inactive\n'; fi
}
for fixture_unit in rocknix-desktop-games.service steam-bigpicture.scope; do
  for fixture_state in inactive failed; do check_games_idle "$journal"; done
  for fixture_state in active activating deactivating reloading '' unknown; do
    if (check_games_idle "$journal") >"$scratch/output" 2>&1; then exit 1; fi
    grep -q 'Steam must be fully inactive' "$scratch/output"
  done
done
fixture_state=inactive
fixture_error=1
if (check_games_idle "$journal") >"$scratch/output" 2>&1; then exit 1; fi
grep -q 'cannot inspect Steam state' "$scratch/output"
fixture_error=0
touch "$journal"
if (check_games_idle "$journal") >"$scratch/output" 2>&1; then exit 1; fi
grep -q 'finish Steam session recovery' "$scratch/output"
rm "$journal"
ln -s "$scratch/missing" "$journal"
if (check_games_idle "$journal") >"$scratch/output" 2>&1; then exit 1; fi
grep -q 'finish Steam session recovery' "$scratch/output"
rm "$journal"

# Model a supervisor releasing its flock between the initial device check and
# lock acquisition. The post-lock recheck must exit before power/download work.
check_device() { check_games_idle "$journal"; }
acquire_install_lock() {
  exec 9>"$scratch/install.lock"
  flock -n 9
  touch "$journal"
}
check_power() { touch "$scratch/late-work"; }
curl() { touch "$scratch/late-work"; return 1; }
if (main --dev --yes) >"$scratch/output" 2>&1; then exit 1; fi
grep -q 'finish Steam session recovery' "$scratch/output"
test ! -e "$scratch/late-work"
# Refusal releases the lock rather than keeping Desktop recovery blocked.
flock -n "$scratch/install.lock" true
printf 'PASS: standalone installer rejects Steam activity and recovery before downloads and releases its lock\n'
