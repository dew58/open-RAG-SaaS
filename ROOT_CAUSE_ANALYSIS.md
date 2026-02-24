# Root Cause Analysis — RAG SaaS Production Issues

**Date:** 2025-02-22  
**Scope:** Document upload, chat freezing, authentication, Docker/environment

---

## Executive Summary

| Issue | Root Cause | Fix |
|-------|------------|-----|
| Chat freezing | Frontend sent `query`, backend expected `question` → 422 validation error | Frontend sends `question`; backend accepts both |
| Documents not appearing | Frontend expected array; API returns `{ total, page, page_size, items }` | Extract `items` in API layer; use `original_filename`, `file_size_bytes`, `status` |
| Document upload intermittent | Content-Type override + no token persistence + refresh broken | FormData Content-Type fix; auth persistence; refresh token flow |
| Auth instability | No refresh_token storage; setAuth cleared token on /auth/me; no persistence | Store refresh_token; preserve tokens on /auth/me; Zustand persist |

---

## Issue 1 — Document Upload / List

### Root Causes

1. **Response shape mismatch**
   - Backend `GET /documents` returns `{ total, page, page_size, items }`.
   - Frontend used `res.data` as if it were an array and called `documents?.filter(...)`.
   - `{}.filter` is undefined → runtime error or empty list.

2. **Field name mismatch**
   - Backend `DocumentResponse` uses `original_filename` and `file_size_bytes`.
   - Frontend used `doc.filename` and `doc.size` → undefined.

3. **Document status**
   - Frontend always showed "Indexed" regardless of `status`.
   - Documents in `processing` or `failed` looked incorrect.

4. **Content-Type for multipart**
   - Default `Content-Type: application/json` applied to FormData.
   - Server could not parse multipart uploads correctly.

### Fixes Applied

- `documentApi.list()` now returns `res.data.items ?? []`.
- Documents page uses `doc.original_filename ?? doc.filename` and `doc.file_size_bytes ?? doc.size`.
- Status display shows `indexed`, `processing`, or `failed`.
- Axios interceptor removes `Content-Type` when body is FormData so the browser sets it correctly.

---

## Issue 2 — Chat Freezing

### Root Cause

- Backend `ChatQueryRequest` expects `question`.
- Frontend sent `{ query }`.
- FastAPI returns 422: `body.question → Field required`.
- Loading state stayed on because the mutation error path did not surface feedback; UI appeared frozen.

### Fixes Applied

- Frontend sends `{ question: query }`.
- Backend added `@model_validator` so `query` is accepted as alias for `question`.
- Chat mutation has `onError` that surfaces errors and clears loading state.

---

## Issue 3 — Authentication Audit

### Root Causes

1. **Refresh token never stored**
   - Login/register returned `access_token` and `refresh_token`, but only `access_token` was stored.
   - 401 interceptor called `/auth/refresh` with empty body; backend expects `{ refresh_token }`.
   - Refresh always failed → user logged out on any 401.

2. **Token cleared on /auth/me**
   - `setAuth(response.data, "")` overwrote token with `""`.
   - After init, subsequent requests had `Authorization: Bearer ` → 401.

3. **No token persistence**
   - Zustand state was in memory only.
   - Page reload cleared tokens → immediate logout.

4. **Backend login/register**
   - `TokenResponse` returns `access_token`, `refresh_token`, `expires_in` — no `user`.
   - Frontend called `setAuth(user, access_token)` with undefined `user`.

### Fixes Applied

- Auth store extended with `refreshToken` and Zustand `persist` middleware (partialize: `accessToken`, `refreshToken`).
- Login/register store both tokens, then call `/auth/me` to populate `user`.
- AuthProvider `/auth/me` success: `setAuth(user, currentAccessToken, currentRefreshToken)` (tokens preserved).
- Refresh interceptor sends `{ refresh_token }` and stores both new tokens on success.

---

## Issue 4 — Docker & Environment

### Validation

- Volumes: `chroma_data`, `upload_data`, `postgres_data`, `logs_data` — correct.
- `JWT_SECRET_KEY` and `SECRET_KEY` come from `.env`; docker-compose uses `${JWT_SECRET_KEY:?}` — validated.
- CORS: `.env` `CORS_ORIGINS=["http://localhost:5173","http://localhost"]` matches Vite dev server.
- Hot reload: `- ./app:/app/app:ro` — read-only; no overwrite of secrets.
- Migrate container shares `JWT_SECRET_KEY` and `SECRET_KEY` from `.env`.

### Recommendations

1. **Stable JWT secrets across restarts**
   - Ensure `.env` is loaded and not overridden.
   - Avoid `SECRET_KEY` / `JWT_SECRET_KEY` defaults that differ between containers.

2. **CORS**
   - Ensure production `CORS_ORIGINS` matches frontend origin(s).

3. **Redis**
   - `.env` `REDIS_PASSWORD` should match `docker-compose`; adjust default if needed.

---

## Architectural Improvements

1. **Shared API schema**
   - Add OpenAPI generation and, if possible, frontend type generation (e.g. from OpenAPI).

2. **Error handling**
   - Surface 422/4xx validation errors in UI and reset loading states.

3. **Logging**
   - Log `client_id` on document list/upload and chat for debugging tenant isolation.

4. **Background indexing**
   - Consider Celery/ARQ for production instead of `asyncio.create_task`.

5. **Refresh token**
   - For production, use httpOnly cookies for refresh tokens.

---

## Files Changed

| File | Change |
|------|--------|
| `frontend/src/api/index.ts` | Chat `question`, document list `items`, upload timeout |
| `frontend/src/lib/auth-store.ts` | `refreshToken`, `persist`, updated `setAuth` |
| `frontend/src/lib/axios.ts` | FormData Content-Type handling, refresh with `refresh_token` |
| `frontend/src/providers/AuthProvider.tsx` | Preserve tokens on /auth/me; login/register flow |
| `frontend/src/pages/DocumentsPage.tsx` | Use `original_filename`, `file_size_bytes`, `status` |
| `frontend/src/pages/ChatPage.tsx` | Error handling and display |
| `frontend/src/types/auth.ts` | `refreshToken`, `setAuth` signature |
| `app/schemas/schemas.py` | `query` alias for `question` |
