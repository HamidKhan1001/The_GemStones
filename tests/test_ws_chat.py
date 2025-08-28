from starlette.websockets import WebSocketDisconnect

def test_ws_chat_requires_auth(client):
    # page requires login
    r = client.get("/chat/general", allow_redirects=False)
    assert r.status_code == 303

def test_ws_connect_after_login(client):
    # quick signup/login
    client.post("/signup", data={
        "first_name":"C","last_name":"D","username":"bob","password":"p","confirm_password":"p"
    })
    client.post("/login", data={"username":"bob","password":"p"})
    # get JWT from the chat page
    html = client.get("/chat/general").text
    # very basic token scrape:
    import re
    m = re.search(r"user_token['\"]?\s*:\s*['\"]([A-Za-z0-9\-\._]+)['\"]", html)
    token = m.group(1) if m else None
    assert token

    with client.websocket_connect(f"/ws/chat/general?token={token}") as ws:
        # send a message
        ws.send_json({"content": "hello!"})
        msg = ws.receive_json()
        assert "content" in msg
