from datetime import timedelta
from app import db
from app.common_servicies.service import get_date, TEACHER, ADULT, CHOOSE
from app.school.employees.models import Employee
from app.school.models import Person
from app.school.students.service import format_children, format_status, create_contact
from app.school.subjects.models import Subject
from app.school_classes.models import SchoolClass
from app.timetable.models import Lesson


def format_employee(employee):
    if employee.contacts[0].telegram:
        employee.contact = f"Телеграм: {employee.contacts[0].telegram}"
    elif employee.contacts[0].phone:
        employee.contact = f"Тел.: {employee.contacts[0].phone}"
    elif employee.contacts[0].other_contact:
        employee.contact = employee.contacts[0].other_contact
    if employee.subjects_taught.all():
        school_classes = set()
        school_subjects = []
        filtered_subjects = []
        for subject in employee.subjects_taught:
            distinct_classes = db.session.query(SchoolClass) \
                .join(Lesson.school_classes) \
                .filter(Lesson.teacher_id == employee.id,
                        Lesson.subject_id == subject.id,
                        SchoolClass.school_class <= 4).all()

            if distinct_classes:
                school_classes.update([sc_cl.school_name for sc_cl in distinct_classes])
                school_subjects.append(subject.name)
            else:
                filtered_subjects.append(subject.name)
        all_subjects = (list(school_classes) if len(school_subjects) > 2 else school_subjects) + filtered_subjects
        employee.all_subjects = ', '.join(all_subjects)

    if employee.children.all():
        format_children(employee)
    if employee.status:
        format_status(employee)


def lesson_duration(lesson):
    return (lesson.end_time.hour * 60 + lesson.end_time.minute) - \
           (lesson.start_time.hour * 60 + lesson.start_time.minute)


def employee_record(employees, week):
    week_start = get_date(0, week)
    week_end = get_date(6, week)
    employees_list = []

    def add_employee_dict(employee_id, name, role, activity):
        employees_list.append({
            'id': employee_id,
            'name': name,
            'role': role,
            'activity': activity
        })

    for employee in employees:
        for role in employee.roles:
            if role.role != "Учитель":
                add_employee_dict(employee.id, f"{employee.last_name} {employee.first_name}", role.role, {})

        if employee.teacher:
            teacher_lessons = Lesson.query.filter(
                Lesson.date >= week_start,
                Lesson.date <= week_end,
                Lesson.teacher_id == employee.id
            ).all()
            main_teacher = SchoolClass.query.filter(
                SchoolClass.school_class < 5,
                SchoolClass.main_teacher_id == employee.id
            ).all()
            lessons_dict = {}
            if main_teacher:
                teacher_classes_ids = [sc_cl.id for sc_cl in main_teacher]
                for lesson in teacher_lessons:
                    lesson_date = f'{lesson.date:%d.%m}'
                    if len(lesson.school_classes.all()) == 1 and (lesson.school_classes[0].id in teacher_classes_ids):
                        if lessons_dict.get(lesson.school_classes[0].school_name):
                            if lessons_dict[lesson.school_classes[0].school_name].get(lesson_date):
                                lessons_dict[lesson.school_classes[0].school_name][lesson_date] += 1
                            else:
                                lessons_dict[lesson.school_classes[0].school_name][lesson_date] = 1
                        else:
                            lessons_dict[lesson.school_classes[0].school_name] = {lesson_date: 1}
                    else:
                        if lessons_dict.get(lesson.subject.name):
                            if lessons_dict[lesson.subject.name].get(lesson_date):
                                if lesson.lesson_type.name != 'school':
                                    lessons_dict[lesson.subject.name][lesson_date] += lesson_duration(lesson)
                                else:
                                    lessons_dict[lesson.subject.name][lesson_date] += 1
                            else:
                                if lesson.lesson_type.name != 'school':
                                    lessons_dict[lesson.subject.name][lesson_date] = lesson_duration(lesson)
                                else:
                                    lessons_dict[lesson.subject.name][lesson_date] = 1
                        else:
                            if lesson.lesson_type.name != 'school':
                                lessons_dict[lesson.subject.name] = {lesson_date: lesson_duration(lesson)}
                            else:
                                lessons_dict[lesson.subject.name] = {lesson_date: 1}
            else:
                for lesson in teacher_lessons:
                    lesson_date = f'{lesson.date:%d.%m}'
                    if lessons_dict.get(lesson.subject.name):
                        if lessons_dict[lesson.subject.name].get(lesson_date):
                            if lesson.lesson_type.name != 'school':
                                lessons_dict[lesson.subject.name][lesson_date] += lesson_duration(lesson)
                            else:
                                lessons_dict[lesson.subject.name][lesson_date] += 1
                        else:
                            if lesson.lesson_type.name != 'school':
                                lessons_dict[lesson.subject.name][lesson_date] = lesson_duration(lesson)
                            else:
                                lessons_dict[lesson.subject.name][lesson_date] = 1
                    else:
                        if lesson.lesson_type.name != 'school':
                            lessons_dict[lesson.subject.name] = {lesson_date: lesson_duration(lesson)}
                        else:
                            lessons_dict[lesson.subject.name] = {lesson_date: 1}
            for role, activity in lessons_dict.items():
                add_employee_dict(employee.id, f"{employee.last_name} {employee.first_name}", role, activity)

    dates = [f"{week_start + timedelta(day):%d.%m}" for day in range(7)]

    return employees_list, dates


def add_new_employee(form):
    employee_select = form.client_select.data
    if employee_select == CHOOSE:
        person_id = int(form.selected_client.data)
        employee = Person.query.filter_by(id=person_id).first()

    else:
        last_name = form.last_name.data
        first_name = form.first_name.data
        same_person = Person.query.filter_by(last_name=last_name, first_name=first_name).all()
        if same_person:
            return None, f"Человек с именем {last_name} {first_name} уже есть в системе"

        else:
            patronym = form.patronym.data
            employee = Person(
                last_name=last_name,
                first_name=first_name,
                patronym=patronym,
                person_type=ADULT
            )
            contact = create_contact(form)
            db.session.add(employee)
            db.session.add(contact)
            db.session.flush()
            employee.contacts.append(contact)
            employee.primary_contact = employee.id

    roles = form.roles.data
    if roles:
        for role in roles:
            employee_role = role[0].upper() + role[1:]
            new_employee = Employee(
                person_id=employee.id,
                role=employee_role
            )
            db.session.add(new_employee)
            if role == TEACHER:
                employee.teacher = True
                subject_ids = [int(subject_id) for subject_id in form.subjects.data]
                subjects = Subject.query.filter(Subject.id.in_(subject_ids)).all()
                employee.subjects_taught.extend(subjects)
                classes_ids = [int(class_id) for class_id in form.school_classes.data]
                school_classes = SchoolClass.query.filter(SchoolClass.id.in_(classes_ids)).all()
                employee.teaching_classes.extend(school_classes)
                employee.color = form.teacher_color.data

    return employee, ''


def handle_employee_edit(form, employee):
    last_name = form.get('last_name')
    first_name = form.get('first_name')
    same_person = Person.query.filter(
        Person.id != employee.id,
        Person.last_name == last_name,
        Person.first_name == first_name
    ).all()
    if same_person:
        return f"Человек с именем {last_name} {first_name} уже есть в системе"

    employee.last_name = last_name
    employee.first_name = first_name
    employee.patronym = form.get('patronym')
    employee.contacts[0].telegram = form.get('telegram')
    employee.contacts[0].phone = form.get('phone')
    employee.contacts[0].other_contact = form.get('other_contact')

    for role in employee.roles:
        if not form.get(f'role_{role.id}'):
            db.session.delete(role)
            if role.role == TEACHER:
                employee.teacher = False
                employee.subjects_taught = []
                employee.teaching_classes = []
        else:
            role.role = form.get(f'role_{role.id}')
    db.session.flush()

    if employee.teacher:
        subjects_to_remove = []
        for subject in employee.subjects_taught:
            if not form.get(f'subject_{subject.id}'):
                subjects_to_remove.append(subject)

        [employee.subjects_taught.remove(subj) for subj in subjects_to_remove]

        new_subject_ids = form.getlist('new_subjects')
        if new_subject_ids:
            new_subjects = Subject.query.filter(
                Subject.id.in_([int(subject_id) for subject_id in new_subject_ids])
            ).all()
            employee.subjects_taught.extend(new_subjects)

        classes_to_remove = []
        for school_class in employee.teaching_classes:
            if not form.get(f'school_class_{school_class.id}'):
                classes_to_remove.append(school_class)

        [employee.teaching_classes.remove(sc_cl) for sc_cl in classes_to_remove]

        new_classes_ids = form.getlist('new_classes')
        if new_classes_ids:
            new_classes = SchoolClass.query.filter(
                SchoolClass.id.in_([int(class_id) for class_id in new_classes_ids])
            ).all()
            employee.teaching_classes.extend(new_classes)

        employee.color = form.get('new_teacher_color')
        db.session.flush()

    new_roles = form.getlist('new_roles')
    if new_roles:
        for new_role in new_roles:
            new_employee_role = Employee(
                person_id=employee.id,
                role=new_role
            )
            db.session.add(new_employee_role)

            if new_role == TEACHER:
                employee.teacher = True
                subject_ids = form.getlist('subjects')
                if subject_ids:
                    teacher_subjects = Subject.query.filter(
                        Subject.id.in_([int(subject_id) for subject_id in subject_ids])
                    ).all()
                    employee.subjects_taught.extend(teacher_subjects)
                classes_ids = form.getlist('classes')
                if classes_ids:
                    teacher_classes = SchoolClass.query.filter(
                        SchoolClass.id.in_([int(class_id) for class_id in classes_ids])
                    ).all()
                    employee.teaching_classes.extend(teacher_classes)
                employee.color = form.get('teacher_color')

        db.session.flush()

    return ''
