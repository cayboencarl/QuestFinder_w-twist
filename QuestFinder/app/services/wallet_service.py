"""Wallet operations. Every balance change goes through here and writes a Transaction.

Rows are locked with SELECT ... FOR UPDATE so two requests can never spend
the same pesos twice. Callers are responsible for db.session.commit().
"""
import secrets
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from app.extensions import db
from app.models.wallet import (
    TX_DEPOSIT, TX_QUEST_EARNING, TX_QUEST_HOLD, TX_QUEST_REFUND, TX_WITHDRAW,
    Transaction, Wallet,
)

CENT = Decimal("0.01")


class WalletError(Exception):
    """Raised for business-rule violations (shown to the user as a flash message)."""


def to_money(value) -> Decimal:
    try:
        amount = Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        raise WalletError("Enter a valid amount.")
    if not amount.is_finite():
        raise WalletError("Enter a valid amount.")
    return amount


def get_or_create_wallet(user_id: int) -> Wallet:
    wallet = Wallet.query.filter_by(user_id=user_id).first()
    if wallet is None:
        wallet = Wallet(user_id=user_id, balance=Decimal("0.00"))
        db.session.add(wallet)
        db.session.flush()
    return wallet


def _locked_wallet(user_id: int) -> Wallet:
    get_or_create_wallet(user_id)
    return Wallet.query.filter_by(user_id=user_id).with_for_update().one()


def _record(wallet: Wallet, kind: str, amount: Decimal, *, quest_id=None, method=None, note=None
            ) -> Transaction:
    tx = Transaction(
        wallet_id=wallet.id, kind=kind, amount=amount, balance_after=wallet.balance,
        quest_id=quest_id, method=method, note=note,
        reference="QF" + secrets.token_hex(6).upper(),
    )
    db.session.add(tx)
    return tx


def _credit(user_id: int, amount: Decimal, kind: str, **kw) -> Transaction:
    if amount <= 0:
        raise WalletError("Amount must be greater than ₱0.")
    wallet = _locked_wallet(user_id)
    wallet.balance = (wallet.balance or Decimal("0")) + amount
    return _record(wallet, kind, amount, **kw)


def _debit(user_id: int, amount: Decimal, kind: str, insufficient_msg: str, **kw) -> Transaction:
    if amount <= 0:
        raise WalletError("Amount must be greater than ₱0.")
    wallet = _locked_wallet(user_id)
    if wallet.balance < amount:
        raise WalletError(insufficient_msg)
    wallet.balance = wallet.balance - amount
    return _record(wallet, kind, amount, **kw)


# --- Public operations ---------------------------------------------------------

def deposit(user_id: int, amount, method: str, max_amount: float) -> Transaction:
    amount = to_money(amount)
    if amount > Decimal(str(max_amount)):
        raise WalletError(f"The maximum deposit is ₱{max_amount:,.0f} per transaction.")
    return _credit(user_id, amount, TX_DEPOSIT, method=method, note=f"Deposit via {method} (simulated)")


def withdraw(user_id: int, amount, method: str, max_amount: float) -> Transaction:
    amount = to_money(amount)
    if amount > Decimal(str(max_amount)):
        raise WalletError(f"The maximum withdrawal is ₱{max_amount:,.0f} per transaction.")
    return _debit(user_id, amount, TX_WITHDRAW, "Your balance is not enough for this withdrawal.",
                  method=method, note=f"Withdrawal to {method} (simulated)")


def hold_for_quest(client_id: int, quest) -> Transaction:
    """Reserve the quest pay from the client's wallet when a worker is accepted."""
    return _debit(client_id, to_money(quest.pay), TX_QUEST_HOLD,
                  "Your wallet balance is not enough to reserve this quest's pay. Please deposit first.",
                  quest_id=quest.id, note=f"Reserved for quest: {quest.title}")


def release_to_worker(worker_id: int, quest) -> Transaction:
    """Pay the worker on completion (the amount was already taken from the client)."""
    return _credit(worker_id, to_money(quest.pay), TX_QUEST_EARNING,
                   quest_id=quest.id, note=f"Payment for quest: {quest.title}")


def refund_to_client(client_id: int, quest) -> Transaction:
    return _credit(client_id, to_money(quest.pay), TX_QUEST_REFUND,
                   quest_id=quest.id, note=f"Returned from quest: {quest.title}")
