import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    DATA_DIR.mkdir(exist_ok=True)
    DATABASE_URL = f"sqlite:///{DATA_DIR / 'app.db'}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

# 評価の進行順。後ろの状態ほど先に進んでいる
STATUSES = ["draft", "submitted", "summarized", "manager_evaluated", "evaluated", "published"]


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    affiliation: Mapped[str] = mapped_column(String(100), default="")
    # マネージャー・社長として評価を担当できるか
    can_decide: Mapped[bool] = mapped_column(default=False)
    is_admin: Mapped[bool] = mapped_column(default=False)


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    position: Mapped[int] = mapped_column(unique=True)
    title: Mapped[str] = mapped_column(String(100))
    # 1〜5の各評価基準を改行区切りで保持する
    anchors: Mapped[str] = mapped_column(Text)


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    period: Mapped[str] = mapped_column(String(50))
    member_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    interviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    manager_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    president_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(20), default="draft")
    interviewer_overall: Mapped[str] = mapped_column(Text, default="")
    manager_overall: Mapped[str] = mapped_column(Text, default="")
    president_overall: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    member: Mapped[User] = relationship(foreign_keys=[member_id])
    interviewer: Mapped[User] = relationship(foreign_keys=[interviewer_id])
    manager: Mapped[User] = relationship(foreign_keys=[manager_id])
    president: Mapped[User] = relationship(foreign_keys=[president_id])
    items: Mapped[list["ReviewItem"]] = relationship(
        back_populates="review", cascade="all, delete-orphan", order_by="ReviewItem.item_id"
    )


class ReviewItem(Base):
    __tablename__ = "review_items"
    __table_args__ = (UniqueConstraint("review_id", "item_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    review_id: Mapped[int] = mapped_column(ForeignKey("reviews.id"))
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"))
    self_score: Mapped[int | None] = mapped_column(default=None)
    self_comment: Mapped[str] = mapped_column(Text, default="")
    interviewer_note: Mapped[str] = mapped_column(Text, default="")
    manager_score: Mapped[int | None] = mapped_column(default=None)
    manager_comment: Mapped[str] = mapped_column(Text, default="")
    president_score: Mapped[int | None] = mapped_column(default=None)
    president_comment: Mapped[str] = mapped_column(Text, default="")

    review: Mapped[Review] = relationship(back_populates="items")
