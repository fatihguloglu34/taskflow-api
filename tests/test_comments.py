def test_comment_flow(client, project, register):
    pid = project["id"]
    owner = project["owner"]["headers"]
    member = register(email="veli@example.com")
    client.post(f"/api/v1/projects/{pid}/members", json={"email": "veli@example.com"}, headers=owner)
    task = client.post(f"/api/v1/projects/{pid}/tasks", json={"title": "X"}, headers=owner).json()
    url = f"/api/v1/projects/{pid}/tasks/{task['id']}/comments"

    c1 = client.post(url, json={"content": "Basladim"}, headers=member["headers"]).json()
    c2 = client.post(url, json={"content": "Super"}, headers=owner).json()
    assert [c["content"] for c in client.get(url, headers=owner).json()] == ["Basladim", "Super"]

    # uye baskasinin yorumunu silemez, owner silebilir
    assert client.delete(f"{url}/{c2['id']}", headers=member["headers"]).status_code == 403
    assert client.delete(f"{url}/{c1['id']}", headers=owner).status_code == 204
    assert len(client.get(url, headers=owner).json()) == 1
