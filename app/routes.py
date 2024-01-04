from flask import render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from app.models import User, Person, Subject, Room, Lesson, SubjectType, SchoolClass
from app.app_functions import add_child, add_adult, basic_student_info, extensive_student_info, \
    handle_student_edit, clients_data, week_lessons_dict, filter_lessons, copy_lessons, \
    week_school_lessons_dict, show_lesson, handle_lesson, class_students_info, subscription_subjects_data, \
    purchase_subscription, lesson_subjects_data
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
    all_students = Person.query.filter(Person.status.isnot(None)).order_by(Person.last_name, Person.first_name).all()

    for student in all_students:
        basic_student_info(student)
    subscription_subjects = subscription_subjects_data()
    today = datetime.now().date().strftime("%d.%m.%Y")
    lesson_subjects = lesson_subjects_data()

    return render_template('students.html', students=all_students,
                           subscription_subjects=subscription_subjects, today=today,
                           lesson_subjects=lesson_subjects)


@app.route('/add-comment', methods=['POST'])
@login_required
def add_comment():
    person_id = int(request.form.get('person_id'))
    comment = request.form.get('comment')
    person = Person.query.filter_by(id=person_id).first()
    person.comment = comment
    db.session.commit()

    return comment


@app.route('/deposit/<string:student_id>', methods=['POST'])
@login_required
def deposit(student_id):
    try:
        deposit = int(request.form.get('deposit'))
        student = Person.query.filter_by(id=student_id).first()
        student.balance += deposit
        db.session.commit()
        flash('Депозит внесен на счет.', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при внесении депозита: {str(e)}', 'error')

    return redirect(url_for('students'))


@app.route('/subscription/<string:student_id>', methods=['POST'])
@login_required
def subscription(student_id):
    try:
        new_subscription = purchase_subscription(request.form, student_id)
        db.session.add(new_subscription)
        db.session.commit()
        flash('Новый абонемент добавлен в систему.', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при добавлении абонемента: {str(e)}', 'error')

    return redirect(url_for('student, student_id=student_id'))


@app.route('/add-student', methods=['GET', 'POST'])
@login_required
def add_student():
    if request.method == 'POST':
        try:
            if 'add_child_btn' in request.form:
                student = add_child(request.form)

                flash('Новый клиент добавлен в систему.', 'success')
                return redirect(url_for('show_student', student_id=student.id))

            if 'add_adult_btn' in request.form:
                client = add_adult(request.form)

                flash('Новый клиент добавлен в систему.', 'success')
                return redirect(url_for('show_edit_student', student_id=client.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при добавлении киента: {str(e)}', 'error')
            return redirect(url_for('add_student'))

    clients = clients_data('child')
    possible_clients = clients_data('adult')

    return render_template('add_student.html', clients=clients, possible_clients=possible_clients)


@app.route('/student/<string:student_id>', methods=['GET', 'POST'])
@login_required
def show_edit_student(student_id):
    student = Person.query.filter_by(id=student_id).first()
    if student:
        extensive_student_info(student)
        clients = clients_data('child')

        if request.method == 'POST':
            try:
                handle_student_edit(request.form, student)
                flash('Изменения внесены.', 'success')
                return redirect(url_for('show_edit_student', student_id=student.id))
            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при внесении изменений: {str(e)}', 'error')
                return redirect(url_for('show_edit_student', student_id=student.id))

        return render_template('student.html', student=student, clients=clients)
    else:
        flash("Такого клиента нет", 'error')
        return redirect(url_for('students.html'))


# @app.route('/edit-student/<string:student_id>', methods=['GET', 'POST'])
# @login_required
# def edit_student(student_id):
#     student = Person.query.filter_by(id=student_id).first()
#     if student:
#         extensive_student_info(student)
#     clients = clients_data()
#
#     return render_template('edit_student.html', student=student, clients=clients)


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
    school = SubjectType.query.filter_by(name='school').first()
    all_subjects = Subject.query.filter(Subject.subject_type_id != school.id).order_by(Subject.name).all()
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
    week_lessons = week_lessons_dict(week, rooms, DAYS_OF_WEEK)

    return render_template('timetable.html', days=DAYS_OF_WEEK, rooms=rooms,
                           classes=week_lessons, week=week)


@app.route('/school-timetable/<string:week>')
@login_required
def school_timetable(week):
    week = int(week)
    school_classes = SchoolClass.query.order_by(SchoolClass.school_class).all()
    week_school_lessons = week_school_lessons_dict(week, school_classes, DAYS_OF_WEEK)
    return render_template('school_timetable.html', days=DAYS_OF_WEEK, school_classes=school_classes,
                           classes=week_school_lessons, week=week, week_day=DAYS_OF_WEEK[0])


@app.route('/lesson/<string:subject_id>/<string:lesson_id>', methods=['GET', 'POST'])
@login_required
def lesson(subject_id, lesson_id):
    lesson_subject = Subject.query.filter_by(id=subject_id).first()
    if lesson_subject.subject_type.name == 'school':
        return redirect(url_for('school_lesson', lesson_id=lesson_id))
    subject_lesson = show_lesson(lesson_subject, lesson_id)

    if request.method == 'POST':
        handle_lesson(request.form, lesson_subject, subject_lesson)

        return redirect(url_for('lesson', subject_id=subject_id, lesson_id=subject_lesson.id))

    all_clients = Person.query.filter(Person.status.in_(["Клиент", "Лид"])).order_by(Person.last_name,
                                                                                     Person.first_name).all()
    possible_clients = [client for client in all_clients if client not in subject_lesson.students]

    return render_template('lesson.html', subject_lesson=subject_lesson, clients=possible_clients,
                           lesson_subject=lesson_subject)


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


@app.route('/school-students')
@login_required
def school_students():
    school_classes = SchoolClass.query.order_by(SchoolClass.school_class).all()
    school_classes_dict = {}
    for school_class in school_classes:
        school_classes_dict[school_class.school_name] = class_students_info(school_class)

    return render_template('school_students.html', school_classes=school_classes,
                           class_students=school_classes_dict)


# @app.route('/lesson/<string:subject_id>/<string:lesson_id>', methods=['GET', 'POST'])
# @login_required
# def lesson(subject_id, lesson_id):
#     subject_id = int(subject_id)
#     if not lesson_id:
#         today = datetime.now().date()
#         last_lesson = Lesson.query.filter_by(subject_id=subject_id). \
#             order_by(Lesson.date.desc(), Lesson.start_time.desc()).first()
#         coming_lesson = Lesson.query.filter(Lesson.date >= today,
#                                           Lesson.subject_id == subject_id). \
#             order_by(Lesson.date, Lesson.start_time).first()
#         extra_lesson = coming_lesson if coming_lesson else last_lesson if last_lesson else None
#     else:
#         lesson_id = int(lesson_id)
#         extra_lesson = Lesson.query.filter_by(id=lesson_id).first()
#     if extra_lesson:
#         previous_lesson = Lesson.query.filter(Lesson.date >= extra_lesson.date,
#                                               Lesson.subject_id == extra_lesson.subject_id)\
#             .order_by(Lesson.date, Lesson.start_time).first()
#         next_lesson = Lesson.query.filter(Lesson.date <= extra_lesson.date,
#                                           Lesson.subject_id == extra_lesson.subject_id) \
#             .order_by(Lesson.date.desc(), Lesson.start_time.desc()).first()
#     previous_lesson_id = previous_lesson.id if previous_lesson else 'no_lesson'
#     next_lesson_id = next_lesson.id if next_lesson else 'no_lesson'


@app.route('/school-lesson/<string:lesson_id>')
@login_required
def school_lesson(lesson_id):
    sc_lesson = Lesson.query.filter_by(id=lesson_id).first()
    classes = [cl.school_name for cl in sc_lesson.school_classes]
    sc_lesson.classes = ', '.join([cl.school_name for cl in sc_lesson.school_classes])
    lesson_students = Person.query.filter(
        Person.subjects.any(Subject.id == sc_lesson.subject_id),
        Person.school_class.has(SchoolClass.school_name.in_(classes))
    ).order_by(Person.last_name).all()

    for student in lesson_students:
        student.attended = ''
        student.grade = ''
        student.school_comment = ''
    days_dict = {day_num: day for (day_num, day) in enumerate(DAYS_OF_WEEK)}
    sc_students = Person.query.filter(Person.school_class_id.is_not(None)).all()
    return render_template('school_lesson.html', school_lesson=sc_lesson, days_dict=days_dict,
                           lesson_students=lesson_students, school_students=sc_students)


# @app.route('/add-lesson', methods=['GET', 'POST'])
# @login_required
# def add_lesson():
#     if request.method == 'POST':
#         try:
#             filtered_lessons, new_week = filter_lessons(request.form)
#             new_lessons, conflicts = copy_lessons(filtered_lessons, new_week)
#             db.session.add_all(new_lessons)
#             db.session.commit()
#             if conflicts == 0:
#                 flash('Все занятия добавлены в расписание.', 'success')
#             elif not new_lessons:
#                 flash(f'Занятия не добавлены, т.к. есть занятия в это же время.', 'error')
#             else:
#                 flash(f'Добавлено занятий: {len(new_lessons)}', 'success')
#                 flash(f'Не добавлено занятий: {conflicts}, т.к. есть занятия в это же время', 'error')
#             return redirect(url_for('timetable', week=new_week))
#
#         except Exception as e:
#             db.session.rollback()
#             flash(f'Ошибка при добавлении новых занятий: {str(e)}', 'error')
#             return redirect(url_for('timetable', week=0))
#
#     subject_types = SubjectType.query.all()
#     rooms = Room.query.all()
#     school_classes = SchoolClass.query.order_by(SchoolClass.school_name).all()
#     all_teachers = Person.query.filter_by(teacher=True).order_by(Person.last_name).all()
#     return render_template('add_lessons.html', days=DAYS_OF_WEEK, subject_types=subject_types,
#                            rooms=rooms, school_classes=school_classes, teachers=all_teachers)
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
