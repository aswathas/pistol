# pistol-web

Astro single-page chat UI for pistol. Static build, no SSR.

Built by `npm run build`. Output in `dist/`. FastAPI (`packages/pistol-core/src/pistol/chat_app.py`) serves `dist/index.html` from `/` and `dist/_astro/*` from `/_astro/*`.

The HTML calls `http://127.0.0.1:8000/api/chat` (CORS open on `/api/*`).
