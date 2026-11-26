"""Home Page: profile (top-left), settings (top-right), logo, Post and Quest buttons."""
from flask import Blueprint, g, redirect, render_template, url_for

bp = Blueprint("main", __name__)


@bp.route("/")
def home():
    if g.user is None:
        return render_template("main/welcome.html")
    if g.user.is_admin:
        return redirect(url_for("admin.dashboard"))
    return render_template("main/home.html", active_tab="home")
