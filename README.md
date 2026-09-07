# GKT + Find Your 7 Twins — production package

This package was assembled from the actual uploaded GKT repository and the actual uploaded Find Your 7 Twins source. The existing GKT production `index.html` remains the base site; Find Your 7 Twins is added under `gkt/twins/`.

## Final web layout

- GKT homepage: `https://gkt.com.np/`
- Find Your 7 Twins: `https://gkt.com.np/twins/`
- Backend: separate HTTPS FastAPI service (Render Blueprint included)
- Database: PostgreSQL in production
- Persistent photos/model cache: Render persistent disk
- Face model: InsightFace `buffalo_l`

## Important

`gkt/twins/config.js` intentionally does not contain a made-up backend URL. After the Render API is created, put its real HTTPS URL into that file as `API_BASE` and publish the GKT/twins files.

The original local SQLite database, uploaded user photos, `.secret_key`, virtual environment, Git metadata, caches, and Python bytecode are intentionally not included in the production package.


## Free Render mode

The current no-cost deployment removes server-side InsightFace/ONNX inference. Face embeddings are generated in the browser and the lightweight FastAPI service performs storage, authentication, and cosine-similarity ranking. This is suitable for a demo/test deployment on Render Free, whose web services have 512 MB RAM and an ephemeral filesystem. It is not durable production hosting.
