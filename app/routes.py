from flask import render_template, flash, redirect, url_for, request
from flask_login import login_user, logout_user, current_user, login_required
from app.models import User, Person, Contact, parent_child_table, Subject
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
    all_students = Person.query.filter_by(person_type="Ребенок").all()

    for student in all_students:
        if student.dob:
            student.birth_date = f"{student.dob.strftime('%d.%m.%Y')}"
        primary_contact = student.primary_contact
        if primary_contact:
            if primary_contact == student.id:
                if student.contacts:
                    if student.contacts[0].telegram:
                        student.contact = f"(Телеграм: {students.contacts[0].telegram}"
                    elif student.contacts[0].phone:
                        student.contact = f"(Тел.: {students.contacts[0].phone}"
                    elif student.contacts[0].other_contact:
                        student.contact = students.contacts[0].other_contact
            else:
                parent_type = db.session.query(parent_child_table.c.relation).filter(
                    parent_child_table.c.parent_id == primary_contact,
                    parent_child_table.c.child_id == student.id).scalar()
                parent = Person.query.filter_by(id=primary_contact).first()
                parent_name = f"{parent.last_name} {parent.first_name}"
                student.contact_name = f"{parent_type} - {parent_name}"
                if parent.contacts[0].telegram:
                    student.contact = f"(Телеграм: {parent.contacts[0].telegram}"
                elif parent.contacts[0].phone:
                    student.contact = f"(Тел.: {parent.contacts[0].phone}"
                elif parent.contacts[0].other_contact:
                    student.contact = parent.contacts[0].other_contact

        if student.status == "Закрыт":
            student.status_info = f"{student.status} причина: {student.leaving_reason}"
        elif student.status == "Пауза":
            student.status_info = f"{student.status} до {student.pause_until.strftime('%d.%m.%Y')}"
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
    dob = datetime.strptime(form.get('dob'), '%d.%m.%Y').date() \
        if form.get('dob') else None
    status = form.get('status')
    pause_date = datetime.strptime(form.get('pause_until'), '%d.%m.%Y').date() \
        if form.get('pause_until') else None
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
        db.session.add(contact)
        db.session.commit()

        student.contacts.append(contact)

    else:
        parent = create_parent(form, i)
        db.session.add(parent)
        db.session.add(contact)
        db.session.commit()

        student.parents.append(parent)
        parent.contacts.append(contact)
        parent.primary_contact = parent.id
        assign_relation_type(form, student, parent, i)

    if form['primary_contact'] == f'contact_{i}':
        student.primary_contact = contact.person.id
    db.session.commit()


def assign_relation_type(form, student, parent, i):
    relation_type = form.get(f'relation_{i}')

    if relation_type == "Другое":
        relation_type = form.get(f'other_relation_{i}')

    relation_entry = parent_child_table.update().where(
        (parent_child_table.c.parent_id == parent.id) &
        (parent_child_table.c.child_id == student.id)
    ).values(relation=relation_type)

    db.session.execute(relation_entry)


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

    all_subjects = Subject.query.all()
    subjects = [subject.name for subject in all_subjects]
    return render_template('add_student.html', subjects=subjects)


@app.route('/student/<string:student_id>')
@login_required
def show_student(student_id):
    student = Person.query.filter_by(id=student_id).first()
    if student:
        if student.dob:
            student.birth_date = f"{student.dob.strftime('%d.%m.%Y')}"
        if student.status == "Закрыт":
            student.status_info = f"{student.status} причина: {student.leaving_reason}"
        elif student.status == "Пауза":
            student.status_info = f"{student.status} до {student.pause_until.strftime('%d.%m.%Y')}"
        else:
            student.status_info = student.status

        student.main_contact = Person.query.filter_by(id=student.primary_contact).first()
        contacts = []
        if student.contacts:
            if student.primary_contact == student.id:
                student.main_contact = student
            else:
                contacts.append(student)
        for parent in student.parents:
            parent_type = db.session.query(parent_child_table.c.relation).filter(
                parent_child_table.c.parent_id == parent.id,
                parent_child_table.c.child_id == student.id).scalar()
            parent.type = parent_type
            if student.primary_contact == parent.id:
                student.main_contact = parent
            else:
                contacts.append(parent)
        student.additional_contacts = contacts

        return render_template('student.html', student=student)
    else:
        flash("Такого клиента нет")
        return redirect(url_for('students.html'))


@app.route('/edit-student/<string:student_id>', methods=['GET', 'POST'])
@login_required
def edit_student(student_id):
    student = Person.query.filter_by(id=student_id).first()
    if student:
        if student.dob:
            student.birth_date = f"{student.dob.strftime('%d.%m.%Y')}"
        if student.pause_until:
            student.pause_date = f"{student.pause_until.strftime('%d.%m.%Y')}"

        student.main_contact = Person.query.filter_by(id=student.primary_contact).first()
        contacts = []
        if student.primary_contact == student.id:
            student.main_contact = student
            student.main_contact.type = "Сам ребенок"
            if not student.contacts:
                contact = Contact.query.filter_by(id=1).first()
                student.contacts.append(contact)
        else:
            contacts.append(student)

        for parent in student.parents:
            parent_type = db.session.query(parent_child_table.c.relation).filter(
                parent_child_table.c.parent_id == parent.id,
                parent_child_table.c.child_id == student.id).scalar()
            parent.type = parent_type
            if student.primary_contact == parent.id:
                student.main_contact = parent
            else:
                contacts.append(parent)
        student.additional_contacts = contacts

    return render_template('edit_student.html', student=student)
