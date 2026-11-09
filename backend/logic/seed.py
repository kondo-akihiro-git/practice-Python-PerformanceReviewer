import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from logic.security import hash_password
from model.models import Item, Review, ReviewItem, User

# 既存のGoogleフォームの評価項目（1〜5の評価基準）
ITEMS = [
    ("週報", [
        "ほとんど週報を提出していない",
        "週報の提出日を過ぎてしまうことが多く、内容も薄いものになっている",
        "週報の提出日を順守し、内容も豊富に記載している",
        "週報の提出日の順守だけでなく、内容を充実させ、上位者が必要な情報を細やかに共有している",
        "週報に取り組む姿勢や内容が模範的である",
    ]),
    ("行動（勤怠）", [
        "会社が求めることへはほとんど対応せず、風評を流している",
        "会社からの依頼事項への対応など、会社が求めることへは必要最低限のことしか行っていない",
        "会社からの依頼事項への対応など、会社が求めることへ協力をしている",
        "会社が求めることだけでなく、会社の成長や活性化に寄与するアイデア等の提案や取り組みを行っている",
        "自分の提案や取り組みが会社で採用され、会社の活性化や利益アップに貢献をしている",
    ]),
    ("参加", [
        "会社の行事やイベントや同好会に参加していない",
        "会社の行事やイベントや同好会にはあまり積極的には参加していない",
        "会社の行事やイベントや同好会などに積極的に参加している",
        "会社の行事やイベント、同好会に積極的に参加するだけでなく、他の社員と積極的にコミュニケーションを取り、関係性を良くするために努めている",
        "会社の行事やイベントなどでは、運営側のサポートを行ったり、他の社員にも積極的に参加するよう働きかけている",
    ]),
    ("自己啓発・学習", [
        "現在の業務遂行に必要な知識やスキルを獲得する姿勢が見られない",
        "現在の業務遂行に必要な知識やスキルを獲得する努力が不足している",
        "現在の業務遂行に必要な知識やスキルを獲得できるように努めている",
        "現在の業務遂行に必要な知識やスキルを獲得するための努力には目を見張るものがある",
        "現在の業務遂行に必要なものだけではなく、未来を見据えた知識やスキルを獲得するための努力をし、成果物を出している",
    ]),
    ("人間関係", [
        "自分本位なところがあり、チームメンバー等と協力的に仕事をすすめることができていない",
        "相手によって、良い関係を築ける場合とそうでない場合があり、業務遂行において支障を生じることがある",
        "人間関係において特段の問題も無く、誰とでも協力して業務を進めている",
        "新しいプロジェクトへの参加や新しいメンバーの参加などの際も、比較的早くに良い人間関係を作れている",
        "顧客やプロジェクトメンバーに自ら進んで関係性をつくり、顧客から重要な仕事を任されたり、リーダー的ポジションを獲得している",
    ]),
    ("スキルアップ", [
        "努力が足りなくスキルがとても不足している",
        "経験年数からはスキルがやや不足している",
        "経験年数に応じたスキルを保有している",
        "多くのプロジェクトやタスクを遂行できるスキルを保有している",
        "他のメンバーが保有するのが難しい高度なスキルを保有している",
    ]),
    ("報連相", [
        "報連相が不十分なために、顧客へ迷惑をかけてしまっている",
        "事後報告での連絡になってしまうことなどが多少ある。または、相談のタイミングが遅い",
        "報連相をしないことでの問題などはほとんどなかった",
        "顧客・営業・本社から催促されることなく、適切なタイミングで報連相を行っている",
        "自分自身の報連相だけでなく、他のメンバーにも報連相を促したり、模範的な報連相をすることができる",
    ]),
    ("業務遂行", [
        "顧客から求められるプロジェクトやタスクにやや遅れがある",
        "顧客から求められるプロジェクトやタスクをにやや遅れなどあるが、挽回する手立てを講じている",
        "顧客から求められるプロジェクトやタスクを滞りなく遂行している",
        "顧客から求められるプロジェクトやタスクを遂行するだけでなく、スピード・クオリティが上がる改善やリスク相談を行っている",
        "顧客から仕事ぶりを評価され、リーダー的なポジションや新たなプロジェクトやタスクを任されている",
    ]),
]

# ローカル動作確認専用のデモアカウント。本番では SEED_DEMO=0 とし、管理者を別途作成すること
DEMO_PASSWORD = "password"
DEMO_USERS = [
    ("管理者", "admin@example.com", "管理部", True, False),
    ("社長", "president@example.com", "経営", False, True),
    ("マネージャー 三郎", "manager@example.com", "開発部", False, True),
    ("面談 太郎", "interviewer@example.com", "開発部", False, False),
    ("メンバー 花子", "member1@example.com", "プログラマー", False, False),
    ("メンバー 次郎", "member2@example.com", "webデザインフロントエンドエンジニア", False, False),
]


def seed_items(db: Session) -> None:
    if db.scalar(select(Item.id).limit(1)) is not None:
        return
    for position, (title, anchors) in enumerate(ITEMS, start=1):
        db.add(Item(position=position, title=title, anchors="\n".join(anchors)))
    db.commit()


def seed_demo(db: Session) -> None:
    if os.environ.get("SEED_DEMO", "1") != "1" or db.scalar(select(User.id).limit(1)) is not None:
        return
    users = {}
    for name, email, affiliation, is_admin, can_decide in DEMO_USERS:
        user = User(
            name=name, email=email, affiliation=affiliation,
            is_admin=is_admin, can_decide=can_decide,
            password_hash=hash_password(DEMO_PASSWORD),
        )
        db.add(user)
        users[email] = user
    db.flush()
    review = Review(
        period="2026年 下期",
        member_id=users["member1@example.com"].id,
        interviewer_id=users["interviewer@example.com"].id,
        manager_id=users["manager@example.com"].id,
        president_id=users["president@example.com"].id,
    )
    db.add(review)
    db.flush()
    attach_items(db, review)
    db.commit()


def attach_items(db: Session, review: Review) -> None:
    for item_id in db.scalars(select(Item.id).order_by(Item.position)):
        db.add(ReviewItem(review_id=review.id, item_id=item_id))
