# FlipLens AI

Minimal web app for analysing second-hand marketplace deals with AI.

## 1. Start the backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and configure AI_PROVIDER / GEMINI_API_KEY
python -m uvicorn app.main:app --reload
```

Backend: http://127.0.0.1:8000  
API docs: http://127.0.0.1:8000/docs

## 2. Start the website

Open a second terminal:

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Website: http://localhost:3000

The website sends the uploaded image and deal details to `POST /api/v1/deals/analyze-image` and renders the complete FlipLens report.

## Windows quick start

1. Install **Python 3.11+** (tick "Add python.exe to PATH") and **Node.js LTS**.
2. Double-click `setup-windows.bat`. It creates `backend\.venv`, installs the
   Python and Node packages, and creates `backend\.env` / `frontend\.env.local`
   if they are missing.
3. Put your keys in `backend\.env` (`AI_PROVIDER=gemini`, `GEMINI_API_KEY`,
   `PRICING_PROVIDER=ebay`, `EBAY_CLIENT_ID`, `EBAY_CLIENT_SECRET`). Without keys
   the app runs on mock data.
4. Double-click `start-windows.bat`. It opens the API (port 8000), the website
   (port 3000) and your browser. Close the two console windows to stop it.
5. `test-windows.bat` runs the backend tests and the frontend type check.

If you copied the project from a Mac, `setup-windows.bat` removes the
Mac-built `.venv` and `node_modules` and rebuilds them for Windows.
