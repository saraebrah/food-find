# FoodFind frontend

Svelte 5 and SvelteKit browser application for the FoodFind FastAPI backend.

From this directory:

```sh
npm install
npm run dev
```

Run FastAPI on `127.0.0.1:8000`; the Vite development server proxies `/api` to it. Open <http://127.0.0.1:5173>.

Checks and builds:

```sh
npm run check
npm run test:unit -- --run
npx playwright install chromium
npm run test:e2e
npm run build
```

Automated tests mock or intercept FoodFind API responses and do not contact Google.
