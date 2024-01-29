from flask import render_template, flash, redirect, url_for, request
from flask_login import login_user, logout_user, current_user, login_required
from app.models import User, Person, Employee, Lesson, SubjectType, Subject, Room, SchoolClass, SubscriptionType, \
    teacher_class_table
from app.app_functions import DAYS_OF_WEEK, TODAY, basic_student_info, subscription_subjects_data, \
    lesson_subjects_data, purchase_subscription, add_child, add_adult, clients_data, extensive_student_info, \
    student_lesson_register, handle_student_edit, format_employee, add_new_employee, format_subscription_types, \
    add_new_subject, handle_subject_edit, week_lessons_dict, week_school_lessons_dict, filter_lessons, copy_lessons, \
    add_new_lessons, subjects_data, show_lesson, handle_lesson, format_school_class_students, format_school_class_subjects
from app import app, db


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
    lesson_subjects = lesson_subjects_data()

    return render_template('students.html', students=all_students,
                           subscription_subjects=subscription_subjects, today=f'{TODAY:%d.%m.%Y}',
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


@app.route('/lesson-register/<string:student_id>', methods=['POST'])
@login_required
def lesson_register(student_id):
    try:
        subject_id, lesson_id = student_lesson_register(request.form, student_id)
        db.session.commit()
        flash('Клиент записан на занятие.', 'success')

        return redirect(url_for('lesson', subject_id=subject_id, lesson_id=lesson_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при записи клиента: {str(e)}', 'error')

        return redirect(url_for('students'))


@app.route('/subscription/<string:student_id>', methods=['POST'])
@login_required
def subscription(student_id):
    try:
        new_subscription = purchase_subscription(request.form, student_id)
        db.session.add(new_subscription)
        db.session.commit()
        flash('Новый абонемент добавлен в систему.', 'success')

        return redirect(url_for('show_edit_student', student_id=student_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при добавлении абонемента: {str(e)}', 'error')

        return redirect(url_for('students'))


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


@app.route('/add-student', methods=['GET', 'POST'])
@login_required
def add_student():
    if request.method == 'POST':
        try:
            if 'add_child_btn' in request.form:
                student = add_child(request.form)
                db.session.commit()
                flash('Новый клиент добавлен в систему.', 'success')
                return redirect(url_for('show_edit_student', student_id=student.id))

            if 'add_adult_btn' in request.form:
                client = add_adult(request.form)
                db.session.commit()
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
        lesson_subjects = lesson_subjects_data()
        subscription_subjects = subscription_subjects_data()

        if request.method == 'POST':
            try:
                handle_student_edit(request.form, student)
                db.session.commit()
                flash('Изменения внесены.', 'success')
                return redirect(url_for('show_edit_student', student_id=student.id))
            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при внесении изменений: {str(e)}', 'error')
                return redirect(url_for('show_edit_student', student_id=student.id))

        return render_template('student.html', student=student, clients=clients, today=f'{TODAY:%d.%m.%Y}',
                               lesson_subjects=lesson_subjects, subscription_subjects=subscription_subjects)
    else:
        flash("Такого клиента нет", 'error')
        return redirect(url_for('students.html'))


@app.route('/employees')
@login_required
def employees():
    all_employees = Person.query.filter(Person.roles.any(Employee.id)).order_by(Person.last_name, Person.first_name).all()

    for employee in all_employees:
        format_employee(employee)

    return render_template('employees.html', employees=all_employees)


@app.route('/add-employee', methods=['GET', 'POST'])
@login_required
def add_employee():
    if request.method == 'POST':
        try:
            employee = add_new_employee(request.form)
            db.session.commit()
            flash('Новый сотрудник добавлен в систему.', 'success')
            # return redirect(url_for('show_edit_employee', employee_id=employee.id))
            return redirect(url_for('show_edit_employee', employee_id=employee.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при добавлении сотрудника: {str(e)}', 'error')
            return redirect(url_for('add_employee'))

    possible_employees = clients_data('employee')
    distinct_roles = db.session.query(Employee.role.distinct()).all()
    all_subjects = Subject.query.order_by(Subject.name).all()
    subject_list = [(subj.id, f'{subj.name} ({subj.subject_type.description})') for subj in all_subjects]

    return render_template('add_employee.html', possible_employees=possible_employees, roles=distinct_roles,
                           subjects=subject_list)


@app.route('/employee/<string:employee_id>', methods=['GET', 'POST'])
@login_required
def show_edit_employee(employee_id):
    employee = Person.query.filter_by(id=employee_id).first()
    if employee:
        format_employee(employee)
        if employee.teacher:
            future_lessons = Lesson.query.filter(Lesson.date >= TODAY, Lesson.teacher_id == employee_id).all()
            lesson_subjects = set([lesson.subject.name for lesson in future_lessons])
            employee.future_lessons = future_lessons
            employee.lesson_subjects = lesson_subjects

        # if request.method == 'POST':
        #     try:
        #         handle_student_edit(request.form, student)
        #         flash('Изменения внесены.', 'success')
        #         return redirect(url_for('show_edit_student', student_id=student.id))
        #     except Exception as e:
        #         db.session.rollback()
        #         flash(f'Ошибка при внесении изменений: {str(e)}', 'error')
        #         return redirect(url_for('show_edit_student', student_id=student.id))

        return render_template('employee.html', employee=employee)
    else:
        flash("Такого клиента нет", 'error')
        return redirect(url_for('employees'))


@app.route('/subjects')
@login_required
def subjects():
    school = SubjectType.query.filter_by(name='school').first()
    all_subjects = Subject.query.filter(Subject.subject_type_id != school.id).order_by(Subject.name).all()
    for subject in all_subjects:
        subject.types_of_subscription = format_subscription_types(subject.subscription_types.all())

    return render_template('subjects.html', subjects=all_subjects, subjects_type="extra_school")


@app.route('/add-subject', methods=['GET', 'POST'])
@login_required
def add_subject():
    if request.method == 'POST':
        try:
            new_subject = add_new_subject(request.form)
            db.session.add(new_subject)
            db.session.commit()
            flash('Новое занятие добавлено в систему.', 'success')

            return redirect(url_for('subjects'))

        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при добавлении занятия: {str(e)}', 'error')

            return redirect(url_for('add_subject'))

    subject_types = SubjectType.query.filter(~SubjectType.name.in_(['after_school', 'school'])).all()
    subscription_types = format_subscription_types(SubscriptionType.query.all())
    all_teachers = Person.query.filter_by(teacher=True).order_by(Person.last_name, Person.first_name).all()

    return render_template('add_subject.html', subject_types=subject_types, subscription_types=subscription_types,
                           teachers=all_teachers, subjects_type="extra_school")


@app.route('/subject/<string:subject_id>', methods=['GET', 'POST'])
@login_required
def edit_subject(subject_id):
    subject = Subject.query.filter_by(id=subject_id).first()
    if subject:
        if request.method == 'POST':
            try:
                handle_subject_edit(subject, request.form)
                db.session.commit()
                flash('Изменения внесены.', 'success')

            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при внесении изменений: {str(e)}', 'error')

            return redirect(url_for('edit_subject', subject_id=subject_id))

        subject.types_of_subscription = format_subscription_types(subject.subscription_types.all())
        filtered_subscription_types = SubscriptionType.query.filter(
            ~SubscriptionType.subjects.any(Subject.id == subject.id)
        ).all()

        subscription_types = format_subscription_types(filtered_subscription_types)

        return render_template('edit_subject.html', subject=subject, subscription_types=subscription_types)

    else:
        flash("Такого занятия нет.", 'error')
        return redirect(url_for('subjects'))


@app.route('/timetable/<string:week>')
@login_required
def timetable(week):
    week = int(week)
    rooms = Room.query.all()
    week_lessons = week_lessons_dict(week, rooms)

    return render_template('timetable.html', days=DAYS_OF_WEEK, rooms=rooms,
                           classes=week_lessons, week=week)


@app.route('/copy-lessons', methods=['GET', 'POST'])
@login_required
def copy_lessons():
    if request.method == 'POST':
        try:
            filtered_lessons, week_diff, next_week = filter_lessons(request.form)
            if filtered_lessons:
                new_lessons, conflicts = copy_lessons(filtered_lessons, week_diff)

                db.session.add_all(new_lessons)
                db.session.commit()
                if conflicts == 0:
                    flash('Все занятия добавлены в расписание.', 'success')
                elif not new_lessons:
                    flash(f'Занятия не добавлены, т.к. есть занятия в это же время.', 'error')
                else:
                    flash(f'Добавлено занятий: {len(new_lessons)}', 'success')
                    flash(f'Не добавлено занятий: {conflicts}, т.к. есть занятия в это же время', 'error')
                return redirect(url_for('timetable', week=next_week))

            else:
                flash('Нет занятий, удовлетворяющих заданным параметрам', 'error')
                return redirect(url_for('copy_lessons'))

        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при добавлении новых занятий: {str(e)}', 'error')
            return redirect(url_for('copy_lessons'))

    subject_types = SubjectType.query.all()
    rooms = Room.query.all()
    school_classes = SchoolClass.query.order_by(SchoolClass.school_class).all()
    all_teachers = Person.query.filter_by(teacher=True).order_by(Person.last_name, Person.first_name).all()
    school = SubjectType.query.filter_by(name='school').first()

    return render_template('copy_lessons.html', days=DAYS_OF_WEEK, subject_types=subject_types, rooms=rooms,
                           school_classes=school_classes, teachers=all_teachers, school=school)


@app.route('/add-lessons', methods=['GET', 'POST'])
@login_required
def add_lessons():
    if request.method == 'POST':
        try:
            messages, week = add_new_lessons(request.form)
            db.session.commit()
            for message in messages:
                flash(message['text'], message['type'])
            return redirect(url_for('timetable', week=week))

        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при добавлении новых занятий: {str(e)}', 'error')
            return redirect(url_for('add_lessons'))

    all_subjects = subjects_data()
    rooms = Room.query.all()
    school_classes = SchoolClass.query.order_by(SchoolClass.school_class).all()
    school_classes_data = [{school_class.id: school_class.school_name} for school_class in school_classes]
    all_teachers = Person.query.filter_by(teacher=True).order_by(Person.last_name, Person.first_name).all()
    teachers_data = [{teacher.id: f"{teacher.last_name} {teacher.first_name}"} for teacher in all_teachers]
    school = SubjectType.query.filter_by(name='school').first()
    return render_template('add_lessons.html', subjects=all_subjects, school_classes=school_classes_data,
                           rooms=rooms, teachers=teachers_data, school=school)


@app.route('/edit-lesson/<string:lesson_id>', methods=['GET', 'POST'])
@login_required
def edit_lesson(lesson_id):
    edited_lesson = Lesson.query.filter_by(id=lesson_id).first()
    # if edited_lesson:
    if edited_lesson.lesson_type.name in ["school", "after_school"]:
        return redirect(url_for('school_timetable', week=0))

    else:
        rooms = Room.query.all()
        all_teachers = Person.query.filter_by(teacher=True).order_by(Person.last_name, Person.first_name).all()
        extra_school_subjects = Subject.query.filter(
            Subject.subject_type.has(~SubjectType.name.in_(["school", "after_school"]))
        ).order_by(Subject.name).all()

        return render_template('edit_lesson.html', lesson=edited_lesson, subjects=extra_school_subjects,
                               rooms=rooms, teachers=all_teachers)


@app.route('/lesson/<string:subject_id>/<string:lesson_id>', methods=['GET', 'POST'])
@login_required
def lesson(subject_id, lesson_id):
    if int(subject_id) != 0:
        lesson_subject = Subject.query.filter_by(id=subject_id).first()
        if lesson_subject.subject_type.name == 'school':
            return redirect(url_for('school_lesson', lesson_id=lesson_id))

    subject_lesson = show_lesson(subject_id, lesson_id)
    lesson_subject = subject_lesson.subject

    if request.method == 'POST':
        try:
            message = handle_lesson(request.form, lesson_subject, subject_lesson)
            db.session.commit()
            if message:
                flash(message, 'success')

        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при проведении занятия: {str(e)}', 'error')

        return redirect(url_for('lesson', subject_id=subject_id, lesson_id=subject_lesson.id))

    all_clients = Person.query.filter(Person.status.in_(["Клиент", "Лид"])).order_by(Person.last_name,
                                                                                     Person.first_name).all()
    possible_clients = [client for client in all_clients if client not in subject_lesson.students]

    return render_template('lesson.html', subject_lesson=subject_lesson, clients=possible_clients,
                           lesson_subject=lesson_subject)


@app.route('/school-students')
@login_required
def school_students():
    school_classes = SchoolClass.query.order_by(SchoolClass.school_class).all()
    for school_class in school_classes:
        format_school_class_students(school_class)

    lesson_subjects = lesson_subjects_data()
    possible_students = Person.query.filter(
        Person.person_type == 'Ребенок',
        Person.status == 'Клиент',
        Person.school_class_id.is_(None)
    ).order_by(Person.last_name, Person.first_name).all()

    return render_template('school.html', school_classes=school_classes, lesson_subjects=lesson_subjects,
                           possible_students=possible_students, render_type="students")


@app.route('/add-school-student', methods=['POST'])
@login_required
def add_school_student():
    try:
        added_student_id = int(request.form.get('added_student_id'))
        new_school_student = Person.query.filter_by(id=added_student_id).first()
        school_class_id = int(request.form.get('school_class_id'))
        new_school_student.school_class_id = school_class_id
        db.session.commit()
        school_class = SchoolClass.query.filter_by(id=school_class_id).first()
        flash(f'Новый ученик добавлен класс ({school_class.school_name}).', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при добавлении нового ученика: {str(e)}', 'error')

    return redirect(url_for('school_students'))


# @app.route('/school-subjects')
# @login_required
# def school_subjects():
#     all_school_subjects = Subject.query.filter(
#         Subject.subject_type.has(SubjectType.name == "school")
#     ).order_by(Subject.name).all()
#     for subject in all_school_subjects:
#         subject.classes = format_subject_classes(subject)
#
#     return render_template('subjects.html', subjects=all_school_subjects, subjects_type="school")


@app.route('/school-subjects')
@login_required
def school_subjects():
    school_classes = SchoolClass.query.order_by(SchoolClass.school_class).all()
    for school_class in school_classes:
        format_school_class_subjects(school_class)
    all_teachers = Person.query.filter_by(teacher=True).order_by(Person.last_name, Person.first_name).all()

    return render_template('school.html', school_classes=school_classes, teachers=all_teachers, render_type="subjects")


@app.route('/school-timetable/<string:week>')
@login_required
def school_timetable(week):
    week = int(week)
    school_classes = SchoolClass.query.order_by(SchoolClass.school_class).all()
    week_school_lessons = week_school_lessons_dict(week, school_classes, DAYS_OF_WEEK)

    return render_template('school_timetable.html', days=DAYS_OF_WEEK, school_classes=school_classes,
                           classes=week_school_lessons, week=week, week_day=3)


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

