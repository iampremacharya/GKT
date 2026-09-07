# Find Your 7 Twins — GKT

The existing Find Your 7 Twins frontend is integrated under the GKT site at `/twins/`.

## Free deployment mode

Face detection and the 128-value face descriptor are generated in the visitor's browser using `@vladmandic/face-api`. The FastAPI backend only receives the descriptor plus the profile image needed to display discoverable profiles. This keeps the Render backend small enough for the free 512 MB instance.

The browser loads the face model library and model weights from version-pinned jsDelivr URLs. The model files are several MB, so the first face-analysis operation may take a little longer.

Set `API_BASE` in `config.js` to the real HTTPS URL of the deployed FastAPI backend. Do not commit backend secrets.

## Important free-tier limitation

Render Free web services have an ephemeral filesystem. Local SQLite data and uploaded profile images can disappear after a restart, redeploy, or idle spin-down. Render also documents that Free Postgres expires after 30 days. This mode is therefore for testing/demo use, not durable production hosting.

For a durable production deployment, move the database to managed PostgreSQL and put uploaded images in persistent/object storage, then the face model can also be moved back to a server-side inference service.
