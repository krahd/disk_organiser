from backend.app import app


def test_ui_routes_serve_customer_application():
    client = app.test_client()
    index = client.get("/ui/")
    assert index.status_code == 200
    assert b"Disk Organiser" in index.data

    script = client.get("/ui/main.js")
    assert script.status_code == 200
    assert b"/api/" in script.data

    style = client.get("/ui/styles.css")
    assert style.status_code == 200
