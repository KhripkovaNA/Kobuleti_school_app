from flask import request, flash
from flask_login import login_required, current_user
from app import db
from app.school import school
from .models import Person


@school.route('/add-comment', methods=['POST'])
@login_required
def add_comment():
    if current_user.rights in ["admin", "user"]:
        person_id = int(request.form.get('person_id'))
        comment = request.form.get('comment')
        person = Person.query.filter_by(id=person_id).first()
        person.comment = comment
        db.session.commit()

        return comment

    else:
        flash('Нет прав администратора', 'error')
        return
