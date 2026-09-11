# GKT / LAB 001 — Roast My Bio (AI)

This is the AI-powered replacement for the old GKT website.

## Stack

- Static frontend: HTML + CSS + JavaScript
- AI endpoint: Cloudflare Pages Function
- Model: Google Gemini 2.5 Flash-Lite
- No database
- No login
- Bio is sent to the AI endpoint only when the user presses ROAST IT
- Local fallback keeps the product usable if the AI endpoint is unavailable

## Folder structure

```text
GKT-Roast-My-Bio-AI/
├── index.html
├── styles.css
├── app.js
├── functions/
│   └── api/
│       └── roast.js
└── README.md
```

## Deploy on Cloudflare Pages

1. Create a GitHub repository and upload these files.
2. In Cloudflare, create a Pages project from the GitHub repository.
3. Framework preset: None.
4. Build command: leave empty.
5. Build output directory: `/` (the repository root).
6. Deploy.
7. In the Pages project, open Settings → Variables and Secrets.
8. Add a secret named:

```text
GEMINI_API_KEY
```

9. Paste your Google Gemini API key as the secret value.
10. Redeploy.

The frontend calls:

```text
/api/roast
```

The API key is used only by the server-side Pages Function. It is NOT placed in `app.js`.

## Getting a Gemini API key

Create the key in Google AI Studio:

https://aistudio.google.com/

The Gemini Developer API currently has a free tier for selected models, including Gemini 2.5 Flash-Lite. Free-tier availability and limits can change, so check Google's current pricing/rate-limit pages before launching at scale.

## Local development

A plain `python -m http.server` will show the frontend but cannot execute the `/api/roast` Pages Function.

For the full local stack, use Cloudflare Wrangler:

```bash
npm install -g wrangler
wrangler pages dev .
```

Then open the local URL Wrangler provides.

For local secrets, create `.dev.vars`:

```text
GEMINI_API_KEY=your_key_here
```

Do NOT commit `.dev.vars`.

## Important

Never put `GEMINI_API_KEY` inside `app.js`, `index.html`, or any browser-delivered file.

## Product roadmap

LAB 001 can later add:

- Savage Mode
- Different roast personalities
- Shareable result URLs
- OG preview images
- Anonymous usage limits
- Premium unlimited mode
- Stripe/payment integration
- Analytics
- A gallery of the funniest roasts
