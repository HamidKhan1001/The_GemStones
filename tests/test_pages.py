def test_homepage_renders(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "current_year" in r.text or "Alliance" in r.text or "home" in r.text

def test_redirects_when_not_logged_in(client):
    r = client.get("/profile", allow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"].endswith("/login")
