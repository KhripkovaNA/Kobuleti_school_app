from flask import render_template, flash, redirect, request, url_for
from flask_login import login_required, current_user
from .service import (
    basic_student_info, clients_data, add_child, add_adult,
    extensive_student_info, potential_client_subjects, handle_student_edit
)
from app.school.models import Person
from app.common_servicies.service import get_today_date, MONTHS, get_period
from app.school.subjects.service import subscription_subjects_data, lesson_subjects_data
from app.school.subjects.models import Subject
from app import db, cache
from app.app_settings.service import user_action
from app.school.forms import (
    ChildForm, AdultForm, NewContactPersonForm, AddContForm, EditAddContPersonForm,
    ContactForm, EditContactPersonForm, EditStudentForm
)
from app.after_school.service import get_after_school_prices
from app.finance.models import Finance
from app.school.subscriptions.forms import SubscriptionsEditForm
from flask import Blueprint

from app.app_settings.models import SubscriptionType

school_students = Blueprint('students', __name__)


@school_students.route('/students')
@login_required
def students():
    if current_user.rights in ["admin", "user"]:

        all_students = Person.query.filter(Person.status.isnot(None)).order_by(
            Person.last_name, Person.first_name
        ).all()

        for student in all_students:
            basic_student_info(student)
        subscription_subjects = subscription_subjects_data()
        lesson_subjects = lesson_subjects_data()

        return render_template(
            'school/students/students.html', students=all_students,
            subscription_subjects=subscription_subjects, today=f'{get_today_date():%d.%m.%Y}',
            lesson_subjects=lesson_subjects
        )

    else:
        flash('Нет прав администратора', 'error')
        return redirect(request.referrer)


@school_students.route('/student-subjects/<string:student_id>', methods=['POST'])
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


@school_students.route('/add-student', methods=['GET', 'POST'])
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
                            return redirect(url_for('school.students.show_edit_student', student_id=student.id))

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
                            return redirect(url_for('school.students.show_edit_student', student_id=client.id))

                        else:
                            flash(message, 'error')

                flash('Ошибка в форме добавления киента', 'error')

            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при добавлении киента: {str(e)}', 'error')
                return redirect(url_for('students.school.add_student'))

        return render_template('school/students/add_student.html', clients=clients, possible_clients=possible_clients,
                               form1=form1, form2=form2, render_type=render_type)

    else:
        flash('Нет прав администратора', 'error')
        return redirect(url_for('main.index'))


@school_students.route('/student/<string:student_id>', methods=['GET', 'POST'])
@login_required
def show_edit_student(student_id):
    student = Person.query.filter(Person.id == student_id, Person.status.isnot(None)).first()
    if student:
        if current_user.rights == "parent" and student not in current_user.user_persons.all():
            flash('Нет прав администратора', 'error')
            return redirect(url_for('main.index'))

        extensive_student_info(student)
        clients = clients_data('child')
        lesson_subjects = lesson_subjects_data()
        potential_subjects = potential_client_subjects()
        subscription_subjects = subscription_subjects_data()
        periods = [get_period(0), get_period(1)]
        months = [(f"{period[0]}-{period[1]}", MONTHS[period[0]-1].capitalize()) for period in periods]
        after_school_prices_objects = SubscriptionType.query.filter(SubscriptionType.period != '').all()
        after_school_prices = get_after_school_prices(after_school_prices_objects)

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
                                return redirect(url_for('school.students.show_edit_student', student_id=student.id))

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
                                return redirect(url_for('school.students.show_edit_student', student_id=student.id))

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
                                    return redirect(url_for('school.students.show_edit_student', student_id=student.id))

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
                                return redirect(url_for('school.students.show_edit_student', student_id=student.id))

                            else:
                                flash(message, 'error')

                    if 'del_subject_btn' in request.form:
                        handle_student_edit(request.form, student, 'del_subject', current_user)
                        description = f"Удаление занятия у клиента {student.last_name} {student.first_name}"
                        user_action(current_user, description)
                        db.session.commit()
                        flash('Изменения внесены', 'success')
                        return redirect(url_for('school.students.show_edit_student', student_id=student.id))

                    if 'form_subscriptions_submit' in request.form:
                        if current_user.rights == 'admin':
                            render_type = 'subscription'
                            if subscriptions_form.validate_on_submit():
                                handle_student_edit(subscriptions_form, student, 'subscription', current_user)
                                db.session.commit()
                                flash('Изменения внесены', 'success')
                                return redirect(url_for('school.students.show_edit_student', student_id=student.id))

                        else:
                            flash('Нет прав руководителя', 'error')
                            return redirect(url_for('school.students.show_edit_student', student_id=student.id))

                    if 'del_after_school' in request.form:
                        if current_user.rights == 'admin':
                            handle_student_edit(request.form, student, 'del_after_school', current_user)
                            description = f"Отмена покупки продленки клиента {student.last_name} {student.first_name}"
                            user_action(current_user, description)
                            db.session.commit()
                            flash('Изменения внесены', 'success')

                        else:
                            flash('Нет прав руководителя', 'error')

                        return redirect(url_for('school.students.show_edit_student', student_id=student.id))

                    flash('Ошибка в форме изменения клиента', 'error')

                else:
                    flash('Нет прав администратора', 'error')

            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при внесении изменений: {str(e)}', 'error')
                return redirect(url_for('school.students.show_edit_student', student_id=student.id))

        return render_template('school/students/student.html', student=student, clients=clients, today=f'{get_today_date():%d.%m.%Y}',
                               lesson_subjects=lesson_subjects, subscription_subjects=subscription_subjects,
                               edit_student_form=student_form, render_type=render_type, main_contact=main_contact_form,
                               add_cont_forms=add_cont_forms, new_contact_form=new_contact_form, months=months,
                               potential_subjects=potential_subjects, subscriptions_form=subscriptions_form,
                               after_school_prices=after_school_prices)
    else:
        flash("Такого клиента нет", 'error')
        return redirect(url_for('main.index'))
