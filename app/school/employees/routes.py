from io import BytesIO
from flask import render_template, flash, redirect, url_for, request, send_file
from flask_login import login_required, current_user
from openpyxl import Workbook
from app.school import school
from app import db
from app.common_servicies.service import get_today_date
from .forms import EmployeeForm
from .models import Employee
from .service import format_employee, employee_record, add_new_employee, handle_employee_edit
from app.school.forms import PersonForm
from app.school.models import Person
from app.school.students.service import clients_data
from app.school.subjects.models import Subject, SubjectType
from app.app_settings.service import user_action
from app.school_classes.models import SchoolClass
from app.timetable.models import Lesson


@school.route('/employees')
@login_required
def employees():
    if current_user.rights in ["admin", "user", "teacher"]:
        all_employees = Person.query.filter(
            Person.roles.any(Employee.id)
        ).order_by(Person.last_name, Person.first_name).all()

        for employee in all_employees:
            format_employee(employee)

        return render_template('school/employees/employees.html', employees=all_employees)
    else:
        flash('Нет прав администратора', 'error')
        return redirect(url_for('main.index'))


@school.route('/employee-report/<string:week>')
@login_required
def employee_report(week):
    if current_user.rights in ["admin", "user"]:
        week = int(week)
        all_employees = Person.query.filter(
            Person.roles.any(Employee.id)
        ).order_by(Person.last_name, Person.first_name).all()

        employees_list, dates = employee_record(all_employees, week)
        filename = f"employee_report_{dates[0].replace('.', '_')}_{dates[-1].replace('.', '_')}.xlsx"

        return render_template('school/employees/employee_report.html', employees=employees_list, dates=dates,
                               week=week, filename=filename)

    else:
        flash('Нет прав администратора', 'error')
        return redirect(request.referrer)


@school.route('/add-employee', methods=['GET', 'POST'])
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
                        return redirect(url_for('school.show_edit_employee', employee_id=employee.id))

                    else:
                        flash(message, 'error')

                flash('Ошибка в форме добавления сотрудника', 'error')

            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при добавлении сотрудника: {str(e)}', 'error')
                return redirect(url_for('school.add_employee'))

        return render_template('school/employees/add_employee.html', possible_employees=possible_employees, form=form)

    else:
        flash('Нет прав администратора', 'error')
        return redirect(request.referrer)


@school.route('/employee/<string:employee_id>', methods=['GET', 'POST'])
@login_required
def show_edit_employee(employee_id):
    if current_user.rights in ["admin", "user", "teacher"]:
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
                                return redirect(url_for('school.show_edit_employee', employee_id=employee.id))

                            else:
                                flash(message, 'error')

                        flash('Ошибка в форме изменения сотрудника', 'error')

                    else:
                        flash('Нет прав администратора', 'error')
                        return redirect(url_for('school.show_edit_employee', employee_id=employee.id))

                except Exception as e:
                    db.session.rollback()
                    flash(f'Ошибка при внесении изменений: {str(e)}', 'error')

                    return redirect(url_for('school.show_edit_employee', employee_id=employee.id))

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

            return render_template('school/employees/employee.html', employee=employee, form=form, possible_roles=possible_roles,
                                   possible_subjects=possible_subjects, subjects=all_subjects, render_type=render_type,
                                   possible_classes=possible_classes, school_classes=all_classes)
        else:
            flash("Такого сотрудника нет", 'error')
            return redirect(url_for('school.employees'))

    else:
        flash('Нет прав администратора', 'error')
        return redirect(request.referrer)


@employees.route('/generate-report/<string:week>')
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
