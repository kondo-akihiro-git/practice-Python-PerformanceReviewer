from conftest import auth


def full_self(items):
    return {"items": [{"item_id": i["item_id"], "score": 3, "comment": "自己"} for i in items]}


def evaluation(items, score, comment, overall):
    return {"items": [{"item_id": i["item_id"], "score": score, "comment": comment} for i in items], "overall": overall}


def test_login_and_auth_required(client):
    assert client.get("/api/reviews").status_code == 401
    bad = client.post("/api/login", json={"email": "member1@example.com", "password": "x"})
    assert bad.status_code == 401


def test_full_workflow_and_visibility(client):
    member = auth(client, "member1@example.com")
    interviewer = auth(client, "interviewer@example.com")
    manager = auth(client, "manager@example.com")
    president = auth(client, "president@example.com")
    other = auth(client, "member2@example.com")
    admin = auth(client, "admin@example.com")

    review = client.get("/api/reviews", headers=member).json()[0]
    base = f"/api/reviews/{review['id']}"
    assert review["status"] == "draft"

    # 無関係のメンバー・管理者は内容を閲覧できない
    assert client.get(base, headers=other).status_code == 403
    assert client.get(base, headers=admin).status_code == 403

    items = client.get(base, headers=member).json()["items"]
    assert len(items) == 8

    # 未入力では提出できない。段階外の操作・他人の操作はできない
    assert client.post(f"{base}/self/submit", headers=member).status_code == 422
    assert client.get(base, headers=interviewer).json()["items"][0]["self_score"] is None
    assert client.put(f"{base}/interviewer", headers=interviewer,
                      json={"items": [], "overall": ""}).status_code == 409
    bad_score = {"items": [{"item_id": items[0]["item_id"], "score": 6, "comment": ""}]}
    assert client.put(f"{base}/self", headers=member, json=bad_score).status_code == 422

    assert client.put(f"{base}/self", headers=member, json=full_self(items)).status_code == 200
    assert client.post(f"{base}/self/submit", headers=member).json()["status"] == "submitted"
    assert client.put(f"{base}/self", headers=member, json=full_self(items)).status_code == 409

    # 面談担当者の取りまとめ
    assert client.get(base, headers=interviewer).json()["items"][0]["self_score"] == 3
    assert client.put(f"{base}/self", headers=interviewer, json=full_self(items)).status_code == 403
    summary = {"items": [{"item_id": i["item_id"], "note": "所見"} for i in items], "overall": "総括"}
    assert client.put(f"{base}/interviewer", headers=interviewer, json=summary).status_code == 200
    assert client.get(base, headers=manager).json()["items"][0]["self_score"] is None
    assert client.post(f"{base}/interviewer/submit", headers=interviewer).json()["status"] == "summarized"

    # マネージャーが先に評価する。社長はまだ操作も閲覧もできない
    assert client.put(f"{base}/president", headers=president,
                      json=evaluation(items, 4, "社長", "社長総括")).status_code == 409
    assert client.get(base, headers=president).json()["items"][0]["self_score"] is None
    seen = client.get(base, headers=manager).json()
    assert seen["interviewer_overall"] == "総括" and seen["items"][0]["self_score"] == 3
    assert client.post(f"{base}/manager/submit", headers=manager).status_code == 422
    assert client.put(f"{base}/manager", headers=president,
                      json=evaluation(items, 2, "x", "x")).status_code == 403
    assert client.put(f"{base}/manager", headers=manager,
                      json=evaluation(items, 3, "マネ評価", "マネ総括")).status_code == 200
    assert client.post(f"{base}/manager/submit", headers=manager).json()["status"] == "manager_evaluated"

    # 社長はマネージャーの評価を見たうえで評価する。マネージャーは社長の評価を見られない
    seen = client.get(base, headers=president).json()
    assert seen["items"][0]["manager_score"] == 3 and seen["manager_overall"] == "マネ総括"
    assert client.put(f"{base}/president", headers=president,
                      json=evaluation(items, 5, "社長評価", "社長総括")).status_code == 200
    assert client.post(f"{base}/president/submit", headers=president).json()["status"] == "evaluated"
    assert client.get(base, headers=manager).json()["items"][0]["president_score"] is None

    # 公開前は本人に所見・管理職の評価が見えない
    hidden = client.get(base, headers=member).json()
    for key in ("interviewer_note", "manager_score", "president_score", "president_comment"):
        assert hidden["items"][0][key] is None
    assert hidden["manager_overall"] is None and hidden["president_overall"] is None

    # 面談担当者は両者の評価を確認でき、公開できる（本人は公開不可）
    checked = client.get(base, headers=interviewer).json()
    assert checked["items"][0]["manager_score"] == 3 and checked["items"][0]["president_score"] == 5
    assert client.post(f"{base}/publish", headers=member).status_code == 403
    assert client.post(f"{base}/publish", headers=interviewer).json()["status"] == "published"

    # 公開後は本人が両者の評価を確認できる
    final = client.get(base, headers=member).json()
    assert final["items"][0]["manager_comment"] == "マネ評価"
    assert final["items"][0]["president_comment"] == "社長評価"
    assert final["manager_overall"] == "マネ総括" and final["president_overall"] == "社長総括"


def test_admin_user_and_review_management(client):
    admin = auth(client, "admin@example.com")
    member = auth(client, "member1@example.com")
    assert client.get("/api/users", headers=member).status_code == 403
    users = {u["email"]: u["id"] for u in client.get("/api/users", headers=admin).json()}

    new = client.post("/api/users", headers=admin, json={
        "name": "新人", "email": "new@example.com", "password": "longenough1"})
    assert new.status_code == 201
    dup = client.post("/api/users", headers=admin, json={
        "name": "新人", "email": "new@example.com", "password": "longenough1"})
    assert dup.status_code == 409

    ok = {"period": "2027年 上期", "member_id": new.json()["id"],
          "interviewer_id": users["interviewer@example.com"],
          "manager_id": users["manager@example.com"], "president_id": users["president@example.com"]}
    assert client.post("/api/reviews", headers=member, json=ok).status_code == 403
    assert client.post("/api/reviews", headers=admin, json=ok).status_code == 201
    # 評価権限のないユーザー、同一人物は指定できない
    no_right = {**ok, "manager_id": users["interviewer@example.com"]}
    assert client.post("/api/reviews", headers=admin, json=no_right).status_code == 422
    same = {**ok, "manager_id": users["president@example.com"]}
    assert client.post("/api/reviews", headers=admin, json=same).status_code == 422
