# Source inspection and merge audit

## Uploaded archives inspected

- `GKT.zip` — ZIP integrity verified; 97 archive entries; 9 non-Git source/assets files.
- `find-your-7-twins.zip` — ZIP integrity verified; 25,173 archive entries. The archive contains a large checked-in Windows virtual environment; that environment was inspected as packaging/runtime evidence but excluded from the production deliverable. The actual application source/assets comprise 12 non-venv/non-bytecode files.

## GKT production source identified

The supplied GKT repository contains Git history. `HEAD` points at commit `79168d8` and the working tree has a one-line favicon change relative to that commit. The current working-tree `index.html` was treated as the production homepage because it is the repository's tracked `index.html`; the other HTML files (`test.html`, `test3.html`, `test5.html`, `test7.html`, `gkt-index.html`, and `cv.html`) were retained as supplied rather than silently replacing the homepage with a test variant.

The GKT site is a single static HTML application with inline CSS/JavaScript and Three.js, plus `CNAME` and the existing favicon asset.

## Find Your 7 Twins source inspected

Actual application source inspected:

- `backend/main.py` — FastAPI app, auth endpoints, profile, upload handling, twin ranking, swipes, matches, password reset, email delivery and health/root endpoints.
- `backend/database.py` — users, swipes, password-reset tokens, embedding storage and atomic reset transaction logic.
- `backend/face_engine.py` — InsightFace `buffalo_l`, CPU execution and single-face embedding extraction.
- `backend/auth.py` — bcrypt password hashing and JWT authentication.
- `backend/requirements.txt` — original dependency set inspected and reconciled with the actual imports.
- `frontend/index.html` — complete auth, reset, discovery, swipe, match and profile UI/JS inspected.
- `backend/data/twins.db` — schema and row counts inspected; it contains real user records and embeddings, so it is excluded from the production package.
- `backend/data/.secret_key` — inspected as a local secret and excluded from the production package.
- `backend/uploads/*` — four real uploaded images inspected for file validity/dimensions; excluded from the public production package.

## Existing password-reset behavior confirmed

The original frontend already had the requested fixed flow: an explicit JavaScript `submit` listener, `event.preventDefault()`, in-page success/error messages, URL token removal using `history.replaceState`, errors left visible, and a delayed return to login after success. That implementation was preserved rather than replaced with an inline-only handler.

## Integration changes

- Added the real Twins frontend under `gkt/twins/`.
- Added a path-safe `config.js` instead of retaining the original localhost API URL.
- Added GKT navigation/CTA links to `/twins/` without replacing unrelated GKT sections.
- Corrected the supplied current GKT favicon reference from `cv` to the favicon file that already exists in the supplied repository.
- Refactored persistence to support PostgreSQL in production while retaining SQLite compatibility for local development.
- Added a SQLite-to-PostgreSQL migration tool.
- Added configurable persistent storage for uploads and InsightFace model cache.
- Added upload size/type/content validation and safe generated filenames.
- Added authenticated handling for non-discoverable profile photos and restricted public user enumeration.
- Kept email addresses out of public user/twin/match responses.
- Added production CORS configuration.
- Added the requested face-similarity disclaimer and privacy/consent experience.
- Added production Docker/Render deployment configuration.

## Excluded runtime junk/secrets

The production ZIP intentionally excludes `.git`, the Windows `venv`, Python bytecode, the local SQLite database, the local JWT secret file, real user uploads, and caches. These are not required to reproduce the application and should not be published.
