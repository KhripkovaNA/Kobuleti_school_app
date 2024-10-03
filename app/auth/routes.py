from flask import render_template, flash, redirect, url_for, Blueprint
from flask_login import login_user, logout_user, current_user
from app import db
from app.app_functions import user_action
from app.auth.forms import LoginForm
from app.auth.models import User


auth = Blueprint('auth', __name__)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Неправильное имя пользователя или пароль', "error")
            return redirect(url_for('login'))

        login_user(user)
        user_action(user, "Вход в систему")
        db.session.commit()
        flash('Вы успешно вошли в систему', "success")
        return redirect(url_for('index'))

    return render_template('auth/login.html', form=form)


@auth.route('/logout')
def logout():
    if current_user.is_authenticated:
        user_action(current_user, "Выход из системы")
        db.session.commit()
        logout_user()
        flash('Вы вышли из системы', "success")

    return redirect(url_for('auth/login.html'))
