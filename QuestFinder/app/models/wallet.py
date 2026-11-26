"""Digital wallet (simulated) and its transaction history."""
from decimal import Decimal

from app.extensions import db
from app.models.base import TimestampMixin, utcnow

TX_DEPOSIT = "deposit"
TX_WITHDRAW = "withdraw"
TX_QUEST_HOLD = "quest_hold"        # client's pay reserved when a worker is accepted
TX_QUEST_REFUND = "quest_refund"    # reserved pay returned to the client
TX_QUEST_EARNING = "quest_earning"  # pay released to the worker on completion
TX_KINDS = (TX_DEPOSIT, TX_WITHDRAW, TX_QUEST_HOLD, TX_QUEST_REFUND, TX_QUEST_EARNING)

TX_LABELS = {
    TX_DEPOSIT: "Deposit",
    TX_WITHDRAW: "Withdrawal",
    TX_QUEST_HOLD: "Quest payment reserved",
    TX_QUEST_REFUND: "Quest payment returned",
    TX_QUEST_EARNING: "Quest earning",
}

CREDIT_KINDS = {TX_DEPOSIT, TX_QUEST_REFUND, TX_QUEST_EARNING}


class Wallet(TimestampMixin, db.Model):
    __tablename__ = "wallets"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
                        nullable=False, unique=True)
    balance = db.Column(db.Numeric(12, 2), nullable=False, default=Decimal("0.00"))

    user = db.relationship("User", back_populates="wallet")
    transactions = db.relationship("Transaction", back_populates="wallet", lazy="dynamic",
                                   order_by="Transaction.created_at.desc()",
                                   cascade="all, delete-orphan")

    __table_args__ = (db.CheckConstraint("balance >= 0", name="ck_wallets_balance_nonneg"),)


class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    wallet_id = db.Column(db.Integer, db.ForeignKey("wallets.id", ondelete="CASCADE"),
                          nullable=False, index=True)
    kind = db.Column(db.String(15), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)  # always positive
    balance_after = db.Column(db.Numeric(12, 2), nullable=False)
    quest_id = db.Column(db.Integer, db.ForeignKey("quests.id", ondelete="SET NULL"), index=True)
    method = db.Column(db.String(30))  # e.g. GCash / Maya / Bank (simulated)
    reference = db.Column(db.String(32), nullable=False, unique=True)
    note = db.Column(db.String(255))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)

    wallet = db.relationship("Wallet", back_populates="transactions")
    quest = db.relationship("Quest")

    __table_args__ = (
        db.CheckConstraint("amount > 0", name="ck_transactions_amount_positive"),
        db.CheckConstraint("kind IN (" + ", ".join(f"'{k}'" for k in TX_KINDS) + ")",
                           name="ck_transactions_kind"),
    )

    @property
    def is_credit(self) -> bool:
        return self.kind in CREDIT_KINDS

    @property
    def label(self) -> str:
        return TX_LABELS.get(self.kind, self.kind)
