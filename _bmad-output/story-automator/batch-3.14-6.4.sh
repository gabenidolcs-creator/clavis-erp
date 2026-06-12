#!/usr/bin/env bash
# Batch orchestration: stories 3.14 → 6.4
# Models: Sonnet (create/dev/auto), Haiku (review)
# Resume after system restart — 3.14 dev code already in working tree (uncommitted)
set -uo pipefail

SCRIPTS=".claude/skills/bmad-story-automator/scripts/story-automator"
STATE_FILE="_bmad-output/story-automator/orchestration-1-20260606-103602.md"
EPIC="1"
LOG_FILE="_bmad-output/story-automator/batch-3.14-6.4-$(date +%Y%m%d-%H%M%S).log"

STORIES=(3.14 4.1 4.2 4.3 4.4 4.5 4.6 5.1 5.2 5.3 5.4 6.1 6.2 6.3 6.4)
TOTAL=${#STORIES[@]}

log() { local ts; ts=$(date -u +%Y-%m-%dT%H:%M:%SZ); echo "[$ts] $1" | tee -a "$LOG_FILE"; }

update_progress() {
    local story_id="$1" c="$2" d="$3" a="$4" r="$5" g="$6" s="$7"
    local tmp; tmp=$(mktemp)
    sed "s/^| ${story_id} |.*$/| ${story_id} | ${c} | ${d} | ${a} | ${r} | ${g} | ${s} |/" \
        "$STATE_FILE" > "$tmp" && mv "$tmp" "$STATE_FILE"
}

get_title() {
    python3 -c "
import json
with open('_bmad-output/story-automator/agents/agents-orchestration-1-20260606-103602.md') as f:
    content = f.read()
js = content[content.index('\`\`\`json\n')+8:content.rindex('\n\`\`\`')]
data = json.loads(js)
for s in data['stories']:
    if s['storyId'] == '$1': print(s['title']); break
" 2>/dev/null || echo "Story $1"
}

resolve_agent() {
    local task="$1" story_id="$2"
    local result; result=$("$SCRIPTS" orchestrator-helper agents-resolve \
        --state-file "$STATE_FILE" --story "$story_id" --task "$task")
    primary_agent=$(echo "$result" | jq -r '.primary')
    fallback_agent=$(echo "$result" | jq -r '.fallback')
    primary_model=$(echo "$result" | jq -r '.model // ""')
    [ "$fallback_agent" = "false" ] && fallback_agent=""
}

spawn_and_monitor() {
    local task="$1" story_id="$2" agent="$3" model="$4"
    local built_cmd session result
    if [ -n "$model" ]; then
        built_cmd=$("$SCRIPTS" tmux-wrapper build-cmd "$task" "$story_id" \
            --agent "$agent" --model "$model" --state-file "$STATE_FILE")
    else
        built_cmd=$("$SCRIPTS" tmux-wrapper build-cmd "$task" "$story_id" \
            --agent "$agent" --state-file "$STATE_FILE")
    fi
    session=$("$SCRIPTS" tmux-wrapper spawn "$task" "$EPIC" "$story_id" \
        --agent "$agent" --command "$built_cmd")
    result=$("$SCRIPTS" monitor-session "$session" --json --agent "$agent" || true)
    "$SCRIPTS" tmux-wrapper kill "$session" 2>/dev/null || true
    echo "$result"
}

spawn_review() {
    local story_id="$1" cycle="$2" agent="$3" model="$4"
    local built_cmd session result
    if [ -n "$model" ]; then
        built_cmd=$("$SCRIPTS" tmux-wrapper build-cmd review "$story_id" \
            --agent "$agent" --model "$model" --state-file "$STATE_FILE")
    else
        built_cmd=$("$SCRIPTS" tmux-wrapper build-cmd review "$story_id" \
            --agent "$agent" --state-file "$STATE_FILE")
    fi
    session=$("$SCRIPTS" tmux-wrapper spawn review "$EPIC" "$story_id" \
        --agent "$agent" --cycle "$cycle" --command "$built_cmd")
    result=$("$SCRIPTS" monitor-session "$session" --json --agent "$agent" \
        --workflow review --story-key "$story_id" --state-file "$STATE_FILE" || true)
    "$SCRIPTS" tmux-wrapper kill "$session" 2>/dev/null || true
    echo "$result"
}

# ================================================================
log "=== BATCH RUN STARTED: $TOTAL stories (3.14→6.4) ==="
log "=== Models: Sonnet create/dev/auto | Haiku review ==="
log "=== NOTE: 3.14 dev code already in working tree from prior run ==="

for idx in "${!STORIES[@]}"; do
    story_id="${STORIES[$idx]}"
    n=$((idx + 1))
    log "--- Story $n/$TOTAL: $story_id ---"

    "$SCRIPTS" orchestrator-helper state-update "$STATE_FILE" \
        --set currentStory="$story_id" --set currentStep=step-03-execute \
        --set status=IN_PROGRESS \
        --set lastUpdated="$(date -u +%Y-%m-%dT%H:%M:%SZ)" >/dev/null

    # --- A. CREATE ---
    verify=$("$SCRIPTS" orchestrator-helper verify-step create "$story_id" \
        --state-file "$STATE_FILE" 2>/dev/null || echo '{"verified":false}')
    if echo "$verify" | grep -q '"verified":true'; then
        log "[$story_id] create: SKIP (exists)"
        update_progress "$story_id" "done" "⏳" "⏳" "⏳" "⏳" "in-progress"
    else
        resolve_agent "create" "$story_id"
        log "[$story_id] create: START (model=${primary_model:-default})"
        create_ok=false
        for attempt in 1 2 3 4 5; do
            result=$(spawn_and_monitor "create" "$story_id" "$primary_agent" "$primary_model")
            verify=$("$SCRIPTS" orchestrator-helper verify-step create "$story_id" \
                --state-file "$STATE_FILE" 2>/dev/null || echo '{"verified":false}')
            if echo "$verify" | grep -q '"verified":true'; then
                create_ok=true; break
            fi
            log "[$story_id] create attempt $attempt failed"
            [ $attempt -lt 5 ] && sleep 30
        done
        if $create_ok; then
            update_progress "$story_id" "done" "⏳" "⏳" "⏳" "⏳" "in-progress"
            log "[$story_id] create: DONE"
        else
            update_progress "$story_id" "fail" "⏳" "⏳" "⏳" "⏳" "error"
            log "[$story_id] create: FAILED - skipping"
            continue
        fi
    fi

    # --- B. DEV ---
    resolve_agent "dev" "$story_id"
    log "[$story_id] dev: START (model=${primary_model:-default})"
    dev_ok=false
    for attempt in 1 2 3 4 5; do
        result=$(spawn_and_monitor "dev" "$story_id" "$primary_agent" "$primary_model")
        final=$(echo "$result" | jq -r '.final_state // "unknown"')
        if [ "$final" = "completed" ] || [ "$final" = "success" ]; then
            dev_ok=true; break
        fi
        log "[$story_id] dev attempt $attempt failed (state=$final)"
        [ $attempt -lt 5 ] && sleep 30
    done
    if $dev_ok; then
        update_progress "$story_id" "done" "done" "⏳" "⏳" "⏳" "in-progress"
        log "[$story_id] dev: DONE"
    else
        update_progress "$story_id" "done" "fail" "⏳" "⏳" "⏳" "error"
        log "[$story_id] dev: FAILED - skipping"
        continue
    fi

    # --- C. AUTO (non-blocking) ---
    resolve_agent "auto" "$story_id"
    log "[$story_id] auto: START (model=${primary_model:-default})"
    auto_result=$(spawn_and_monitor "auto" "$story_id" "$primary_agent" "$primary_model" || true)
    auto_state=$(echo "$auto_result" | jq -r '.final_state // "unknown"')
    if [ "$auto_state" = "completed" ] || [ "$auto_state" = "success" ]; then
        update_progress "$story_id" "done" "done" "done" "⏳" "⏳" "in-progress"
        log "[$story_id] auto: DONE"
    else
        update_progress "$story_id" "done" "done" "skip" "⏳" "⏳" "in-progress"
        log "[$story_id] auto: SKIP (state=$auto_state, non-blocking)"
    fi

    # --- D. REVIEW LOOP ---
    resolve_agent "review" "$story_id"
    log "[$story_id] review: START (model=${primary_model:-default})"
    review_ok=false
    for cycle in 1 2 3 4 5; do
        result=$(spawn_review "$story_id" "$cycle" "$primary_agent" "$primary_model")
        final=$(echo "$result" | jq -r '.final_state // "unknown"')
        if [ "$final" = "completed" ]; then
            review_ok=true; break
        fi
        log "[$story_id] review cycle $cycle: $final"
        [ $cycle -lt 5 ] && sleep 15
    done
    if $review_ok; then
        update_progress "$story_id" "done" "done" "$(grep "^| ${story_id} |" "$STATE_FILE" | awk -F'|' '{print $5}' | tr -d ' ')" "done" "⏳" "in-progress"
        log "[$story_id] review: DONE"
    else
        update_progress "$story_id" "done" "done" "$(grep "^| ${story_id} |" "$STATE_FILE" | awk -F'|' '{print $5}' | tr -d ' ')" "fail" "⏳" "error"
        log "[$story_id] review: FAILED (max cycles)"
        continue
    fi

    # --- E. COMMIT ---
    title=$(get_title "$story_id")
    log "[$story_id] commit: '$title'"
    commit=$("$SCRIPTS" commit-story --repo "." --story "$story_id" --title "$title" 2>&1 || echo '{"ok":false,"error":"commit_failed"}')
    if echo "$commit" | grep -q '"ok":true'; then
        update_progress "$story_id" "done" "done" "done" "done" "done" "done"
        echo "- **[$(date -u +%Y-%m-%dT%H:%M:%SZ)]** Story ${story_id}: ✅ complete" >> "$STATE_FILE"
        log "[$story_id] ✅ COMPLETE"
    else
        err=$(echo "$commit" | jq -r '.error // "unknown"' 2>/dev/null || echo "unknown")
        update_progress "$story_id" "done" "done" "done" "done" "fail" "error"
        log "[$story_id] commit FAILED: $err"
    fi

    "$SCRIPTS" orchestrator-helper state-update "$STATE_FILE" \
        --set lastUpdated="$(date -u +%Y-%m-%dT%H:%M:%SZ)" >/dev/null
done

log "=== BATCH RUN COMPLETE ==="
"$SCRIPTS" orchestrator-helper state-update "$STATE_FILE" \
    --set status=EXECUTION_COMPLETE \
    --set lastUpdated="$(date -u +%Y-%m-%dT%H:%M:%SZ)" >/dev/null
