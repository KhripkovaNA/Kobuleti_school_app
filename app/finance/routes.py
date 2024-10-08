from flask import Blueprint, render_template, request, flash, redirect, url_for, send_file
from flask_login import login_required, current_user
from datetime import timedelta, datetime
from io import BytesIO
from decimal import Decimal
from .models import Finance
from .service import finance_operation
from .. import db
from ..app_functions import subscription_subjects_data, get_after_school_prices
from ..app_settings.service import user_action
from ..common_servicies.excel_generators import download_finance_report
from ..common_servicies.service import MONTHS, OPERATION_CATEGORIES, OPERATION_TYPES, get_today_date, get_period
from ..models import Person, Subject, SubjectType


finance = Blueprint('finance', __name__)


@finance.route('/finances', methods=['GET', 'POST'])
@login_required
def finances():
    if current_user.rights in ["admin", "user"]:
        today = get_today_date()
        two_weeks_ago = today - timedelta(days=14)
        finance_operations = Finance.query.filter(
            Finance.date >= two_weeks_ago
        ).order_by(Finance.date.desc(), Finance.id.desc()).all()
        all_persons = Person.query.order_by(Person.last_name, Person.first_name).all()

        if request.method == 'POST':
            try:
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

            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при изменении финансовой операции: {str(e)}', 'error')

            return redirect(url_for('finance.finances'))

        subscription_subjects = subscription_subjects_data()
        periods = [get_period(0), get_period(1)]
        months = [(f"{period[0]}-{period[1]}", MONTHS[period[0] - 1].capitalize()) for period in periods]
        after_school_prices = get_after_school_prices()
        subject_tuples = db.session.query(Subject.id, Subject.name).filter(
            Subject.subject_type.has(SubjectType.name.in_(["individual", "extra"]))
        ).all()

        return render_template('finance/finances.html', finance_operations=finance_operations, all_persons=all_persons,
                               today=f'{today:%d.%m.%Y}', subscription_subjects=subscription_subjects,
                               after_school_prices=after_school_prices, months=months, subjects=subject_tuples,
                               render_type="last_weeks")

    else:
        flash('Нет прав администратора', 'error')
        return redirect(url_for('index'))


@finance.route('/all-finances')
@login_required
def all_finances():
    if current_user.rights in ["admin", "user"]:
        finance_operations = Finance.query.order_by(Finance.date.desc(), Finance.id.desc()).all()

        return render_template('finance/finances.html', finance_operations=finance_operations, render_type="all")

    else:
        flash('Нет прав администратора', 'error')
        return redirect(url_for('index'))


@finance.route('/finance-report', methods=['POST'])
@login_required
def finance_report():
    if current_user.rights in ["admin", "user"]:
        try:
            report_date = datetime.strptime(request.form.get('report_date'), '%d.%m.%Y').date()
            workbook = download_finance_report(report_date)

            filename = f"finance_report_{report_date:%d_%m_%y}.xlsx"
            excel_buffer = BytesIO()
            workbook.save(excel_buffer)
            excel_buffer.seek(0)
            return send_file(excel_buffer, download_name=filename, as_attachment=True)

        except Exception as e:
            flash(f'Ошибка при скачивании файла: {str(e)}', 'error')
            return redirect(request.referrer)

    else:
        flash('Нет прав администратора', 'error')
        return redirect(url_for('index'))


@finance.route('/finance-operation', methods=['POST'])
@login_required
def add_finance_operation():
    try:
        if current_user.rights in ["admin", "user"]:
            person_id = request.form.get('person_id')
            service = request.form.get('operation_category')

            if not person_id and service != "collection":
                flash('Клиент не выбран', 'error')
                return redirect(request.referrer)

            if not service:
                flash('Предмет не выбран', 'error')
                return redirect(request.referrer)

            if service.startswith("subject"):
                subject_tuple = service.split("_")[1:]
                subject_id, subject_name = int(subject_tuple[0]), subject_tuple[1]
                service = "del_lesson"
            else:
                subject_id, subject_name = None, None

            finance_date = datetime.strptime(request.form.get('finance_date'), '%d.%m.%Y').date()

            description = request.form.get('description')
            if not description:
                if service == "del_lesson":
                    description = f"Возврат за занятие {subject_name}"
                else:
                    description = OPERATION_CATEGORIES[service]

            amount = float(request.form.get('amount'))
            type_of_operation = request.form.get('operation_type')
            if type_of_operation.startswith('minus'):
                amount = -amount
            operation_type = type_of_operation.split('_')[1]
            person = Person.query.filter_by(id=person_id).first()
            finance_operation(person, amount, operation_type, description, service,
                              subject_id=subject_id, date=finance_date)
            if person:
                user_description = f"Проведение финансовой операции клиента {person.last_name} {person.first_name}: " \
                                   f"{description} ({OPERATION_TYPES.get(operation_type, '?')} {amount:.1f})"
            else:
                user_description = f"Проведение финансовой операции {OPERATION_TYPES.get(operation_type, '?')} " \
                                   f"{amount:.1f})"
            user_action(current_user, user_description)
            db.session.commit()
            flash('Финансовая операция проведена', 'success')

        else:
            flash('Нет прав администратора', 'error')

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при проведении финансовой операции: {str(e)}', 'error')

    return redirect(request.referrer)


@finance.route('/salary', methods=['POST'])
@login_required
def salary():
    try:
        if current_user.rights in ["admin", "user"]:
            employee_id = int(request.form.get('employee_id')) if request.form.get('employee_id') else None
            amount = request.form.get('amount')
            employee = Person.query.filter_by(id=employee_id).first()
            if not employee:
                flash('Сотрудник не выбран', 'error')
                return redirect(request.referrer)

            if amount:
                operation_type = request.form.get('operation_type')
                salary = Decimal(amount)
                description = f"Выдача зарплаты сотруднику"
                finance_operation(employee, salary, operation_type, description, "salary", None)
                user_description = f"{description} {employee.last_name} {employee.first_name} " \
                                   f"({OPERATION_TYPES.get(operation_type, '?')} {salary:.1f})"
                user_action(current_user, user_description)
                db.session.commit()
                flash(f'Финансовая операция проведена', 'success')

        else:
            flash('Нет прав администратора', 'error')

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при внесении депозита: {str(e)}', 'error')

    return redirect(request.referrer)
