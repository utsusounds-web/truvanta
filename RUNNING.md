# Truvanta — Run Everything Locally

Two independent apps that talk over HTTP:
- `backend/` — Django REST API on **http://localhost:8000**
- `frontend/` — React (Vite) on **http://localhost:5173**

CORS is already configured on the backend to accept requests from
`http://localhost:5173`, and the frontend's `.env.example` already points at
`http://localhost:8000/api`. You just need both processes running.

## First-time setup

**Backend:**

macOS / Linux:
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser   # optional, for /admin/
```

Windows (PowerShell):
```powershell
cd backend
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py createsuperuser   # optional, for /admin/
```
(If PowerShell blocks the activate script with a "running scripts is
disabled" error, run this once first: `Set-ExecutionPolicy -Scope
CurrentUser RemoteSigned`, then try activating again.)

**Frontend:**
```bash
cd frontend
npm install
cp .env.example .env
```

## Run both at once

Two terminals, in the project root:

macOS / Linux:
```bash
# Terminal 1
cd backend && source venv/bin/activate && python manage.py runserver

# Terminal 2
cd frontend && npm run dev
```

Windows (PowerShell):
```powershell
# Terminal 1
cd backend; venv\Scripts\Activate.ps1; python manage.py runserver

# Terminal 2
cd frontend; npm run dev
```

Then open **http://localhost:5173** — that's the app. It talks to the API at
`http://localhost:8000/api` automatically.

### One-command option (macOS/Linux)
A helper script is included that starts both and stops both together on Ctrl+C:
```bash
./run-dev.sh
```

### One-command option (Windows)
```bat
run-dev.bat
```

## Sanity check
With both running:
1. Open http://localhost:5173 — you land on the sign-up screen.
2. Create an account, then walk through business setup — upload a logo and
   watch the receipt preview update live.
3. On submit, check `backend` terminal logs for `POST /api/tenants/businesses/ 201`.
4. Visit http://localhost:8000/admin/ (superuser login) to see the Business,
   Branch, and Membership rows that were just created.

## Ports already in use?
- Backend: `python manage.py runserver 0.0.0.0:8001` — then also update
  `frontend/.env`'s `VITE_API_BASE_URL` and `backend/.env`'s
  `CORS_ALLOWED_ORIGINS` to match.
- Frontend: Vite will prompt to use the next free port automatically — in dev
  (`DEBUG=True`), the backend already trusts any `localhost`/`127.0.0.1` port
  for CORS, so this just works without touching `.env`.

## "Can't reach the server" / "Something went wrong" on login, or the app seems stuck

This means the frontend genuinely couldn't reach the backend — not a wrong
password (a real wrong-password attempt shows a specific message like "No
active account found with the given credentials"). Work through these in order:

**1. Is the backend actually running and healthy?**
Open http://localhost:8000/api/auth/me/ directly in a browser. You should see
`{"detail":"Authentication credentials were not provided."}` — that's correct,
it means the server responded. If the page fails to load at all (browser
error, not a JSON response), the backend isn't running or crashed. Check the
terminal it's running in for a traceback.

If you're using `./run-dev.sh` or `run-dev.bat`, they now wait for the
backend to respond before starting the frontend, and print the backend's
actual error output if it doesn't come up within 20 seconds — that error is
almost always the real cause (missing dependencies, a pending migration,
port 8000 already in use by something else).

**2. Are dependencies actually installed?**
A half-finished `pip install -r requirements.txt` (interrupted, or run
outside the venv) is the single most common cause. Confirm you're inside the
venv (`source venv/bin/activate` on macOS/Linux, `venv\Scripts\Activate.ps1`
on Windows — see the Windows troubleshooting section below if this itself
fails). Your prompt should show `(venv)` once it's active, then re-run
`pip install -r requirements.txt` and watch for errors.

**3. Does `frontend/.env`'s `VITE_API_BASE_URL` actually point at the backend?**
Default is `http://localhost:8000/api`. If you changed the backend's port,
this must match. Vite only reads `.env` at startup — restart `npm run dev`
after editing it.

## Windows: "failed to locate pyvenv.cfg: The system cannot find the file specified"

This means the `python` command on your PATH is **not** a fresh Python
install — it's already pointing at some *other*, different virtual
environment (from an earlier project) whose folder has since been deleted
or moved. Every venv's `python.exe` is a small file that refers back to
its own `pyvenv.cfg`; if that's gone, `python` fails immediately, before
even reading your actual command — which is why it fails even on
`python -m venv venv` itself.

Fix, in order:
1. **Close this PowerShell window completely and open a brand new one.**
   If a previous project's venv was ever activated in this same window,
   PowerShell keeps pointing at it for the rest of that session even
   after the folder is deleted — a new window clears this.
2. In the new window, run `where.exe python` — every path it lists should
   point inside a Python install (e.g. `...\Python312\python.exe`), never
   inside any `venv\Scripts\` folder. If one does, that confirms the stale
   venv is still on your permanent PATH — remove it via Windows Settings
   → "Edit environment variables for your account."
3. Try `py -3 -m venv venv` instead of `python -m venv venv` — `py` is
   Windows' own Python launcher and usually bypasses a broken `python`
   shim entirely.
4. If none of that resolves it, reinstall Python from python.org (not the
   Microsoft Store version, which uses its own alias system that causes
   exactly this kind of confusion) and make sure "Add python.exe to PATH"
   is checked during setup.

**4. Are you opening the app from a phone or another device on your network?**
This is the most common non-obvious cause. `localhost` on a phone means
*the phone itself*, not your computer — so `VITE_API_BASE_URL=http://localhost:8000/api`
will never work from a second device, even though it works fine in a
browser on the same machine as the backend. Fix: find your computer's LAN IP
(`ipconfig` on Windows / `ifconfig` or `ip addr` on macOS/Linux, something
like `192.168.1.42`), then:
- Set `frontend/.env`: `VITE_API_BASE_URL=http://192.168.1.42:8000/api`
- Set `backend/.env`: add that origin to `CORS_ALLOWED_ORIGINS`, e.g.
  `CORS_ALLOWED_ORIGINS=http://localhost:5173,http://192.168.1.42:5173`
- Restart both `npm run dev` and the backend after editing `.env` files.
- Run the frontend as `npm run dev -- --host` so Vite listens on your LAN
  IP, not just `localhost`.

**5. Port 8000 (or 5173) already used by something else?**
See "Ports already in use?" above — the symptom is usually the backend
"starting" successfully but every request failing, because something else
answered on that port instead of Django.

**6. Firewall blocking the connection?**
Especially relevant on Windows or if the backend is on a different machine —
temporarily disable the firewall (or add an inbound rule for port 8000) to
confirm before spending time elsewhere.
