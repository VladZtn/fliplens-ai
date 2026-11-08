# FlipLens deployment

## 1. Push this folder to GitHub

Never commit `backend/.env` or `frontend/.env.local`.

## 1b. Get eBay API keys (needed for live prices)

1. Sign up at https://developer.ebay.com and create a **Production** keyset.
2. Copy the **App ID (Client ID)** and **Cert ID (Client Secret)**.
3. Set `PRICING_PROVIDER=ebay`, `EBAY_CLIENT_ID`, `EBAY_CLIENT_SECRET` on the backend.

Without these keys the API uses mock prices, and the site shows
"test market estimate (mock data)". Do not launch publicly in that state.

## Free tier limit

`FREE_DAILY_LIMIT` (default 5) caps analyses per visitor per day so Gemini
costs stay predictable. Counts are kept in memory: they reset on redeploy and
are per instance, so run one backend instance until accounts are added.

## 2. Deploy the FastAPI backend on Render (or Railway)

1. In Render, select **New → Blueprint** and connect the GitHub repository.
2. Render reads `render.yaml`.
3. Add these secret environment variables:
   - `GEMINI_API_KEY`
   - `EBAY_CLIENT_ID`
   - `EBAY_CLIENT_SECRET`
4. Set `CORS_ORIGINS` temporarily to your future Vercel URL, for example:
   `https://fliplens-ai.vercel.app`
5. Deploy and copy the Render API URL.

Health check:
`https://YOUR-RENDER-URL/health`

## 3. Deploy the Next.js frontend on Vercel

1. Import the same GitHub repository.
2. Set **Root Directory** to `frontend`.
3. Add:
   `NEXT_PUBLIC_API_URL=https://YOUR-RENDER-URL`
4. Deploy.

## 4. Final CORS update

Return to Render and set `CORS_ORIGINS` to the exact Vercel production URL.
Multiple origins are comma-separated.

## 5. Install the PWA

- iPhone/iPad: Safari → Share → **Add to Home Screen**
- Android/Chrome: menu → **Install app**
- macOS Chrome/Edge: install icon in the address bar
