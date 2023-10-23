from flask import render_template, flash, redirect, url_for, request
from flask_login import login_user, logout_user, current_user, login_required
from app.models import User, Person, Subject
from app.app_functions import create_student, handle_contact_info, \
    basic_student_info, extensive_student_info, clients_data
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
    all_students = Person.query.filter_by(person_type="Ребенок").order_by(Person.last_name).all()

    for student in all_students:
        basic_student_info(student)

    return render_template('students.html', students=all_students)


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
    all_subjects = Subject.query.order_by(Subject.name).all()
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


@app.route('/timetable')
@login_required
def timetable():
    class_data = [
        {"name": "Математика", "start_time": "10:00", "end_time": "11:00", "room": "каб 1"},
        {"name": "Английский", "start_time": "11:00", "end_time": "12:00", "room": "каб 2"}
    ]
    return render_template('timetable_test.html', class_data=class_data)
