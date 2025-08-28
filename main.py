# ─── Standard library ──────────────────────────────────────────────────────────
import os
import shutil
import secrets
from datetime import datetime
from sqlalchemy import select
# near the top of main.py
from models import Item, User, Message, Bid

# ─── Environment & Configuration ───────────────────────────────────────────────
from dotenv import load_dotenv
from fastapi.responses import HTMLResponse
from collections import Counter
# ─── Security & Hashing ────────────────────────────────────────────────────────
from passlib.hash import bcrypt
from jose import jwt, JWTError
# near the top of main.py
from typing import Optional

# ─── Database / ORM ────────────────────────────────────────────────────────────
from sqlalchemy.orm import Session
# main.py
from fastapi import Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from collections import Counter
# ─── Web framework (FastAPI) ──────────────────────────────────────────────────
from fastapi import (
    FastAPI,
    Request,
    Form,
    Depends,
    UploadFile,
    File,
    HTTPException,
    Body,
)
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# ─── Templating & Sessions (Starlette) ────────────────────────────────────────
from starlette.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

# ─── External APIs ─────────────────────────────────────────────────────────────
from openai import OpenAI
import stripe

# ─── Your local modules ────────────────────────────────────────────────────────
from database import SessionLocal, engine, Base
from models import Item, User
from schemas import SEOSuggestionRequest, ChatMessage
from starlette.websockets import WebSocket, WebSocketDisconnect
from typing import Dict, List
import secrets
from starlette.middleware.sessions import SessionMiddleware
from starlette.templating import Jinja2Templates
# ─── (Optional) Flask, if you still need it ────────────────────────────────────
from flask import session, render_template, request as flask_request, \
                  redirect as flask_redirect, url_for

# ──────────────── INIT ────────────────

load_dotenv()
app = FastAPI()

# use your single, consistent secret from .env
# ─── generate a new secret on each run if none is set in env ─────────────────
SESSION_SECRET = os.getenv("SESSION_SECRET") or secrets.token_hex(32)
JWT_SECRET     = os.getenv("JWT_SECRET")     or secrets.token_hex(32)

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "fallback_secret")  
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
JWT_SECRET = os.getenv("JWT_SECRET") or secrets.token_hex(32)

def create_jwt_for(user):
    """
    Embed whatever you need in the token. Here we include
    user_id and username (you can add exp, roles, etc).
    """
    payload = {
        "user_id":   user.id,
        "username":  user.username,
        # e.g. "exp": datetime.utcnow() + timedelta(hours=1)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")
async def your_authenticate(token: str, db: Session) -> Optional[User]:
    """
    Decode the token, look up the user, or return None on failure.
    """
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_id = data.get("user_id")
        if not user_id:
            return None
        return db.query(User).filter(User.id == user_id).first()
    except JWTError:
        return None

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")











class ConnectionManager:
    def __init__(self):
        # maps room name → list of websockets
        self.active: Dict[str, List[WebSocket]] = {}

    async def connect(self, room: str, ws: WebSocket):
        await ws.accept()
        self.active.setdefault(room, []).append(ws)

    def disconnect(self, room: str, ws: WebSocket):
        conns = self.active.get(room, [])
        if ws in conns:
            conns.remove(ws)
            if not conns:
                del self.active[room]

    async def broadcast(self, room: str, message: dict):
        for ws in self.active.get(room, []):
            try:
                await ws.send_json(message)
            except:
                pass

auction_mgr = ConnectionManager()
chat_mgr    = ConnectionManager()

# ──────────────── UTILS ────────────────

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if user_id:
        return db.query(User).filter_by(id=user_id).first()
    return None

# ──────────────── ROUTES ────────────────

@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    items = db.query(Item).all()
    user = get_current_user(request, db)

      # ─── New: fetch the newest (latest) item and the top 4 “hot” items ───
    latest_item = db.query(Item).order_by(Item.id.desc()).first()
    hot_items   = db.query(Item).order_by(Item.id.desc()).limit(4).all()

    # ─── ADDED: prepare notifications & tour prompt ───
    notifications = []
    show_tour_prompt = False
    if not user and not request.session.get("tour_prompt_shown", False):
        show_tour_prompt = True
        request.session["tour_prompt_shown"] = True

    return templates.TemplateResponse("index.html", {
        "request": request,
        "items": items,
        "user": user,
        "page": "home",
        "page": "home",
        "latest_item": latest_item,  # pass into template
        "hot_items": hot_items,      # pass into template
        "notifications": notifications,            # ─── ADDED
        "show_tour_prompt": show_tour_prompt,      # ─── ADDED
        "current_year": datetime.now().year
    })

@app.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request, db: Session = Depends(get_db)):   # ─── ADDED db
    user = get_current_user(request, db)                            # ─── ADDED
    notifications = []                                              # ─── ADDED
    return templates.TemplateResponse("index.html", {
        "request": request,
        "user": user,                                               # ─── ADDED
        "page": "signup",
        "notifications": notifications,                             # ─── ADDED
        "show_tour_prompt": False,                                  # ─── ADDED
        "current_year": datetime.now().year                         # ─── ADDED
    })

@app.post("/signup")
def signup(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    if password != confirm_password:
        return RedirectResponse("/signup", status_code=303)
    if db.query(User).filter_by(username=username).first():
        return RedirectResponse("/signup", status_code=303)

    hashed = bcrypt.hash(password)
    user = User(
        username=username,
        password=hashed,
        first_name=first_name,
        last_name=last_name,
        is_admin=False
    )
    db.add(user)
    db.commit()
    request.session["user_id"] = user.id
    return RedirectResponse("/dashboard", status_code=303)

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, db: Session = Depends(get_db)):    # ─── ADDED db
    user = get_current_user(request, db)                            # ─── ADDED
    notifications = []                                              # ─── ADDED
    return templates.TemplateResponse("index.html", {
        "request": request,
        "user": user,                                               # ─── ADDED
        "page": "login",
        "notifications": notifications,                             # ─── ADDED
        "show_tour_prompt": False,                                  # ─── ADDED
        "current_year": datetime.now().year                         # ─── ADDED
    })

@app.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter_by(username=username).first()
    if not user or not user.verify_password(password):
        return RedirectResponse("/login", status_code=303)

    request.session["user_id"] = user.id
    return RedirectResponse("/", status_code=303)


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    # ─── ADDED
    notifications = []

    return templates.TemplateResponse("index.html", {
        "request": request,
        "user": user,
        "page": "dashboard",
        "notifications": notifications,         # ─── ADDED
        "show_tour_prompt": False,              # ─── ADDED
        "current_year": datetime.now().year      # ─── ADDED
    })
@app.get("/admin/chats", response_class=HTMLResponse)
def admin_chats(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not user or not user.is_admin:
        raise HTTPException(403, "Not authorized")
    # Grab every distinct room name from your messages table
    rooms = [r[0] for r in db.query(Message.room).distinct().all()]
    return templates.TemplateResponse("admin_chats.html", {
        "request": request,
        "rooms": rooms,
    })
@app.websocket("/ws/auction/{item_id}")
async def ws_auction(
    websocket: WebSocket,
    item_id: int,
    token: str = Query(...),                    # your auth token
    db: Session = Depends(get_db),
):
    # 1) Authenticate
    user = await your_authenticate(token, db)
    if not user or not user.email_verified:
        await websocket.close(code=4001)
        return

    room = f"auction_{item_id}"
    await auction_mgr.connect(room, websocket)

    try:
        # On connect, send the current highest bid
        highest = db.query(Bid).filter_by(item_id=item_id).order_by(Bid.amount.desc()).first()
        await websocket.send_json({
            "type": "init",
            "highest": highest.amount if highest else 0
        })

        while True:
            data = await websocket.receive_json()
            # { "bid": 123.45 }
            new_bid = float(data.get("bid", 0))
            # re-load highest
            curr = db.query(Bid).filter_by(item_id=item_id).order_by(Bid.amount.desc()).first()
            curr_amt = curr.amount if curr else 0
            if new_bid <= curr_amt:
                await websocket.send_json({"type":"error","msg":"Bid too low","highest":curr_amt})
                continue

            # save new bid
            bid = Bid(item_id=item_id, user_id=user.id, amount=new_bid)
            db.add(bid); db.commit()

            # broadcast to everyone in this auction room
            await auction_mgr.broadcast(room, {
                "type": "new_bid",
                "user": user.username,
                "amount": new_bid,
                "timestamp": bid.timestamp.isoformat()
            })

    except WebSocketDisconnect:
        auction_mgr.disconnect(room, websocket)


@app.get("/auction/{item_id}", response_class=HTMLResponse)
def auction_page(request: Request, item_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    item = db.query(Item).get(item_id)
    return templates.TemplateResponse("auction.html", {
      "request": request,
      "item": item,
      "user_token": create_jwt_for(user)   # or however you auth
    })


@app.websocket("/ws/chat/{room}")
async def ws_chat(websocket: WebSocket, room: str, token: str = Query(...), db: Session = Depends(get_db)):
    user = await your_authenticate(token, db)
    if not user:
        await websocket.close(code=4001)
        return

    await chat_mgr.connect(room, websocket)
    try:
        # send past history
        history = db.query(Message).filter_by(room=room).order_by(Message.timestamp).all()
        for m in history:
            await websocket.send_json({
                "sender": m.sender.username,
                "content": m.content,
                "ts": m.timestamp.isoformat()
            })

        while True:
            data = await websocket.receive_json()       # data is a dict
            text = data.get("content")                  # <-- use dict key
            if not text:
                continue

            # save it
            msg = Message(room=room, sender_id=user.id, content=text)
            db.add(msg)
            db.commit()

            # broadcast
            await chat_mgr.broadcast(room, {
                "sender":  user.username,
                "content": text,
                "ts":      msg.timestamp.isoformat()
            })

    except WebSocketDisconnect:
        chat_mgr.disconnect(room, websocket)



@app.get("/chat/{room}", response_class=HTMLResponse)
def chat_page(request: Request, room: str, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    # ─── ADD THIS GUARD ─────────────────────────────────────────
    if not user:
        # send them to login if they tried to open chat without being authenticated
        return RedirectResponse("/login", status_code=303)
    # ─────────────────────────────────────────────────────────────
    token = create_jwt_for(user)
    return templates.TemplateResponse("chat.html", {
      "request":   request,
      "room":      room,
      "user_token": token
    })

@app.post("/add-to-cart")
async def add_to_cart(request: Request):
    data = await request.json()
    item_id = int(data["item_id"])
    cart = request.session.get("cart", [])
    cart.append(item_id)
    request.session["cart"] = cart
    return {"count": len(cart)}

@app.get("/cart", response_class=HTMLResponse)
async def cart(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    ids = request.session.get("cart", [])
    items = db.execute(select(Item).where(Item.id.in_(ids))).scalars().all()
    total = sum(item.price for item in items)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "page": "cart",
        "user": user,
        "items": items,
        "total": total,
        "stripe_pub": STRIPE_PUB,
        "show_tour_prompt": False,
        "notifications": [],
        "current_year": datetime.now().year
    })
from fastapi.responses import JSONResponse

@app.get("/cart-data")
def cart_data(request: Request, db: Session = Depends(get_db)):
    ids = request.session.get("cart", [])
    items = db.query(Item).filter(Item.id.in_(ids)).all()
    total = sum(i.price for i in items)
    return JSONResponse({
      "items": [{"name":i.name, "price": i.price} for i in items],
      "total": total
    })

@app.post("/create-checkout-session")
async def create_checkout_session(request: Request):
    data = await request.json()
    cart_ids = request.session.get("cart", [])
    line_items = []

    if data.get("single_item"):
        gem = Gemstone.query.get(data["item_id"])
        line_items.append({
          "price_data": {
            "currency": "usd",
            "product_data": {"name": gem.name},
            "unit_amount": int(gem.price * 100),
          },
          "quantity": 1
        })
    else:
        for gid in cart_ids:
            gem = Gemstone.query.get(gid)
            line_items.append({
              "price_data": {
                "currency": "usd",
                "product_data": {"name": gem.name},
                "unit_amount": int(gem.price * 100),
              },
              "quantity": 1
            })

    sess = stripe.checkout.Session.create(
      payment_method_types=["card"],
      line_items=line_items,
      mode="payment",
      success_url=str(request.url_for("success")),
      cancel_url=str(request.url_for("cart")),
    )
    return {"id": sess.id}

@app.get("/success", response_class=HTMLResponse)
async def success(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    request.session["cart"] = []
    return templates.TemplateResponse("index.html", {
        "request": request,
        "page": "success",
        "user": user,
        "show_tour_prompt": False,
        "notifications": [],
        "current_year": datetime.now().year
    })
@app.get("/checkout", response_class=HTMLResponse)
def checkout_page(request: Request, db: Session = Depends(get_db)):
    # build (Item, qty) list
    ids = request.session.get("cart", [])
    counts = Counter(ids)
    items = []
    for gem_id, qty in counts.items():
        gem = db.query(Item).get(gem_id)
        if gem:
            items.append((gem, qty))

    total = sum(g.price * qty for g, qty in items)
    return templates.TemplateResponse("checkout.html", {
        "request": request,
        "items": items,
        "total": total,
        "cart_count": len(ids),
        "current_year": datetime.now().year
    })
@app.post("/checkout-mock")
async def checkout_mock(request: Request):
    data = await request.json()
    # You could record the “order” here (e.g. write to DB) if you want
    request.session["cart"] = []
    return JSONResponse({"success": True})
@app.get("/profile", response_class=HTMLResponse)
def profile(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    # ─── ADDED
    notifications = []

    return templates.TemplateResponse("index.html", {
        "request": request,
        "user": user,
        "page": "profile",
        "notifications": notifications,         # ─── ADDED
        "show_tour_prompt": False,              # ─── ADDED
        "current_year": datetime.now().year      # ─── ADDED
    })

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)

@app.get("/admin/add", response_class=HTMLResponse)
def admin_add_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse("/", status_code=303)

    # ─── ADDED
    notifications = []

    return templates.TemplateResponse("index.html", {
        "request": request,
        "user": user,
        "page": "admin_add",
        "notifications": notifications,         # ─── ADDED
        "show_tour_prompt": False,              # ─── ADDED
        "current_year": datetime.now().year      # ─── ADDED
    })

@app.post("/admin/add")
def admin_add_item(
    request: Request,
    name: str = Form(...),
    description: str = Form(None),
    price: float = Form(...),
    image: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user or not user.is_admin:
        return RedirectResponse("/", status_code=303)

    upload_dir = "app/static/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, image.filename)
    with open(filepath, "wb") as f:
        shutil.copyfileobj(image.file, f)

    image_url = f"/static/uploads/{image.filename}"
    item = Item(name=name, description=description, price=price, image_url=image_url)
    db.add(item)
    db.commit()
    return RedirectResponse("/", status_code=303)

# ──────────────── SEO SUGGESTION ────────────────

@app.post("/admin/suggest-seo")
def suggest_seo(data: SEOSuggestionRequest):
    prompt = f"""Improve this gemstone listing for SEO:
Name: {data.name}
Description: {data.description}
Reply with:
Title: [better title]
Description: [better description]"""


    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a gemstone product SEO expert."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=200
        )
        lines = response.choices[0].message.content.strip().split("\n")
        title = next((l.split(":", 1)[1].strip() for l in lines if "Title:" in l), data.name)
        desc = next((l.split(":", 1)[1].strip() for l in lines if "Description:" in l), data.description)
        return {"title": title, "description": desc}
    except Exception as e:
        print("SEO Error:", e)
        return {"error": "Failed to generate SEO content"}

# ──────────────── GEMBOT CHATBOT ────────────────

@app.post("/chatbot")
async def chatbot_endpoint(payload: dict = Body(...)):
    question = payload.get("question")
    if not question:
        return {"answer": "❗Please ask a question."}

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are GemBot, an expert gemstone advisor helping users discover gemstones and encourage purchases."},
                {"role": "user", "content": question}
            ],
            max_tokens=150,
            temperature=0.8
        )
        answer = response.choices[0].message.content.strip()
        return {"answer": answer}
    except Exception as e:
        print("Chatbot error:", e)
        return {"answer": "⚠️ Sorry, something went wrong. Please try again."}


@app.get("/admin/auction/{item_id}", response_class=HTMLResponse)
def auction_admin_page(request: Request, item_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user or not user.is_admin:
        raise HTTPException(403)
    item = db.query(Item).get(item_id)
    return templates.TemplateResponse("auction_admin.html", {"request": request, "item": item})

@app.post("/admin/auction/{item_id}")
def auction_admin_save(
    request: Request,
    item_id: int,
    auction_live: Optional[bool]      = Form(False),
    youtube_channel: Optional[str]    = Form(None),
    fallback_image: Optional[str]     = Form(None),
    db: Session                       = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user or not user.is_admin:
        raise HTTPException(403)
    item = db.query(Item).get(item_id)
    item.auction_live    = bool(auction_live)
    item.youtube_channel = youtube_channel or None
    item.fallback_image  = fallback_image or None
    db.commit()
    return RedirectResponse(f"/admin/auction/{item_id}", status_code=303)
@app.get("/auctions", response_class=HTMLResponse)
def auctions_list(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    # only show items marked as live auctions
    live_items = db.query(Item).filter(Item.auction_live == True).all()
    return templates.TemplateResponse("auctions.html", {
        "request": request,
        "user":    user,
        "items":   live_items,
        "current_year": datetime.now().year
    })