from datetime import timedelta, datetime
from flask import render_template, flash, redirect, url_for, request
from flask_login import login_required, current_user
from sqlalchemy import or_, and_
from app import db
from .forms import ExtraSubjectForm, EditExtraSubjectForm
from .service import add_new_subject, handle_subject_edit, subject_record
from .models import Subject, SubjectType
from app.app_settings.models import SubscriptionType
from app.school.models import Person
from app.school.subscriptions.service import format_subscription_types, check_subscriptions
from app.app_settings.service import user_action
from app.school.subscriptions.models import Subscription
from app.common_servicies.service import get_today_date
from flask import Blueprint


school_subjects = Blueprint('subjects', __name__)


@school_subjects.route('/subjects')
@login_required
def subjects():
    if current_user.rights in ["admin", "user", "teacher"]:
        all_subjects = Subject.query.filter(
            Subject.subject_type.has(SubjectType.name.in_(['extra', 'individual']))
        ).order_by(Subject.name).all()
        for subject in all_subjects:
            subject.types_of_subscription = format_subscription_types(subject.subscription_types.all())

        return render_template('school/subjects/subjects.html', subjects=all_subjects)

    else:
        flash('Нет прав администратора', 'error')
        return redirect(url_for('main.index'))


@school_subjects.route('/add-subject', methods=['GET', 'POST'])
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
        form.teachers.choices = [
            (teacher.id, f"{teacher.last_name} { teacher.first_name }") for teacher in all_teachers
        ]
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
                        return redirect(url_for('school.subjects.subjects'))

                    else:
                        flash('Предмет с таким названием уже есть', 'error')
                        return redirect(url_for('school.subjects.add_subject'))

                flash('Ошибка в форме добавления предмета', 'error')

            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при добавлении предмета: {str(e)}', 'error')

                return redirect(url_for('school.subjects.add_subject'))

        return render_template('school/subjects/add_subject.html', form=form)

    else:
        flash('Нет прав администратора', 'error')
        return redirect(url_for('main.index'))


@school_subjects.route('/edit-subject/<string:subject_id>', methods=['GET', 'POST'])
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
                        return redirect(url_for('school.subjects.subjects'))

                    flash(f'Ошибка в форме изменения предмета', 'error')

                except Exception as e:
                    db.session.rollback()
                    flash(f'Ошибка при внесении изменений: {str(e)}', 'error')

                    return redirect(url_for('school.subjects.edit_subject', subject_id=subject_id))

            return render_template('school/subjects/edit_subject.html', subject=subject, form=form,
                                   subscription_types=subscription_types)

        else:
            flash("Такого занятия нет.", 'error')
            return redirect(url_for('school.subjects.subjects'))

    else:
        flash('Нет прав администратора', 'error')
        return redirect(url_for('main.index'))


@school_subjects.route('/subject/<string:subject_id>/<string:month_index>')
@login_required
def subject(subject_id, month_index):
    if current_user.rights in ["admin", "user", "teacher"]:
        subject_id = int(subject_id) if str(subject_id).isdigit() else None
        subject = Subject.query.filter(
            Subject.id == subject_id,
            Subject.subject_type.has(SubjectType.name.in_(["extra", "individual"]))
        ).first()
        month_index = int(month_index) if str(month_index).lstrip('-').isdigit() else None
        if not subject or month_index is None:
            flash("Журнал не найден", 'error')
            return redirect(url_for('school.subjects.subjects'))

        subject_records, datetimes, subject_students, month = subject_record(subject_id, month_index)
        other_subjects = Subject.query.filter(
            Subject.id != subject_id,
            ~Subject.subject_type.has(SubjectType.name.in_(['school', 'event', 'after_school']))
        ).order_by(Subject.name).all()

        return render_template('school/subjects/subject_record.html', subject_records=subject_records,
                               datetimes=datetimes, students=subject_students, subject=subject, month_index=month_index,
                               other_subjects=other_subjects, month=month)

    else:
        flash('Нет прав администратора', 'error')
        return redirect(url_for('main.index'))


@school_subjects.route('/subscriptions', methods=['GET', 'POST'])
@login_required
def subscriptions():
    if current_user.rights in ["admin", "user", "teacher"]:
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

            return redirect(url_for('school.subjects.subscriptions'))

        today = get_today_date()
        three_months_ago = today - timedelta(days=90)
        recent_subscriptions = Subscription.query.join(Person).filter(
            ~Subscription.is_after_school,
            or_(
                and_(
                    Subscription.purchase_date >= three_months_ago,
                    ~Subscription.active
                ),
                Subscription.active
            )
        ).order_by(
            Subscription.purchase_date.desc(), Person.last_name, Person.first_name
        ).all()

        check_subscriptions(recent_subscriptions)

        return render_template('school/subjects/subscriptions.html', subscriptions=recent_subscriptions)

    else:
        flash('Нет прав администратора', 'error')
        return redirect(url_for('main.index'))
