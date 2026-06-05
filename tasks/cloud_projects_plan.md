# Cloud Projects — File Explorer Home

Authenticated users land on a flat file-explorer instead of the demo auto-load.
Logged-out behavior is unchanged. Saving a project is an explicit action on /job
after processing completes.

## Data model

`projects` table (new `web/db/projects.sql`):

- `id` text PK (uuid)
- `user_id` text FK → users(id) ON DELETE CASCADE
- `name` text NOT NULL
- `dxf_blob_url` text NOT NULL
- `dxf_filename` text NOT NULL
- `dxf_size_bytes` bigint
- `source_units` text NOT NULL
- `layer_mapping` jsonb NOT NULL
- `result` jsonb NOT NULL  (full ProcessResult — geometry + artifacts URLs + warnings)
- `view_mode` text NOT NULL DEFAULT 'plan'
- `created_at` timestamptz DEFAULT now()
- `updated_at` timestamptz DEFAULT now()

Index on `user_id`.

## Server

- [ ] `web/src/lib/db.ts` — shared Neon Pool, plus `query<T>()` helper
- [ ] `web/src/auth.ts` — import pool from `db.ts` (remove its own pool)
- [ ] `web/src/app/api/projects/route.ts` — GET (list) + POST (create)
- [ ] `web/src/app/api/projects/[id]/route.ts` — GET (load) + DELETE
  - Use `await context.params` (Next 16 async params)
  - All routes 401 if no session

## Client API

- [ ] Extend `web/src/lib/api.ts` with `listProjects`, `saveProject`,
      `getProject`, `deleteProject`.
- [ ] Add `ProjectSummary` and `ProjectRecord` types to `lib/types.ts`.

## UI

- [ ] `web/src/app/page.tsx` → server component. Branch on session:
      - authenticated AND not `?upload=1` AND not `?expired=1` → `<ProjectExplorer />`
      - else → `<UploadFlow />` (existing client code, extracted unchanged)
- [ ] `web/src/components/UploadFlow.tsx` — extracted from current page.tsx
- [ ] `web/src/components/ProjectExplorer.tsx` — flat list view:
      - header row: `NAME | MODIFIED | SIZE`
      - first row: `[+] Upload new project` → navigates to `/?upload=1`
      - project rows: click to open, hover reveals delete (×)
      - empty state row: `(empty — drop a .dxf here)` with whole-table drop zone
- [ ] `web/src/app/job/page.tsx`:
      - On mount, if `sessionStorage.openedProject` is set, load that result
        directly instead of calling `/api/process`. Keep `processParams` path
        for the normal upload flow.
      - Keep `blob_url`, `filename`, `mapping`, `source_units` in state after
        process so the Save button can submit them.
      - Add `<SaveProjectButton />` overlay on the ResultsView container, and a
        copy in the no-geometry fallback. Hidden when `!session`.

## Out of scope (not asked)

- Rename. Folder hierarchy. Sharing. Search. Sorting.

## Verification

- [ ] Logged-out: visiting `/` still auto-loads Demo 3 (no regression).
- [ ] Logged-in fresh account: `/` shows empty explorer with drop zone.
- [ ] Drop DXF on empty state → goes through upload flow → process → can Save.
- [ ] After Save, navigate back to `/` and see the project in the list.
- [ ] Click the project row → loads result without re-calling `/api/process`.
- [ ] Delete row → row disappears, project gone from DB.
