from flask import render_template, Blueprint, request, flash, redirect
from flask_login import login_required, current_user
from app import db
from app.main.service import del_record


main = Blueprint('main', __name__)


@main.route('/')
@main.route('/index')
@login_required
def index():
    return render_template('main/index.html')


@main.route('/delete-record', methods=['POST'])
@login_required
def delete_record():
    record_type = request.form.get('record_type')

    try:
        if record_type in ['student', 'employee', 'fin_operation', 'subscription']:
            if current_user.rights == 'admin':
                message = del_record(request.form, record_type, current_user)
                db.session.commit()
                flash(message[0], message[1])

            else:
                flash('Необходимо обладать правами руководителя', 'error')

        else:
            if current_user.rights in ["admin", "user"]:
                message = del_record(request.form, record_type, current_user)
                db.session.commit()
                if type(message) == list:
                    for mes in message:
                        flash(mes[0], mes[1])
                else:
                    flash(message[0], message[1])

            else:
                flash('Необходимо обладать правами администратора', 'error')

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении: {str(e)}', 'error')

    return redirect(request.referrer)
