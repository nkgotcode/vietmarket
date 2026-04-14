# VietMarket D1 Nomad Runtime Recovery Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Recover the Phase 9 supervisor daily/evaluation Nomad runtime so forced periodic child jobs reach healthy dead/complete outcomes on real infrastructure, not just registered parent schedules.

**Architecture:** Treat this as a live ops recovery across three layers: Nomad server/scheduler state, OptiPlex client/runtime state, and the bind-mounted repo actually executed inside Nomad containers. Compare the failing supervisor children against known-good VietMarket batch jobs, then sync/fix the real runtime repo and job specs, re-register, force, and verify child alloc success with fresh logs.

**Tech Stack:** Nomad, Docker, SSH to OptiPlex, Python supervisor jobs, bind-mounted repo at /home/itsnk/vietmarket, VietMarket repo at /Users/lenamkhanh/Coding/vietmarket.

---

### Task 1: Capture fresh evidence for the failing supervisor children

**Files:**
- Reference: `deploy/nomad/jobs/vietmarket-supervisor-daily-cycle.nomad.hcl`
- Reference: `deploy/nomad/jobs/vietmarket-supervisor-evaluation-cycle.nomad.hcl`
- Reference: `docs/operations/phase9-supervisor-orchestration-runbook.md`

**Step 1: Inspect parent and latest child jobs**
Run: `nomad job status vietmarket-supervisor-daily-cycle && nomad job status vietmarket-supervisor-evaluation-cycle && nomad job status vietmarket-supervisor-daily-cycle/<child> && nomad job status vietmarket-supervisor-evaluation-cycle/<child>`
Expected: parents remain periodic/running; child jobs expose alloc IDs and actual failed/complete state.

**Step 2: Inspect alloc status and logs**
Run: `nomad alloc status <alloc-id> && nomad alloc logs <alloc-id> && nomad alloc logs -stderr <alloc-id>`
Expected: exact runtime failure cause, not just parent summary.

**Step 3: Inspect OptiPlex client state/logs**
Run: `ssh itsnk@100.83.150.39 'systemctl is-active nomad docker; journalctl -u nomad -n 120 --no-pager; docker ps --format ...'`
Expected: whether client is healthy, whether alloc GC explains old 404s, and whether Docker launches are normal.

### Task 2: Compare supervisor jobs with known-good VietMarket batch jobs

**Files:**
- Reference: `deploy/nomad/jobs/vietmarket-corporate-actions-ingest.nomad.hcl`
- Reference: `deploy/nomad/jobs/vietmarket-derived-market-sync.nomad.hcl`
- Reference: `deploy/nomad/jobs/vietmarket-vietstock-fetch-timescale.nomad.hcl`
- Reference: `deploy/nomad/jobs/vietmarket-symbols-sync.nomad.hcl`

**Step 1: Inspect known-good parent/child status**
Run: `nomad job status <known-good-job>` for each target.
Expected: child jobs are routinely dead/complete or currently running with normal alloc lifecycle.

**Step 2: Compare task config patterns**
Run: inspect HCL plus `nomad job inspect <job>` output.
Expected: identify working runtime assumptions such as bind mounts, command style, env propagation, and exit-code behavior.

### Task 3: Inspect the actual bind-mounted OptiPlex repo, not just local files

**Files:**
- Modify if needed: `/home/itsnk/vietmarket/packages/supervisor/...` via sync from local repo
- Modify if needed: `/home/itsnk/vietmarket/deploy/nomad/jobs/vietmarket-supervisor-*.nomad.hcl`

**Step 1: Compare local patched files with OptiPlex runtime copies**
Run: `ssh itsnk@100.83.150.39 'sed -n ... /home/itsnk/vietmarket/packages/supervisor/...` for the patched entrypoints.
Expected: discover drift if OptiPlex still has stale pre-bootstrap files.

**Step 2: Sync the real runtime repo**
Run: `rsync -a ... /Users/lenamkhanh/Coding/vietmarket/packages/supervisor/ itsnk@100.83.150.39:/home/itsnk/vietmarket/packages/supervisor/` plus any required job-spec sync.
Expected: OptiPlex bind mount matches the verified local code.

### Task 4: Fix runtime/job-spec issues and re-register jobs

**Files:**
- Modify: `deploy/nomad/jobs/vietmarket-supervisor-daily-cycle.nomad.hcl`
- Modify: `deploy/nomad/jobs/vietmarket-supervisor-evaluation-cycle.nomad.hcl`

**Step 1: Apply minimal runtime-hardening changes**
Possible changes: use `bash -lc 'cd /src && python3 ...'` if needed, avoid masked/derived PG_URL hacks, keep bind mount, preserve Telegram env.

**Step 2: Validate job specs**
Run: `nomad job plan deploy/nomad/jobs/vietmarket-supervisor-daily-cycle.nomad.hcl` and same for evaluation.
Expected: clean plan output with intended diff only.

**Step 3: Re-register**
Run: `nomad job run deploy/nomad/jobs/vietmarket-supervisor-daily-cycle.nomad.hcl` and same for evaluation.
Expected: parents updated successfully.

### Task 5: Force one-shot runs until the child jobs complete successfully

**Files:**
- Reference only: Nomad child jobs and alloc logs

**Step 1: Force new child runs**
Run: `nomad job periodic force vietmarket-supervisor-daily-cycle` and `nomad job periodic force vietmarket-supervisor-evaluation-cycle`
Expected: new child job IDs returned.

**Step 2: Verify child completion end-to-end**
Run: `nomad job status <new-child>`, `nomad alloc status <new-alloc>`, `nomad alloc logs <new-alloc>`, and DB/app verification scripts if relevant.
Expected: child summary shows complete, alloc exit code 0, and stdout payload reports `ok: true` or equivalent success result.

### Task 6: Record final evidence

**Files:**
- Update if useful: `docs/operations/phase9-supervisor-orchestration-runbook.md`

**Step 1: Capture final comparison snapshot**
Collect: parent status, new child IDs, alloc IDs, exit codes, and any client-log evidence explaining the old unknown-allocation state.

**Step 2: Report remaining gaps only if verified**
If something still fails, report exact command output and blocking cause instead of a success claim.
