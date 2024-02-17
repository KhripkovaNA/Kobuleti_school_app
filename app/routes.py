from flask import render_template, flash, redirect, url_for, request, send_file
from flask_login import login_user, logout_user, current_user, login_required
from app.models import User, Person, Employee, Lesson, SubjectType, Subject, Room, SchoolClass, \
    SubscriptionType, SchoolLessonJournal
from app.forms import LoginForm, ChildForm, AdultForm, EditStudentForm, EditContactPersonForm, ContactForm, \
    EditAddContPersonForm, AddContForm, NewContactPersonForm, SubscriptionsEditForm, SubscriptionForm
from app.app_functions import DAYS_OF_WEEK, TODAY, MONTHS, basic_student_info, subscription_subjects_data, \
    lesson_subjects_data, potential_client_subjects, purchase_subscription, add_child, add_adult, clients_data, \
    extensive_student_info, student_lesson_register, handle_student_edit, format_employee, add_new_employee, \
    handle_employee_edit, format_subscription_types, add_new_subject, handle_subject_edit, week_lessons_dict, \
    day_school_lessons_dict, filter_lessons, copy_filtered_lessons, add_new_lessons, subjects_data, show_lesson, \
    handle_lesson, format_school_class_students, format_school_class_subjects, show_school_lesson, \
    handle_school_lesson, employee_record, subject_record, calc_month_index, student_record, \
    get_after_school_students, get_after_school_prices, handle_after_school_adding, finance_operation, \
    download_timetable, get_date_range, get_period

from app import app, db
from datetime import datetime, timedelta
from io import BytesIO
from openpyxl import Workbook


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('students'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Неправильное имя пользователя или пароль', "error")
            return redirect(url_for('login'))
        login_user(user)
        flash('Вы успешно вошли в систему.', "success")
        return redirect(url_for('students'))
    return render_template('login.html', form=form)


@app.route('/logout')
def logout():
    logout_user()
    flash('Вы вышли из системы.', "success")
    return redirect(url_for('login'))


@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')

        if current_user.check_password(old_password):
            current_user.password = current_user.set_password(new_password)
            db.session.commit()
            flash('Пароль успешно изменен', 'success')
            return redirect(url_for('settings'))
        else:
            flash('Неправильный пароль', 'error')


@app.route('/')
@app.route('/students')
@login_required
def students():
    all_students = Person.query.filter(Person.status.isnot(None)).order_by(Person.last_name, Person.first_name).all()

    for student in all_students:
        basic_student_info(student)
    subscription_subjects = subscription_subjects_data()
    lesson_subjects = lesson_subjects_data()

    return render_template('students.html', students=all_students, subscription_subjects=subscription_subjects,
                           today=f'{TODAY:%d.%m.%Y}', lesson_subjects=lesson_subjects, rights=current_user.rights)


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
        lesson_id = student_lesson_register(request.form, student_id)
        db.session.commit()
        flash('Клиент записан на занятие', 'success')

        return redirect(url_for('lesson', lesson_id=lesson_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при записи клиента: {str(e)}', 'error')

        return redirect(request.referrer)


@app.route('/student-subjects/<string:student_id>', methods=['POST'])
@login_required
def student_subjects_add(student_id):
    try:
        student = Person.query.filter_by(id=student_id, status="Лид").first()
        selected_subjects = request.form.getlist("selected_subjects")
        selected_class = request.form.get("selected_class")
        if student:
            if selected_subjects:
                for subject in selected_subjects:
                    subject_id = int(subject)
                    potential_subject = Subject.query.filter_by(id=subject_id).first()
                    if potential_subject not in student.subjects.all():
                        student.subjects.append(potential_subject)
                        db.session.flush()
            if selected_class:
                student.school_class_id = int(selected_class)

            db.session.commit()
            flash('Занятия добавлены', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при записи клиента: {str(e)}', 'error')

    return redirect(request.referrer)


@app.route('/subscription/<string:student_id>', methods=['POST'])
@login_required
def subscription(student_id):
    try:
        new_subscription, price = purchase_subscription(request.form, student_id)
        db.session.add(new_subscription)
        db.session.flush()
        description = f"Покупка абонемента {new_subscription.subject.name}"
        finance_operation(student_id, -price, description)
        db.session.commit()
        flash('Новый абонемент добавлен в систему.', 'success')

        return redirect(url_for('show_edit_student', student_id=student_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при добавлении абонемента: {str(e)}', 'error')

        return redirect(request.referrer)


@app.route('/deposit/<string:student_id>', methods=['POST'])
@login_required
def deposit(student_id):
    try:
        deposit = int(request.form.get('deposit'))
        student = Person.query.filter_by(id=student_id).first()
        student.balance += deposit
        description = "Пополнение баланса"
        finance_operation(student_id, deposit, description)
        db.session.commit()
        flash('Депозит внесен на счет.', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при внесении депозита: {str(e)}', 'error')

    return redirect(url_for('students'))


@app.route('/delete-record', methods=['POST'])
@login_required
def delete_record():
    record_type = request.form.get('record_type')

    if current_user.rights == 'admin':
        try:
            if record_type == 'student':
                student_id = int(request.form.get('student_id'))
                student = Person.query.filter_by(id=student_id).first()
                if student:
                    if student.parents.all():
                        for parent in student.parents:
                            if len(parent.children.all()) == 1 and not parent.status and not parent.roles:
                                db.session.delete(parent.contacts[0])
                                db.session.delete(parent)
                    student_name = f"{student.last_name} {student.first_name}"
                    db.session.delete(student)
                    db.session.commit()
                    flash(f"Клиент {student_name} удален", "success")
                else:
                    flash("Такого клиента нет", 'error')

        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при удалении: {str(e)}', 'error')

    else:
        flash('Необходимо обладать правами администратора', 'error')

    if record_type.startswith('contact'):
        contact_person_id = int(request.form.get('contact_id'))
        contact_person = Person.query.filter_by(id=contact_person_id).first()
        if contact_person:
            if record_type == 'contact':
                if contact_person.contacts[0]:
                    db.session.delete(contact_person.contacts[0])
            if record_type == 'contact_person':
                if len(contact_person.children.all()) == 1 and not contact_person.status \
                        and not contact_person.roles:
                    db.session.delete(contact_person.contacts[0])
                    db.session.delete(contact_person)
            db.session.commit()
            flash("Контактная информация удалена", "success")
        else:
            flash("Такого контакта нет", 'error')

    return redirect(request.referrer)


@app.route('/add-student', methods=['GET', 'POST'])
@login_required
def add_student():
    clients = clients_data('child')
    form1 = ChildForm()
    form1.contacts[0].selected_contact.choices = [(person["id"], f'{person["last_name"]} {person["first_name"]}')
                                                  for person in clients]

    possible_clients = clients_data('adult')
    form2 = AdultForm()
    form2.selected_client.choices = [(person["id"], f'{person["last_name"]} {person["first_name"]}')
                                     for person in possible_clients]
    render_type = 'child'

    if request.method == 'POST':
        try:
            if 'add_child_btn' in request.form:
                if form1.validate_on_submit():
                    student = add_child(form1)
                    db.session.commit()
                    flash('Новый клиент добавлен в систему.', 'success')
                    return redirect(url_for('show_edit_student', student_id=student.id))

            if 'add_adult_btn' in request.form:
                render_type = 'adult'
                if form2.validate_on_submit():
                    client = add_adult(form2)
                    db.session.commit()
                    flash('Новый клиент добавлен в систему.', 'success')
                    return redirect(url_for('show_edit_student', student_id=client.id))

            flash('Ошибка в форме добавления киента', 'error')

        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при добавлении киента: {str(e)}', 'error')
            return redirect(url_for('add_student'))

    return render_template('add_student.html', clients=clients, possible_clients=possible_clients,
                           form1=form1, form2=form2, render_type=render_type)


@app.route('/student/<string:student_id>', methods=['GET', 'POST'])
@login_required
def show_edit_student(student_id):
    student = Person.query.filter(Person.id == student_id, Person.status.isnot(None)).first()
    if student:
        extensive_student_info(student)
        clients = clients_data('child')
        lesson_subjects = lesson_subjects_data()
        potential_subjects = potential_client_subjects()
        subscription_subjects = subscription_subjects_data()
        periods = [get_period(0), get_period(1)]
        months = [(f"{period[0]}-{period[1]}", MONTHS[period[0]-1].capitalize()) for period in periods]
        after_school_prices = get_after_school_prices()

        student_form = EditStudentForm(
            last_name=student.last_name,
            first_name=student.first_name,
            patronym=student.patronym,
            dob=f'{student.dob:%d.%m.%Y}' if student.dob else None,
            status=student.status,
            pause_until=f'{student.pause_until:%d.%m.%Y}' if student.pause_until else None,
            leaving_reason=student.leaving_reason
        )

        if student.primary_contact != student.id:
            main_contact_form = EditContactPersonForm(
                prefix="main",
                last_name=student.main_contact.last_name,
                first_name=student.main_contact.first_name,
                patronym=student.main_contact.patronym,
                telegram=student.main_contact.contacts[0].telegram,
                phone=student.main_contact.contacts[0].phone,
                other_contact=student.main_contact.contacts[0].other_contact
            )

        else:
            main_contact_form = ContactForm(
                prefix="main",
                telegram=student.main_contact.contacts[0].telegram,
                phone=student.main_contact.contacts[0].phone,
                other_contact=student.main_contact.contacts[0].other_contact
            )

        add_cont_forms = []
        if student.additional_contacts:
            for i, contact in enumerate(student.additional_contacts, 1):
                if contact.id != student.id:
                    add_cont_form = EditAddContPersonForm(
                        prefix=f"contact_{i}",
                        last_name=contact.last_name,
                        first_name=contact.first_name,
                        patronym=contact.patronym,
                        telegram=contact.contacts[0].telegram,
                        phone=contact.contacts[0].phone,
                        other_contact=contact.contacts[0].other_contact
                    )
                else:
                    add_cont_form = AddContForm(
                        prefix=f"contact_{i}",
                        telegram=contact.contacts[0].telegram,
                        phone=contact.contacts[0].phone,
                        other_contact=contact.contacts[0].other_contact
                    )
                add_cont_forms.append(add_cont_form)

        new_contact_form = NewContactPersonForm(prefix="new_contact")
        new_contact_form.selected_contact.choices = [(person["id"], f'{person["last_name"]} {person["first_name"]}')
                                                     for person in clients]
        data = {'subscriptions': []}
        if student.subscriptions_info:
            for subscription in student.subscriptions_info:
                data['subscriptions'].append({
                    'subscription_id': subscription["subscription_id"],
                    'subject_name': subscription["subject_name"],
                    'lessons': subscription["lessons_left"],
                    'end_date': subscription["end_date"]
                })
        subscriptions_form = SubscriptionsEditForm(data=data)

        render_type = 'student'

        if request.method == 'POST':
            try:
                if 'form_student_submit' in request.form:
                    render_type = 'edit_student'
                    if student_form.validate_on_submit():
                        handle_student_edit(student_form, student, 'edit_student')
                        db.session.commit()
                        flash('Изменения внесены', 'success')
                        return redirect(url_for('show_edit_student', student_id=student.id))

                if 'form_main_contact_submit' in request.form:
                    render_type = 'contact_main_edit'
                    if main_contact_form.validate_on_submit():
                        handle_student_edit(main_contact_form, student, 'edit_main_contact')
                        db.session.commit()
                        flash('Изменения внесены', 'success')
                        return redirect(url_for('show_edit_student', student_id=student.id))

                for i in range(1, len(student.additional_contacts) + 2):
                    if f'form_cont_{i}_submit' in request.form:
                        render_type = f'contact_edit_{i}'
                        if add_cont_forms[i-1].validate_on_submit():
                            handle_student_edit(add_cont_forms[i-1], student, f'edit_contact_{i}')
                            db.session.commit()
                            flash('Изменения внесены', 'success')
                            return redirect(url_for('show_edit_student', student_id=student.id))

                if 'form_cont_new_submit' in request.form:
                    render_type = 'contact_new'
                    if new_contact_form.validate_on_submit():
                        handle_student_edit(new_contact_form, student, 'new_contact')
                        db.session.commit()
                        flash('Новый контакт добавлен', 'success')
                        return redirect(url_for('show_edit_student', student_id=student.id))

                if 'del_subject_btn' in request.form:
                    handle_student_edit(request.form, student, 'del_subject')
                    db.session.commit()
                    flash('Изменения внесены', 'success')
                    return redirect(url_for('show_edit_student', student_id=student.id))

                if 'form_subscriptions_submit' in request.form:
                    render_type = 'subscription'
                    if subscriptions_form.validate_on_submit():
                        handle_student_edit(subscriptions_form, student, 'subscription')
                        db.session.commit()
                        flash('Изменения внесены', 'success')
                        return redirect(url_for('show_edit_student', student_id=student.id))

                if 'del_after_school' in request.form:
                    handle_student_edit(request.form, student, 'del_after_school')
                    db.session.commit()
                    flash('Изменения внесены', 'success')
                    return redirect(url_for('show_edit_student', student_id=student.id))

                flash('Ошибка в форме изменения клиента', 'error')

            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при внесении изменений: {str(e)}', 'error')
                return redirect(url_for('show_edit_student', student_id=student.id))

        return render_template('student.html', student=student, clients=clients, today=f'{TODAY:%d.%m.%Y}',
                               lesson_subjects=lesson_subjects, subscription_subjects=subscription_subjects,
                               edit_student_form=student_form, render_type=render_type, main_contact=main_contact_form,
                               add_cont_forms=add_cont_forms, new_contact_form=new_contact_form, months=months,
                               potential_subjects=potential_subjects, subscriptions_form=subscriptions_form,
                               after_school_prices=after_school_prices)
    else:
        flash("Такого клиента нет", 'error')
        return redirect(url_for('students'))


@app.route('/employees')
@login_required
def employees():
    all_employees = Person.query.filter(Person.roles.any(Employee.id)).order_by(Person.last_name, Person.first_name).all()

    for employee in all_employees:
        format_employee(employee)

    return render_template('employees.html', employees=all_employees)


@app.route('/employee-report/<string:week>')
@login_required
def employee_report(week):
    week = int(week)
    all_employees = Person.query.filter(
        Person.roles.any(Employee.id)
    ).order_by(Person.last_name, Person.first_name).all()

    employees_list, dates = employee_record(all_employees, week)
    filename = f"employee_report_{dates[0].replace('.', '_')}_{dates[-1].replace('.', '_')}.xlsx"

    return render_template('employee_report.html', employees=employees_list, dates=dates,
                           week=week, filename=filename)


@app.route('/add-employee', methods=['GET', 'POST'])
@login_required
def add_employee():
    if request.method == 'POST':
        try:
            employee = add_new_employee(request.form)
            db.session.commit()
            flash('Новый сотрудник добавлен в систему.', 'success')
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
    employee = Person.query.filter_by(id=int(employee_id)).first()

    if employee and employee.roles:
        format_employee(employee)

        if employee.teacher:
            future_lessons = Lesson.query.filter(Lesson.date >= TODAY, Lesson.teacher_id == employee_id).all()
            lesson_subjects = set([lesson.subject.id for lesson in future_lessons])
            employee.future_lessons = future_lessons
            employee.lesson_subjects = lesson_subjects

        if request.method == 'POST':
            try:
                handle_employee_edit(request.form, employee)
                db.session.commit()
                flash('Изменения внесены.', 'success')

            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при внесении изменений: {str(e)}', 'error')

            return redirect(url_for('show_edit_employee', employee_id=employee.id))

        employee_roles = [role.role for role in employee.roles]
        possible_roles = db.session.query(Employee.role.distinct()).filter(
            ~Employee.role.in_(employee_roles)
        ).all()
        employee_subjects = [subject.id for subject in employee.subjects_taught]
        possible_subjects = Subject.query.filter(
            ~Subject.id.in_(employee_subjects)
        ).order_by(Subject.name).all()
        all_subjects = Subject.query.order_by(Subject.name).all()

        return render_template('employee.html', employee=employee, possible_roles=possible_roles,
                               possible_subjects=possible_subjects, subjects=all_subjects)
    else:
        flash("Такого сотрудника нет", 'error')
        return redirect(url_for('employees'))


@app.route('/subjects')
@login_required
def subjects():
    school = SubjectType.query.filter_by(name='school').first()
    all_subjects = Subject.query.filter(Subject.subject_type_id != school.id).order_by(Subject.name).all()
    for subject in all_subjects:
        subject.types_of_subscription = format_subscription_types(subject.subscription_types.all())

    subject_types = SubjectType.query.filter(~SubjectType.name.in_(['after_school', 'school'])).all()
    subscription_types = format_subscription_types(SubscriptionType.query.all())
    all_teachers = Person.query.filter_by(teacher=True).order_by(Person.last_name, Person.first_name).all()

    return render_template('subjects.html', subjects=all_subjects, subjects_type="extra_school",
                           subject_types=subject_types, subscription_types=subscription_types, teachers=all_teachers)


@app.route('/add-subject', methods=['GET', 'POST'])
@login_required
def add_subject():
    if request.method == 'POST':
        subject_type_id = request.form.get("subject_type")
        school_type = SubjectType.query.filter_by(name="school").first()
        subject_type = "school" if subject_type_id == school_type else "extra_school"
        try:
            new_subject = add_new_subject(request.form, subject_type)
            db.session.add(new_subject)
            db.session.commit()
            flash('Новый предмет добавлен в систему.', 'success')

            if subject_type == "school":
                return redirect(url_for('school_subjects'))
            else:
                return redirect(url_for('subjects'))

        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при добавлении занятия: {str(e)}', 'error')

            if subject_type == "school":
                return redirect(url_for('school_subjects'))
            else:
                return redirect(url_for('add_subject'))

    subject_types = SubjectType.query.filter(~SubjectType.name.in_(['after_school', 'school'])).all()
    subscription_types = format_subscription_types(SubscriptionType.query.all())
    all_teachers = Person.query.filter_by(teacher=True).order_by(Person.last_name, Person.first_name).all()

    return render_template('add_subject.html', subject_types=subject_types, subscription_types=subscription_types,
                           teachers=all_teachers)


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
                new_lessons, conflicts = copy_filtered_lessons(filtered_lessons, week_diff)
                db.session.commit()

                if conflicts == 0:
                    flash('Все занятия добавлены в расписание.', 'success')
                elif new_lessons == 0:
                    flash(f'Занятия не добавлены, т.к. есть занятия в это же время.', 'error')
                else:
                    flash(f'Добавлено занятий: {new_lessons}', 'success')
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
    if not edited_lesson or edited_lesson.lesson_type.name == "after_school":
        flash("Такого занятия нет.", 'error')
        return redirect(url_for('timetable', week=0))

    elif edited_lesson.lesson_type.name == "school":
        edited_lesson.classes = ', '.join([cl.school_name for cl in sorted(edited_lesson.school_classes,
                                                                           key=lambda x: x.school_class)])
    rooms = Room.query.all()
    all_teachers = Person.query.filter_by(teacher=True).order_by(Person.last_name, Person.first_name).all()

    return render_template('edit_lesson.html', lesson=edited_lesson, rooms=rooms, teachers=all_teachers)


@app.route('/lesson/<string:lesson_id>', methods=['GET', 'POST'])
@login_required
def lesson(lesson_id):
    subject_lesson, lesson_subject = show_lesson(lesson_id)

    if subject_lesson:
        if request.method == 'POST':
            try:
                message = handle_lesson(request.form, lesson_subject, subject_lesson)
                db.session.commit()
                if message:
                    flash(message, 'success')

            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при проведении занятия: {str(e)}', 'error')

            return redirect(url_for('lesson', lesson_id=subject_lesson.id))

        all_clients = Person.query.filter(Person.status.in_(["Клиент", "Лид"])).order_by(Person.last_name,
                                                                                         Person.first_name).all()
        possible_clients = [client for client in all_clients if client not in subject_lesson.students]

        return render_template('lesson.html', subject_lesson=subject_lesson, clients=possible_clients,
                               lesson_subject=lesson_subject)

    else:
        if lesson_subject:
            return render_template('lesson.html', subject_lesson=subject_lesson, lesson_subject=lesson_subject)
        else:
            flash("Такого занятия нет.", 'error')
            return redirect(url_for('school-subjects'))


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


@app.route('/school-subjects')
@login_required
def school_subjects():
    school_classes = SchoolClass.query.order_by(SchoolClass.school_class).all()
    for school_class in school_classes:
        format_school_class_subjects(school_class)
    all_teachers = Person.query.filter_by(teacher=True).order_by(Person.last_name, Person.first_name).all()
    school_type = SubjectType.query.filter_by(name="school").first()
    return render_template('school.html', school_classes=school_classes, teachers=all_teachers,
                           school_type=school_type, render_type="subjects")


@app.route('/school-timetable/<string:week>/<string:day>')
@login_required
def school_timetable(week, day):
    week_day = int(day)
    if week_day == 0:
        week_day = TODAY.weekday() + 1
    if week_day > 6:
        return redirect(url_for('school_timetable', week=week+1, day=1))

    week = int(week)
    school_classes = SchoolClass.query.order_by(SchoolClass.school_class).all()
    day_school_lessons = day_school_lessons_dict(week_day, week, school_classes)
    dates = get_date_range(week)
    filename = f"timetable_{dates[0].replace('.', '_')}_{dates[-1].replace('.', '_')}.xlsx"

    return render_template('school_timetable.html', days=DAYS_OF_WEEK, school_classes=school_classes,
                           classes=day_school_lessons, week=week, week_day=week_day, filename=filename)


@app.route('/school-lesson/<string:lesson_id>', methods=['GET', 'POST'])
@login_required
def school_lesson(lesson_id):
    sc_lesson, sc_subject = show_school_lesson(lesson_id)
    if sc_lesson:
        subject_classes = str(sc_lesson.subject_id) + '-' + '-'.join(map(str, sc_lesson.classes_ids))
        month_index = calc_month_index(sc_lesson.date)

        if request.method == 'POST':
            try:
                message = handle_school_lesson(request.form, sc_lesson)
                db.session.commit()
                if message:
                    flash(message, 'success')

            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при проведении занятия: {str(e)}', 'error')

            if 'new_grade_btn' in request.form:

                return redirect(url_for('school_subject', subject_classes=subject_classes,
                                        month_index=month_index))
            else:

                return redirect(url_for('school_lesson', lesson_id=sc_lesson.id))

        sc_students = Person.query.filter(
            Person.school_class_id.is_not(None),
            ~Person.id.in_([student.id for student in sc_lesson.lesson_students])
        ).order_by(Person.last_name, Person.first_name).all()
        distinct_grade_types = db.session.query(SchoolLessonJournal.grade_type.distinct()).all()
        grade_types = [grade_type[0] for grade_type in distinct_grade_types if grade_type[0]]
        days_dict = {day_num: day for (day_num, day) in enumerate(DAYS_OF_WEEK)}

        return render_template('school_lesson.html', school_lesson=sc_lesson, days_dict=days_dict,
                               school_students=sc_students, grade_types=grade_types, school_subject=sc_subject)

    else:
        if sc_subject:
            return render_template('school_lesson.html', school_lesson=sc_lesson, school_subject=sc_subject)
        else:
            flash("Такого занятия нет.", 'error')
            return redirect(url_for('school_subjects'))


@app.route('/school-subject/<subject_classes>/<string:month_index>', methods=['GET', 'POST'])
@login_required
def school_subject(subject_classes, month_index):
    subject_classes_ids = subject_classes.split('-')
    subject_id = int(subject_classes_ids[0])
    classes_ids = [int(sc_cl) for sc_cl in subject_classes_ids[1:]]
    subject_records, dates_topics = subject_record(subject_id, classes_ids, int(month_index))
    sc_students = subject_records.keys()
    subject = Subject.query.filter_by(id=subject_id).first()
    school_classes = SchoolClass.query.filter(SchoolClass.id.in_(classes_ids)).order_by(SchoolClass.school_class).all()
    school_classes_names = ', '.join([cl.school_name for cl in school_classes])

    return render_template('school_subject.html', subject_records=subject_records, dates_topics=dates_topics,
                           students=sc_students, subject=subject, school_classes=school_classes_names)


@app.route('/student-record/<string:student_id>/<string:month_index>', methods=['GET', 'POST'])
@login_required
def student_school_record(student_id, month_index):
    school_student = Person.query.filter_by(id=int(student_id)).first()
    if school_student:
        student_records, dates_topics = student_record(school_student, int(month_index))
        student_subjects = student_records.keys()

        return render_template('school_student.html', student=school_student, dates_topics=dates_topics,
                               student_records=student_records, student_subjects=student_subjects,
                               month_index=int(month_index))


@app.route('/after-school/<string:month_index>')
@login_required
def after_school(month_index):
    after_school_subject = Subject.query.filter(Subject.subject_type.has(SubjectType.name == 'after_school')).first()
    month_students, period, current_period = get_after_school_students(int(month_index))
    after_school_subject.month_students = month_students
    month_students_ids = [student.id for student in month_students]
    possible_clients = Person.query.filter(
        ~Person.id.in_(month_students_ids),
        Person.status.in_(["Клиент", "Лид"]),
        Person.person_type == "Ребенок"
    ).order_by(Person.last_name, Person.first_name).all()
    after_school_prices = get_after_school_prices()

    return render_template('after_school.html', after_school_subject=after_school_subject, period=period,
                           current_period=current_period, months=MONTHS, month_index=int(month_index),
                           possible_clients=possible_clients, after_school_prices=after_school_prices,
                           today=f'{TODAY:%d.%m.%Y}')


@app.route('/after-school-purchase', methods=['POST'])
@login_required
def after_school_purchase():
    try:
        attendee_id = int(request.form.get("selected_client"))
        period = request.form.get("period")
        new_after_school = handle_after_school_adding(attendee_id, request.form, period)
        db.session.add(new_after_school)
        db.session.flush()
        price = new_after_school.subscription_type.price
        if new_after_school.period not in ["month", "day"]:
            hours = int(new_after_school.period.split()[0])
            price *= hours
        description = "Оплата продленки"
        finance_operation(attendee_id, -price, description)
        db.session.commit()
        flash('Клиент записан на продленку', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при записи на продленку: {str(e)}', 'error')

    return redirect(request.referrer)


@app.route('/generate-report/<string:week>')
@login_required
def generate_employee_report(week):
    try:
        all_employees = Person.query.filter(
            Person.roles.any(Employee.id)
        ).order_by(Person.last_name, Person.first_name).all()

        employees_list, dates = employee_record(all_employees, int(week))
        header = ["Имя", "Должность/предмет"] + dates

        filename = f"employee_report_{dates[0].replace('.', '_')}_{dates[-1].replace('.', '_')}.xlsx"
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(header)

        for record in employees_list:
            row = [record["name"], record["role"]]
            activity = [record["activity"].get(date, 0) for date in dates]
            row += activity
            sheet.append(row)

        excel_buffer = BytesIO()
        workbook.save(excel_buffer)
        excel_buffer.seek(0)
        return send_file(excel_buffer, download_name=filename, as_attachment=True)

    except Exception as e:
        flash(f'Ошибка при скачивании файла: {str(e)}', 'error')
        return


@app.route('/generate-timetable/<string:week>')
@login_required
def generate_timetable(week):
    try:
        workbook, dates = download_timetable(int(week))

        filename = f"timetable_{dates[0].replace('.', '_')}_{dates[-1].replace('.', '_')}.xlsx"
        excel_buffer = BytesIO()
        workbook.save(excel_buffer)
        excel_buffer.seek(0)
        return send_file(excel_buffer, download_name=filename, as_attachment=True)

    except Exception as e:
        flash(f'Ошибка при скачивании файла: {str(e)}', 'error')
        return

