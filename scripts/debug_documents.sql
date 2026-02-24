-- Documents empty list – debugging queries
-- Run from project root:
--   Get-Content scripts/debug_documents.sql | docker compose exec -T postgres psql -U postgres -d rag_saas
-- Or: docker compose exec postgres psql -U postgres -d rag_saas
--     then paste each SELECT block.

\echo '=== 1. Total documents (all, including soft-deleted) ==='
SELECT COUNT(*) AS total FROM documents;

\echo ''
\echo '=== 2. Documents per client (non-deleted only) ==='
SELECT client_id, COUNT(*) AS doc_count
FROM documents
WHERE deleted_at IS NULL
GROUP BY client_id;

\echo ''
\echo '=== 3. All clients and their document counts ==='
SELECT c.id AS client_id, c.name, c.slug,
       COALESCE(doc_counts.cnt, 0) AS doc_count
FROM clients c
LEFT JOIN (
  SELECT client_id, COUNT(*) AS cnt
  FROM documents
  WHERE deleted_at IS NULL
  GROUP BY client_id
) doc_counts ON c.id = doc_counts.client_id
ORDER BY doc_count DESC;

\echo ''
\echo '=== 4. Latest 10 documents (id, client_id, status, deleted_at, original_filename) ==='
SELECT id, client_id, status, deleted_at, original_filename, created_at
FROM documents
ORDER BY created_at DESC
LIMIT 10;

\echo ''
\echo '=== 5. Soft-deleted documents per client ==='
SELECT client_id, COUNT(*) AS deleted_count
FROM documents
WHERE deleted_at IS NOT NULL
GROUP BY client_id;
