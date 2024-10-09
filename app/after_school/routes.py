from datetime import datetime
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from .service import (
    get_after_school_students, calc_day_index, get_after_school_prices, handle_after_school_adding
)
from app.app_settings.models import SubscriptionType
from app.app_settings.service import user_action
from app.common_servicies.service import MONTHS, calc_month_index
from app.finance.service import finance_operation
from app.school.models import Person
from app.school.subjects.models import Subject, SubjectType


after_school = Blueprint('after_school', __name__)


@after_school.route('/after-school/<string:month_index>')
@login_required
def after_school_month(month_index):
    if current_user.rights in ["admin", "user", "teacher"]:
        month_index = int(month_index) if str(month_index).lstrip('-').isdigit() else 0
        after_school_subject = Subject.query.filter(Subject.subject_type.has(SubjectType.name == 'after_school')).first()
        after_school_prices = SubscriptionType.query.filter(SubscriptionType.period != '').all()
        if not after_school_prices:
            flash("Цен на продленку еще нет", 'error')
            return redirect(url_for('main.index'))

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

        return render_template(
            'after_school/after_school.html', after_school_subject=after_school_subject,
            period=period, current_period=current_period, months=MONTHS, month_index=month_index,
            possible_clients=possible_clients, after_school_prices=after_school_prices, date=f'{date:%d.%m.%Y}',
            day_index=day_index, render_type="month"
        )

    else:
        flash('Нет прав администратора', 'error')
        return redirect(url_for('main.index'))


@after_school.route('/after-school-days/<string:day_index>')
@login_required
def after_school_days(day_index):
    if current_user.rights in ["admin", "user", "teacher"]:
        day_index = int(day_index) if str(day_index).lstrip('-').isdigit() else 0
        after_school_subject = Subject.query.filter(Subject.subject_type.has(SubjectType.name == 'after_school')).first()
        day_students, period, current_period, date = get_after_school_students(day_index, "day")
        after_school_subject.students = day_students
        month_index = calc_month_index(date)

        return render_template(
            'after_school/after_school.html', after_school_subject=after_school_subject,
            period=period, current_period=current_period, months=MONTHS, day_index=day_index,
            date=f'{date:%d.%m.%Y}', month_index=month_index, render_type="day"
        )

    else:
        flash('Нет прав администратора', 'error')
        return redirect(url_for('main.index'))


@after_school.route('/after-school-purchase', methods=['POST'])
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
