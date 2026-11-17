from datetime import date, timedelta


def _url(pid):
    return f"/api/v1/projects/{pid}/tasks"


def test_create_and_get_task(client, project):
    headers = project["owner"]["headers"]
    r = client.post(_url(project["id"]), json={"title": "API yaz", "priority": "high"}, headers=headers)
    assert r.status_code == 201
    task = r.json()
    assert task["status"] == "todo"
    assert task["created_by"]["id"] == project["owner"]["id"]

    r = client.get(f"{_url(project['id'])}/{task['id']}", headers=headers)
    assert r.json()["title"] == "API yaz"


def test_assignee_must_be_member(client, project, register):
    outsider = register(email="veli@example.com")
    r = client.post(
        _url(project["id"]),
        json={"title": "X", "assignee_id": outsider["id"]},
        headers=project["owner"]["headers"],
    )
    assert r.status_code == 400


def test_filter_sort_paginate(client, project):
    headers = project["owner"]["headers"]
    url = _url(project["id"])
    client.post(url, json={"title": "Login sayfasi", "priority": "low"}, headers=headers)
    client.post(url, json={"title": "Veritabani", "priority": "high", "status": "done"}, headers=headers)
    client.post(url, json={"title": "Login testleri", "priority": "medium"}, headers=headers)

    assert client.get(url, params={"status": "done"}, headers=headers).json()["total"] == 1
    assert client.get(url, params={"q": "login"}, headers=headers).json()["total"] == 2

    r = client.get(url, params={"sort_by": "priority", "order": "desc"}, headers=headers).json()
    assert [t["priority"] for t in r["items"]] == ["high", "medium", "low"]

    r = client.get(url, params={"limit": 2, "offset": 2}, headers=headers).json()
    assert r["total"] == 3 and len(r["items"]) == 1


def test_overdue_and_stats(client, project):
    headers = project["owner"]["headers"]
    url = _url(project["id"])
    yesterday = str(date.today() - timedelta(days=1))
    client.post(url, json={"title": "Gecikti", "due_date": yesterday}, headers=headers)
    client.post(url, json={"title": "Bitti", "due_date": yesterday, "status": "done"}, headers=headers)

    assert client.get(url, params={"overdue": True}, headers=headers).json()["total"] == 1

    stats = client.get(f"/api/v1/projects/{project['id']}/stats", headers=headers).json()
    assert stats["total_tasks"] == 2
    assert stats["overdue"] == 1
    assert stats["completion_rate"] == 50.0


def test_update_task(client, project):
    headers = project["owner"]["headers"]
    task = client.post(_url(project["id"]), json={"title": "X"}, headers=headers).json()
    r = client.patch(f"{_url(project['id'])}/{task['id']}", json={"status": "in_progress"}, headers=headers)
    assert r.json()["status"] == "in_progress"
    r = client.patch(f"{_url(project['id'])}/{task['id']}", json={"title": None}, headers=headers)
    assert r.status_code == 422


def test_member_cannot_delete_others_task(client, project, register):
    pid = project["id"]
    owner = project["owner"]["headers"]
    member = register(email="veli@example.com")
    client.post(f"/api/v1/projects/{pid}/members", json={"email": "veli@example.com"}, headers=owner)
    task = client.post(_url(pid), json={"title": "Owner task"}, headers=owner).json()

    assert client.delete(f"{_url(pid)}/{task['id']}", headers=member["headers"]).status_code == 403
    assert client.delete(f"{_url(pid)}/{task['id']}", headers=owner).status_code == 204


def test_my_tasks(client, project):
    headers = project["owner"]["headers"]
    client.post(_url(project["id"]), json={"title": "Bana", "assignee_id": project["owner"]["id"]}, headers=headers)
    client.post(_url(project["id"]), json={"title": "Kimseye"}, headers=headers)
    r = client.get("/api/v1/users/me/tasks", headers=headers).json()
    assert r["total"] == 1 and r["items"][0]["title"] == "Bana"


def test_task_from_other_project_not_accessible(client, project):
    headers = project["owner"]["headers"]
    other = client.post("/api/v1/projects", json={"name": "Diger"}, headers=headers).json()
    task = client.post(_url(other["id"]), json={"title": "X"}, headers=headers).json()
    assert client.get(f"{_url(project['id'])}/{task['id']}", headers=headers).status_code == 404
