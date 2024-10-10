from flask import request, flash
from flask_login import login_required, current_user
from app import db
from .models import Person
from flask import Blueprint


school = Blueprint('school', __name__)


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


from .employees.routes import school_employees
school.register_blueprint(school_employees)

from .students.routes import school_students
school.register_blueprint(school_students)

from .subjects.routes import school_subjects
school.register_blueprint(school_subjects)
