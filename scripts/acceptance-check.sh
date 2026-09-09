#!/usr/bin/env bash
#
# acceptance-check.sh — sprint 016 DO-1
#
# Checks one sprint spec file, or one sprint evidence file, against the
# mechanical rules in docs/sprints/016-spec.md DO-1. Zero judgement, zero
# model, plain text comparison only. It reports; it never edits.
#
#   usage:  scripts/acceptance-check.sh docs/sprints/016-spec.md
#           scripts/acceptance-check.sh docs/sprints/016-evidence.md
#
#   exit 0  no violation
#   exit 1  at least one violation (each printed as path:line: [ID] message)
#   exit 2  cannot run (bad argument, file outside docs/, unknown file kind)
#
# GENERAL RULE: every check skips fenced code blocks (``` ... ```). What is
# inside them is an example or pasted output, not a claim.
#
# ---------------------------------------------------------------------------
# Not enabled as a hook. Sprint 016 前提決定 1: run it by hand first and show
# that it does not fire on innocent files. A Stop hook that can never be
# satisfied stops the session from ever finishing. If, after it has proven
# itself, you do want it wired in, this is the shape — put it in
# .claude/settings.json yourself; this sprint does not touch that file:
#
#   {
#     "hooks": {
#       "Stop": [
#         {
#           "matcher": "",
#           "hooks": [
#             {
#               "type": "command",
#               "command": "for f in $(git diff --name-only HEAD -- 'docs/sprints/*-spec.md' 'docs/sprints/*-evidence.md'); do scripts/acceptance-check.sh \"$f\" || exit 2; done"
#             }
#           ]
#         }
#       ]
#     }
#   }
#
# exit 2 from a Stop hook blocks the stop and feeds stderr back. That is the
# whole point, and also the whole risk: a criterion that misfires turns into a
# session that cannot end. Do not enable it until H1/H2 have run clean for a
# few sprints.
# ---------------------------------------------------------------------------

set -uo pipefail

MAX_LINES=200          # A5
MAX_CODES=8            # A6
VISUAL_WORDS=(對齊 一眼 看得出 好懂)                      # A2
VISUAL_REQUIRED=(目視驗證 不得以測試通過為證據)            # A2

usage() { echo "usage: $0 <docs/sprints/NNN-spec.md | docs/sprints/NNN-evidence.md>" >&2; }

[ $# -eq 1 ] || { usage; exit 2; }

ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || { echo "not a git repository" >&2; exit 2; }
TARGET=$1
[ -f "$TARGET" ] || { echo "no such file: $TARGET" >&2; exit 2; }

# Path relative to the repo root, so the docs/ guard and the A3 lookups agree.
ABS=$(cd "$(dirname "$TARGET")" && pwd)/$(basename "$TARGET")
REL=${ABS#"$ROOT"/}
case "$REL" in
  docs/*) ;;
  *) echo "refusing to check a file outside docs/: $REL" >&2; exit 2 ;;
esac

case "$REL" in
  *-spec.md)     KIND=spec ;;
  *-evidence.md) KIND=evidence ;;
  *) echo "unknown file kind (expected *-spec.md or *-evidence.md): $REL" >&2; exit 2 ;;
esac

VIOLATIONS=0
report() {  # report <line> <id> <message>
    printf '%s:%s: [%s] %s\n' "$REL" "$1" "$2" "$3"
    VIOLATIONS=$((VIOLATIONS + 1))
}

# --- general rule: line numbers of everything outside a fenced code block ----
# STRIP_LN[i] / STRIP_TXT[i] keep original line numbers so every report points
# at the real line in the file.
STRIP_LN=(); STRIP_TXT=()
in_fence=0; n=0
while IFS= read -r line || [ -n "$line" ]; do
    n=$((n + 1))
    case "$line" in
        '```'*) in_fence=$((1 - in_fence)); continue ;;
    esac
    [ "$in_fence" -eq 1 ] && continue
    STRIP_LN+=("$n"); STRIP_TXT+=("$line")
done < "$ABS"
TOTAL_LINES=$(wc -l < "$ABS" | tr -d ' ')

# --- acceptance-condition blocks -------------------------------------------
# A block starts on a line shaped like "- H1 — ..." or "- H8（目視）— ...", and
# continues onto the immediately following indented, non-blank lines.
# CODES[i] / BLOCK_LN[i] / BLOCK_TXT[i] are filled in document order.
CODES=(); BLOCK_LN=(); BLOCK_TXT=()
i=0
while [ "$i" -lt "${#STRIP_TXT[@]}" ]; do
    txt=${STRIP_TXT[$i]}
    if printf '%s' "$txt" | grep -qE '^- [A-Z][0-9]+[^ ]* ?—'; then
        code=$(printf '%s' "$txt" | grep -oE '^- [A-Z][0-9]+' | sed 's/^- //')
        body=$txt
        prev_ln=${STRIP_LN[$i]}
        j=$((i + 1))
        while [ "$j" -lt "${#STRIP_TXT[@]}" ]; do
            nxt=${STRIP_TXT[$j]}
            [ "${STRIP_LN[$j]}" -eq $((prev_ln + 1)) ] || break
            case "$nxt" in
                ' '*|$'\t'*) ;;
                *) break ;;
            esac
            [ -n "${nxt// /}" ] || break
            body="$body$nxt"
            prev_ln=${STRIP_LN[$j]}
            j=$((j + 1))
        done
        CODES+=("$code"); BLOCK_LN+=("${STRIP_LN[$i]}"); BLOCK_TXT+=("$body")
        i=$j
        continue
    fi
    i=$((i + 1))
done

check_a1() {
    local k
    for k in "${!CODES[@]}"; do
        case "${BLOCK_TXT[$k]}" in
            *WHEN*THEN*) ;;
            *) report "${BLOCK_LN[$k]}" A1 \
                 "驗收條件 ${CODES[$k]} 不含 WHEN … THEN …（標「（目視）」的也不設例外）" ;;
        esac
    done
}

check_a2() {
    local k w hit miss
    for k in "${!CODES[@]}"; do
        hit=""
        for w in "${VISUAL_WORDS[@]}"; do
            [[ ${BLOCK_TXT[$k]} == *"$w"* ]] && { hit=$w; break; }
        done
        [ -n "$hit" ] || continue
        for w in "${VISUAL_REQUIRED[@]}"; do
            [[ ${BLOCK_TXT[$k]} == *"$w"* ]] || miss="${miss}「${w}」"
        done
        [ -n "${miss:-}" ] && report "${BLOCK_LN[$k]}" A2 \
            "驗收條件 ${CODES[$k]} 含目視詞「${hit}」，同段落缺少${miss}"
        miss=""
    done
}

check_a3() {
    local k tok path want have
    for k in "${!STRIP_TXT[@]}"; do
        for tok in $(printf '%s' "${STRIP_TXT[$k]}" \
                     | grep -oE '[A-Za-z0-9_./-]+\.(py|sh|md|ya?ml|toml):[0-9]+'); do
            path=${tok%:*}; want=${tok##*:}
            case "$path" in
                */*) ;;
                *) report "${STRIP_LN[$k]}" A3 \
                     "引用 $tok 是 basename，要寫完整路徑（同名檔案會讓解析出錯）"
                   continue ;;
            esac
            if [ ! -f "$ROOT/$path" ]; then
                report "${STRIP_LN[$k]}" A3 "引用 $tok 的檔案不存在"
                continue
            fi
            have=$(wc -l < "$ROOT/$path" | tr -d ' ')
            [ "$want" -le "$have" ] || report "${STRIP_LN[$k]}" A3 \
                "引用 $tok 超過檔案長度（$path 只有 $have 行）"
        done
    done
}

check_a5() {
    [ "$TOTAL_LINES" -le "$MAX_LINES" ] || report "$TOTAL_LINES" A5 \
        "spec 共 $TOTAL_LINES 行，超過上限 $MAX_LINES"
}

check_a6() {
    local count=${#CODES[@]}
    [ "$count" -le "$MAX_CODES" ] || report "${BLOCK_LN[$MAX_CODES]}" A6 \
        "驗收條件代號共 $count 個（${CODES[*]}），超過上限 $MAX_CODES"
}

check_b1() {
    local ln
    ln=$(grep -nE '[0-9]+ passed in [0-9.]+s' "$ABS" | head -1 | cut -d: -f1)
    [ -n "$ln" ] || report 1 B1 "找不到形如「N passed in Ns」的 pytest 摘要行"
}

check_b2() {
    local spec code
    spec=${ABS%-evidence.md}-spec.md
    if [ ! -f "$spec" ]; then
        report 1 B2 "找不到對應的 spec：$(basename "$spec")"
        return
    fi
    for code in $(grep -oE '^- [A-Z][0-9]+[^ ]* ?—' "$spec" \
                  | grep -oE '[A-Z][0-9]+' | sort -u); do
        grep -q "$code" "$ABS" || report 1 B2 "spec 的驗收條件 $code 沒有出現在 evidence 裡"
    done
}

if [ "$KIND" = spec ]; then
    check_a1; check_a2; check_a3; check_a5; check_a6
else
    check_b1; check_b2
fi

if [ "$VIOLATIONS" -eq 0 ]; then
    echo "$REL: OK（${KIND}，0 violations）"
    exit 0
fi
echo "$REL: $VIOLATIONS violations"
exit 1
