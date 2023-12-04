from flask import render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from app.models import User, Person, Subject, Room, Lesson, SubjectType, SchoolClass
from app.app_functions import create_student, handle_contact_info, basic_student_info, \
    extensive_student_info, clients_data, week_lessons_dict, filter_lessons, copy_lessons
from app import app, db
from datetime import datetime, timedelta


DAYS_OF_WEEK = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"]


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('students'))
    if request.method == "POST":
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user is None or not user.check_password(request.form.get('password')):
            flash('Неправильное имя пользователя или пароль', "error")
            return redirect(url_for('login'))
        login_user(user)
        flash('Вы успешно вошли в систему.', "success")
        return redirect(url_for('students'))
    return render_template('login.html')


@app.route('/logout')
def logout():
    logout_user()
    flash('Вы вышли из системы.', "success")
    return redirect(url_for('login'))


@app.route('/')
@app.route('/students')
@login_required
def students():
    all_students = Person.query.filter_by(person_type="Ребенок").order_by(Person.last_name).all()

    for student in all_students:
        basic_student_info(student)

    return render_template('students.html', students=all_students)


@app.route('/add-comment', methods=['POST'])
@login_required
def add_comment():
    person_id = int(request.form.get('person_id'))
    comment = request.form.get('comment')
    person = Person.query.filter_by(id=person_id).first()
    person.comment = comment
    db.session.commit()

    return comment


@app.route('/add-student', methods=['GET', 'POST'])
@login_required
def add_student():
    if request.method == 'POST':

        try:
            student = create_student(request.form)
            db.session.add(student)
            db.session.commit()

            contact_count = int(request.form['contact_count'])
            for i in range(1, contact_count + 1):
                handle_contact_info(request.form, student, i)

            flash('Новый ученик добавлен в систему.', 'success')
            return redirect(url_for('students'))

        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при добавлении ученика: {str(e)}', 'error')
            return redirect(url_for('add_student'))

    clients = clients_data()

    return render_template('add_student.html', clients=clients)


@app.route('/student/<string:student_id>')
@login_required
def show_student(student_id):
    student = Person.query.filter_by(id=student_id).first()
    if student:
        extensive_student_info(student)

        return render_template('student.html', student=student)
    else:
        flash("Такого клиента нет")
        return redirect(url_for('students.html'))


@app.route('/edit-student/<string:student_id>', methods=['GET', 'POST'])
@login_required
def edit_student(student_id):
    student = Person.query.filter_by(id=student_id).first()
    if student:
        extensive_student_info(student)
    clients = clients_data()

    return render_template('edit_student.html', student=student, clients=clients)


@app.route('/teachers')
@login_required
def teachers():
    all_teachers = Person.query.filter_by(teacher=True).order_by(Person.last_name).all()

    for teacher in all_teachers:
        if teacher.contacts[0].telegram:
            teacher.contact = f"Телеграм: {teacher.contacts[0].telegram}"
        elif teacher.contacts[0].phone:
            teacher.contact = f"Тел.: {teacher.contacts[0].phone}"
        elif teacher.contacts[0].other_contact:
            teacher.contact = teacher.contacts[0].other_contact

    return render_template('teachers.html', teachers=all_teachers)


@app.route('/subjects')
@login_required
def subjects():
    all_subjects = Subject.query.filter(~Subject.subject_types.any(name='school')).all()
    for subject in all_subjects:
        subscription_types = []
        for subscription_type in subject.subscription_types.all():
            if subscription_type.lessons:
                type_of_subscription = f"{subscription_type.lessons} занятий за {subscription_type.price:.0f} " \
                                       f"({subscription_type.duration} дней)"
                subscription_types.append(type_of_subscription)
            elif subscription_type.period:
                type_of_subscription2 = f"{subscription_type.price:.0f} за {subscription_type.period}"
                subscription_types.append(type_of_subscription2)
        subject.types_of_subscription = subscription_types

    return render_template('subjects.html', subjects=all_subjects)


@app.route('/timetable/<string:week>')
@login_required
def timetable(week):
    week = int(week)
    rooms = Room.query.all()
    current_week_lessons = week_lessons_dict(week, rooms, DAYS_OF_WEEK)

    return render_template('time_table.html', days=DAYS_OF_WEEK, rooms=rooms,
                           classes=current_week_lessons, week=week)


@app.route('/lesson/<string:subject_id>/<string:param>', methods=['GET', 'POST'])
@login_required
def lesson(subject_id, param):
    if request.method == 'POST':
        lesson_subject = Subject.query.filter_by(id=subject_id).first()
        subject_lesson_id = int(request.form['subject_lesson_id'])
        subject_lesson = Lesson.query.filter_by(id=subject_lesson_id).first()
        if 'del_client_btn' in request.form:
            del_client_id = int(request.form['del_client_btn'])
            del_client = Person.query.filter_by(id=del_client_id).first()
            lesson_subject.students.remove(del_client)
            db.session.commit()
        if 'add_client_btn' in request.form:
            new_client_id = int(request.form['added_client_id'])
            new_client = Person.query.filter_by(id=new_client_id).first()
            lesson_subject.students.append(new_client)
            db.session.commit()
        if 'registered_btn' in request.form:
            for client in lesson_subject.students:
                if (
                        client not in subject_lesson.students_registered
                        and request.form.get(f'registered_{client.id}') == 'on'
                ):
                    subject_lesson.students_registered.append(client)
                    db.session.commit()
                elif (
                        client in subject_lesson.students_registered
                        and not request.form.get(f'registered_{client.id}')
                ):
                    subject_lesson.students_registered.remove(client)
                    db.session.commit()

        if 'attended_btn' in request.form:
            for key in request.form.keys():
                if key.startswith('attending_status_'):
                    client_id = int(key[len('attending_status_'):])
                    attending_client = Person.query.filter_by(id=client_id).first()
                    if request.form[key] == 'attend':
                        subject_lesson.students_attended.append(attending_client)
                        db.session.commit()
        return redirect(url_for('lesson', subject_id=subject_id, param=param))

    param = int(param)
    today = datetime.now().date()

    lesson_subject = Subject.query.filter_by(id=subject_id).first()
    if param < 0:
        subject_lessons = Lesson.query.filter(Lesson.date < today,
                                              Lesson.subject_id == lesson_subject.id).\
            order_by(Lesson.date.desc(), Lesson.start_time.desc()).all()
        order_param = abs(param) - 1
    else:
        subject_lessons = Lesson.query.filter(Lesson.date >= today,
                                              Lesson.subject_id == lesson_subject.id).\
            order_by(Lesson.date, Lesson.start_time).all()
        order_param = param
    subject_lesson = subject_lessons[order_param] if order_param < len(subject_lessons) else None
    all_clients = Person.query.filter(Person.status.in_(["Клиент", "Лид"])).order_by(Person.last_name).all()
    possible_clients = [client for client in all_clients if client not in lesson_subject.students]

    return render_template('lesson.html', subject_lesson=subject_lesson, clients=possible_clients,
                           lesson_subject=lesson_subject, param=param)


@app.route('/add-lessons', methods=['GET', 'POST'])
@login_required
def add_lessons():
    if request.method == 'POST':
        try:
            filtered_lessons, new_week = filter_lessons(request.form)
            new_lessons, conflicts = copy_lessons(filtered_lessons, new_week)
            db.session.add_all(new_lessons)
            db.session.commit()
            if conflicts == 0:
                flash('Все занятия добавлены в расписание.', 'success')
            elif not new_lessons:
                flash(f'Занятия не добавлены, т.к. есть занятия в это же время.', 'error')
            else:
                flash(f'Добавлено занятий: {len(new_lessons)}', 'success')
                flash(f'Не добавлено занятий: {conflicts}, т.к. есть занятия в это же время', 'error')
            return redirect(url_for('timetable', week=new_week))

        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при добавлении новых занятий: {str(e)}', 'error')
            return redirect(url_for('timetable', week=0))

    subject_types = SubjectType.query.all()
    rooms = Room.query.all()
    school_classes = SchoolClass.query.order_by(SchoolClass.school_name).all()
    all_teachers = Person.query.filter_by(teacher=True).order_by(Person.last_name).all()
    return render_template('add_lessons.html', days=DAYS_OF_WEEK, subject_types=subject_types,
                           rooms=rooms, school_classes=school_classes, teachers=all_teachers)


#     if request.method == 'POST':
#         try:
#             new_lesson = create_lesson(request.form)
#             db.session.add(new_lesson)
#             db.session.commit()
#
#             flash('Новый урок добавлен в расписание.', 'success')
#             return redirect(url_for('students'))
#
#         except Exception as e:
#             db.session.rollback()
#             flash(f'Ошибка при добавлении нового урока: {str(e)}', 'error')
#             return redirect(url_for('add_lesson'))
#
#     all_subjects = Subject.query.order_by(Subject.name).all()
#     all_rooms = Room.query.all()
#     all_teachers = Person.query.filter_by(teacher=True).order_by(Person.last_name).all()
#
#     return render_template('add_lesson.html', subjects=all_subjects, rooms=all_rooms, teachers=all_teachers)
