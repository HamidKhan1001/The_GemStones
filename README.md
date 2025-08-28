

# Gemstone Marketplace (FastAPI)

A FastAPI web app for selling gemstones with:

* Accounts & sessions (bcrypt, signed cookies)
* Items & admin uploads (images to `/static/uploads`)
* Cart & (demo) checkout via Stripe
* Live auctions (WebSocket bidding per item)
* Room chat with history (WebSocket)
* SEO assistant & chatbot via an OpenAI-compatible API (e.g., OpenRouter)
* Jinja2 templates & static assets
* Works with **SQLite** (default) or **MySQL** (optional)

---

## Project Structure

```
.
├─ app/
│  ├─ __init__.py
│  ├─ main.py                   # your big FastAPI file
│  ├─ database.py               # SQLAlchemy engine/session
│  ├─ models.py                 # User, Item, Message, Bid
│  ├─ schemas.py                # Pydantic DTOs
│  ├─ static/
│  │  └─ uploads/.gitkeep       # user-uploaded images
│  └─ templates/
│     ├─ index.html
│     ├─ chat.html
│     ├─ auction.html
│     ├─ admin_chats.html
│     └─ auctions.html
├─ requirements.txt
└─ .env
```

> If your `main.py` is at repo root (not under `app/`), use `uvicorn main:app` instead of `uvicorn app.main:app` and keep local imports as `from database import ...`.

---

## Quick Start (Windows PowerShell or macOS/Linux)

### 1) Create a virtualenv & install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # macOS/Linux: source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

If you see a `UnicodeDecodeError` on `requirements.txt`, recreate it in UTF-8 (no fancy quotes) and run again.

### 2) Configure environment

Create a `.env` in the repo root:

```env
# DB (SQLite default – no server needed)
DATABASE_URL=sqlite:///./app.db

# For MySQL later (optional):
# DATABASE_URL=mysql+pymysql://user:pass@localhost:3306/gems?charset=utf8mb4

# Secrets
SESSION_SECRET=change-me-long-random
JWT_SECRET=change-me-long-random

# Stripe (optional demo)
STRIPE_SECRET=sk_test_xxx
STRIPE_PUB=pk_test_xxx

# AI (optional; OpenAI-compatible)
OPENAI_API_KEY=or_xxx
OPENAI_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=mistralai/Mistral-7B-Instruct   # or gpt-3.5-turbo if using OpenAI
```

### 3) Run the server

```powershell
# from the repo root
$env:PYTHONPATH="."               # safe on Windows; no-op elsewhere
uvicorn app.main:app --reload --port 8000
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000)

> If you kept `main.py` at repo root, use: `uvicorn main:app --reload`.

---

## First Use

1. Visit `/signup`, create a user.
2. (Optional admin) Promote your user to admin:

* **SQLite (app.db)** — using Python:

  ```powershell
  python -c "import sqlite3; c=sqlite3.connect('app.db'); c.execute(\"update users set is_admin=1 where username='YOURNAME'\"); c.commit(); c.close(); print('ok')"
  ```
* **MySQL**:

  ```sql
  UPDATE users SET is_admin=1 WHERE username='YOURNAME';
  ```

3. Go to `/admin/add` to add an item with an image.
4. Visit `/auctions` → open an item → bid live.
5. Chat: `/chat/general` (must be logged in).

Interactive API docs: **`/docs`**

---

## Key Routes

### HTML pages

* `GET /` — home (items, latest/hot)
* `GET /signup`, `POST /signup`
* `GET /login`, `POST /login`
* `GET /dashboard`
* `GET /cart`, `POST /add-to-cart`, `GET /cart-data`
* `POST /create-checkout-session` (Stripe demo), `GET /success`
* `GET /admin/add`, `POST /admin/add` — add item (image upload)
* `GET /auction/{item_id}` — auction page with token for WS
* `GET /chat/{room}` — chat page with token for WS
* `GET /admin/chats` — list chat rooms (admin)

### JSON APIs

* `POST /admin/suggest-seo` → `{ title, description }` (AI)
* `POST /chatbot` → `{ answer }` (AI)

### WebSockets

* `WS /ws/auction/{item_id}?token=JWT`
* `WS /ws/chat/{room}?token=JWT`

Example browser client (from `chat.html`):

```js
const ws = new WebSocket(`ws://${location.host}/ws/chat/general?token=${token}`);
ws.onmessage = e => console.log(JSON.parse(e.data));
ws.onopen = () => ws.send(JSON.stringify({ content: "hello 💎" }));
```

---

## Database

### SQLite (default)

No setup required. A file `app.db` will be created automatically, as long as `Base.metadata.create_all(bind=engine)` is executed on startup (your `main.py` does this).

### MySQL (optional)

1. Create DB & user (MySQL Shell → `\sql`):

```sql
CREATE DATABASE gems CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'gems_user'@'%' IDENTIFIED BY 'SuperSecure#123';
GRANT ALL PRIVILEGES ON gems.* TO 'gems_user'@'%';
FLUSH PRIVILEGES;
```

2. Set `.env`:

```
DATABASE_URL=mysql+pymysql://gems_user:SuperSecure#123@localhost:3306/gems?charset=utf8mb4
```

3. Restart the app; tables will be created.

---

## Configuration Notes

* **Imports:** Because `main.py` is inside `app/`, local imports must be package-qualified:

  ```python
  from app.database import SessionLocal, engine, Base
  from app.models import Item, User, Message, Bid
  from app.schemas import SEOSuggestionRequest, ChatMessage
  ```
* **Static & templates:** Use project-relative paths:

  ```python
  from pathlib import Path
  BASE_DIR = Path(__file__).resolve().parent
  app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
  templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
  ```
* **Stripe:** define `STRIPE_SECRET` and `STRIPE_PUB`, or use the `/checkout-mock` route during dev.
* **AI client:** ensure you define

  ```python
  client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL) if OPENAI_API_KEY else None
  ```

  and guard endpoints if `client is None`.

---

## Troubleshooting

* **`Could not import module "app.main"`**

  * Ensure `app\__init__.py` exists (even empty).
  * Run from the project root: `uvicorn app.main:app`
  * Fix imports to `from app.database ...`, `from app.models ...`
  * Quick check:

    ```powershell
    python -c "import sys; sys.path.insert(0,'.'); import importlib; importlib.import_module('app.main'); print('OK')"
    ```

* **`Chatbot error: name 'client' is not defined`**

  * Add the OpenAI client initialization and guard the endpoints (see config notes).

* **WebSocket closes immediately (`connection is CLOSED`)**

  * You must pass `?token=JWT` in the WS URL. Open `/chat/<room>` or `/auction/<id>` to get a valid token generated by `create_jwt_for(user)`. Make sure you’re logged in.

* **`UnicodeDecodeError` installing requirements on Windows**

  * Recreate `requirements.txt` in UTF-8 (plain ASCII lines).
  * `pip install -r requirements.txt` again.

* **`no such table`**

  * Ensure the line `Base.metadata.create_all(bind=engine)` runs on startup.

---

## Tests (optional)

If you add `pytest` tests:

```bash
pip install pytest
pytest -q
```
## Screenshots (optional)
![WhatsApp Image 2025-08-28 at 13 44 36_ff3b3279](https://github.com/user-attachments/assets/c61273fd-8e94-4afc-a57f-de46764d499e)
![WhatsApp Image 2025-08-28 at 13 45 20_32c65f9b](https://github.com/user-attachments/assets/14468ca2-d943-4006-86b2-860b751dd840)
![WhatsApp Image 2025-08-28 at 13 46 21_36730050](https://github.com/user-attachments/assets/53e1c97b-f102-41e4-ab0e-d1155cba8df7)
![WhatsApp Image 2025-08-28 at 13 47 30_9746d5ec](https://github.com/user-attachments/assets/9cf7b392-9ac9-4da2-8246-afed50cee3a4)




---

## Deployment (quick notes)

* Containerize with a `Dockerfile` (Gunicorn + Uvicorn worker) and deploy to Koyeb/Render/Fly/etc.
* For “free-ish” hosting today, SQLite + a small container on Koyeb/Render can work for hobby usage; for a managed DB, Neon (Postgres) has a decent free tier. (MySQL free tiers are scarce; you may need a small paid instance.)

---

## License

All rights reserved by Hamid Khan
