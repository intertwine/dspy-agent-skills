#!/usr/bin/env bash
# Install DSPy agent skills into Claude Code and/or Codex CLI skill directories.
#
# Claude Code skill root:  ~/.claude/skills/
# Codex CLI skill root:    ~/.agents/skills/   (per https://developers.openai.com/codex/skills)
#
# Usage:
#   scripts/install.sh                      # install for both, symlink mode
#   scripts/install.sh --claude-only        # only Claude Code
#   scripts/install.sh --codex-only         # only Codex
#   scripts/install.sh --copy               # copy instead of symlink (default: symlink)
#   scripts/install.sh --uninstall          # remove installed skills
#   scripts/install.sh --verify             # check installed skills are present and valid
#   scripts/install.sh --dry-run            # print actions, do nothing
#
# Symlinks are preferred: edits to this repo propagate to installed skills without re-running.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_SRC="$REPO_ROOT/skills"

CLAUDE_DEST="$HOME/.claude/skills"
CODEX_DEST="$HOME/.agents/skills"

DO_CLAUDE=1
DO_CODEX=1
MODE="link"   # link | copy
UNINSTALL=0
DRY_RUN=0
VERIFY=0

log() { printf "  %s\n" "$*"; }
run() {
    if [[ $DRY_RUN -eq 1 ]]; then
        printf "  [dry-run] %s\n" "$*"
    else
        eval "$@"
    fi
}

for arg in "$@"; do
    case "$arg" in
        --claude-only) DO_CODEX=0 ;;
        --codex-only)  DO_CLAUDE=0 ;;
        --copy)        MODE="copy" ;;
        --link)        MODE="link" ;;
        --uninstall)   UNINSTALL=1 ;;
        --verify)      VERIFY=1 ;;
        --dry-run)     DRY_RUN=1 ;;
        -h|--help)
            sed -n '2,15p' "$0"; exit 0 ;;
        *) echo "Unknown arg: $arg" >&2; exit 2 ;;
    esac
done

skills=()
while IFS= read -r d; do
    [[ -f "$d/SKILL.md" ]] && skills+=("$(basename "$d")")
done < <(find "$SKILLS_SRC" -maxdepth 1 -mindepth 1 -type d | sort)

if [[ ${#skills[@]} -eq 0 ]]; then
    echo "No skills found under $SKILLS_SRC" >&2
    exit 1
fi

install_into() {
    local dest="$1"
    local label="$2"

    if [[ $UNINSTALL -eq 1 ]]; then
        echo "Uninstalling from $label ($dest)..."
        for name in "${skills[@]}"; do
            local tgt="$dest/$name"
            if [[ -L "$tgt" || -e "$tgt" ]]; then
                run "rm -rf \"$tgt\""
                log "removed $tgt"
            fi
        done
        return
    fi

    echo "Installing into $label ($dest) [$MODE]..."
    run "mkdir -p \"$dest\""
    for name in "${skills[@]}"; do
        local src="$SKILLS_SRC/$name"
        local tgt="$dest/$name"
        if [[ -L "$tgt" || -e "$tgt" ]]; then
            run "rm -rf \"$tgt\""
        fi
        if [[ "$MODE" == "link" ]]; then
            run "ln -s \"$src\" \"$tgt\""
        else
            run "cp -R \"$src\" \"$tgt\""
        fi
        log "$name → $tgt"
    done
}

verify_dest() {
    local dest="$1"
    local label="$2"
    local fails=0

    if [[ ! -d "$dest" ]]; then
        echo "FAIL: $label skill directory does not exist ($dest)"
        return 1
    fi

    echo "Verifying $label ($dest)..."
    for name in "${skills[@]}"; do
        local tgt="$dest/$name"
        if [[ -L "$tgt" ]]; then
            local link_target
            link_target="$(readlink -f "$tgt")"
            if [[ -d "$link_target" && -f "$link_target/SKILL.md" ]]; then
                log "OK   $name → $link_target (symlink)"
            else
                log "FAIL $name → symlink target missing or has no SKILL.md"
                fails=$((fails + 1))
            fi
        elif [[ -d "$tgt" && -f "$tgt/SKILL.md" ]]; then
            log "OK   $name (copy)"
        else
            log "FAIL $name — not found"
            fails=$((fails + 1))
        fi
    done
    return "$fails"
}

if [[ $VERIFY -eq 1 ]]; then
    exit_code=0
    [[ $DO_CLAUDE -eq 1 ]] && { verify_dest "$CLAUDE_DEST" "Claude Code" || exit_code=1; }
    [[ $DO_CODEX -eq 1 ]]  && { verify_dest "$CODEX_DEST"  "Codex CLI"   || exit_code=1; }
    echo
    if [[ $exit_code -eq 0 ]]; then
        echo "All skills verified."
    else
        echo "Some skills failed verification — see above."
    fi
    exit "$exit_code"
fi

[[ $DO_CLAUDE -eq 1 ]] && install_into "$CLAUDE_DEST" "Claude Code"
[[ $DO_CODEX -eq 1 ]]  && install_into "$CODEX_DEST"  "Codex CLI"

echo
if [[ $UNINSTALL -eq 1 ]]; then
    echo "Done. Restart your agent to drop the skills."
else
    echo "Done. Restart your agent (or /reload) to pick up the skills."
    echo "Available skills: ${skills[*]}"
fi
