from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from logic.security import create_token, hash_password, read_token, verify_password
from logic.seed import attach_items, seed_demo, seed_items
from logic.workflow import (
    require_role_and_status,
    roles_of,
    serialize_detail,
    serialize_summary,
)
from model.models import STATUSES, Base, Item, Review, SessionLocal, User, engine

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed_items(db)
        seed_demo(db)
    yield


app = FastAPI(title="PerformanceReviewer", lifespan=lifespan)


def get_db():
    with SessionLocal() as db:
        yield db


def current_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> User:
    scheme, _, token = (authorization or "").partition(" ")
    user_id = read_token(token) if scheme.lower() == "bearer" else None
    user = db.get(User, user_id) if user_id else None
    if user is None:
        raise HTTPException(401, "ログインが必要です")
    return user


def admin_user(user: User = Depends(current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(403, "管理者のみ実行できます")
    return user


def user_dict(user: User) -> dict:
    return {
        "id": user.id, "name": user.name, "email": user.email,
        "affiliation": user.affiliation, "can_decide": user.can_decide, "is_admin": user.is_admin,
    }


def load_review(db: Session, review_id: int) -> Review:
    review = db.get(Review, review_id)
    if review is None:
        raise HTTPException(404, "評価が見つかりません")
    return review


def all_items(db: Session) -> list[Item]:
    return list(db.scalars(select(Item).order_by(Item.position)))


def detail(db: Session, review: Review, user: User) -> dict:
    return serialize_detail(review, user, all_items(db))


class LoginBody(BaseModel):
    email: str
    password: str


class UserBody(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8)
    affiliation: str = ""
    can_decide: bool = False
    is_admin: bool = False


class ReviewBody(BaseModel):
    period: str = Field(min_length=1, max_length=50)
    member_id: int
    interviewer_id: int
    manager_id: int
    president_id: int


class SelfItem(BaseModel):
    item_id: int
    score: int | None = Field(default=None, ge=1, le=5)
    comment: str = ""


class SelfBody(BaseModel):
    items: list[SelfItem]


class InterviewerItem(BaseModel):
    item_id: int
    note: str = ""


class InterviewerBody(BaseModel):
    items: list[InterviewerItem]
    overall: str = ""


class EvaluationItem(BaseModel):
    item_id: int
    score: int | None = Field(default=None, ge=1, le=5)
    comment: str = ""


class EvaluationBody(BaseModel):
    items: list[EvaluationItem]
    overall: str = ""


@app.post("/api/login")
def login(body: LoginBody, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "メールアドレスまたはパスワードが正しくありません")
    return {"token": create_token(user.id), "user": user_dict(user)}


@app.get("/api/me")
def me(user: User = Depends(current_user)):
    return user_dict(user)


@app.get("/api/users")
def list_users(_: User = Depends(admin_user), db: Session = Depends(get_db)):
    return [user_dict(u) for u in db.scalars(select(User).order_by(User.id))]


@app.post("/api/users", status_code=201)
def create_user(body: UserBody, _: User = Depends(admin_user), db: Session = Depends(get_db)):
    if db.scalar(select(User.id).where(User.email == body.email)) is not None:
        raise HTTPException(409, "このメールアドレスは既に登録されています")
    user = User(
        name=body.name, email=body.email, affiliation=body.affiliation,
        can_decide=body.can_decide, is_admin=body.is_admin,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    return user_dict(user)


@app.get("/api/reviews")
def list_reviews(user: User = Depends(current_user), db: Session = Depends(get_db)):
    query = select(Review).order_by(Review.id.desc())
    if not user.is_admin:
        query = query.where(or_(
            Review.member_id == user.id,
            Review.interviewer_id == user.id,
            Review.manager_id == user.id,
            Review.president_id == user.id,
        ))
    return [
        {**serialize_summary(r), "roles": sorted(roles_of(user, r))}
        for r in db.scalars(query)
    ]


@app.post("/api/reviews", status_code=201)
def create_review(body: ReviewBody, admin: User = Depends(admin_user), db: Session = Depends(get_db)):
    member, interviewer, manager, president = (
        db.get(User, i) for i in (body.member_id, body.interviewer_id, body.manager_id, body.president_id)
    )
    if None in (member, interviewer, manager, president):
        raise HTTPException(404, "指定されたユーザーが見つかりません")
    if not (manager.can_decide and president.can_decide):
        raise HTTPException(422, "マネージャー・社長に指定できるのは評価権限のあるユーザーのみです")
    if manager.id == president.id:
        raise HTTPException(422, "マネージャーと社長は別のユーザーを指定してください")
    if member.id in (interviewer.id, manager.id, president.id):
        raise HTTPException(422, "本人を面談担当者・マネージャー・社長にはできません")
    review = Review(
        period=body.period, member_id=member.id, interviewer_id=interviewer.id,
        manager_id=manager.id, president_id=president.id,
    )
    db.add(review)
    db.flush()
    attach_items(db, review)
    db.commit()
    return serialize_summary(review)


@app.get("/api/reviews/{review_id}")
def get_review(review_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    review = load_review(db, review_id)
    if not roles_of(user, review):
        raise HTTPException(403, "この評価を閲覧する権限がありません")
    return detail(db, review, user)


def _rows(review: Review) -> dict:
    return {row.item_id: row for row in review.items}


def _check_ids(review: Review, submitted_ids: list[int]) -> None:
    if sorted(submitted_ids) != sorted(_rows(review)):
        raise HTTPException(422, "評価項目が一致しません")


@app.put("/api/reviews/{review_id}/self")
def save_self(review_id: int, body: SelfBody, user: User = Depends(current_user), db: Session = Depends(get_db)):
    review = load_review(db, review_id)
    require_role_and_status(user, review, "member", ["draft"])
    _check_ids(review, [i.item_id for i in body.items])
    rows = _rows(review)
    for item in body.items:
        rows[item.item_id].self_score = item.score
        rows[item.item_id].self_comment = item.comment
    db.commit()
    return detail(db, review, user)


@app.post("/api/reviews/{review_id}/self/submit")
def submit_self(review_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    review = load_review(db, review_id)
    require_role_and_status(user, review, "member", ["draft"])
    if any(row.self_score is None for row in review.items):
        raise HTTPException(422, "すべての項目の評価点を入力してください")
    review.status = "submitted"
    db.commit()
    return detail(db, review, user)


@app.put("/api/reviews/{review_id}/interviewer")
def save_interviewer(review_id: int, body: InterviewerBody, user: User = Depends(current_user), db: Session = Depends(get_db)):
    review = load_review(db, review_id)
    require_role_and_status(user, review, "interviewer", ["submitted"])
    _check_ids(review, [i.item_id for i in body.items])
    rows = _rows(review)
    for item in body.items:
        rows[item.item_id].interviewer_note = item.note
    review.interviewer_overall = body.overall
    db.commit()
    return detail(db, review, user)


@app.post("/api/reviews/{review_id}/interviewer/submit")
def submit_interviewer(review_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    review = load_review(db, review_id)
    require_role_and_status(user, review, "interviewer", ["submitted"])
    review.status = "summarized"
    db.commit()
    return detail(db, review, user)


def _register_evaluation(role: str, required_status: str, next_status: str) -> None:
    score_attr, comment_attr, overall_attr = f"{role}_score", f"{role}_comment", f"{role}_overall"

    @app.put(f"/api/reviews/{{review_id}}/{role}", name=f"save_{role}")
    def save(review_id: int, body: EvaluationBody, user: User = Depends(current_user), db: Session = Depends(get_db)):
        review = load_review(db, review_id)
        require_role_and_status(user, review, role, [required_status])
        _check_ids(review, [i.item_id for i in body.items])
        rows = _rows(review)
        for item in body.items:
            setattr(rows[item.item_id], score_attr, item.score)
            setattr(rows[item.item_id], comment_attr, item.comment)
        setattr(review, overall_attr, body.overall)
        db.commit()
        return detail(db, review, user)

    @app.post(f"/api/reviews/{{review_id}}/{role}/submit", name=f"submit_{role}")
    def submit(review_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
        review = load_review(db, review_id)
        require_role_and_status(user, review, role, [required_status])
        if any(getattr(row, score_attr) is None for row in review.items):
            raise HTTPException(422, "すべての項目の評価点を入力してください")
        review.status = next_status
        db.commit()
        return detail(db, review, user)


_register_evaluation("manager", "summarized", "manager_evaluated")
_register_evaluation("president", "manager_evaluated", "evaluated")


@app.post("/api/reviews/{review_id}/publish")
def publish(review_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    review = load_review(db, review_id)
    require_role_and_status(user, review, "interviewer", ["evaluated"])
    review.status = "published"
    db.commit()
    return detail(db, review, user)


@app.get("/api/statuses")
def statuses():
    return STATUSES


app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
