#!/usr/bin/env bash
# Batch: story 3.15 (Conditional row coloring) — full pipeline, create already done
# Models: Sonnet (dev/auto), Haiku (review) — same config as prior batches
# Bucket A clean-room: NEVER read premium/enterprise; provenance record is CI gate
set -uo pipefail

SCRIPTS=".claude/skills/bmad-story-automator/scripts/story-automator"
STATE_FILE="_bmad-output/story-automator/orchestration-1-20260606-103602.md"
EPIC="1"
STORY="3.15"
DEV_MODEL="sonnet"
REVIEW_MODEL="haiku"
LOG_FILE="_bmad-output/story-automator/batch-3.15-$(date +%Y%m%d-%H%M%S).log"

log() { local ts; ts=$(date -u +%Y-%m-%dT%H:%M:%SZ); echo "[$ts] $1" | tee -a "$LOG_FILE"; }

update_progress() {
    local c="$1" d="$2" a="$3" r="$4" g="$5" s="$6"
    local tmp; tmp=$(mktemp)
    sed "s/^| ${STORY} |.*$/| ${STORY} | ${c} | ${d} | ${a} | ${r} | ${g} | ${s} |/" \
        "$STATE_FILE" > "$tmp" && mv "$tmp" "$STATE_FILE"
}

spawn_and_monitor() {
    local task="$1" model="$2"
    local built_cmd session result
    built_cmd=$("$SCRIPTS" tmux-wrapper build-cmd "$task" "$STORY" \
        --agent claude --model "$model" --state-file "$STATE_FILE")
    session=$("$SCRIPTS" tmux-wrapper spawn "$task" "$EPIC" "$STORY" \
        --agent claude --command "$built_cmd")
    result=$("$SCRIPTS" monitor-session "$session" --json --agent claude || true)
    "$SCRIPTS" tmux-wrapper kill "$session" 2>/dev/null || true
    echo "$result"
}

spawn_review() {
    local cycle="$1" model="$2"
    local built_cmd session result
    built_cmd=$("$SCRIPTS" tmux-wrapper build-cmd review "$STORY" \
        --agent claude --model "$model" --state-file "$STATE_FILE")
    session=$("$SCRIPTS" tmux-wrapper spawn review "$EPIC" "$STORY" \
        --agent claude --cycle "$cycle" --command "$built_cmd")
    result=$("$SCRIPTS" monitor-session "$session" --json --agent claude \
        --workflow review --story-key "$STORY" --state-file "$STATE_FILE" || true)
    "$SCRIPTS" tmux-wrapper kill "$session" 2>/dev/null || true
    echo "$result"
}

# ================================================================
log "=== BATCH 3.15 STARTED: dev=$DEV_MODEL review=$REVIEW_MODEL (create already done) ==="

"$SCRIPTS" orchestrator-helper state-update "$STATE_FILE" \
    --set currentStory="$STORY" --set currentStep=step-03-execute \
    --set status=IN_PROGRESS \
    --set lastUpdated="$(date -u +%Y-%m-%dT%H:%M:%SZ)" >/dev/null

# --- A. CREATE (verify only; story file already exists) ---
verify=$("$SCRIPTS" orchestrator-helper verify-step create "$STORY" \
    --state-file "$STATE_FILE" 2>/dev/null || echo '{"verified":false}')
if echo "$verify" | grep -q '"verified":true'; then
    log "[$STORY] create: SKIP (exists)"
else
    log "[$STORY] create: story file MISSING — abort"
    update_progress "fail" "⏳" "⏳" "⏳" "⏳" "error"
    exit 1
fi

# --- B. DEV ---
log "[$STORY] dev: START (model=$DEV_MODEL)"
dev_ok=false
for attempt in 1 2 3 4 5; do
    result=$(spawn_and_monitor "dev" "$DEV_MODEL")
    final=$(echo "$result" | jq -r '.final_state // "unknown"')
    if [ "$final" = "completed" ] || [ "$final" = "success" ]; then
        dev_ok=true; break
    fi
    log "[$STORY] dev attempt $attempt failed (state=$final)"
    [ $attempt -lt 5 ] && sleep 30
done
if $dev_ok; then
    update_progress "done" "done" "⏳" "⏳" "⏳" "in-progress"
    log "[$STORY] dev: DONE"
else
    update_progress "done" "fail" "⏳" "⏳" "⏳" "error"
    log "[$STORY] dev: FAILED - abort"
    exit 1
fi

# --- C. AUTO (non-blocking) ---
log "[$STORY] auto: START (model=$DEV_MODEL)"
auto_result=$(spawn_and_monitor "auto" "$DEV_MODEL" || true)
auto_state=$(echo "$auto_result" | jq -r '.final_state // "unknown"')
if [ "$auto_state" = "completed" ] || [ "$auto_state" = "success" ]; then
    update_progress "done" "done" "done" "⏳" "⏳" "in-progress"
    log "[$STORY] auto: DONE"
else
    update_progress "done" "done" "skip" "⏳" "⏳" "in-progress"
    log "[$STORY] auto: SKIP (state=$auto_state, non-blocking)"
fi

# --- D. REVIEW LOOP ---
log "[$STORY] review: START (model=$REVIEW_MODEL)"
review_ok=false
for cycle in 1 2 3 4 5; do
    result=$(spawn_review "$cycle" "$REVIEW_MODEL")
    final=$(echo "$result" | jq -r '.final_state // "unknown"')
    if [ "$final" = "completed" ]; then
        review_ok=true; break
    fi
    log "[$STORY] review cycle $cycle: $final"
    [ $cycle -lt 5 ] && sleep 15
done
auto_col=$(grep "^| ${STORY} |" "$STATE_FILE" | awk -F'|' '{print $5}' | tr -d ' ')
if $review_ok; then
    update_progress "done" "done" "$auto_col" "done" "⏳" "in-progress"
    log "[$STORY] review: DONE"
else
    update_progress "done" "done" "$auto_col" "fail" "⏳" "error"
    log "[$STORY] review: FAILED (max cycles) - abort"
    exit 1
fi

# --- E. COMMIT ---
title="Conditional row coloring (view decorations)"
log "[$STORY] commit: '$title'"
commit=$("$SCRIPTS" commit-story --repo "." --story "$STORY" --title "$title" 2>&1 || echo '{"ok":false,"error":"commit_failed"}')
if echo "$commit" | grep -q '"ok":true'; then
    update_progress "done" "done" "$auto_col" "done" "done" "done"
    echo "- **[$(date -u +%Y-%m-%dT%H:%M:%SZ)]** Story ${STORY}: ✅ complete" >> "$STATE_FILE"
    log "[$STORY] ✅ COMPLETE"
else
    err=$(echo "$commit" | jq -r '.error // "unknown"' 2>/dev/null || echo "unknown")
    update_progress "done" "done" "$auto_col" "done" "fail" "error"
    log "[$STORY] commit FAILED: $err"
fi

"$SCRIPTS" orchestrator-helper state-update "$STATE_FILE" \
    --set status=EXECUTION_COMPLETE \
    --set lastUpdated="$(date -u +%Y-%m-%dT%H:%M:%SZ)" >/dev/null
log "=== BATCH 3.15 COMPLETE ==="
