# Admin Console Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A web admin console at `/admin/` for review (with mandatory 视频号 info), shipping, event ops, and user flower adjustments.

**Architecture:** New admin endpoints in `app/routers/admin.py` backed by services; a static vanilla HTML/JS SPA in `server/admin/` mounted by FastAPI with `StaticFiles(html=True)`.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Alembic, pytest; vanilla JS (no build, no CDN).

**Spec:** `docs/superpowers/specs/2026-11-26-admin-console-design.md`

## Global Constraints

- All new endpoints under `/api/v1/admin`, guarded by `require_admin` (`X-Admin-Token`).
- Error copy: `请填写视频 token，或视频号 ID 与 feed_id`.
- Paginated admin lists return `{"items": [...], "total": n}`, `page` from 1, `page_size` default 20, max 100.
- Balance changes only via `ledger.apply_delta` under `lock_user`; admin adjust reason `admin_adjust`, growth 0.
- "Today" = `rules.today_start_utc()`.

## Review Focus

- Approve with only `finder_user_name` (no `feed_id`) → 400 (test in Task 1).
- Approve reusing values already stored on the submission (empty request fields) → allowed (Task 1).
- Admin adjust that would make balance negative → 400 `小红花余额不足`, nothing written (Task 3).
- `PATCH /admin/submissions/{id}` clearing token on an approved submission with no fallback → 400 (Task 1).
- Expired/wrong token in the browser → UI returns to login screen instead of silent failures (Task 4, manual).

---

### Task 1: Review requires 视频号 info + submission feed patch + paginated lists + stats

**Files:** Modify `app/services/submissions.py`, `app/routers/admin.py`, `app/schemas.py`; Test `tests/test_admin.py`; update `tests/*` and `scripts/smoke_api.py` callers that approve without feed info.

**Interfaces — Produces:**
- `ensure_feed_info(sub: Submission) -> None` (400 with the constant copy `FEED_INFO_REQUIRED`).
- `update_feed_info(db, submission_id, data: FeedPatch) -> Submission`.
- Schemas: `FeedPatch{finder_user_name?, feed_id?, feed_token?}`, `SubmissionPage{items, total}`, `OrderAdminOut(OrderOut + user_id, user_nickname)`, `OrderPage`, `StatsOut{pending_submissions, pending_shipments, users_today, flowers_today}`.
- `GET /admin/submissions?status=&q=&page=&page_size=` → `SubmissionPage`; `GET /admin/orders?status=&page=` → `OrderPage`; `GET /admin/stats`.

- [ ] Tests: `test_approve_requires_feed_info`, `test_approve_with_finder_only_rejected`, `test_approve_uses_stored_feed_info`, `test_patch_feed_info`, `test_patch_cannot_clear_approved`, `test_admin_lists_paginated`, `test_stats`.
- [ ] Implement; fix existing approve callers to pass `feed_token`.
- [ ] `uv run pytest` all green.

### Task 2: Admin events list + `featured` patch

**Files:** `app/routers/admin.py`, `app/schemas.py` (`EventAdminOut = EventOut + featured, sort_order`; `EventPatch.featured`). Test `tests/test_admin.py::test_admin_events`.

### Task 3: Users, ledger, flower adjust (+ ledger note)

**Files:** `app/models.py` (`FlowerLedger.note: str|None String(200)`), `alembic/versions/0003_ledger_note.py`, `app/schemas.py` (`LedgerEntryOut.note`, `AdminUserOut = UserOut + openid`, `AdjustIn{delta: int != 0, |delta| <= 100000, note: 1..200}`), `app/routers/admin.py`.
- `GET /admin/users?q=&page=` (q numeric → id match OR nickname ilike), `GET /admin/users/{id}/ledger?page=`, `POST /admin/users/{id}/flowers`.
- Tests: `test_admin_users_search`, `test_admin_adjust_flowers`, `test_admin_adjust_negative_balance`, `test_admin_adjust_requires_note`.

### Task 4: Static console

**Files:** Create `server/admin/index.html`, `server/admin/app.js`, `server/admin/app.css`; mount in `app/main.py` at `/admin` (`StaticFiles(directory=ADMIN_DIR, html=True)`); `.claude` nothing. Docs: `docs/design.md` admin table, `server/README.md`.
- Verify in the browser pane: login, each tab loads, approve without token shows the 400 copy, approve with token succeeds.
