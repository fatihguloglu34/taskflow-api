def test_create_and_list_projects(client, project):
    headers = project["owner"]["headers"]
    r = client.get("/api/v1/projects", headers=headers)
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["my_role"] == "owner"


def test_non_member_cannot_see_project(client, project, register):
    other = register(email="veli@example.com")
    r = client.get(f"/api/v1/projects/{project['id']}", headers=other["headers"])
    assert r.status_code == 404


def test_add_member_and_roles(client, project, register):
    pid = project["id"]
    owner = project["owner"]["headers"]
    member = register(email="veli@example.com")

    r = client.post(f"/api/v1/projects/{pid}/members", json={"email": "veli@example.com"}, headers=owner)
    assert r.status_code == 201
    assert r.json()["role"] == "member"

    # uye projeyi gorebilir ama guncelleyemez/silemez
    assert client.get(f"/api/v1/projects/{pid}", headers=member["headers"]).status_code == 200
    assert client.patch(f"/api/v1/projects/{pid}", json={"name": "X"}, headers=member["headers"]).status_code == 403
    assert client.delete(f"/api/v1/projects/{pid}", headers=member["headers"]).status_code == 403

    # admin olunca guncelleyebilir ama silemez
    client.patch(f"/api/v1/projects/{pid}/members/{member['id']}", json={"role": "admin"}, headers=owner)
    assert client.patch(f"/api/v1/projects/{pid}", json={"name": "X"}, headers=member["headers"]).status_code == 200
    assert client.delete(f"/api/v1/projects/{pid}", headers=member["headers"]).status_code == 403


def test_duplicate_member(client, project, register):
    register(email="veli@example.com")
    url = f"/api/v1/projects/{project['id']}/members"
    headers = project["owner"]["headers"]
    client.post(url, json={"email": "veli@example.com"}, headers=headers)
    assert client.post(url, json={"email": "veli@example.com"}, headers=headers).status_code == 409


def test_owner_cannot_be_removed(client, project):
    pid = project["id"]
    owner = project["owner"]
    r = client.delete(f"/api/v1/projects/{pid}/members/{owner['id']}", headers=owner["headers"])
    assert r.status_code == 400


def test_member_can_leave(client, project, register):
    pid = project["id"]
    member = register(email="veli@example.com")
    client.post(f"/api/v1/projects/{pid}/members", json={"email": "veli@example.com"}, headers=project["owner"]["headers"])
    r = client.delete(f"/api/v1/projects/{pid}/members/{member['id']}", headers=member["headers"])
    assert r.status_code == 204
    assert client.get(f"/api/v1/projects/{pid}", headers=member["headers"]).status_code == 404


def test_delete_project(client, project):
    pid = project["id"]
    headers = project["owner"]["headers"]
    assert client.delete(f"/api/v1/projects/{pid}", headers=headers).status_code == 204
    assert client.get(f"/api/v1/projects/{pid}", headers=headers).status_code == 404
