"""Wallet (₱ tab) and Transaction History (receipt tab). Payments are simulated."""
from flask import Blueprint, current_app, flash, g, redirect, render_template, request, url_for
from flask_wtf import FlaskForm
from wtforms import DecimalField, SelectField
from wtforms.validators import DataRequired, NumberRange

from app.extensions import db
from app.models.wallet import CREDIT_KINDS, Transaction
from app.services import quest_service, wallet_service
from app.utils.auth import member_required, verified_required

bp = Blueprint("wallet", __name__, url_prefix="/wallet")

METHODS = [("GCash", "GCash"), ("Maya", "Maya"), ("Bank transfer", "Bank transfer")]
QUICK_AMOUNTS = [100, 200, 500, 1000]


class MoneyForm(FlaskForm):
    amount = DecimalField("Amount", places=2, validators=[
        DataRequired(message="Enter an amount."), NumberRange(min=1, message="Enter at least ₱1.")])
    method = SelectField("Method", choices=METHODS)


@bp.route("/")
@member_required
def index():
    wallet = wallet_service.get_or_create_wallet(g.user.id)
    db.session.commit()
    recent = wallet.transactions.limit(5).all()
    return render_template("wallet/index.html", wallet=wallet, held=quest_service.held_total(g.user.id),
                           recent=recent, active_tab="wallet")


def _money_page(kind: str):
    form = MoneyForm()
    wallet = wallet_service.get_or_create_wallet(g.user.id)
    if form.validate_on_submit():
        try:
            if kind == "deposit":
                tx = wallet_service.deposit(g.user.id, form.amount.data, form.method.data,
                                            current_app.config["MAX_DEPOSIT"])
            else:
                tx = wallet_service.withdraw(g.user.id, form.amount.data, form.method.data,
                                             current_app.config["MAX_WITHDRAW"])
            db.session.commit()
        except wallet_service.WalletError as err:
            db.session.rollback()
            flash(str(err), "danger")
        else:
            verb = "added to" if kind == "deposit" else "withdrawn from"
            flash(f"₱{tx.amount:,.2f} {verb} your wallet. Reference {tx.reference}.", "success")
            return redirect(url_for("wallet.index"))
    return render_template("wallet/money.html", form=form, kind=kind, wallet=wallet,
                           quick=QUICK_AMOUNTS, back_url=url_for("wallet.index"), active_tab="wallet")


@bp.route("/deposit", methods=["GET", "POST"])
@verified_required
def deposit():
    return _money_page("deposit")


@bp.route("/withdraw", methods=["GET", "POST"])
@verified_required
def withdraw():
    return _money_page("withdraw")


@bp.route("/history")
@member_required
def history():
    wallet = wallet_service.get_or_create_wallet(g.user.id)
    db.session.commit()
    flow = request.args.get("flow", "all")
    query = wallet.transactions
    if flow == "in":
        query = query.filter(Transaction.kind.in_(CREDIT_KINDS))
    elif flow == "out":
        query = query.filter(Transaction.kind.notin_(CREDIT_KINDS))
    else:
        flow = "all"
    return render_template("wallet/history.html", items=query.limit(300).all(), flow=flow,
                           wallet=wallet, active_tab="history")
