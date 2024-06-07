from flask import render_template, flash, redirect, url_for, request, send_file
from flask_login import login_user, logout_user, current_user, login_required
from app.models import User, Person, Employee, Lesson, Subscription, SubjectType, Subject, Room, SchoolClass, \
    SubscriptionType, SchoolLessonJournal, Finance
from app.forms import LoginForm, ChildForm, AdultForm, EditStudentForm, EditContactPersonForm, ContactForm, \
    EditAddContPersonForm, AddContForm, NewContactPersonForm, SubscriptionsEditForm, EmployeeForm, PersonForm, \
    ExtraSubjectForm, EditExtraSubjectForm, AddLessonsForm, EditLessonForm
from wtforms.validators import InputRequired
from app.app_functions import DAYS_OF_WEEK, MONTHS, get_today_date, basic_student_info, subscription_subjects_data, \
    lesson_subjects_data, potential_client_subjects, purchase_subscription, add_child, add_adult, clients_data, \
    extensive_student_info, student_lesson_register, handle_student_edit, format_employee, add_new_employee, \
    handle_employee_edit, format_subscription_types, add_new_subject, handle_subject_edit, week_lessons_dict, \
    change_lessons_date, day_school_lessons_dict, filter_lessons, copy_filtered_lessons, add_new_lessons, \
    subjects_data, calculate_week, lesson_edit, show_lesson, handle_lesson, format_school_class_students, \
    format_school_class_subjects, show_school_lesson, handle_school_lesson, employee_record, school_subject_record, \
    add_new_grade, change_grade, calc_month_index, student_record, get_after_school_students, get_after_school_prices, \
    handle_after_school_adding, finance_operation, download_timetable, get_date_range, get_period, del_record, \
    add_new_event, get_date, user_action, subject_record, OPERATION_TYPES, check_subscriptions, calc_day_index
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy import distinct
from app import app, db
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
        user_action(user, "Вход в систему")
        db.session.commit()
        flash('Вы успешно вошли в систему', "success")
        return redirect(url_for('students'))
    return render_template('login.html', form=form)


@app.route('/logout')
def logout():
    user_action(current_user, "Выход из системы")
    db.session.commit()
    logout_user()
    flash('Вы вышли из системы', "success")
    return redirect(url_for('login'))


@app.route('/settings')
@login_required
def settings():
    rooms = Room.query.all()
    school_classes = SchoolClass.query.order_by(SchoolClass.school_class, SchoolClass.school_name).all()
    subscription_types = SubscriptionType.query.filter(SubscriptionType.lessons.isnot(None)).all()
    after_school_prices = SubscriptionType.query.filter(SubscriptionType.period != '').all()

    return render_template('settings.html', rooms=rooms, school_classes=school_classes,
                           subscription_types=subscription_types, after_school_prices=after_school_prices)


@app.route('/change-add-room', methods=['POST'])
@login_required
def change_add_room():
    try:
        if current_user.rights == 'admin':
            if 'change_room_btn' in request.form:
                room_id = int(request.form.get('change_room_btn')) if request.form.get('change_room_btn').isdigit() \
                    else None
                new_name = request.form.get(f'name_{room_id}')
                new_color = request.form.get(f'color_{room_id}')
                room = Room.query.filter_by(id=room_id).first()
                if room and new_name and new_color:
                    room.name = new_name
                    room.color = new_color
                    user_action(current_user, f"Внесение изменений в кабинет '{room.name}'")
                    db.session.commit()
                    flash(f"Кабинет '{room.name}' изменен", 'success')

            if 'delete_room_btn' in request.form:
                room_id = int(request.form.get('delete_room_btn')) if request.form.get('delete_room_btn').isdigit() \
                    else None
                room = Room.query.filter_by(id=room_id).first()
                if room:
                    db.session.delete(room)
                    user_action(current_user, f"Удаление кабинета '{room.name}'")
                    db.session.commit()
                    flash(f"Кабинет '{room.name}' удален", 'success')

            if 'add_room' in request.form:
                room_name = request.form.get('room_name')
                room_color = request.form.get('room_color')
                new_room = Room(name=room_name, color=room_color)
                db.session.add(new_room)
                user_action(current_user, f"Добавление кабинета '{new_room.name}'")
                db.session.commit()
                flash(f"Новый кабинет '{new_room.name}' добавлен в систему", 'success')

        else:
            flash('Нет прав руководителя', 'error')

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при добавлении/изменении кабинета: {str(e)}', 'error')

    return redirect(url_for('settings'))


@app.route('/change-add-class', methods=['POST'])
@login_required
def change_add_class():
    try:
        if current_user.rights == 'admin':
            if 'change_class_btn' in request.form:
                class_id = int(request.form.get('change_class_btn')) if request.form.get('change_class_btn').isdigit() \
                    else None
                new_school_class = int(request.form.get(f'class_{class_id}')) \
                    if request.form.get(f'class_{class_id}').isdigit() else None
                new_school_name = request.form.get(f'name_{class_id}')
                school_class = SchoolClass.query.filter_by(id=class_id).first()
                if school_class and new_school_class and new_school_name:
                    school_class.school_class = new_school_class
                    school_class.school_name = new_school_name
                    user_action(current_user, f"Внесение изменений в класс '{school_class.school_name}'")
                    db.session.commit()
                    flash(f"Класс '{school_class.school_name}' изменен", 'success')

            if 'delete_class_btn' in request.form:
                class_id = int(request.form.get('delete_class_btn')) if request.form.get('delete_class_btn').isdigit() \
                    else None
                school_class = SchoolClass.query.filter_by(id=class_id).first()
                if school_class:
                    db.session.delete(school_class)
                    user_action(current_user, f"Удаление класса '{school_class.school_name}'")
                    db.session.commit()
                    flash(f"Класс '{school_class.school_name}' удален", 'success')

            if 'add_class' in request.form:
                new_school_class = int(request.form.get('new_school_class')) \
                    if request.form.get('new_school_class').isdigit() else None
                new_school_name = request.form.get('new_school_name')
                new_class = SchoolClass(school_class=new_school_class, school_name=new_school_name)
                db.session.add(new_class)
                user_action(current_user, f"Добавление класса '{new_class.school_name}'")
                db.session.commit()
                flash(f"Новый класс '{new_class.school_name}' добавлен в систему", 'success')

        else:
            flash('Нет прав руководителя', 'error')

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при добавлении/изменении кабинета: {str(e)}', 'error')

    return redirect(url_for('settings'))


@app.route('/change-add-subscription', methods=['POST'])
@login_required
def change_add_subscription():
    try:
        if current_user.rights == 'admin':
            if 'change_subscription_btn' in request.form:
                subscription_type_id = int(request.form.get('change_class_subscription')) \
                    if request.form.get('change_class_subscription').isdigit() else None
                subscription_lessons = int(request.form.get(f'lessons_{subscription_type_id}')) \
                    if request.form.get(f'lessons_{subscription_type_id}').isdigit() else None
                subscription_duration = int(request.form.get(f'duration_{subscription_type_id}')) \
                    if request.form.get(f'duration_{subscription_type_id}').isdigit() else None
                subscription_price = request.form.get(f'price_{subscription_type_id}').replace(',', '.')
                if not subscription_price.replace('.', '').isdigit():
                    flash('Неправильный формат цены', 'error')
                    return redirect(url_for('settings'))

                subscription_type = SubscriptionType.query.filter_by(id=subscription_type_id).first()
                if subscription_type and subscription_lessons and subscription_duration:
                    same_subscription_type = SubscriptionType.query.filter_by(
                        lessons=subscription_lessons,
                        duration=subscription_duration,
                        price=float(subscription_price)
                    ).all()
                    if not same_subscription_type:
                        subscription_type.lessons = subscription_lessons
                        subscription_type.duration = subscription_duration
                        subscription_type.price = float(subscription_price)
                        user_action(current_user, "Изменение абонемента")
                        db.session.commit()
                        flash('Абонемент изменен', 'success')
                    else:
                        flash('Такой абонемент уже есть', 'error')

            if 'delete_subscription_btn' in request.form:
                subscription_type_id = int(request.form.get('delete_subscription_btn')) \
                    if request.form.get('delete_subscription_btn').isdigit() else None
                subscription_type = SubscriptionType.query.filter_by(id=subscription_type_id).first()
                if subscription_type:
                    db.session.delete(subscription_type)
                    user_action(current_user, "Удаление абонемента")
                    db.session.commit()
                    flash('Абонемент удален', 'success')

            if 'add_subscription' in request.form:
                new_subscription_lessons = int(request.form.get('new_subscription_lessons')) \
                    if request.form.get('new_subscription_lessons').isdigit() else None
                new_subscription_duration = int(request.form.get('new_subscription_duration')) \
                    if request.form.get('new_subscription_duration').isdigit() else None
                new_subscription_price = request.form.get('new_subscription_price').replace(',', '.')
                if not new_subscription_price.replace('.', '').isdigit():
                    flash('Неправильный формат цены', 'error')
                    return redirect(url_for('settings'))
                if new_subscription_lessons and new_subscription_duration:
                    same_subscription_type = SubscriptionType.query.filter_by(
                        lessons=new_subscription_lessons,
                        duration=new_subscription_duration,
                        price=float(new_subscription_price)
                    ).all()
                    if not same_subscription_type:
                        new_subscription = SubscriptionType(
                            lessons=new_subscription_lessons,
                            duration=new_subscription_duration,
                            price=float(new_subscription_price)
                        )
                        db.session.add(new_subscription)
                        user_action(current_user, "Добавление абонемента")
                        db.session.commit()
                        flash('Новый абонемент добавлен в систему', 'success')

                    else:
                        flash('Такой абонемент уже есть', 'error')

        else:
            flash('Нет прав руководителя', 'error')

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при добавлении/изменении абонемента: {str(e)}', 'error')

    return redirect(url_for('settings'))


@app.route('/change-add-after-school', methods=['POST'])
@login_required
def change_add_after_school():
    try:
        if current_user.rights == 'admin':
            if 'change_after_school_btn' in request.form:
                after_school_id = int(request.form.get('change_after_school_btn')) \
                    if request.form.get('change_after_school_btn').isdigit() else None
                after_school_period = request.form.get(f'period_{after_school_id}')
                after_school_price = request.form.get(f'price_{after_school_id}').replace(',', '.')
                if not after_school_price.replace('.', '').isdigit():
                    flash('Неправильный формат цены', 'error')
                    return redirect(url_for('settings'))

                after_school_type = SubscriptionType.query.filter_by(id=after_school_id).first()
                if after_school_type and after_school_period:
                    same_subscription_type = SubscriptionType.query.filter_by(
                        period=after_school_period,
                        price=float(after_school_price)
                    ).all()
                    if not same_subscription_type:
                        after_school_type.period = after_school_period
                        after_school_type.price = float(after_school_price)
                        user_action(current_user, "Изменение цены на продленку")
                        db.session.commit()
                        flash('Цена на продленку изменена', 'success')
                    else:
                        flash('Такая цена на продленку уже есть', 'error')

            if 'delete_after_school_btn' in request.form:
                after_school_id = int(request.form.get('delete_after_school_btn')) \
                    if request.form.get('delete_after_school_btn').isdigit() else None
                after_school_type = SubscriptionType.query.filter_by(id=after_school_id).first()
                if after_school_type:
                    db.session.delete(after_school_type)
                    user_action(current_user, "Удаление цены на продленку")
                    db.session.commit()
                    flash('Цена на продленку удалена', 'success')

            if 'add_after_school' in request.form:
                new_after_school_period = request.form.get('new_period')
                new_after_school_price = request.form.get('new_price').replace(',', '.')
                if not new_after_school_price.replace('.', '').isdigit():
                    flash('Неправильный формат цены', 'error')
                    return redirect(url_for('settings'))

                if new_after_school_period:
                    same_subscription_type = SubscriptionType.query.filter_by(
                        period=new_after_school_period,
                        price=float(new_after_school_price)
                    ).all()
                    if not same_subscription_type:
                        new_after_school_type = SubscriptionType(
                            period=new_after_school_period,
                            price=float(new_after_school_price)
                        )
                        db.session.add(new_after_school_type)
                        user_action(current_user, "Добавление цены на продленку")
                        db.session.commit()
                        flash('Новая цена на продленку добавлена в систему', 'success')

                    else:
                        flash('Такая цена на продленку уже есть', 'error')

        else:
            flash('Нет прав руководителя', 'error')

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при добавлении/изменении цены на продленку: {str(e)}', 'error')

    return redirect(url_for('settings'))


@app.route('/create-user', methods=['POST'])
@login_required
def create_user():
    try:
        if current_user.rights == 'admin':
            username = request.form.get('username')
            password = request.form.get('password')
            repeat_password = request.form.get('repeat_password')
            rights = request.form.get('rights')
            if password == repeat_password:
                same_username = User.query.filter_by(username=username).all()
                if not same_username:
                    new_user = User(
                        username=username,
                        rights=rights
                    )
                    new_user.set_password(password)
                    db.session.add(new_user)
                    user_action(current_user, f"Добавление пользователя {new_user.username}")
                    db.session.commit()
                    flash(f'Новый пользователь {new_user.username} зарегистрирован', 'success')
                else:
                    flash(f'Пользователь {username} уже существует. Выберете другое имя пользователя', 'error')
            else:
                flash('Пароли не совпадают', 'error')

        else:
            flash('Нет прав руководителя', 'error')

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при добавлении пользователя: {str(e)}', 'error')

    return redirect(url_for('settings'))


@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    try:
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        if current_user.check_password(old_password):
            current_user.password = current_user.set_password(new_password)
            user_action(current_user, f"Изменение пароля")
            db.session.commit()
            flash('Пароль успешно изменен', 'success')

        else:
            flash('Неправильный пароль', 'error')

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при изменении пароля: {str(e)}', 'error')

    return redirect(url_for('settings'))


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
                           today=f'{get_today_date():%d.%m.%Y}', lesson_subjects=lesson_subjects)


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
        if current_user.rights in ["admin", "user"]:
            student_id = int(student_id) if str(student_id).isdigit() else None
            student = Person.query.filter_by(id=student_id, status="Клиент").first()
            lesson, message = student_lesson_register(request.form, student)
            if lesson:
                description = f"Запись клиента {student.last_name} {student.first_name} " \
                              f"на занятие {lesson.subject.name} {lesson.date:%d.%m.%Y}"
                user_action(current_user, description)
                db.session.commit()
                flash(message, 'success')

                return redirect(url_for('lesson', lesson_str=f'1-{lesson.id}'))

            else:
                flash(message, 'error')

        else:
            flash('Нет прав администратора', 'error')

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при записи клиента: {str(e)}', 'error')

    return redirect(request.referrer)


@app.route('/student-subjects/<string:student_id>', methods=['POST'])
@login_required
def student_subjects_add(student_id):
    try:
        if current_user.rights in ["admin", "user"]:
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

                user_action(current_user, f"Добавление занятий лиду {student.last_name} {student.first_name}")
                db.session.commit()
                flash('Занятия добавлены', 'success')

        else:
            flash('Нет прав администратора', 'error')

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при записи клиента: {str(e)}', 'error')

    return redirect(request.referrer)


@app.route('/subscription', methods=['POST'])
@login_required
def subscription():
    try:
        if current_user.rights in ["admin", "user"]:
            new_subscription, price, operation_type = purchase_subscription(request.form)
            db.session.add(new_subscription)
            db.session.flush()
            description = f"Покупка абонемента {new_subscription.subject.name}"
            finance_operation(new_subscription.student, -price, operation_type,
                              description, "subscription", new_subscription.id)
            user_action(current_user, f"Покупка абонемента {new_subscription.subject.name} клиентом "
                                      f"{new_subscription.student.last_name} {new_subscription.student.first_name}")
            db.session.commit()
            flash('Новый абонемент добавлен в систему', 'success')

            return redirect(url_for('show_edit_student', student_id=new_subscription.student_id))

        else:
            flash('Нет прав администратора', 'error')

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при добавлении абонемента: {str(e)}', 'error')

    return redirect(request.referrer)


@app.route('/deposit/<string:student_id>', methods=['POST'])
@login_required
def deposit(student_id):
    try:
        if current_user.rights in ["admin", "user"]:
            amount = request.form.get('deposit')
            if amount:
                operation_type = request.form.get('operation_type')
                deposit = Decimal(amount)
                student = Person.query.filter_by(id=student_id).first()
                description = f"Пополнение баланса клиента"
                finance_operation(student, deposit, operation_type, description, "balance", None, True)
                user_description = f"{description} {student.last_name} {student.first_name} " \
                                   f"({OPERATION_TYPES.get(operation_type, '?')} {deposit:.1f})"
                user_action(current_user, user_description)
                db.session.commit()
                flash(f'Депозит внесен на счет клиента {student.last_name} {student.first_name}', 'success')

        else:
            flash('Нет прав администратора', 'error')

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при внесении депозита: {str(e)}', 'error')

    return redirect(request.referrer)


@app.route('/add-student', methods=['GET', 'POST'])
@login_required
def add_student():
    if current_user.rights in ["admin", "user"]:
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
                        student, message = add_child(form1)
                        if student:
                            user_action(current_user, f"Добавление клиента {student.last_name} {student.first_name}")
                            db.session.commit()
                            flash('Новый клиент добавлен в систему', 'success')
                            return redirect(url_for('show_edit_student', student_id=student.id))

                        else:
                            flash(message, 'error')

                if 'add_adult_btn' in request.form:
                    render_type = 'adult'
                    if form2.validate_on_submit():
                        client, message = add_adult(form2)
                        if client:
                            user_action(current_user, f"Добавление клиента {client.last_name} {client.first_name}")
                            db.session.commit()
                            flash('Новый клиент добавлен в систему', 'success')
                            return redirect(url_for('show_edit_student', student_id=client.id))

                        else:
                            flash(message, 'error')

                flash('Ошибка в форме добавления киента', 'error')

            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при добавлении киента: {str(e)}', 'error')
                return redirect(url_for('add_student'))

        return render_template('add_student.html', clients=clients, possible_clients=possible_clients,
                               form1=form1, form2=form2, render_type=render_type)

    else:
        flash('Нет прав администратора', 'error')
        return redirect(url_for('students'))


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
                    'full_subscription': subscription["full_subscription"],
                    'purchase_date': subscription["purchase_date"],
                    'end_date': subscription["end_date"]
                })
        subscriptions_form = SubscriptionsEditForm(data=data)
        student_finances = Finance.query.filter_by(person_id=student.id).order_by(
            Finance.date.desc(), Finance.id.desc()
        ).all()
        student.finance_operations = student_finances
        render_type = 'student'

        if request.method == 'POST':
            try:
                if current_user.rights in ["admin", "user"]:
                    if 'form_student_submit' in request.form:
                        render_type = 'edit_student'
                        if student_form.validate_on_submit():
                            message = handle_student_edit(student_form, student, 'edit_student', current_user)
                            if not message:
                                description = f"Изменение данных клиента {student.last_name} {student.first_name}"
                                user_action(current_user, description)
                                db.session.commit()
                                flash('Изменения внесены', 'success')
                                return redirect(url_for('show_edit_student', student_id=student.id))

                            else:
                                flash(message, 'error')

                    if 'form_main_contact_submit' in request.form:
                        render_type = 'contact_main_edit'
                        if main_contact_form.validate_on_submit():
                            message = handle_student_edit(main_contact_form, student, 'edit_main_contact', current_user)
                            if not message:
                                description = f"Изменение основного контакта клиента " \
                                              f"{student.last_name} {student.first_name}"
                                user_action(current_user, description)
                                db.session.commit()
                                flash('Изменения внесены', 'success')
                                return redirect(url_for('show_edit_student', student_id=student.id))

                            else:
                                flash(message, 'error')

                    for i in range(1, len(student.additional_contacts) + 2):
                        if f'form_cont_{i}_submit' in request.form:
                            render_type = f'contact_edit_{i}'
                            if add_cont_forms[i-1].validate_on_submit():
                                message = handle_student_edit(add_cont_forms[i-1], student,
                                                              f'edit_contact_{i}', current_user)
                                if not message:
                                    description = f"Изменение контактных данных клиента " \
                                                  f"{student.last_name} {student.first_name}"
                                    user_action(current_user, description)
                                    db.session.commit()
                                    flash('Изменения внесены', 'success')
                                    return redirect(url_for('show_edit_student', student_id=student.id))

                                else:
                                    flash(message, 'error')

                    if 'form_cont_new_submit' in request.form:
                        render_type = 'contact_new'
                        if new_contact_form.validate_on_submit():
                            message = handle_student_edit(new_contact_form, student, 'new_contact', current_user)
                            if not message:
                                description = f"Добавление нового контакта клиенту {student.last_name} " \
                                              f"{student.first_name}"
                                user_action(current_user, description)
                                db.session.commit()
                                flash('Новый контакт добавлен', 'success')
                                return redirect(url_for('show_edit_student', student_id=student.id))

                            else:
                                flash(message, 'error')

                    if 'del_subject_btn' in request.form:
                        handle_student_edit(request.form, student, 'del_subject', current_user)
                        description = f"Удаление занятия у клиента {student.last_name} {student.first_name}"
                        user_action(current_user, description)
                        db.session.commit()
                        flash('Изменения внесены', 'success')
                        return redirect(url_for('show_edit_student', student_id=student.id))

                    if 'form_subscriptions_submit' in request.form:
                        if current_user.rights == 'admin':
                            render_type = 'subscription'
                            if subscriptions_form.validate_on_submit():
                                handle_student_edit(subscriptions_form, student, 'subscription', current_user)
                                db.session.commit()
                                flash('Изменения внесены', 'success')
                                return redirect(url_for('show_edit_student', student_id=student.id))

                        else:
                            flash('Нет прав руководителя', 'error')
                            return redirect(url_for('show_edit_student', student_id=student.id))

                    if 'del_after_school' in request.form:
                        if current_user.rights == 'admin':
                            handle_student_edit(request.form, student, 'del_after_school', current_user)
                            description = f"Отмена покупки продленки клиента {student.last_name} {student.first_name}"
                            user_action(current_user, description)
                            db.session.commit()
                            flash('Изменения внесены', 'success')

                        else:
                            flash('Нет прав руководителя', 'error')

                        return redirect(url_for('show_edit_student', student_id=student.id))

                    flash('Ошибка в форме изменения клиента', 'error')

                else:
                    flash('Нет прав администратора', 'error')

            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при внесении изменений: {str(e)}', 'error')
                return redirect(url_for('show_edit_student', student_id=student.id))

        return render_template('student.html', student=student, clients=clients, today=f'{get_today_date():%d.%m.%Y}',
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
    all_employees = Person.query.filter(
        Person.roles.any(Employee.id)
    ).order_by(Person.last_name, Person.first_name).all()

    for employee in all_employees:
        format_employee(employee)

    return render_template('employees.html', employees=all_employees)


@app.route('/employee-report/<string:week>')
@login_required
def employee_report(week):
    if current_user.rights in ["admin", "user"]:
        week = int(week)
        all_employees = Person.query.filter(
            Person.roles.any(Employee.id)
        ).order_by(Person.last_name, Person.first_name).all()

        employees_list, dates = employee_record(all_employees, week)
        filename = f"employee_report_{dates[0].replace('.', '_')}_{dates[-1].replace('.', '_')}.xlsx"

        return render_template('employee_report.html', employees=employees_list, dates=dates,
                               week=week, filename=filename)

    else:
        flash('Нет прав администратора', 'error')
        return redirect(url_for('employees'))


@app.route('/add-employee', methods=['GET', 'POST'])
@login_required
def add_employee():
    if current_user.rights in ["admin", "user"]:
        possible_employees = clients_data('employee')
        distinct_roles = db.session.query(Employee.role.distinct()).all()
        all_subjects = Subject.query.filter(
            Subject.subject_type.has(SubjectType.name != 'event')
        ).order_by(Subject.name).all()
        school_classes = SchoolClass.query.order_by(SchoolClass.school_class, SchoolClass.school_name).all()
        subject_list = [(subj.id, f'{subj.name} ({subj.subject_type.description})') for subj in all_subjects]
        school_classes_list = [(sc_cl.id, sc_cl.school_name) for sc_cl in school_classes]
        form = EmployeeForm()
        form.selected_client.choices = [(person["id"], f"{person['last_name']} {person['first_name']}")
                                        for person in possible_employees]
        form.roles.choices = ["Учитель"] + [role[0] for role in distinct_roles]
        form.subjects.choices = subject_list
        form.school_classes.choices = school_classes_list

        if request.method == 'POST':
            try:
                if form.validate_on_submit():
                    employee, message = add_new_employee(form)
                    if employee:
                        description = f'Добавление нового сотрудника {employee.last_name} {employee.first_name}'
                        user_action(current_user, description)
                        db.session.commit()
                        flash('Новый сотрудник добавлен в систему.', 'success')
                        return redirect(url_for('show_edit_employee', employee_id=employee.id))

                    else:
                        flash(message, 'error')

                flash('Ошибка в форме добавления сотрудника', 'error')

            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при добавлении сотрудника: {str(e)}', 'error')
                return redirect(url_for('add_employee'))

        return render_template('add_employee.html', possible_employees=possible_employees, form=form)

    else:
        flash('Нет прав администратора', 'error')
        return redirect(url_for('employees'))


@app.route('/employee/<string:employee_id>', methods=['GET', 'POST'])
@login_required
def show_edit_employee(employee_id):
    employee_id = int(employee_id) if str(employee_id).isdigit() else None
    employee = Person.query.filter(Person.id == employee_id, Person.roles.any(Employee.id)).first()

    if employee:
        format_employee(employee)
        form = PersonForm(
            first_name=employee.first_name,
            last_name=employee.last_name,
            patronym=employee.patronym
        )

        if employee.teacher:
            future_lessons = Lesson.query.filter(Lesson.date >= get_today_date(), Lesson.teacher_id == employee_id).all()
            lesson_subjects = set([lesson.subject.id for lesson in future_lessons])
            employee.future_lessons = future_lessons
            employee.lesson_subjects = lesson_subjects

        render_type = 'show'

        if request.method == 'POST':
            try:
                if current_user.rights in ["admin", "user"]:
                    render_type = 'edit'
                    if form.validate_on_submit():
                        message = handle_employee_edit(request.form, employee)
                        if not message:
                            description = f'Изменение данных сотрудника {employee.last_name} {employee.first_name}'
                            user_action(current_user, description)
                            db.session.commit()
                            flash('Изменения внесены', 'success')
                            return redirect(url_for('show_edit_employee', employee_id=employee.id))

                        else:
                            flash(message, 'error')

                    flash('Ошибка в форме изменения сотрудника', 'error')

                else:
                    flash('Нет прав администратора', 'error')
                    return redirect(url_for('show_edit_employee', employee_id=employee.id))

            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при внесении изменений: {str(e)}', 'error')

                return redirect(url_for('show_edit_employee', employee_id=employee.id))

        employee_roles = [role.role for role in employee.roles]
        possible_roles = db.session.query(Employee.role.distinct()).filter(
            ~Employee.role.in_(employee_roles)
        ).all()
        employee_subjects = [subject.id for subject in employee.subjects_taught]
        employee_classes = [sc_cl.id for sc_cl in employee.teaching_classes]
        possible_subjects = Subject.query.filter(
            ~Subject.id.in_(employee_subjects),
            Subject.subject_type.has(SubjectType.name != 'event')
        ).order_by(Subject.name).all()
        all_subjects = Subject.query.filter(
            Subject.subject_type.has(SubjectType.name != 'event')
        ).order_by(Subject.name).all()
        possible_classes = SchoolClass.query.filter(
            ~SchoolClass.id.in_(employee_classes)
        ).order_by(SchoolClass.school_class, SchoolClass.school_name).all()
        all_classes = SchoolClass.query.order_by(SchoolClass.school_class, SchoolClass.school_name).all()

        return render_template('employee.html', employee=employee, form=form, possible_roles=possible_roles,
                               possible_subjects=possible_subjects, subjects=all_subjects, render_type=render_type,
                               possible_classes=possible_classes, school_classes=all_classes)
    else:
        flash("Такого сотрудника нет", 'error')
        return redirect(url_for('employees'))


@app.route('/subjects')
@login_required
def subjects():
    all_subjects = Subject.query.filter(
        Subject.subject_type.has(SubjectType.name.in_(['extra', 'individual']))
    ).order_by(Subject.name).all()
    for subject in all_subjects:
        subject.types_of_subscription = format_subscription_types(subject.subscription_types.all())

    return render_template('subjects.html', subjects=all_subjects)


@app.route('/add-subject', methods=['GET', 'POST'])
@login_required
def add_subject():
    if current_user.rights in ["admin", "user"]:
        subject_types = SubjectType.query.filter(~SubjectType.name.in_(['after_school', 'school', 'event'])).all()
        subscription_types = format_subscription_types(SubscriptionType.query.all())
        all_teachers = Person.query.filter_by(teacher=True).order_by(Person.last_name, Person.first_name).all()
        form = ExtraSubjectForm()
        form.subject_type.choices = [(subject_type.id, subject_type.description) for subject_type in subject_types]
        form.subscription_types.choices = [(type_of_subscription[0], type_of_subscription[1])
                                           for type_of_subscription in subscription_types]
        form.teachers.choices = [(teacher.id, f"{teacher.last_name} { teacher.first_name }") for teacher in all_teachers]
        if request.method == 'POST':
            try:
                if form.validate_on_submit():
                    new_subject = add_new_subject(form, "extra_school")
                    if new_subject:
                        db.session.add(new_subject)
                        db.session.flush()
                        user_description = f"Добавление нового предмета {new_subject.name} " \
                                           f"({new_subject.subject_type.description})"
                        user_action(current_user, user_description)
                        db.session.commit()
                        flash('Новый предмет добавлен в систему', 'success')
                        return redirect(url_for('subjects'))

                    else:
                        flash('Предмет с таким названием уже есть', 'error')
                        return redirect(url_for('add_subject'))

                flash('Ошибка в форме добавления предмета', 'error')

            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при добавлении предмета: {str(e)}', 'error')

                return redirect(url_for('add_subject'))

        return render_template('add_subject.html', form=form)

    else:
        flash('Нет прав администратора', 'error')
        return redirect(url_for('subjects'))


@app.route('/edit-subject/<string:subject_id>', methods=['GET', 'POST'])
@login_required
def edit_subject(subject_id):
    if current_user.rights in ["admin", "user"]:
        subject_id = int(subject_id) if str(subject_id).isdigit() else None
        subject = Subject.query.filter(
            Subject.id == subject_id,
            Subject.subject_type.has(SubjectType.name.in_(['extra', 'individual']))
        ).first()
        if subject:
            form = EditExtraSubjectForm(
                subject_name=subject.name,
                subject_short_name=subject.short_name,
                subject_price=round(subject.one_time_price, 1),
                subject_school_price=round(subject.school_price, 1) if subject.school_price else None,
                no_subject_school_price=True if not subject.school_price else False
            )
            subject.types_of_subscription = format_subscription_types(subject.subscription_types.all())
            filtered_subscription_types = SubscriptionType.query.filter(
                ~SubscriptionType.subjects.any(Subject.id == subject.id)
            ).all()

            subscription_types = format_subscription_types(filtered_subscription_types)

            if request.method == 'POST':
                try:
                    if form.validate_on_submit():
                        handle_subject_edit(subject, request.form)
                        user_action(current_user, f'Внесение изменений в предмет {subject.name}')
                        db.session.commit()
                        flash('Изменения внесены', 'success')
                        return redirect(url_for('subjects'))

                    flash(f'Ошибка в форме изменения предмета', 'error')

                except Exception as e:
                    db.session.rollback()
                    flash(f'Ошибка при внесении изменений: {str(e)}', 'error')

                    return redirect(url_for('edit_subject', subject_id=subject_id))

            return render_template('edit_subject.html', subject=subject, form=form,
                                   subscription_types=subscription_types)

        else:
            flash("Такого занятия нет.", 'error')
            return redirect(url_for('subjects'))

    else:
        flash('Нет прав администратора', 'error')
        return redirect(url_for('subjects'))


@app.route('/timetable/<string:week>')
@login_required
def timetable(week):
    week = int(week) if str(week).lstrip('-').isdigit() else 0
    week_range = [f'{get_date(day, week):%d.%m}' for day in range(7)]
    all_rooms = Room.query.all()
    week_lessons, week_dates, used_rooms, time_range = week_lessons_dict(week, all_rooms)
    rooms = [room.name for room in all_rooms if room.name in used_rooms]
    cols = len(week_dates) * len(rooms)
    subject_types = SubjectType.query.all()
    events = Subject.query.filter(Subject.subject_type.has(SubjectType.name == 'event')).order_by(Subject.name).all()

    return render_template('timetable.html', days=DAYS_OF_WEEK, rooms=rooms, cols=cols, start_time=time_range[0],
                           end_time=time_range[1], classes=week_lessons, week=week, week_dates=week_dates,
                           all_rooms=all_rooms, events=events, subject_types=subject_types, week_range=week_range)


@app.route('/extra-timetable/<string:week>')
@login_required
def extra_timetable(week):
    week = int(week) if str(week).lstrip('-').isdigit() else 0
    all_rooms = Room.query.all()
    week_lessons, week_dates, used_rooms, time_range = week_lessons_dict(week, all_rooms, 'extra')
    rooms = [room.name for room in all_rooms if room.name in used_rooms]
    cols = len(week_dates) * len(rooms)

    return render_template('extra_timetable.html', days=DAYS_OF_WEEK, rooms=rooms, cols=cols, start_time=time_range[0],
                           end_time=time_range[1], classes=week_lessons, week=week, week_dates=week_dates,
                           timetable_type='extra')


@app.route('/individual-timetable/<string:week>')
@login_required
def individual_timetable(week):
    week = int(week) if str(week).lstrip('-').isdigit() else 0
    all_rooms = Room.query.all()
    week_lessons, week_dates, used_rooms, time_range = week_lessons_dict(week, all_rooms, 'individual')
    rooms = [room.name for room in all_rooms if room.name in used_rooms]
    cols = len(week_dates) * len(rooms)

    return render_template('extra_timetable.html', days=DAYS_OF_WEEK, rooms=rooms, cols=cols, start_time=time_range[0],
                           end_time=time_range[1], classes=week_lessons, week=week, week_dates=week_dates,
                           timetable_type='individual')


@app.route('/teacher-timetable/<string:teacher_id>/<string:week>')
@login_required
def teacher_timetable(teacher_id, week):
    teacher_id = int(teacher_id) if str(teacher_id).isdigit() else None
    teacher = Person.query.filter_by(id=teacher_id, teacher=True).first()
    if teacher:
        week = int(week) if str(week).lstrip('-').isdigit() else 0
        all_rooms = Room.query.all()
        week_lessons, week_dates, used_rooms, time_range = week_lessons_dict(week, all_rooms, f'teacher_{teacher_id}')
        rooms = [room.name for room in all_rooms if room.name in used_rooms]
        cols = len(week_dates) * len(rooms)

        return render_template('teacher_timetable.html', days=DAYS_OF_WEEK, rooms=rooms, cols=cols,
                               start_time=time_range[0], end_time=time_range[1], classes=week_lessons,
                               week=week, week_dates=week_dates, lessons_teacher=teacher)


@app.route('/add-event', methods=['POST'])
@login_required
def add_event():
    try:
        if current_user.rights in ["admin", "user"]:
            message, event = add_new_event(request.form)
            description = f"Добавление мероприятия '{event.subject.name}' {event.date:%d.%m.%y}"
            user_action(current_user, description)
            db.session.commit()
            flash(message[0], message[1])

        else:
            flash('Нет прав администратора', 'error')

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при добавлении мероприятия: {str(e)}', 'error')

    return redirect(request.referrer)


@app.route('/change-lessons', methods=['POST'])
@login_required
def change_lessons():
    try:
        if current_user.rights in ["admin", "user"]:
            new_week, message, dates = change_lessons_date(request.form)
            db.session.commit()
            for msg in message:
                flash(msg[0], msg[1])
            if new_week is not None:
                description = f"Перенос занятий с {dates[0]:%d.%m.%y} на {dates[1]:%d.%m.%y}"
                user_action(current_user, description)
                db.session.commit()
                return redirect(url_for('timetable', week=new_week))

            else:
                return redirect(request.referrer)

        else:
            flash('Нет прав администратора', 'error')

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при переносе занятий: {str(e)}', 'error')

        return redirect(request.referrer)


@app.route('/copy-lessons', methods=['GET', 'POST'])
@login_required
def copy_lessons():
    if current_user.rights in ["admin", "user"]:
        if request.method == 'POST':
            try:
                filtered_lessons, week_diff, next_week = filter_lessons(request.form)
                if filtered_lessons:
                    new_lessons, conflicts = copy_filtered_lessons(filtered_lessons, week_diff)
                    if new_lessons > 0:
                        week_range = f'{get_date(0, next_week):%d.%m}-{get_date(6, next_week):%d.%m.%Y}'
                        description = f'Копирование уроков в расписание на неделю {week_range}'
                        user_action(current_user, description)
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

        subject_types = SubjectType.query.filter(SubjectType.name != 'event').all()
        rooms = Room.query.all()
        school_classes = SchoolClass.query.order_by(SchoolClass.school_class).all()
        all_teachers = Person.query.filter_by(teacher=True).order_by(Person.last_name, Person.first_name).all()
        school = SubjectType.query.filter_by(name='school').first()

        return render_template('copy_lessons.html', days=DAYS_OF_WEEK, subject_types=subject_types, rooms=rooms,
                               school_classes=school_classes, teachers=all_teachers, school=school)

    else:
        flash('Нет прав администратора', 'error')
        return redirect(url_for('timetable', week=0))


@app.route('/add-lessons', methods=['GET', 'POST'])
@login_required
def add_lessons():
    if current_user.rights in ["admin", "user"]:
        all_subjects = subjects_data()
        rooms = Room.query.all()
        school_type = SubjectType.query.filter_by(name='school').first().id
        form = AddLessonsForm()
        form.lessons[0].subject.choices = [(f"{subject['id']}-{subject['subject_type']}",
                                            f"{subject['name']} ({subject['description']})")
                                           for subject in all_subjects]
        form.lessons[0].room.choices = [(room.id, room.name) for room in rooms]
        if request.method == 'POST':
            try:
                if form.validate_on_submit():
                    messages, date, new_lessons = add_new_lessons(form)
                    if new_lessons > 0:
                        week = calculate_week(date)
                        description = f"Добавление новых занятий в расписание {date:%d.%m.%Y}"
                        user_action(current_user, description)
                        db.session.commit()
                        for message in messages:
                            flash(message[0], message[1])

                        return redirect(url_for('timetable', week=week))

                    else:
                        for message in messages:
                            flash(message[0], message[1])

                else:
                    flash(f'Ошибка в форме добавления занятий', 'error')

            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при добавлении новых занятий: {str(e)}', 'error')
                return redirect(url_for('add_lessons'))

        school_classes = SchoolClass.query.order_by(SchoolClass.school_class).all()
        school_classes_data = [{school_class.id: school_class.school_name} for school_class in school_classes]
        all_teachers = Person.query.filter_by(teacher=True).order_by(Person.last_name, Person.first_name).all()
        teachers_data = [{teacher.id: f"{teacher.last_name} {teacher.first_name}"} for teacher in all_teachers]

        return render_template('add_lessons.html', subjects=all_subjects, school_classes=school_classes_data,
                               form=form, teachers=teachers_data, school_type=school_type)

    else:
        flash('Нет прав администратора', 'error')
        return redirect(url_for('timetable', week=0))


@app.route('/edit-lesson/<string:lesson_id>', methods=['GET', 'POST'])
@login_required
def edit_lesson(lesson_id):
    if current_user.rights in ["admin", "user"]:
        edited_lesson = Lesson.query.filter_by(id=lesson_id).first()
        if not edited_lesson:
            flash("Такого занятия нет", 'error')
            return redirect(url_for('timetable', week=0))

        if edited_lesson.lesson_completed:
            flash("Занятие уже проведено, невозможно изменить", 'error')
            return redirect(request.referrer)

        week = calculate_week(edited_lesson.date)
        rooms = Room.query.all()
        all_teachers = Person.query.filter_by(teacher=True).order_by(Person.last_name, Person.first_name).all()
        lesson_classes = sorted(edited_lesson.school_classes, key=lambda x: (x.school_class, x.school_name))
        lesson_classes_data = [cl.id for cl in lesson_classes] if lesson_classes else None
        form = EditLessonForm(
            lesson_date=f'{edited_lesson.date:%d.%m.%Y}',
            start_time=f'{edited_lesson.start_time:%H : %M}',
            end_time=f'{edited_lesson.end_time:%H : %M}',
            room=edited_lesson.room_id,
            school_classes=lesson_classes_data,
            split_classes=edited_lesson.split_classes,
            teacher=edited_lesson.teacher_id
        )
        form.subject.validators = []
        if edited_lesson.lesson_type.name == 'event':
            form.teacher.validators = []
        if edited_lesson.lesson_type.name == "school":
            all_classes = SchoolClass.query.order_by(
                SchoolClass.school_class, SchoolClass.school_name
            ).all()
            form.school_classes.choices = [(sc_cl.id, sc_cl.school_name) for sc_cl in all_classes]
            form.school_classes.validators = [InputRequired(message='Заполните это поле')]
            edited_lesson.classes = ', '.join([cl.school_name for cl in lesson_classes])

        form.room.choices = [(room.id, room.name) for room in rooms]
        form.teacher.choices = [(teacher.id, f'{teacher.last_name} {teacher.first_name}') for teacher in all_teachers]

        if request.method == 'POST':
            try:
                if form.validate_on_submit():
                    message = lesson_edit(form, edited_lesson)
                    if message[1] == 'error':
                        flash(message[0], message[1])
                        return redirect(url_for('edit_lesson', lesson_id=edited_lesson.id))

                    if message[1] == 'success':
                        description = f"Внесение изменений в занятие {edited_lesson.subject.name} " \
                                      f"{edited_lesson.date:%d.%m.%Y}"
                        user_action(current_user, description)
                        db.session.commit()
                        week = calculate_week(edited_lesson.date)
                        flash(message[0], message[1])

                        if edited_lesson.lesson_type.name == "school":
                            day = edited_lesson.date.weekday() + 1
                            return redirect(url_for('school_timetable', week=week, day=day))
                        else:
                            return redirect(url_for('timetable', week=week))
                else:
                    flash('Ошибка в форме изменения занятия', 'error')

            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при внесении изменений: {str(e)}', 'error')
                return redirect(url_for('edit_lesson', lesson_id=edited_lesson.id))

        return render_template('edit_lesson.html', lesson=edited_lesson, form=form, week=week)

    else:
        flash('Нет прав администратора', 'error')
        return redirect(url_for('timetable', week=0))


@app.route('/lesson/<string:lesson_str>', methods=['GET', 'POST'])
@login_required
def lesson(lesson_str):
    subject_lesson, lesson_subject = show_lesson(lesson_str)

    if subject_lesson:
        if request.method == 'POST':
            try:
                message = handle_lesson(request.form, lesson_subject, subject_lesson, current_user)
                if 'registered_btn' in request.form:
                    db.session.commit()
                    if message:
                        flash(message[0], message[1])

                else:
                    if message:
                        if message[1] == 'success':
                            db.session.commit()
                            flash(message[0], message[1])
                        else:
                            db.session.rollback()
                            flash(message[0], message[1])
                    else:
                        db.session.commit()

            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при проведении занятия: {str(e)}', 'error')

            return redirect(url_for('lesson', lesson_str=f'1-{subject_lesson.id}'))

        all_clients = Person.query.filter(Person.status.in_(["Клиент", "Лид"])).order_by(Person.last_name,
                                                                                         Person.first_name).all()
        possible_clients = [client for client in all_clients if client not in subject_lesson.students]

        other_lessons = Subject.query.filter(
            Subject.id != lesson_subject.id,
            ~Subject.subject_type.has(SubjectType.name.in_(['school', 'event']))
        ).order_by(Subject.name).all()
        month_index = calc_month_index(subject_lesson.date)

        return render_template('lesson.html', subject_lesson=subject_lesson, clients=possible_clients,
                               lesson_subject=lesson_subject, other_lessons=other_lessons,
                               today=get_today_date(), month_index=month_index)

    else:
        if lesson_subject.subject_type.name == 'after_school':
            return redirect(url_for('after_school', month_index=0))

        elif lesson_subject:
            other_lessons = Subject.query.filter(
                Subject.id != lesson_subject.id,
                ~Subject.subject_type.has(SubjectType.name.in_(['school', 'event']))
            ).order_by(Subject.name).all()

            return render_template('lesson.html', subject_lesson=subject_lesson, lesson_subject=lesson_subject,
                                   other_lessons=other_lessons)

        else:
            flash("Такого занятия нет", 'error')
            return redirect(url_for('subjects'))


@app.route('/subject/<string:subject_id>/<string:month_index>')
@login_required
def subject(subject_id, month_index):
    subject_id = int(subject_id) if str(subject_id).isdigit() else None
    subject = Subject.query.filter(
        Subject.id == subject_id,
        Subject.subject_type.has(SubjectType.name.in_(["extra", "individual"]))
    ).first()
    month_index = int(month_index) if str(month_index).lstrip('-').isdigit() else None
    if not subject or month_index is None:
        flash("Журнал не найден", 'error')
        return redirect(url_for('subjects'))

    subject_records, datetimes, subject_students, month = subject_record(subject_id, month_index)
    other_subjects = Subject.query.filter(
        Subject.id != subject_id,
        ~Subject.subject_type.has(SubjectType.name.in_(['school', 'event', 'after_school']))
    ).order_by(Subject.name).all()

    return render_template('subject_record.html', subject_records=subject_records, datetimes=datetimes,
                           students=subject_students, subject=subject, month_index=month_index,
                           other_subjects=other_subjects, month=month)


@app.route('/school-students/<string:school_class>', methods=['GET', 'POST'])
@login_required
def school_students(school_class):
    school_classes = SchoolClass.query.order_by(
        SchoolClass.school_class,
        SchoolClass.school_name
    ).all()

    if not school_classes:
        flash("Школьных классов еще нет", 'error')
        return redirect(url_for('students'))

    school_class = int(school_class) if str(school_class).isdigit() else None
    school = school_classes[0] if school_class == 0 else SchoolClass.query.filter_by(id=school_class).first()
    if school:
        format_school_class_students(school)
    else:
        flash("Такого класса нет", 'error')
        return redirect(url_for('school_students', school_class=0))

    if request.method == 'POST':
        if 'add_client_btn' in request.form:
            try:
                if current_user.rights in ["admin", "user"]:
                    added_student_id = int(request.form.get('added_student_id')) if request.form.get('added_student_id') else None
                    if added_student_id:
                        new_school_student = Person.query.filter_by(id=added_student_id).first()
                        new_school_student.school_class_id = school.id
                        for subject in school.school_subjects:
                            if subject not in new_school_student.subjects.all():
                                new_school_student.subjects.append(subject)

                        description = f"Добавление ученика {new_school_student.last_name} " \
                                      f"{new_school_student.first_name} в класс '{school.school_name}'"
                        user_action(current_user, description)
                        db.session.commit()
                        flash(f'Новый ученик добавлен в класс', 'success')
                    else:
                        flash('Ученик не выбран', 'error')

                else:
                    flash('Нет прав администратора', 'error')

            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при добавлении нового ученика: {str(e)}', 'error')

        if 'change_teacher_btn' in request.form:
            try:
                if current_user.rights in ["admin", "user"]:
                    main_teacher = int(request.form.get('main_teacher')) if request.form.get('main_teacher') else None
                    school.main_teacher_id = main_teacher
                    description = f"Изменение классного руководителя класса '{school.school_name}'"
                    user_action(current_user, description)
                    db.session.commit()
                    flash('Классный руководитель изменен', 'success')

                else:
                    flash('Нет прав администратора', 'error')

            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при внесении изменений: {str(e)}', 'error')

        return redirect(request.referrer)

    possible_students = Person.query.filter(
        Person.person_type == 'Ребенок',
        Person.status == 'Клиент',
        Person.school_class_id.is_(None)
    ).order_by(Person.last_name, Person.first_name).all()
    teachers = Person.query.filter_by(teacher=True).order_by(Person.last_name, Person.first_name).all()

    return render_template('school.html', school_classes=school_classes, school_class=school,
                           possible_students=possible_students, teachers=teachers, render_type="students")


@app.route('/school-subjects/<string:school_class>', methods=['GET', 'POST'])
@login_required
def school_subjects(school_class):
    school_classes = SchoolClass.query.order_by(
        SchoolClass.school_class,
        SchoolClass.school_name
    ).all()

    if not school_classes:
        flash("Школьных классов еще нет", 'error')
        return redirect(url_for('students'))

    school_class = int(school_class) if str(school_class).isdigit() else None
    school = school_classes[0] if school_class == 0 else SchoolClass.query.filter_by(id=school_class).first()
    if school:
        format_school_class_subjects(school)

    if request.method == 'POST':
        try:
            if current_user.rights in ["admin", "user"]:
                if 'new_subject' in request.form:
                    new_subject = add_new_subject(request.form, "school")
                    if new_subject:
                        db.session.add(new_subject)
                        description = f"Добавление нового школьного предмета {new_subject.name}"
                        user_action(current_user, description)
                        db.session.commit()
                        flash('Новый предмет добавлен в систему', 'success')

                    else:
                        flash('Школьный предмет с таким названием уже есть', 'error')

                if 'choose_subject' in request.form:
                    new_subject_id = int(request.form.get("selected_subject")) if \
                        request.form.get("selected_subject") else None
                    new_subject = Subject.query.filter(
                        Subject.id == new_subject_id,
                        Subject.subject_type.has(SubjectType.name == 'school')
                    ).first()
                    if new_subject:
                        if school not in new_subject.school_classes:
                            new_subject.school_classes.append(school)
                        teacher_ids = [int(teacher) for teacher in request.form.getlist("teachers")
                                       if request.form.getlist("teachers")]
                        teachers = Person.query.filter(Person.id.in_(teacher_ids), Person.teacher).all()
                        for teacher in teachers:
                            if school not in teacher.teaching_classes:
                                teacher.teaching_classes.append(school)
                            if new_subject not in teacher.subjects_taught.all():
                                teacher.subjects_taught.append(new_subject)
                        description = f"Добавление школьного предмета {new_subject.name} в класс '{school.school_name}'"
                        user_action(current_user, description)
                        db.session.commit()
                        flash('Предмет добавлен классу', 'success')

                    else:
                        flash('Не выбран предмет', 'error')

            else:
                flash('Нет прав администратора', 'error')

        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при внесении изменений: {str(e)}', 'error')

        return redirect(request.referrer)

    all_teachers = Person.query.filter_by(teacher=True).order_by(Person.last_name, Person.first_name).all()
    possible_subjects = Subject.query.filter(
        ~Subject.school_classes.any(SchoolClass.id == school.id),
        Subject.subject_type.has(SubjectType.name == 'school')
    ).order_by(Subject.name).all()

    return render_template('school.html', school_classes=school_classes, school_class=school, teachers=all_teachers,
                           possible_subjects=possible_subjects, render_type="subjects")


@app.route('/edit-school-subject/<string:subject_id>', methods=['POST'])
@login_required
def edit_school_subject(subject_id):
    try:
        if current_user.rights in ["admin", "user"]:
            subject_id = int(subject_id) if str(subject_id).isdigit() else None
            school_subject = Subject.query.filter(
                Subject.id == subject_id,
                Subject.subject_type.has(SubjectType.name == 'school')
            ).first()
            if school_subject:
                subject_new_name = request.form.get('subject_name')
                subject_new_short_name = request.form.get('subject_short_name')

                school_subject.name = subject_new_name
                school_subject.short_name = subject_new_short_name
                user_action(current_user, f'Внесение изменений в школьный предмет {school_subject.name}')
                db.session.commit()
                flash('Школьный предмет изменен', 'success')

            else:
                flash('Такого предмета нет', 'error')

        else:
            flash('Нет прав администратора', 'error')

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при внесении изменений: {str(e)}', 'error')

    return redirect(request.referrer)


@app.route('/school-timetable/<string:week>/<string:day>')
@login_required
def school_timetable(week, day):
    week = int(week) if str(week).lstrip('-').isdigit() else None
    week_day = int(day) if str(day).isdigit() else None
    if week is None or week_day is None:
        flash(f'Неправильный адрес сайта', 'error')
        return redirect(url_for('school_students', school_class=0))

    if week_day == 0:
        week_day = get_today_date().weekday() + 1
    if week_day > 7:
        return redirect(url_for('school_timetable', week=week+1, day=1))

    school_classes = SchoolClass.query.order_by(
        SchoolClass.school_class,
        SchoolClass.school_name
    ).all()
    day_school_lessons, date_str, time_range = day_school_lessons_dict(week_day, week, school_classes)
    dates = get_date_range(week)
    filename = f"timetable_{dates[0].replace('.', '_')}_{dates[-1].replace('.', '_')}.xlsx"

    return render_template('school_timetable.html', days=DAYS_OF_WEEK, school_classes=school_classes, dates=dates,
                           classes=day_school_lessons, date=date_str, start_time=time_range[0], end_time=time_range[1],
                           week=week, week_day=week_day, filename=filename)


@app.route('/school-lesson/<string:lesson_str>', methods=['GET', 'POST'])
@login_required
def school_lesson(lesson_str):
    sc_lesson, sc_subject = show_school_lesson(lesson_str)
    if sc_lesson:
        subject_classes = str(sc_lesson.subject_id) + '-' + '-'.join(map(str, sc_lesson.classes_ids))
        month_index = calc_month_index(sc_lesson.date)

        if request.method == 'POST':
            try:
                message = handle_school_lesson(request.form, sc_lesson, current_user)
                db.session.commit()
                if message:
                    flash(message[0], message[1])

            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при проведении занятия: {str(e)}', 'error')

            return redirect(url_for('school_lesson', lesson_str=f'0-{sc_lesson.id}'))

        sc_students = Person.query.filter(
            Person.school_class_id.is_not(None),
            ~Person.id.in_([student.id for student in sc_lesson.lesson_students])
        ).order_by(Person.last_name, Person.first_name).all()
        distinct_grade_types = db.session.query(
            distinct(SchoolLessonJournal.grade_type)
        ).filter(
            SchoolLessonJournal.final_grade.is_(False)
        ).all()
        grade_types = [grade_type[0] for grade_type in distinct_grade_types if grade_type[0]]
        days_dict = {day_num: day for (day_num, day) in enumerate(DAYS_OF_WEEK)}

        return render_template('school_lesson.html', school_lesson=sc_lesson, days_dict=days_dict,
                               school_students=sc_students, grade_types=grade_types, school_subject=sc_subject,
                               subject_classes=subject_classes, month_index=month_index, today=get_today_date())

    else:
        if sc_subject:
            return render_template('school_lesson.html', school_lesson=sc_lesson, school_subject=sc_subject)
        else:
            flash("Такого урока нет", 'error')
            return redirect(url_for('school_subjects', school_class=0))


@app.route('/school-subject/<subject_classes>/<string:month_index>', methods=['GET', 'POST'])
@login_required
def school_subject(subject_classes, month_index):
    subject_classes_ids = subject_classes.split('-')
    subject_id = int(subject_classes_ids[0]) if subject_classes_ids[0].isdigit() else None
    classes_ids = [int(sc_cl) for sc_cl in subject_classes_ids[1:] if sc_cl.isdigit()]
    month_index = int(month_index) if str(month_index).lstrip('-').isdigit() else None
    if not subject_id or not classes_ids or month_index is None:
        flash("Журнал не найден", 'error')
        return redirect(url_for('school_subjects', school_class=0))

    subject_records, dates_topics, sc_students, final_grades_list = school_subject_record(subject_id, classes_ids, month_index)
    subject = Subject.query.filter_by(id=subject_id).first()
    school_classes = SchoolClass.query.filter(SchoolClass.id.in_(classes_ids)).order_by(SchoolClass.school_class).all()
    school_classes_names = ', '.join([cl.school_name for cl in school_classes])
    distinct_grade_types = db.session.query(
        distinct(SchoolLessonJournal.grade_type)
    ).filter(
        SchoolLessonJournal.final_grade.is_(False)
    ).all()
    grade_types = [grade_type[0] for grade_type in distinct_grade_types if grade_type[0]]
    finals = ["1 четверть", "2 четверть", "3 четверть", "4 четверть", "год"]
    distinct_finals = db.session.query(
        distinct(SchoolLessonJournal.grade_type)
    ).filter(
        SchoolLessonJournal.final_grade.is_(True)
    ).all()
    final_grade_types = [grade_type[0] for grade_type in distinct_finals
                         if grade_type[0] and grade_type[0] not in finals]

    finals += final_grade_types

    if request.method == 'POST':
        try:
            if 'new_grade_btn' in request.form:
                grade_info = add_new_grade(request.form, sc_students, subject_id, "grade")
                grade_month_index = calc_month_index(grade_info[0])
                description = f"Добавление оценок по предмету {subject.name} {grade_info[0]:%d.%m.%Y} " \
                              f"({school_classes_names}, {grade_info[1]})"
                user_action(current_user, description)
                db.session.commit()
                flash("Оценки выставлены", 'success')

                return redirect(url_for('school_subject', subject_classes=subject_classes,
                                        month_index=grade_month_index))

            if 'new_final_grade_btn' in request.form:
                grade_info = add_new_grade(request.form, sc_students, subject_id, "final")
                description = f"Добавление итоговых оценок по предмету {subject.name} {grade_info[0]:%d.%m.%Y} " \
                              f"({school_classes_names}, {grade_info[1]})"
                user_action(current_user, description)
                db.session.commit()
                flash("Оценки выставлены", 'success')

                return redirect(url_for('school_subject', subject_classes=subject_classes,
                                        month_index=month_index))
            if 'change_grade_btn' in request.form:
                message = change_grade(request.form, subject, classes_ids, month_index, current_user)
                db.session.commit()
                flash(message[0], message[1])

                return redirect(url_for('school_subject', subject_classes=subject_classes,
                                        month_index=month_index))

        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при выставлении оценок: {str(e)}', 'error')

            return redirect(url_for('school_subject', subject_classes=subject_classes,
                                    month_index=month_index))

    return render_template('school_subject.html', subject_records=subject_records, dates_topics=dates_topics,
                           final_grades_list=final_grades_list, students=sc_students, subject=subject,
                           school_classes=school_classes_names, month_index=month_index, today=get_today_date(),
                           subject_classes=subject_classes, grade_types=grade_types, finals=finals)


@app.route('/student-record/<string:student_id>/<string:month_index>')
@login_required
def student_school_record(student_id, month_index):
    student_id = int(student_id) if str(student_id).isdigit() else None
    month_index = int(month_index) if str(month_index).lstrip('-').isdigit() else None
    school_student = Person.query.filter_by(id=int(student_id)).first()
    if school_student and month_index is not None:
        student_records, dates_topics, finals = student_record(school_student, int(month_index))
        student_subjects = list(student_records.keys())

        return render_template('school_student.html', student=school_student, dates_topics=dates_topics,
                               student_records=student_records, student_subjects=student_subjects,
                               finals=finals, month_index=month_index)

    else:
        flash("Такого ученика нет", 'error')

        return redirect(url_for('school_students', school_class=0))


@app.route('/after-school/<string:month_index>')
@login_required
def after_school(month_index):
    month_index = int(month_index) if str(month_index).lstrip('-').isdigit() else 0
    after_school_subject = Subject.query.filter(Subject.subject_type.has(SubjectType.name == 'after_school')).first()
    after_school_prices = SubscriptionType.query.filter(SubscriptionType.period != '').all()
    if not after_school_prices:
        flash("Цен на продленку еще нет", 'error')
        return redirect(url_for('students'))

    month_students, period, current_period, date = get_after_school_students(month_index, "month")
    after_school_subject.students = month_students
    if month_index == 0:
        day_index = 0
    else:
        date = datetime(period[1], period[0], 1).date()
        day_index = calc_day_index(date)
    possible_clients = Person.query.filter(
        Person.status.in_(["Клиент", "Лид"]),
        Person.person_type == "Ребенок"
    ).order_by(Person.last_name, Person.first_name).all()
    after_school_prices = get_after_school_prices()

    return render_template('after_school.html', after_school_subject=after_school_subject, period=period,
                           current_period=current_period, months=MONTHS, month_index=month_index,
                           possible_clients=possible_clients, after_school_prices=after_school_prices,
                           date=f'{date:%d.%m.%Y}', day_index=day_index, render_type="month")


@app.route('/after-school-days/<string:day_index>')
@login_required
def after_school_days(day_index):
    day_index = int(day_index) if str(day_index).lstrip('-').isdigit() else 0
    after_school_subject = Subject.query.filter(Subject.subject_type.has(SubjectType.name == 'after_school')).first()
    day_students, period, current_period, date = get_after_school_students(day_index, "day")
    after_school_subject.students = day_students
    month_index = calc_month_index(date)

    return render_template('after_school.html', after_school_subject=after_school_subject, period=period,
                           current_period=current_period, months=MONTHS, day_index=day_index,
                           date=f'{date:%d.%m.%Y}', month_index=month_index, render_type="day")


@app.route('/after-school-purchase', methods=['POST'])
@login_required
def after_school_purchase():
    try:
        if current_user.rights in ["admin", "user"]:
            attendee_id = int(request.form.get("selected_client")) if request.form.get("selected_client") else None
            if not attendee_id:
                flash('Клиент не выбран', 'error')
                return redirect(request.referrer)

            period = request.form.get("period")
            new_after_school, period_text = handle_after_school_adding(attendee_id, request.form, period)

            if not new_after_school:
                flash('Клиент уже записан на продленку', 'error')

            else:
                db.session.add(new_after_school)
                db.session.flush()
                price = new_after_school.subscription_type.price
                if new_after_school.period not in ["month", "week", "day"]:
                    hours = int(new_after_school.period.split()[0])
                    price *= hours
                operation_type = request.form.get('operation_type')
                description = f"Оплата продленки ({period_text})"
                attendee = Person.query.filter_by(id=attendee_id).first()
                finance_operation(attendee, -price, operation_type, description, "after_school", new_after_school.id)
                user_description = f"Проведение оплаты клиента {attendee.last_name} {attendee.first_name} " \
                                   f"за Продленку ({period_text})"
                user_action(current_user, user_description)
                db.session.commit()
                flash('Клиент записан на продленку', 'success')

        else:
            flash('Нет прав администратора', 'error')

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при записи на продленку: {str(e)}', 'error')

    return redirect(request.referrer)


@app.route('/generate-report/<string:week>')
@login_required
def generate_employee_report(week):
    try:
        if current_user.rights in ["admin", "user"]:
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

        else:
            flash('Нет прав администратора', 'error')

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


@app.route('/finance-operation', methods=['POST'])
@login_required
def add_finance_operation():
    try:
        if current_user.rights in ["admin", "user"]:
            person_id = request.form.get('person_id')
            if not person_id:
                flash('Клиент не выбран', 'error')
                return redirect(request.referrer)

            finance_date = datetime.strptime(request.form.get('finance_date'), '%d.%m.%Y').date()
            description = request.form.get('description')
            if finance_date != get_today_date():
                description += f" (от {finance_date:%d.%m.%y})"
            amount = float(request.form.get('amount'))
            type_of_operation = request.form.get('operation_type')
            if type_of_operation.startswith('minus'):
                amount = -amount
            operation_type = type_of_operation.split('_')[1]
            person = Person.query.filter_by(id=person_id).first()
            finance_operation(person, amount, operation_type, description, "finance", None)

            user_description = f"Проведение финансовой операции клиента {person.last_name} {person.first_name}: " \
                               f"{description} ({OPERATION_TYPES.get(operation_type, '?')} {amount:.1f})"
            user_action(current_user, user_description)
            db.session.commit()
            flash('Финансовая операция проведена', 'success')

        else:
            flash('Нет прав администратора', 'error')

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при проведении финансовой операции: {str(e)}', 'error')

    return redirect(request.referrer)


@app.route('/finances', methods=['GET', 'POST'])
@login_required
def finances():
    today = get_today_date()
    two_weeks_ago = today - timedelta(days=14)
    finance_operations = Finance.query.filter(
        Finance.date >= two_weeks_ago
    ).order_by(Finance.date.desc(), Finance.id.desc()).all()
    all_persons = Person.query.order_by(Person.last_name, Person.first_name).all()

    if request.method == 'POST':
        try:
            if current_user.rights in ["admin", "user"]:
                operation_id = request.form.get('operation_id')
                fin_operation = Finance.query.filter_by(id=operation_id).first()
                new_finance_date = datetime.strptime(request.form.get('finance_date'), '%d.%m.%Y').date()
                old_finance_date = fin_operation.date
                new_description = request.form.get('description')
                old_description = fin_operation.description
                fin_operation.description = new_description
                fin_operation.date = new_finance_date

                if new_finance_date == old_finance_date and new_description != old_description:
                    user_description = f"Изменение описания финансовой операции от {fin_operation.date:%d.%m.%Y} с " \
                                       f"'{old_description}' на '{new_description}'"
                elif new_finance_date != old_finance_date and new_description == old_description:
                    user_description = f"Изменение даты финансовой операции '{old_description}' " \
                                       f"с {old_finance_date:%d.%m.%Y} на {new_finance_date:%d.%m.%Y}"
                elif new_finance_date != old_finance_date and new_description != old_description:
                    user_description = f"Изменение финансовой операции '{old_description}' " \
                                       f"({old_finance_date:%d.%m.%Y}) " \
                                       f"на '{new_description}' ({new_finance_date:%d.%m.%Y})"
                else:
                    user_description = None

                if user_description:
                    user_action(current_user, user_description)
                db.session.commit()

                flash('Финансовая операция изменена', 'success')

            else:
                flash('Нет прав администратора', 'error')

        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при изменении финансовой операции: {str(e)}', 'error')

        return redirect(url_for('finances'))

    subscription_subjects = subscription_subjects_data()

    return render_template('finances.html', finance_operations=finance_operations, all_persons=all_persons,
                           today=f'{today:%d.%m.%Y}', subscription_subjects=subscription_subjects,
                           render_type="last_weeks")


@app.route('/all-finances')
@login_required
def all_finances():
    finance_operations = Finance.query.order_by(Finance.date.desc(), Finance.id.desc()).all()

    return render_template('finances.html', finance_operations=finance_operations, render_type="all")


@app.route('/subscriptions', methods=['GET', 'POST'])
@login_required
def subscriptions():
    if request.method == 'POST':
        try:
            if current_user.rights == "admin":
                subscription_id = int(request.form.get("subscription_id"))
                subscription = Subscription.query.filter_by(id=subscription_id).first()
                subscription.lessons_left = int(request.form.get("lessons_left"))
                subscription.purchase_date = datetime.strptime(request.form.get("purchase_date"), '%d.%m.%Y').date()
                subscription.end_date = datetime.strptime(request.form.get("end_date"), '%d.%m.%Y').date()
                description = f"Изменение абонемента {subscription.subject.name} клиента " \
                              f"{subscription.student.last_name} {subscription.student.first_name}"
                user_action(current_user, description)
                db.session.commit()
                flash('Изменения внесены', 'success')

            else:
                flash('Нет прав руководителя', 'error')

        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при изменении абонемента: {str(e)}', 'error')

        return redirect(url_for('subscriptions'))

    today = get_today_date()
    three_months_ago = today - timedelta(days=90)
    recent_subscriptions = Subscription.query.join(Person).filter(
        Subscription.purchase_date >= three_months_ago,
        Subscription.subject.has(Subject.subject_type.has(SubjectType.name != 'after_school'))
    ).order_by(
        Subscription.purchase_date.desc(), Person.last_name, Person.first_name
    ).all()
    check_subscriptions(recent_subscriptions)

    return render_template('subscriptions.html', subscriptions=recent_subscriptions)


@app.route('/delete-record', methods=['POST'])
@login_required
def delete_record():
    record_type = request.form.get('record_type')

    try:
        if record_type in ['student', 'employee', 'school_student', 'fin_operation', 'subscription']:
            if current_user.rights == 'admin':
                message = del_record(request.form, record_type, current_user)
                db.session.commit()
                flash(message[0], message[1])

            else:
                flash('Необходимо обладать правами руководителя', 'error')

        else:
            if current_user.rights in ["admin", "user"]:
                message = del_record(request.form, record_type, current_user)
                db.session.commit()
                if type(message) == list:
                    for mes in message:
                        flash(mes[0], mes[1])
                else:
                    flash(message[0], message[1])

            else:
                flash('Необходимо обладать правами администратора', 'error')

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении: {str(e)}', 'error')

    return redirect(request.referrer)
