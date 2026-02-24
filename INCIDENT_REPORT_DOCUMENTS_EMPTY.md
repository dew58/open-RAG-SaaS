# Incident Report: Documents Page Always Empty

## Executive Summary

The documents list API returns 200 with valid SQL but **0 rows** for the authenticated client. The most likely root cause is **no documents exist in the database for the current user's `client_id`**, or a **client_id mismatch** between the JWT and the documents table.

---

## 1. Multi-Tenant Filtering – Verified ✓

| Check | Status | Details |
|-------|--------|---------|
| JWT includes `client_id` | ✓ | `app/core/security.py`: `create_access_token(user_id, client_id, email)` |
| List endpoint uses `current_user.client_id` | ✓ | `documents.py:156` – `list_by_client(current_user.client_id, ...)` |
| Repository filters by `client_id` | ✓ | `repositories.py:185-187` – `WHERE documents.client_id == client_id` |
| Soft delete filter | ✓ | `deleted_at.is_(None)` in both count and list queries |

**Conclusion**: Backend filtering is correct. Empty results mean either:
- No rows exist for this `client_id`, or
- Documents have `deleted_at IS NOT NULL`

---

## 2. Document Creation Flow – Verified ✓

| Check | Status | Details |
|-------|--------|---------|
| Upload uses `current_user.client_id` | ✓ | `documents.py:55` – `client_id=current_user.client_id` |
| Commit before background task | ✓ | `documents.py:76` – `await db.commit()` |
| `deleted_at` default | ✓ | `SoftDeleteMixin` – nullable, no default (stays NULL) |
| Status default | ✓ | `status="pending"` in `DocumentRepository.create()` |
| Background task uses same session | ✓ | Separate `AsyncSessionLocal()` – no rollback of main request |

**Conclusion**: Documents are created with the correct `client_id`. No obvious creation-side bug.

---

## 3. Response Schema – Verified ✓

**Backend** (`app/schemas/schemas.py`):

```python
class DocumentListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[DocumentResponse]  # DocumentResponse has original_filename, NOT filename

class DocumentResponse(BaseModel):
    id: uuid.UUID
    original_filename: str   # <-- Backend uses this
    mime_type: str
    file_size_bytes: int
    status: str
    chunk_count: Optional[int]
    created_at: datetime
    uploaded_by_id: Optional[uuid.UUID]
```

**Frontend** (`frontend/src/api/index.ts`):

```ts
list: () => api.get('/documents').then(res => res.data.items ?? [])
```

Frontend correctly expects `{ items: [...] }` and falls back to `[]` when missing. **Response shape is correct.**

---

## 4. Frontend Rendering Logic – Bugs Found

### Bug A: DocumentsPage filter uses `doc.filename` (API returns `original_filename`)

`DocumentsPage.tsx:76-78`:

```ts
filteredDocs = documents?.filter((doc: any) =>
    doc.filename.toLowerCase().includes(searchTerm.toLowerCase())
) || [];
```

- API returns `original_filename`, not `filename`.
- If documents exist and `doc.filename` is undefined, `doc.filename.toLowerCase()` will throw.
- With empty `documents`, this code path is never hit, so the page shows empty without crashing.

**Fix**: Use `doc.original_filename ?? doc.filename` in the filter.

### Bug B: DashboardOverview wrong response parsing

`DashboardOverview.tsx:16`:

```ts
const { data: docs } = useQuery({ queryKey: ['documents'], queryFn: () => documentApi.list().then(res => res.data) });
```

- `documentApi.list()` returns the items array directly (`res.data.items ?? []`).
- So `res` is already the array; `res.data` is `undefined`.
- `docs` becomes `undefined` → `docs?.length` is always 0.

**Fix**: `documentApi.list()` already returns items; use it directly: `queryFn: () => documentApi.list()`.

---

## 5. Soft Delete – Verified ✓

- `list_by_client` uses `Document.deleted_at.is_(None)`.
- No automatic soft-delete on creation.
- Delete endpoint calls `doc_repo.soft_delete()` explicitly.

---

## 6. SQL Debug Queries (Run in psql or DB client)

```sql
-- 1. Count all documents (no filter)
SELECT id, client_id, status, deleted_at, original_filename, created_at
FROM documents
ORDER BY created_at DESC
LIMIT 20;

-- 2. Count per client
SELECT client_id, COUNT(*) AS doc_count
FROM documents
WHERE deleted_at IS NULL
GROUP BY client_id;

-- 3. Check if any documents exist at all
SELECT COUNT(*) FROM documents;

-- 4. Check soft-deleted documents
SELECT client_id, COUNT(*) AS deleted_count
FROM documents
WHERE deleted_at IS NOT NULL
GROUP BY client_id;

-- 5. Cross-reference: clients and their document counts
SELECT c.id, c.name, c.slug,
       (SELECT COUNT(*) FROM documents d WHERE d.client_id = c.id AND d.deleted_at IS NULL) AS doc_count
FROM clients c
ORDER BY doc_count DESC;
```

### How to get your JWT `client_id`

1. DevTools → Application → Local Storage → inspect `accessToken` (or from Network tab).
2. Decode at https://jwt.io.
3. Compare `client_id` in payload with `client_id` from query 2 or 5.
4. If they differ, documents belong to another tenant.

---

## 7. Docker / Persistence Checks

```bash
# Verify postgres volume exists
docker volume ls | grep postgres

# Check no -v on down (avoid data wipe)
docker compose down   # OK
docker compose down -v   # DANGEROUS – wipes volumes

# Inspect postgres container
docker compose ps
docker compose exec postgres psql -U <user> -d <db> -c "SELECT COUNT(*) FROM documents;"
```

- Ensure `DATABASE_URL` is the same in backend and migration runs.
- Ensure `POSTGRES_DATA` or equivalent volume is not recreated.

---

## 8. Root Cause Determination

| Hypothesis | How to Test | If True |
|------------|-------------|---------|
| **client_id mismatch** | Decode JWT, compare with `documents.client_id` | Same user for upload and list; fix auth/registration flow |
| **No documents uploaded** | Query 3 returns 0 | User needs to upload documents |
| **Documents under different client** | Query 5 shows docs for other clients only | Seed or migrate data, or re-upload as correct user |
| **All soft-deleted** | Query 4 shows rows | Restore or re-upload |
| **DB wiped** | Query 3 = 0, clients exist | Re-upload documents |
| **Response shape mismatch** | Network tab: `items` present but UI empty | Already ruled out; schema matches |

**Most likely root cause**: **No documents exist for the authenticated client's `client_id`** (first-time user, or DB reset, or documents created with a different tenant).

---

## 9. Exact Code Fixes Applied

### 9.1 DocumentsPage – filter by `original_filename`

```ts
// Before
filteredDocs = documents?.filter((doc: any) =>
    doc.filename.toLowerCase().includes(searchTerm.toLowerCase())
) || [];

// After
filteredDocs = documents?.filter((doc: any) =>
    (doc.original_filename ?? doc.filename ?? '').toLowerCase().includes(searchTerm.toLowerCase())
) || [];
```

### 9.2 DashboardOverview – correct document list parsing

```ts
// Before
const { data: docs } = useQuery({ queryKey: ['documents'], queryFn: () => documentApi.list().then(res => res.data) });

// After
const { data: docs } = useQuery({ queryKey: ['documents'], queryFn: () => documentApi.list() });
```

(Display logic already uses `docs?.length`, so no further changes needed.)

---

## 10. Prevention Strategy

1. **Add integration test**: Upload doc → List docs → Assert `items` contains the new doc.
2. **Add `total` to documentApi.list()** for pagination and debugging: `{ items, total }`.
3. **Health check**: Optional `/api/v1/debug/documents-count` (dev only) to verify DB state.
4. **Seed script**: Add sample documents for default tenant in dev/staging.
5. **Schema alignment**: Use a shared TypeScript type for `Document` that matches `DocumentResponse`.

---

## 11. Architectural Improvement

- **Consider returning full response in documentApi.list()**:
  ```ts
  list: (page = 1, pageSize = 20) =>
    api.get(`/documents?page=${page}&page_size=${pageSize}`).then(res => res.data);
  ```
  This gives `{ total, page, page_size, items }` for pagination and better UX (e.g. "Page 1 of 3").
