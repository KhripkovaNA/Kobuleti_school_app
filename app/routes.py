from flask import render_template, flash, redirect, url_for, request
from flask_login import login_user, logout_user, current_user, login_required
from app.models import User, Person, Subject, Room, Lesson
from app.app_functions import create_student, handle_contact_info, \
    basic_student_info, extensive_student_info, clients_data, create_lesson
from app import app, db
from datetime import datetime


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


def time_dif(str_time):
    base_time = datetime.strptime("09:00", '%H:%M')
    time_dif_in_mins = (datetime.strptime(str_time, '%H:%M') - base_time).total_seconds() / 60
    return time_dif_in_mins


@app.route('/timetable')
@login_required
def timetable():
    # rooms = Rooms.query.all()
    days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"]
    rooms = ['каб 1', 'каб 2', 'каб 3', 'изо', 'каб 5', 'зал', 'игровая', 'кухня']
    classes = {
        "Понедельник":
            {"каб 1":
                [{"name": "Математика", "start": time_dif("10:00"), "end": time_dif("11:00")}],
             "каб 2":
                [{"name": "Английский", "start": time_dif("11:30"), "end": time_dif("12:30")}],
             "зал":
                 [{"name": "ОФП Дети", "start": time_dif("11:00"), "end": time_dif("12:00")}],
             },
        "Вторник":
            {"каб 1":
                 [{"name": "1 класс", "start": time_dif("9:00"), "end": time_dif("12:00")}],
             "изо":
                 [{"name": "Робототехника", "start": time_dif("9:30"), "end": time_dif("11:00")}]
             },
        "Среда":
            {"каб 2":
                 [{"name": "2 класс", "start": time_dif("10:45"), "end": time_dif("12:00")}],
             "игровая":
                 [{"name": "Продленка", "start": time_dif("10:00"), "end": time_dif("13:00")}]
             },
        "Четверг": {},
        "Пятница": {},
        "Суббота": {}
        }

    return render_template('time_table.html', days=days, rooms=rooms, classes=classes)


@app.route('/add-lesson', methods=['GET', 'POST'])
@login_required
def add_lesson():
    if request.method == 'POST':

        try:
            lesson = create_lesson(request.form)
            db.session.add(lesson)
            db.session.commit()

            flash('Новый урок добавлен в расписание.', 'success')
            return redirect(url_for('students'))

        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при добавлении нового урока: {str(e)}', 'error')
            return redirect(url_for('add_lesson'))

    all_subjects = Subject.query.order_by(Subject.name).all()
    all_rooms = Room.query.all()
    all_teachers = Person.query.filter_by(teacher=True).order_by(Person.last_name).all()

    return render_template('add_lesson.html', subjects=all_subjects, rooms=all_rooms, teachers=all_teachers)
