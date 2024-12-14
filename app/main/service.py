from sqlalchemy import or_
from app import db
from app.app_settings.service import user_action
from app.caching.service import delete_cache, get_cache_school_class_info
from app.common_servicies.service import get_today_date, conjugate_lessons, CHILD
from app.finance.models import Finance
from app.finance.service import finance_operation
from app.school.models import Person
from app.school.subjects.models import Subject, SubjectType
from app.school.subscriptions.models import Subscription
from app.school_classes.models import SchoolClass
from app.timetable.models import Lesson, StudentAttendance
from app.timetable.service import filter_day_lessons


def del_record(form, record_type, user):
    if record_type == 'student':
        student_id = int(form.get('student_id'))
        student = Person.query.filter_by(id=student_id).first()
        if student:
            student_name = f"{student.last_name} {student.first_name}"
            if student.person_type == CHILD and student.school_class_id is not None:
                delete_cache(['school_attending_students', f'class_{student.school_class_id}_students'])
            elif student.person_type == CHILD:
                delete_cache(['possible_students'])
            if student.parents.all():
                for parent in student.parents:
                    if len(parent.children.all()) == 1 and not parent.status and not parent.roles:
                        student.primary_contact = None
                        student.parents.remove(parent)
                        parent.primary_contact = None
                        db.session.delete(parent.contacts[0])
                        db.session.delete(parent)
                db.session.flush()
            if student.children.all() or student.roles:
                student.status = None
                db.session.flush()
            else:
                student.primary_contact = None
                if student.contacts:
                    db.session.delete(student.contacts[0])
                db.session.delete(student)
            db.session.flush()
            user_action(user, f"Удаление клиента {student_name}")
            message = (f"Клиент {student_name} удален", "success")
        else:
            message = ("Такого клиента нет", 'error')

        return message

    if record_type == 'employee':
        employee_id = int(form.get('employee_id'))
        employee = Person.query.filter_by(id=employee_id).first()

        if employee:
            employee_name = f"{employee.last_name} {employee.first_name}"
            future_lessons = []

            if employee.teacher:
                future_lessons = Lesson.query.filter(
                    Lesson.date >= get_today_date(),
                    Lesson.teacher_id == employee_id
                ).all()

            if future_lessons:
                message = (f"Сотрудник {employee_name} не может быть удален", 'error')

            else:
                if employee.teacher:
                    keys_to_delete = (['teachers'] +
                                      [f'class_{sc_cl.id}_subjects' for sc_cl in employee.teaching_classes])
                    delete_cache(keys_to_delete)

                for role in employee.roles:
                    db.session.delete(role)

                if not employee.children.all() or not employee.status:
                    employee.primary_contact = None
                    db.session.delete(employee.contacts[0])
                    db.session.delete(employee)
                db.session.flush()
                user_action(user, f"Удаление сотрудника {employee_name}")
                message = (f"Сотрудник {employee_name} удален", "success")
        else:
            message = ("Такого сотрудника нет", 'error')

        return message

    if record_type == 'contact':
        contact_person_id = int(form.get('contact_id'))
        student_id = int(form.get('student_id'))
        student = Person.query.filter_by(id=student_id).first()
        contact_person = Person.query.filter_by(id=contact_person_id).first()
        if contact_person:
            if contact_person_id == student_id:
                if contact_person.contacts[0]:
                    db.session.delete(contact_person.contacts[0])
                    db.session.flush()
            else:
                if len(contact_person.children.all()) == 1 and not contact_person.status \
                        and not contact_person.roles:
                    student.parents.remove(contact_person)
                    contact_person.primary_contact = None
                    db.session.delete(contact_person.contacts[0])
                    db.session.delete(contact_person)
                    db.session.flush()
                else:
                    student.parents.remove(contact_person)
                    db.session.flush()

            student_name = f"{student.last_name} {student.first_name}"
            user_action(user, f"Удаление контактной информации клиента {student_name}")
            message = ("Контактная информация удалена", "success")
        else:
            message = ("Такого контакта нет", 'error')

        return message

    if record_type == 'subject':
        subject_id = int(form.get('subject_id'))
        subject = Subject.query.filter(
            Subject.id == subject_id,
            Subject.subject_type.has(~SubjectType.name.in_(['school', 'after_school']))
        ).first()
        if subject:
            subject_name = f"{subject.name} ({subject.subject_type.description})"
            subject_lessons = Lesson.query.filter(subject_id=subject.id).all()
            subscriptions = Subscription.query.filter(
                Subscription.subject_id == subject.id,
                Subscription.end_date >= get_today_date(),
                Subscription.lessons_left > 0
            ).all()
            if subject_lessons or subscriptions:
                text = f"Предмет {subject_name} не может быть удален, "
                text += "т.к. есть дейсвующие абонементы" if subscriptions else "т.к. есть занятия в расписании"
                message = (text, 'error')
            else:
                old_subscriptions = Subscription.query.filter(
                    Subscription.subject_id == subject.id,
                    or_(
                        Subscription.end_date < get_today_date(),
                        Subscription.lessons_left == 0
                    )
                ).all()
                if old_subscriptions:
                    for subscription in old_subscriptions:
                        db.session.delete(subscription)
                db.session.delete(subject)
                db.session.flush()
                user_action(user, f"Удаление предмета {subject_name}")
                message = (f"Предмет {subject_name} удален", 'success')

        else:
            message = ("Такого предмета нет", 'error')

        return message

    if record_type == 'school_subject':
        subject_id = int(form.get('subject_id'))
        subject = Subject.query.filter(
            Subject.id == subject_id,
            Subject.subject_type.has(SubjectType.name == 'school')
        ).first()
        if subject:
            school_class_id = int(form.get('school_class_id'))
            school_class_info = get_cache_school_class_info(school_class_id)
            school_class = school_class_info['school_class'] if school_class_info \
                else SchoolClass.query.filter_by(id=school_class_id).first()
            subject.school_classes.remove(school_class)
            subject_name = subject.name
            subject_lessons = Lesson.query.filter_by(subject_id=subject.id).all()

            if not subject_lessons and not subject.school_classes:
                db.session.delete(subject)
                user_action(user, f"Удаление школьного предмета {subject_name}")
                message = (f"Школьный предмет {subject_name} полностью удален", 'success')

            else:
                user_action(user, f"Удаление школьного предмета {subject_name} из класса '{school_class.school_name}'")
                message = (f"Школьный предмет {subject_name} удален из класса", 'success')

            db.session.flush()
            delete_cache(["school_subjects", f'class_{school_class_id}_subjects'])

        else:
            message = ("Такого предмета нет", 'error')

        return message

    if record_type == 'lesson':
        lesson_id = int(form.get('lesson_id')) if form.get('lesson_id') else None
        lesson = Lesson.query.filter_by(id=lesson_id).first()
        if lesson:
            if not lesson.lesson_completed:
                db.session.delete(lesson)
                db.session.flush()
                user_action(user, f"Отмена занятия {lesson.subject.name} {lesson.date:%d.%m.%Y}")
                return "Занятие отменено", 'success'

            else:
                return "Невозможно отменить занятие", 'error'

        else:
            return "Такого занятия нет", 'error'

    if record_type == 'lessons':
        del_lessons, date = filter_day_lessons(form)
        if del_lessons:
            les = len(del_lessons)
            del_les = 0
            for lesson in del_lessons:
                if not lesson.lesson_completed:
                    db.session.delete(lesson)
                    del_les += 1
                    db.session.flush()

            if del_les == les:
                user_action(user, f"Отмена занятий {date:%d.%m.%Y} ({conjugate_lessons(del_les)})")
                return "Все занятия отменены", 'success'

            elif del_les != 0:
                message1 = (f"{conjugate_lessons(del_les)} отменено", 'success')
                message2 = (f"{conjugate_lessons(del_les)} невозможно отменить", 'error')
                user_action(user, f"Отмена занятий {date:%d.%m.%Y} ({conjugate_lessons(del_les)})")
                return [message1, message2]

            else:
                return "Занятия невозможно отменить", 'error'

        else:
            return "Нет занятий,  удовлетворяющих критериям", 'error'

    if record_type == 'school_student':
        student_id = int(form.get('student_id'))
        student = Person.query.filter(Person.id == student_id, Person.school_class_id).first()
        if student:
            student_name = f"{student.last_name} {student.first_name}"
            school_class_id = student.school_class_id
            school_class_name = student.school_class.school_name
            student.school_class_id = None
            for subject in student.subjects.all():
                if subject.subject_type.name == "school":
                    student.subjects.remove(subject)
            db.session.flush()
            user_action(user, f"Удаление ученика {student_name} из класса '{school_class_name}'")
            message = (f"Ученик {student_name} удален из класса", "success")
            delete_cache(['school_attending_students', 'possible_students', f'class_{school_class_id}_students'])
        else:
            message = ("Такого ученика нет", 'error')

        return message

    if record_type == 'subscription':
        del_subscription_id = int(form.get('subscription_id'))
        del_subscription = Subscription.query.filter_by(id=del_subscription_id).first()
        if del_subscription:
            full_subscription = del_subscription.lessons_left == del_subscription.subscription_type.lessons
            used_subscription = StudentAttendance.query.filter_by(subscription_id=del_subscription_id).all()
            if full_subscription and not used_subscription:
                price = del_subscription.subscription_type.price
                record = Finance.query.filter(
                    Finance.person_id == del_subscription.student_id,
                    Finance.service == "subscription",
                    Finance.service_id == del_subscription.id
                ).first()
                fin_description = f"Возврат за абонемент {del_subscription.subject.name}"
                if record:
                    record.service_id = None
                    finance_operation(del_subscription.student, abs(record.amount), record.operation_type,
                                      fin_description, 'del_subscription', None, balance=record.student_balance,
                                      subject_id=del_subscription.subject_id)
                else:
                    finance_operation(del_subscription.student, price, 'cash', fin_description,
                                      'del_subscription', None, subject_id=del_subscription.subject_id)

                description = f"Удаление абонемента {del_subscription.subject.name} клиента " \
                              f"{del_subscription.student.last_name} {del_subscription.student.first_name}"
                user_action(user, description)
                db.session.delete(del_subscription)
                db.session.flush()
                message = (f"Абонемент удален", "success")

            else:
                message = (f"Абонемент не может быть удален", "error")

        else:
            message = ("Такого абонемента нет", 'error')

        return message
