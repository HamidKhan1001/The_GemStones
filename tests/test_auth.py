def test_signup_login_flow(client):
    # signup
    r = client.post("/signup", data={
        "first_name":"A","last_name":"B","username":"alice","password":"p@ss","confirm_password":"p@ss"
    })
    assert r.status_code in (303, 307)

    # login
    r = client.post("/login", data={"username":"alice","password":"p@ss"})
    assert r.status_code in (303, 307)

    # dashboard loads after login (session cookie set by TestClient)
    r = client.get("/dashboard")
    assert r.status_code == 200
    assert "dashboard" in r.text.lower()
