from flask import render_template, Blueprint
from flask_login import login_required
from app import app


main = Blueprint('main', __name__)


@main.route('/')
@main.route('/index')
@login_required
def index():
    return render_template('main/index.html')
