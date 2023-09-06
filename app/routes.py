from flask import render_template, flash, redirect, url_for, request
from flask_login import login_user, logout_user, current_user, login_required
from app.models import User, Person, Contact, parent_child_table, Subject
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
    all_students = Person.query.filter_by(person_type="Ребенок").all()

    for student in all_students:
        primary_contact = student.primary_contact
        if primary_contact:
            if primary_contact.id == student.id:
                if student.contacts[0].telegram:
                    student.contact = f"(Телеграм: {students.contacts[0].telegram}"
                elif student.contacts[0].phone:
                    student.contact = f"(Тел.: {students.contacts[0].phone}"
                elif student.contacts[0].other_contact:
                    student.contact = students.contacts[0].other_contact
            else:
                parent = db.session.query(parent_child_table.c.relationship).filter(
                    parent_child_table.c.parent_id == primary_contact.id,
                    parent_child_table.c.child_id == student.id).scalar()
                parent_name = f"{primary_contact.last_name} {primary_contact.first_name}"
                student.contact_name = f"{parent} - {parent_name}"
                if primary_contact.contacts[0].telegram:
                    student.contact = f"(Телеграм: {primary_contact.contacts[0].telegram}"
                elif primary_contact.contacts[0].phone:
                    student.contact = f"(Тел.: {primary_contact.contacts[0].phone}"
                elif primary_contact.contacts[0].other_contact:
                    student.contact = primary_contact.contacts[0].other_contact

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

    return render_template('students.html', students=all_students)


def create_student(form):
    last_name = form.get('last_name')
    first_name = form.get('first_name')
    patronym = form.get('patronym')
    dob = form.get('dob')
    status = form.get('status')
    pause_date = form.get('pause_until')
    leaving_reason = form.get('leaving_reason')

    student = Person(
        last_name=last_name,
        first_name=first_name,
        patronym=patronym,
        dob=dob,
        person_type="Ребенок",
        status=status,
        pause_until=pause_date,
        leaving_reason=leaving_reason
    )

    return student


def create_contact(form, i):
    telegram = form.get(f'telegram_{i}')
    phone = form.get(f'phone_{i}')
    other_contact = form.get(f'other_contact_{i}')

    contact = Contact(
        telegram=telegram,
        phone=phone,
        other_contact=other_contact
    )

    return contact


def create_parent(form, i):
    parent_last_name = form.get(f'parent_last_name_{i}')
    parent_first_name = form.get(f'parent_first_name_{i}')
    parent_patronym = form.get(f'parent_patronym_{i}')

    parent = Person(
        last_name=parent_last_name,
        first_name=parent_first_name,
        patronym=parent_patronym,
        person_type="Взрослый"
    )

    return parent


def handle_contact_info(form, student, i):
    contact = create_contact(form, i)
    relation_type = form.get(f'relation_{i}')

    if relation_type == "Сам ребенок":
        student.contacts = contact
        db.session.add(contact)
        db.session.commit()

    else:
        parent = create_parent(form, i)
        db.session.add(parent)
        student.parents.append(parent)
        db.session.commit()

        parent.contacts = contact
        db.session.add(contact)
        assign_relation_type(form, student, parent)
        db.session.commit()

    if form['primary_contact'] == f'contact_{i}':
        student.primary_contact = contact.person.id
        db.session.commit()


def assign_relation_type(form, student, parent):
    relation_type = form.get('relation_type')

    if relation_type:
        relation_entry = parent_child_table.insert().values(
            parent_id=parent.id,
            child_id=student.id,
            relationship=relation_type
        )
        db.session.execute(relation_entry)


@app.route('/add-student', methods=['GET', 'POST'])
@login_required
def add_student():
    if request.method == 'POST':

        try:
            student = create_student(request.form)
            db.session.add(student)
            db.session.commit()

            contact_count = int(request.form.get('contactCount'))
            for i in range(1, contact_count + 1):
                handle_contact_info(request.form, student, i)

            flash('Новый ученик добавлен в систему.', 'success')
            return redirect(url_for('students'))

        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при добавлении ученика: {str(e)}', 'error')
            return redirect(url_for('add_student'))

    all_subjects = Subject.query.all()
    subjects = [subject.name for subject in all_subjects]
    return render_template('add_student.html', subjects=subjects)


@app.route('/student/<string:id>')
@login_required
def show_student(id):
    student = Person.query.filter_by(id=id).first_or_404()
    if student:
        return render_template('student.html', student=student)
    else:
        flash("Такого клиента нет")

    return redirect(url_for('students'))

