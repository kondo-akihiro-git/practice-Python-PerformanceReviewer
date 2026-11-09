from fastapi import HTTPException

from model.models import STATUSES, Item, Review, User


def roles_of(user: User, review: Review) -> set[str]:
    holders = {
        "member": review.member_id,
        "interviewer": review.interviewer_id,
        "manager": review.manager_id,
        "president": review.president_id,
    }
    return {role for role, user_id in holders.items() if user_id == user.id}


def _visibility(roles: set[str], status: str) -> dict[str, bool]:
    idx = STATUSES.index(status)

    def after(name: str) -> bool:
        return idx >= STATUSES.index(name)

    has = roles.__contains__
    return {
        "self": has("member") or (has("interviewer") and after("submitted"))
        or (has("manager") and after("summarized")) or (has("president") and after("manager_evaluated")),
        "interviewer": has("interviewer") or (has("manager") and after("summarized"))
        or (has("president") and after("manager_evaluated")) or (has("member") and after("published")),
        "manager": has("manager") or (has("president") and after("manager_evaluated"))
        or (has("interviewer") and after("evaluated")) or (has("member") and after("published")),
        "president": has("president") or (has("interviewer") and after("evaluated"))
        or (has("member") and after("published")),
    }


def serialize_summary(review: Review) -> dict:
    def person(user: User) -> dict:
        return {"id": user.id, "name": user.name}

    return {
        "id": review.id,
        "period": review.period,
        "status": review.status,
        "member": person(review.member),
        "interviewer": person(review.interviewer),
        "manager": person(review.manager),
        "president": person(review.president),
    }


def serialize_detail(review: Review, user: User, items: list[Item]) -> dict:
    roles = roles_of(user, review)
    visible = _visibility(roles, review.status)
    by_item = {row.item_id: row for row in review.items}

    rows = []
    for item in items:
        row = by_item[item.id]
        rows.append({
            "item_id": item.id,
            "title": item.title,
            "anchors": item.anchors.split("\n"),
            "self_score": row.self_score if visible["self"] else None,
            "self_comment": row.self_comment if visible["self"] else None,
            "interviewer_note": row.interviewer_note if visible["interviewer"] else None,
            "manager_score": row.manager_score if visible["manager"] else None,
            "manager_comment": row.manager_comment if visible["manager"] else None,
            "president_score": row.president_score if visible["president"] else None,
            "president_comment": row.president_comment if visible["president"] else None,
        })
    return {
        **serialize_summary(review),
        "roles": sorted(roles),
        "items": rows,
        "interviewer_overall": review.interviewer_overall if visible["interviewer"] else None,
        "manager_overall": review.manager_overall if visible["manager"] else None,
        "president_overall": review.president_overall if visible["president"] else None,
    }


def require_role_and_status(user: User, review: Review, role: str, statuses: list[str]) -> None:
    if role not in roles_of(user, review):
        raise HTTPException(403, "この操作を行う権限がありません")
    if review.status not in statuses:
        raise HTTPException(409, f"現在の状態（{review.status}）ではこの操作はできません")
