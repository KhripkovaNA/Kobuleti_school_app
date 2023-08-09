from flask import render_template, flash, redirect, url_for, request
from flask_login import login_user, logout_user, current_user, login_required
from app.models import User, Person, Subscription
from app import app, db


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('students'))
    if request.method == "POST":
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user is None or not user.check_password(request.form.get('password')):
            flash('Неправильное имя пользователя или пароль')
            return redirect(url_for('login'))
        login_user(user)
        return redirect(url_for('students'))
    return render_template('login.html')


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/')
@app.route('/students')
@login_required
def students():
    students = Person.query.filter_by(person_type="Ребенок").all()

    for student in students:

        if student.status == "Закрыт":
            student.status_info = f"{student.status} причина: {student.leaving_reason}"
        elif student.status == "Пауза":
            student.status_info = f"{student.status} до {student.pause_until.strftime('%Y-%m-%d')}"
        else:
            student.status_info = student.status

            subjects_with_subscriptions = []
            subscriptions = []
            for subscription in student.subscriptions.all():
                subject_name = subscription.subject.name
                subscriptions.append(subject_name)
                lessons_left = subscription.lessons_left
                subject_with_subscriptions = {
                    'subject_name': subject_name,
                    'lessons_left': lessons_left
                }
                subjects_with_subscriptions.append(subject_with_subscriptions)

            subjects_without_subscriptions = [subject.name for subject in student.subjects.all()
                                              if subject.name not in subscriptions]
            student.subjects_without_subscriptions = subjects_without_subscriptions
            student.subjects_with_subscriptions = subjects_with_subscriptions

    return render_template('students.html', students=students)


@app.route('/add-student', methods=['GET', 'POST'])
@login_required
def add_student():
    return render_template('add_student.html')


@app.route('/student/<string:id>')
@login_required
def show_student(id):
    student = Person.query.filter_by(id=id).first_or_404()
    if student:
        return render_template('student.html', student=student)
    else:
        flash("Такого клиента нет")

    return redirect(url_for('students'))

