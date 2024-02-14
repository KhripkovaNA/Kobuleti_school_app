from app.models import Person, Contact, parent_child_table, Employee, Subject, Subscription, Lesson, \
    SchoolClass, Room, SubjectType, SubscriptionType, student_lesson_attended_table, teacher_class_table, \
    SchoolLessonJournal, Finance
from datetime import datetime, timedelta
from app import db
from sqlalchemy import and_, or_
from dateutil.relativedelta import relativedelta
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter

DAYS_OF_WEEK = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"]
MONTHS = ["январь", "февраль", "март", "апрель", "май", "июнь", "июль",
          "август", "сентябрь", "октябрь", "ноябрь", "декабрь"]
CHILD = "Ребенок"
ADULT = "Взрослый"
TEACHER = "Учитель"
CHILD_SELF = "Сам ребенок"
CHOOSE = "Выбрать"
OTHER = "Другое"
TODAY = datetime.now().date()


def conjugate_lessons(number):
    last_digit = number % 10
    last_two_digits = number % 100

    if 10 <= last_two_digits <= 20:
        return f"{number} занятий"
    elif last_digit == 1:
        return f"{number} занятие"
    elif 2 <= last_digit <= 4:
        return f"{number} занятия"
    else:
        return f"{number} занятий"


def conjugate_years(number):
    last_digit = number % 10
    last_two_digits = number % 100

    if 10 <= last_two_digits <= 20:
        return f"{number} лет"
    elif last_digit == 1:
        return f"{number} год"
    elif 2 <= last_digit <= 4:
        return f"{number} года"
    else:
        return f"{number} лет"


def conjugate_hours(number):
    last_digit = number % 10
    last_two_digits = number % 100

    if 10 <= last_two_digits <= 20:
        return f"{number} часов"
    elif last_digit == 1:
        return f"{number} час"
    elif 2 <= last_digit <= 4:
        return f"{number} часа"
    else:
        return f"{number} часов"


def person_age(dob):
    age = TODAY.year - dob.year - ((TODAY.month, TODAY.day) < (dob.month, dob.day))
    return conjugate_years(age)


def create_student(form, student_type):
    last_name = form.last_name.data
    first_name = form.first_name.data
    patronym = form.patronym.data
    status = form.status.data
    if student_type == 'child':
        dob = datetime.strptime(form.dob.data, '%d.%m.%Y').date() \
            if form.dob.data else None
        person_type = CHILD

    else:
        dob = None
        person_type = ADULT

    student = Person(
        last_name=last_name,
        first_name=first_name,
        patronym=patronym,
        dob=dob,
        person_type=person_type,
        status=status
    )

    return student


def create_contact(form):
    telegram = form.telegram.data
    phone = form.phone.data
    other_contact = form.other_contact.data

    contact = Contact(
        telegram=telegram,
        phone=phone,
        other_contact=other_contact
    )

    return contact


def create_parent(contact_form):
    parent_last_name = contact_form.parent_last_name.data
    parent_first_name = contact_form.parent_first_name.data
    parent_patronym = contact_form.parent_patronym.data

    parent = Person(
        last_name=parent_last_name,
        first_name=parent_first_name,
        patronym=parent_patronym,
        person_type=ADULT
    )

    return parent


def handle_contact_info(contact_form, student):
    contact_select = contact_form.contact_select.data
    relation_type = contact_form.relation.data
    student_contacts = Contact.query.filter_by(person_id=student.id).first()
    if relation_type == CHILD_SELF and not student_contacts:
        contact = create_contact(contact_form)
        db.session.add(contact)
        db.session.flush()

        student.contacts.append(contact)
        db.session.flush()

    elif relation_type != CHILD_SELF:
        if contact_select == CHOOSE:
            parent_id = int(contact_form.selected_contact.data)
            parent = Person.query.filter_by(id=parent_id).first()
            contact = Contact.query.filter_by(person_id=parent_id).first()

        else:
            contact = create_contact(contact_form)
            parent = create_parent(contact_form)
            db.session.add(parent)
            db.session.add(contact)
            db.session.flush()

            parent.contacts.append(contact)
            parent.primary_contact = parent.id

        student.parents.append(parent)
        db.session.flush()
        assign_relation_type(contact_form, student, parent)
    else:
        return

    if contact_form.primary_contact.data == "true":
        student.primary_contact = contact.person_id


def assign_relation_type(form, student, parent):
    relation_type = form.relation.data

    if relation_type == OTHER:
        relation_type = form.other_relation.data

    relation_entry = parent_child_table.update().where(
        (parent_child_table.c.parent_id == parent.id) &
        (parent_child_table.c.child_id == student.id)
    ).values(relation=relation_type)

    db.session.execute(relation_entry)


def add_child(form):
    student = create_student(form, 'child')
    db.session.add(student)
    db.session.flush()

    for contact_form in form.contacts:
        handle_contact_info(contact_form, student)

    return student


def add_adult(form):
    client_select = form.client_select.data
    if client_select == CHOOSE:
        client_id = int(form.selected_client.data)
        client = Person.query.filter_by(id=client_id).first()
        client.status = form.status.data

    else:
        client = create_student(form, 'adult')
        contact = create_contact(form)
        db.session.add(client)
        db.session.add(contact)
        db.session.flush()
        client.contacts.append(contact)
        client.primary_contact = client.id

    db.session.flush()

    return client


def add_new_employee(form):
    employee_select = form.get('employee_select')
    if employee_select == CHOOSE:
        person_id = int(form.get('selected_person'))
        employee = Person.query.filter_by(id=person_id).first()

    else:
        last_name = form.get('last_name')
        first_name = form.get('first_name')
        patronym = form.get('patronym')
        employee = Person(
            last_name=last_name,
            first_name=first_name,
            patronym=patronym,
            person_type=ADULT
        )
        contact = create_contact(form, '')
        db.session.add(employee)
        db.session.add(contact)
        db.session.flush()
        employee.contacts.append(contact)
        employee.primary_contact = employee.id

    roles = form.getlist('roles')
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
                subject_ids = [int(subject_id) for subject_id in form.getlist('subjects')]
                subjects = Subject.query.filter(Subject.id.in_(subject_ids)).all()
                employee.subjects_taught.extend(subjects)
                employee.color = form.get('teacher_color')

    return employee


def clients_data(person_type):
    if person_type == 'child':
        all_clients = Person.query.filter(
            Person.contacts.any(~Contact.id.is_(None))
        ).order_by(Person.last_name, Person.first_name).all()
    elif person_type == 'adult':
        all_clients = Person.query.filter(Person.status.is_(None)).order_by(Person.last_name, Person.first_name).all()
    else:
        all_clients = Person.query.filter(
            ~Person.roles.any(Employee.id),
            Person.person_type == ADULT
        ).order_by(Person.last_name, Person.first_name).all()
    clients = []
    for client in all_clients:
        client_data = {
            "id": client.id,
            "last_name": client.last_name,
            "first_name": client.first_name,
            "patronym": client.patronym
        }
        if client.contacts:
            client_data["telegram"] = client.contacts[0].telegram
            client_data["phone"] = client.contacts[0].phone
            client_data["other_contact"] = client.contacts[0].other_contact
        else:
            client_data["telegram"] = ""
            client_data["phone"] = ""
            client_data["other_contact"] = ""

        clients.append(client_data)

    return clients


def format_status(student):
    if student.status == "Закрыт":
        student.status_info = f"{student.status} причина: {student.leaving_reason}"
    elif student.status == "Пауза":
        student.status_info = f"{student.status} до {student.pause_date}" if student.pause_date else student.status
    else:
        student.status_info = student.status


def format_student_info(student):
    if student.dob:
        dob = student.dob
        student.birth_date = f'{dob:%d.%m.%Y}'
        student.age = person_age(dob)
    if student.pause_until:
        student.pause_date = f'{student.pause_until:%d.%m.%y}'

    format_status(student)

    if student.balance > 0:
        student.balance_plus = round(student.balance, 1)
    elif student.balance < 0:
        student.balance_minus = round(student.balance, 1)
    if student.children.all():
        format_children(student)
    if student.roles:
        student.employee_roles = ', '.join([role.role for role in student.roles])


def format_main_contact(student):
    main_contact = Person.query.filter_by(id=student.primary_contact).first()
    if main_contact.contacts[0].telegram:
        student.contact = f"Телеграм: {main_contact.contacts[0].telegram}"
    elif main_contact.contacts[0].phone:
        student.contact = f"Тел.: {main_contact.contacts[0].phone}"
    elif main_contact.contacts[0].other_contact:
        student.contact = main_contact.contacts[0].other_contact

    if main_contact.id != student.id:
        contact_type = db.session.query(parent_child_table.c.relation).filter(
            parent_child_table.c.parent_id == main_contact.id,
            parent_child_table.c.child_id == student.id).scalar()
        student.contact_name = f"{contact_type} - {main_contact.last_name} {main_contact.first_name}"


def format_all_contacts(student):
    contacts = []

    if student.contacts:
        if student.primary_contact == student.id:
            student.main_contact = student
            student.main_contact.type = CHILD_SELF
        else:
            student.type = CHILD_SELF
            contacts.append(student)

    for parent in student.parents.all():
        parent.type = db.session.query(parent_child_table.c.relation).filter(
            parent_child_table.c.parent_id == parent.id,
            parent_child_table.c.child_id == student.id).scalar()
        if student.primary_contact == parent.id:
            student.main_contact = parent
        else:
            contacts.append(parent)

    student.additional_contacts = contacts


def format_children(person):
    children = []
    for child in person.children.all():
        child_age = person_age(child.dob) if child.dob else None
        child_info = f'{child.last_name} {child.first_name} ({child_age})' \
            if child_age else f'{child.last_name} {child.first_name}'
        children.append((child.id, child_info))
    person.children_info = children


def after_school_subject():
    after_school = Subject.query.filter(Subject.subject_type.has(SubjectType.name == 'after_school')).first()
    return after_school


def format_subjects_and_subscriptions(student):
    check_subscription(student, 0, 0)
    subscriptions = []
    subscriptions_list = []
    subscriptions_set = set()
    after_school_list = []

    school = [student.school_class.school_name] if student.school_class else []

    for subscription in student.subscriptions:
        subject = subscription.subject
        is_after_school = subject == after_school_subject()
        is_active = subscription.active
        subscription_dict = {}

        if is_active and not is_after_school:
            subscription_dict['subscription_id'] = subscription.id
            subscription_dict['subject_name'] = subject.name
            subscription_dict['lessons_left'] = subscription.lessons_left
            subscription_dict['end_date'] = f'{subscription.end_date:%d.%m.%Y}'
            subscriptions.append(subscription_dict)
            subscriptions_list.append(f'{subject.name}({subscription.lessons_left})')
            subscriptions_set.add(subject.id)

        elif is_after_school:
            if is_active:
                subscription_dict['subscription_id'] = subscription.id
                subscription_dict['purchase_date'] = subscription.purchase_date
                subscription_dict['shift'] = subscription.shift
                subscription_dict['period'] = "месяц"
                subscription_dict['validity'] = MONTHS[subscription.purchase_date.month - 1]
                after_school_list.append(subscription_dict)
                subscriptions_list.insert(0, f'{subject.name} ({subscription_dict["validity"]})')
                subscriptions_set.add(subject.id)
            else:
                day_delta = (subscription.purchase_date - TODAY).days
                if (-30 <= day_delta <= 30) and subscription.period != "month":
                    subscription_dict['subscription_id'] = subscription.id
                    subscription_dict['purchase_date'] = subscription.purchase_date
                    subscription_dict['shift'] = subscription.shift
                    subscription_dict['period'] = "день" if subscription.period == "day" else subscription.period
                    subscription_dict['validity'] = f"{subscription.purchase_date:%d.%m}"

                    after_school_list.append(subscription_dict)
                    subscriptions_set.add(subject.id)

    all_subjects_list = sorted(
        [(subject.name, subject.id) for subject in student.subjects if subject.subject_type.name != "school"])
    extra_subjects = sorted([subject.name for subject in student.subjects if
                             subject.id not in subscriptions_set and subject.subject_type.name != "school"])

    student.extra_subjects = extra_subjects
    student.subjects_info = ', '.join(school + subscriptions_list + extra_subjects)
    student.subscriptions_info = subscriptions
    student.after_school_info = after_school_list
    student.all_subjects = ([(school[0], 0)] if school else []) + all_subjects_list


def basic_student_info(student):
    format_student_info(student)
    format_main_contact(student)
    format_subjects_and_subscriptions(student)


def extensive_student_info(student):
    format_student_info(student)
    format_all_contacts(student)
    format_subjects_and_subscriptions(student)


def subscription_subjects_data():
    filtered_subjects = Subject.query.filter(Subject.id != after_school_subject().id,
                                             Subject.subscription_types.any(SubscriptionType.id.isnot(None))) \
        .order_by(Subject.name).all()
    subscription_subjects = []
    for subject in filtered_subjects:
        subject_data = {
            "id": subject.id,
            "name": subject.name,
            "price_info": {subscription_type.id: f"{subscription_type.price:.0f} Лари"
                           for subscription_type in subject.subscription_types},
            "subscription_types_info": {
                subscription_type.id: f"{conjugate_lessons(subscription_type.lessons)} " +
                                      f"на {subscription_type.duration} дней"
                for subscription_type in subject.subscription_types
            }
        }
        subscription_subjects.append(subject_data)

    return subscription_subjects


def subjects_data():
    all_subjects = Subject.query.order_by(Subject.name).all()
    subjects_teachers = []
    for subject in all_subjects:
        subject_data = {
            "id": subject.id,
            "name": subject.name,
            "description": subject.subject_type.description,
            "subject_type": subject.subject_type_id,
            "school_classes": {school_class.id: school_class.school_name
                               for school_class in sorted(subject.school_classes, key=lambda x: x.school_class)},
            "teachers": {teacher.id: f"{teacher.last_name} {teacher.first_name}"
                         for teacher in sorted(subject.teachers, key=lambda x: (x.last_name, x.first_name))}
        }
        subjects_teachers.append(subject_data)

    return subjects_teachers


def lesson_subjects_data():
    now = datetime.now().time()
    filtered_subjects = Subject.query.filter(
        Subject.subject_type.has(SubjectType.name == "extra")
    ).order_by(Subject.name).all()

    lesson_subjects = []
    for subject in filtered_subjects:
        future_lessons = Lesson.query.filter(
            and_(
                Lesson.subject_id == subject.id,
                or_(
                    and_(
                        Lesson.date == TODAY,
                        Lesson.start_time > now
                    ),
                    Lesson.date > TODAY
                )
            )
        ).order_by(Lesson.date, Lesson.start_time).all()
        if future_lessons:
            lessons_list = {lesson.id: f"{DAYS_OF_WEEK[lesson.date.weekday()]} " +
                                       f"{lesson.date:%d.%m} " +
                                       f"в {lesson.start_time:%H:%M}"
                            for lesson in future_lessons}
            subject_data = {
                "id": subject.id,
                "name": subject.name,
                "lessons": lessons_list
            }
            lesson_subjects.append(subject_data)
    return lesson_subjects


def student_lesson_register(form, student_id):
    student = Person.query.filter_by(id=student_id).first()
    subject_id = int(form.get('selected_subject'))
    subject = Subject.query.filter_by(id=subject_id).first()
    lesson_id = int(form.get('lesson'))
    lesson = Lesson.query.filter_by(id=lesson_id).first()
    if student not in subject.students:
        subject.students.append(student)
    if student not in lesson.students_registered:
        lesson.students_registered.append(student)

    return lesson_id


def purchase_subscription(form, student_id):
    subject_id = int(form.get('selected_subject'))
    subscription_type_id = int(form.get('subscription_type'))
    subscription_type = SubscriptionType.query.filter_by(id=subscription_type_id).first()
    purchase_date = datetime.strptime(form.get('purchase_date'), '%d.%m.%Y').date()
    end_date = purchase_date + timedelta(subscription_type.duration)

    new_subscription = Subscription(
        subject_id=subject_id,
        student_id=student_id,
        subscription_type_id=subscription_type_id,
        lessons_left=subscription_type.lessons,
        purchase_date=purchase_date,
        end_date=end_date
    )
    return new_subscription, subscription_type.price


def handle_student_edit(form, student, edit_type):
    if edit_type == 'student_edit':
        student.last_name = form.last_name
        student.first_name = form.first_name
        student.patronym = form.patronym
        student.dob = datetime.strptime(form.dob, '%d.%m.%Y').date() \
            if form.dob else None
        student.status = form.status
        if student.status == "Закрыт":
            student.subjects = []
            student.subscriptions = []
        student.pause_date = datetime.strptime(form.pause_until, '%d.%m.%Y').date() \
            if form.pause_until and student.status == "Пауза" else None

        student.leaving_reason = form.leaving_reason if student.status == "Закрыт" else ''
        db.session.flush()

    if edit_type == 'edit_main_contact':
        main_contact = student.main_contact
        main_contact.contacts[0].telegram = form.get('telegram_main')
        main_contact.contacts[0].phone = form.get('phone_main')
        main_contact.contacts[0].other_contact = form.get('other_contact_main')
        if main_contact.id != student.id:
            main_contact.last_name = form.get('parent_last_name_main')
            main_contact.first_name = form.get('parent_first_name_main')
            main_contact.patronym = form.get('parent_patronym_main')
        db.session.flush()

    for i, contact in enumerate(student.additional_contacts, 1):
        if f'form_cont_{i}_submit' in form:
            contact.contacts[0].telegram = form.get(f'telegram_{i}')
            contact.contacts[0].phone = form.get(f'phone_{i}')
            contact.contacts[0].other_conta = form.get(f'other_contact_{i}')
            if contact.id != student.id:
                contact.last_name = form.get(f'parent_last_name_{i}')
                contact.first_name = form.get(f'parent_first_name_{i}')
                contact.patronym = form.get(f'parent_patronym_{i}')
            if form.get(f'primary_contact_{i}') == 'on':
                student.primary_contact = contact.id
            db.session.flush()

    if 'form_cont_new_submit' in form:
        handle_contact_info(form, student)

    if 'del_subject_btn' in form:
        del_subject_id = int(form.get('del_subject_btn'))
        del_subject = Subject.query.filter_by(id=del_subject_id).first()
        if del_subject in student.subjects:
            student.subjects.remove(del_subject)
            db.session.flush()

    if 'form_subscriptions_submit' in form:
        for subscription in student.subscriptions:
            subscription.lessons_left = form.get(f'subscription_{subscription.id}_lessons')
            subscription.end_date = form.get(f'subscription_{subscription.id}_end_date')
        db.session.flush()


def handle_employee_edit(form, employee):
    employee.last_name = form.get('last_name')
    employee.first_name = form.get('first_name')
    employee.patronym = form.get('patronym')

    for role in employee.roles:
        if not form.get(f'role_{role.id}'):
            db.session.delete(role)
            if role.role == TEACHER:
                employee.teacher = False
                employee.subjects_taught = []
        else:
            role.role = form.get(f'role_{role.id}')
    db.session.flush()

    if employee.teacher:
        for subject in employee.subjects_taught:
            if not form.get(f'subject_{subject.id}'):
                employee.subjects_taught.remove(subject)

        new_subject_ids = form.getlist('new_subjects')
        if new_subject_ids:
            new_subjects = Subject.query.filter(
                Subject.id.in_([int(subject_id) for subject_id in new_subject_ids])
            ).all()
            employee.subjects_taught.extend(new_subjects)
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
                employee.color = form.get('teacher_color')

        db.session.flush()


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


def add_new_subject(form, subject_type):
    name = form.get("subject_name")
    subject_name = name[0].upper() + name[1:]
    short_name = form.get("subject_short_name")
    subject_short_name = short_name[0].upper() + short_name[1:]
    teacher_ids = [int(teacher) for teacher in form.getlist('teachers')]
    teachers = Person.query.filter(Person.id.in_(teacher_ids)).all()
    subject_type_id = form.get("subject_type")

    if subject_type == "school":
        classes = [int(school_class) for school_class in form.getlist('school_classes')]
        school_classes = SchoolClass.query.filter(SchoolClass.id.in_(classes)).all()

        new_subject = Subject(
            name=subject_name,
            short_name=subject_short_name,
            subject_type_id=subject_type_id
        )
        new_subject.school_classes.extend(school_classes)

    else:
        subject_price = float(form.get('subject_price'))
        one_time_price = subject_price if int(subject_price) > 0 else None
        if not form.get('no_subject_school_price'):
            subject_school_price = float(form.get('subject_school_price'))
            school_price = subject_school_price if int(subject_school_price) > 0 else None
        else:
            school_price = None
        if not form.get('no_subscription'):
            subscription_type_ids = [int(st) for st in form.getlist('subscription_types')]
            subscription_types = SubscriptionType.query.filter(SubscriptionType.id.in_(subscription_type_ids)).all()
        else:
            subscription_types = None

        new_subject = Subject(
            name=subject_name,
            short_name=subject_short_name,
            subject_type_id=subject_type_id,
            one_time_price=one_time_price,
            school_price=school_price,
        )
        new_subject.subscription_types.extend(subscription_types)
        subject_type = "extra_school"

    new_subject.teachers.extend(teachers)

    return new_subject


def format_subscription_types(subscription_types):
    types_of_subscription = []
    for subscription_type in subscription_types:
        if subscription_type.lessons:
            type_of_subscription = f"{subscription_type.lessons} занятий за {subscription_type.price:.0f} " \
                                   f"({subscription_type.duration} дней)"
            types_of_subscription.append((subscription_type.id, type_of_subscription))

    return types_of_subscription


def handle_subject_edit(subject, form):
    subject.name = form.get('subject_name')
    subject.short_name = form.get('subject_short_name')
    subject.description = form.get('description')
    if not form.get('no_subject_price'):
        subject_price = float(form.get('subject_price'))
        subject.one_time_price = subject_price if int(subject_price) > 0 else None
    else:
        subject.one_time_price = None
    if not form.get('no_subject_school_price'):
        school_price = float(form.get('subject_school_price'))
        subject.school_price = school_price if int(school_price) > 0 else None
    else:
        subject.school_price = None
    subscription_type_ids = [int(st) for st in form.getlist('subscription_types')]
    subscription_types = SubscriptionType.query.filter(SubscriptionType.id.in_(subscription_type_ids)).all()
    subject.subscription_types = [subscription_type for subscription_type in subscription_types]


def check_subscription(student, lesson, subject_id):
    after_school = after_school_subject()
    cond = lesson == 0
    if cond:
        date = datetime.today().date()
    else:
        date = lesson.date
    if subject_id == 0:
        subscriptions = student.subscriptions
    else:
        subscriptions = Subscription.query.filter(Subscription.subject_id.in_([subject_id, after_school.id]),
                                                  Subscription.student_id == student.id).all()
    for subscription in subscriptions:
        if subscription.subject == after_school:
            cond1 = subscription.purchase_date.month == date.month
            cond2 = subscription.purchase_date > date
            cond3 = subscription.period == "month"
            subscription.active = True if ((cond1 or (cond2 and cond)) and cond3) else False
            db.session.commit()
        else:
            cond1 = subscription.purchase_date <= date
            cond2 = subscription.end_date >= date
            cond3 = subscription.lessons_left >= 0
            cond4 = subscription.lessons_left > 0
            cond5 = subscription.purchase_date > date
            subscription.active = True if (
                    (cond1 and cond2 and cond3 and not cond)
                    or (cond1 and cond2 and cond4)
                    or (cond5 and cond)
            ) else False
            db.session.commit()


def get_payment_options(student, subject_id, lesson):
    check_subscription(student, lesson, subject_id)
    after_school_sub = Subscription.query.filter_by(student_id=student.id,
                                                    subject_id=after_school_subject().id,
                                                    active=True).first()
    subscriptions = Subscription.query.filter_by(student_id=student.id,
                                                 subject_id=subject_id,
                                                 active=True) \
        .order_by(Subscription.purchase_date.desc()).all()
    student_balance = round(student.balance, 1)

    payment_options = []
    if subscriptions:
        for subscription in subscriptions:
            payment_option = {
                'value': f'subscription_{subscription.id}',
                'type': 'Абонемент',
                'info': f'{subscription.lessons_left} (до {subscription.end_date:%d.%m})'
            }
            payment_options.append(payment_option)
    if after_school_sub:
        payment_option = {
            'value': 'after_school',
            'type': 'Продленка',
            'info': f'Баланс: {student_balance}'
        }
        payment_options.append(payment_option)
    else:
        payment_option = {
            'value': 'one_time',
            'type': 'Разовое',
            'info': f'Баланс: {student_balance}'
        }
        payment_options.append(payment_option)
    return payment_options


def carry_out_lesson(form, subject, lesson):
    lesson_price = subject.one_time_price
    lesson_school_price = subject.school_price if subject.school_price else lesson_price
    for student in lesson.students:
        if form.get(f'attending_status_{student.id}') in ['attend', 'unreasonable']:
            payment_option = form.get(f'payment_option_{student.id}')
            if payment_option.startswith('subscription'):
                subscription_id = int(payment_option[len('subscription_'):])
                subscription = Subscription.query.filter_by(id=subscription_id).first()
                if subscription.lessons_left > 0:
                    subscription.lessons_left -= 1
                else:
                    student.balance -= lesson_price
                    description = f"Списание за занятие {subject.name}"
                    finance_operation(student.id, -lesson_price, description, lesson.date)
            else:
                price = lesson_school_price if payment_option == 'after_school' else lesson_price
                student.balance -= price
                description = f"Списание за занятие {subject.name}"
                finance_operation(student.id, -price, description, lesson.date)

            attendance = student_lesson_attended_table.insert().values(
                student_id=student.id,
                lesson_id=lesson.id,
                attending_status=form.get(f'attending_status_{student.id}')
            )
            db.session.execute(attendance)
    lesson.lesson_completed = True


def undo_lesson(form, subject, lesson):
    lesson_price = subject.one_time_price
    lesson_school_price = subject.school_price if subject.school_price else lesson_price
    for student in lesson.students:
        attending_status = db.session.query(student_lesson_attended_table.c.attending_status).filter(
            student_lesson_attended_table.c.student_id == student.id,
            student_lesson_attended_table.c.lesson_id == lesson.id).scalar()

        if attending_status:
            payment_option = form.get(f'payment_option_{student.id}')
            if payment_option.startswith('subscription'):
                subscription_id = int(payment_option[len('subscription_'):])
                subscription = Subscription.query.filter_by(id=subscription_id).first()
                subscription.lessons_left += 1
            else:
                price = lesson_school_price if payment_option == 'after_school' else lesson_price
                student.balance += price
                record = Finance.query.filter(
                    Finance.person_id == student.id,
                    Finance.date == lesson.date,
                    Finance.amount == -price,
                    Finance.description == f"Списание за занятие {subject.name}"
                ).first()
                if record:
                    db.session.delete(record)
                    db.session.flush()
                else:
                    description = f"Возврат за занятие {subject.name}"
                    finance_operation(student.id, price, description, lesson.date)
            lesson.students_attended.remove(student)

    lesson.lesson_completed = False


def handle_lesson(form, subject, lesson):
    if 'del_client_btn' in form:
        del_client_id = int(form.get('del_client_btn'))
        del_client = Person.query.filter_by(id=del_client_id).first()
        if del_client in subject.students:
            subject.students.remove(del_client)
        if del_client in lesson.students_registered:
            lesson.students_registered.remove(del_client)
        db.session.flush()
    if 'add_client_btn' in form:
        new_client_id = int(form.get('added_client_id'))
        new_client = Person.query.filter_by(id=new_client_id).first()
        subject.students.append(new_client)
        db.session.flush()
    if 'registered_btn' in form:
        for student in lesson.students:
            if (
                    student not in lesson.students_registered
                    and form.get(f'registered_{student.id}') == 'on'
            ):
                lesson.students_registered.append(student)
            elif (
                    student in lesson.students_registered
                    and not form.get(f'registered_{student.id}')
            ):
                lesson.students_registered.remove(student)

    if 'attended_btn' in form:
        carry_out_lesson(form, subject, lesson)
        return 'Занятие проведено.'

    if 'change_btn' in form:
        undo_lesson(form, subject, lesson)
        return 'Занятие отменено.'


def get_lesson_students(lesson):
    lesson_students = lesson.students_registered.all() if lesson.lesson_completed else \
        list(set(lesson.students_registered.all() + lesson.subject.students))
    if lesson_students:
        for student in lesson_students:
            student.payment_options = get_payment_options(student, lesson.subject_id, lesson)
            if lesson.lesson_completed:
                attendance = db.session.query(student_lesson_attended_table.c.attending_status).filter(
                    student_lesson_attended_table.c.student_id == student.id,
                    student_lesson_attended_table.c.lesson_id == lesson.id).scalar()
                student.attended = attendance if attendance else 'not_attend'
    return sorted(lesson_students, key=lambda x: (x.last_name, x.first_name))


def prev_next_lessons(lesson):
    query = Lesson.query.filter(Lesson.subject_id == lesson.subject_id)
    previous_lesson = query.filter(
        or_(
            and_(
                Lesson.date == lesson.date,
                Lesson.start_time < lesson.start_time
            ),
            Lesson.date < lesson.date
        )
    ).order_by(Lesson.date.desc(), Lesson.start_time.desc()).first()
    next_lesson = query.filter(
        or_(
            and_(
                Lesson.date == lesson.date,
                Lesson.start_time > lesson.start_time
            ),
            Lesson.date > lesson.date
        )
    ).order_by(Lesson.date, Lesson.start_time).first()
    prev_id = previous_lesson.id if previous_lesson else None
    next_id = next_lesson.id if next_lesson else None
    return prev_id, next_id


def show_lesson(lesson_id):
    if not str(lesson_id).isdigit():
        subject_id_str = lesson_id.split('-')[1]
        subject_id = int(subject_id_str) if subject_id_str.isdigit() else None
        last_lesson = Lesson.query.filter_by(subject_id=subject_id). \
            order_by(Lesson.date.desc(), Lesson.start_time.desc()).first()
        coming_lesson = Lesson.query.filter(Lesson.date >= TODAY,
                                            Lesson.subject_id == subject_id). \
            order_by(Lesson.date, Lesson.start_time).first()
        subject_lesson = coming_lesson if coming_lesson else last_lesson if last_lesson else None
    else:
        subject_lesson = Lesson.query.filter_by(id=int(lesson_id)).first()
        subject_id = subject_lesson.subject_id if subject_lesson else None

    if subject_lesson:
        subject_lesson.students = get_lesson_students(subject_lesson)
        subject_lesson.prev, subject_lesson.next = prev_next_lessons(subject_lesson)
        lesson_subject = subject_lesson.subject

    else:
        lesson_subject = Subject.query.filter_by(id=subject_id).first() if subject_id else None

    return subject_lesson, lesson_subject


def format_school_classes_names(school_classes):
    num_classes = [cl.school_name[:2].strip() for cl in school_classes
                   if (cl.school_name[0].isdigit() or cl.school_name[:2].isdigit())]
    classes = [cl.school_name for cl in school_classes
               if not (cl.school_name[0].isdigit() or cl.school_name[:2].isdigit())]
    formatted_school_classes = (
        f"{'-'.join(num_classes)} класс, {', '.join(classes)}"
        if (classes and num_classes)
        else f"{'-'.join(num_classes)} класс"
        if num_classes
        else f"{', '.join(classes)}"
    )
    return formatted_school_classes


def create_lesson_dict(lesson):
    start_time = (lesson.start_time.hour - 9) * 60 + lesson.start_time.minute
    end_time = (lesson.end_time.hour - 9) * 60 + lesson.end_time.minute

    if lesson.lesson_type.name == 'school':
        lesson_type = format_school_classes_names(lesson.school_classes)
    elif lesson.lesson_type.name == 'individual':
        lesson_type = 'индив'
    else:
        lesson_type = ''

    return {
        'id': lesson.id,
        'time': f'{lesson.start_time:%H:%M} - {lesson.end_time:%H:%M}',
        'start_time': start_time,
        'end_time': end_time,
        'subject': lesson.subject_names,
        'teacher': lesson.teacher.first_name,
        'color': lesson.teacher.color,
        'lesson_type': lesson_type,
        'lesson_type_name': lesson.lesson_type.name
    }


def create_school_lesson_dict(lesson):
    start_time = (lesson.start_time.hour - 9) * 60 + lesson.start_time.minute
    end_time = (lesson.end_time.hour - 9) * 60 + lesson.end_time.minute
    return {
        'id': lesson.id,
        'time': f'{lesson.start_time:%H:%M} - {lesson.end_time:%H:%M}',
        'start_time': start_time,
        'end_time': end_time,
        'subject': lesson.subject.short_name,
        'teacher': lesson.teacher.first_name,
        'room': lesson.room.name,
        'room_color': lesson.room.color
    }


def day_lessons_list(day_room_lessons):
    lessons_for_day = []
    current_lesson = day_room_lessons[0]
    current_lesson.subject_names = [current_lesson.subject.short_name]

    for next_lesson in day_room_lessons[1:]:
        if (
                current_lesson.teacher.id == next_lesson.teacher.id
                and current_lesson.school_classes.all() == next_lesson.school_classes.all()
                and current_lesson.lesson_type.name == 'school'
                and current_lesson.lesson_type.name == 'school'
        ):
            if current_lesson.subject_names[-1] != next_lesson.subject.short_name:
                current_lesson.subject_names.append(next_lesson.subject.short_name)
            current_lesson.end_time = next_lesson.end_time
        else:
            lessons_for_day.append(create_lesson_dict(current_lesson))
            next_lesson.subject_names = [next_lesson.subject.short_name]
            current_lesson = next_lesson

    lessons_for_day.append(create_lesson_dict(current_lesson))

    return lessons_for_day


def get_date(day_of_week, week=0):
    day_of_week_date = TODAY - timedelta(days=TODAY.weekday()) + timedelta(days=day_of_week) + week * timedelta(weeks=1)
    return day_of_week_date


def get_weekday_date(day_of_week, date=TODAY):
    date_of_week_day = date - timedelta(days=date.weekday()) + timedelta(days=day_of_week)
    return date_of_week_day


def get_week_dates():
    week_dates = [get_date(0), get_date(0, 1), get_date(0, -1)]
    return week_dates


def week_lessons_dict(week, rooms):
    week_lessons = {}
    for day, weekday in enumerate(DAYS_OF_WEEK):
        lessons_date = get_date(day, week)
        lessons_date_str = f'{lessons_date:%d.%m}'
        day_lessons = {}
        for room in rooms:
            lessons_filtered = Lesson.query.filter_by(date=lessons_date, room_id=room.id). \
                order_by(Lesson.start_time).all()
            day_lessons[room.name] = day_lessons_list(lessons_filtered) if lessons_filtered else []

        week_lessons[weekday] = (lessons_date_str, day_lessons)

    return week_lessons


def day_school_lessons_dict(day, week, school_classes):
    lesson_date = get_date(day-1, week)
    lesson_date_str = f'{lesson_date:%d.%m}'
    class_lessons = {}
    for school_class in school_classes:
        lessons_filtered = Lesson.query.filter(
            Lesson.lesson_type_id == 1,
            Lesson.date == lesson_date,
            Lesson.school_classes.any(SchoolClass.id == school_class.id)
        ).order_by(Lesson.start_time).all()
        class_lessons[school_class.school_name] = [create_school_lesson_dict(school_lesson)
                                                   for school_lesson in lessons_filtered]

    day_lessons = (lesson_date_str, class_lessons)

    return day_lessons


def check_conflicting_lessons(date, start_time, end_time, classes, room, teacher):
    conflicting_lessons = Lesson.query.filter(
        and_(
            Lesson.date == date,
            or_(
                and_(
                    Lesson.start_time < end_time,
                    Lesson.end_time > start_time,
                    Lesson.room_id == room
                ),
                and_(
                    Lesson.start_time < end_time,
                    Lesson.end_time > start_time,
                    Lesson.teacher_id == teacher
                ),
                and_(
                    Lesson.start_time < end_time,
                    Lesson.end_time > start_time,
                    Lesson.school_classes.any(SchoolClass.id.in_(classes))
                )
            )
        )
    ).all()

    return conflicting_lessons


def create_check_lesson(lesson_date, form, i):
    start_time = datetime.strptime(form.get(f'lesson_start_time_{i}'), '%H : %M').time()
    end_time = datetime.strptime(form.get(f'lesson_end_time_{i}'), '%H : %M').time()
    subject_id, lesson_type_id = form.get(f'subject_{i}').split('-')
    room_id = int(form.get(f'room_{i}'))
    classes = [int(school_class) for school_class in form.getlist(f'school_classes_{i}')]
    teacher_id = int(form.get(f'teacher_{i}'))

    conflicting_lessons = check_conflicting_lessons(lesson_date, start_time, end_time,
                                                    classes, room_id, teacher_id)
    intersection = set()

    if conflicting_lessons:
        for conflict in conflicting_lessons:
            if conflict.room_id == room_id:
                alert = 'кабинету (' + conflict.room.name + ')'
                intersection.add(alert)
            if conflict.teacher_id == teacher_id:
                alert = 'учителю (' + f'{conflict.teacher.last_name} {conflict.teacher.first_name}' + ')'
                intersection.add(alert)
            conflict_classes = set([school_class.id for school_class in conflict.school_classes])
            intersected_classes = conflict_classes.intersection(classes)
            if intersected_classes:
                inter_classes = SchoolClass.query.filter(SchoolClass.id.in_(intersected_classes)).all()
                alert = 'классам (' + ', '.join([school_class.school_name for school_class in inter_classes]) + ')'
                intersection.add(alert)
        message_text = f'Занятие {i} не добавлено в расписание. Пересечения по ' + ', '.join(intersection) + '.'
        lesson = None

    else:
        lesson = Lesson(
            date=lesson_date,
            start_time=start_time,
            end_time=end_time,
            lesson_type_id=int(lesson_type_id),
            room_id=room_id,
            subject_id=int(subject_id),
            teacher_id=teacher_id,
        )

        school_classes = SchoolClass.query.filter(SchoolClass.id.in_(classes)).all()
        lesson.school_classes.extend(school_classes)
        message_text = f'Занятие {i} добавлено в расписание.'

    return lesson, message_text


def add_new_lessons(form):
    lesson_date = datetime.strptime(form.get(f'lesson_date'), '%d.%m.%Y').date()
    lesson_count = int(form.get('lesson_count'))
    messages = []
    for i in range(1, lesson_count + 1):
        new_lesson, text = create_check_lesson(lesson_date, form, i)
        if new_lesson:
            message = {'text': text, 'type': 'success'}
            messages.append(message)
            db.session.add(new_lesson)
            db.session.flush()
        else:
            message = {'text': text, 'type': 'error'}
            messages.append(message)
    week = int((get_weekday_date(0, lesson_date) - get_weekday_date(0, TODAY)).days / 7)
    return messages, week


def filter_lessons(form):
    week = form.get('week')

    if week.lstrip('-').isdigit():
        start_date = get_date(0, int(week))
    else:
        week_date = datetime.strptime(form.get('week_specific'), '%d.%m.%Y').date()
        start_date = get_weekday_date(0, week_date)

    next_week = form.get('next_week')

    if next_week.isdigit():
        next_start_date = get_date(0, int(next_week))
    else:
        next_week_date = datetime.strptime(form.get('next_week_specific'), '%d.%m.%Y').date()
        next_start_date = get_weekday_date(0, next_week_date)
    week_diff = int((next_start_date - start_date).days / 7)
    next_week = int((next_start_date - get_weekday_date(0, TODAY)).days / 7)

    weekday = form.get('lessons_days')
    weekdays = form.getlist('lessons_days_specific') if form.getlist('lessons_days_specific') else "all"

    subject_types = form.get('subject_types')
    school_classes = form.getlist('school_classes')
    rooms = form.get('rooms')
    teachers = form.get('teachers')
    school_type_id = SubjectType.query.filter_by(name='school').first().id

    if (weekday == "all") or (weekdays == "all"):
        end_date = get_weekday_date(6, start_date)
        query = Lesson.query.filter(Lesson.date >= start_date,
                                    Lesson.date <= end_date)
    else:
        lessons_dates = [get_weekday_date(int(day), start_date) for day in weekdays]
        query = Lesson.query.filter(Lesson.date.in_(lessons_dates))

    if rooms != "all" and form.getlist('rooms_specific'):
        rooms_list = [int(room) for room in form.getlist('rooms_specific')]
        query = query.filter(Lesson.room_id.in_(rooms_list))
    if subject_types != "all" and form.getlist('subject_types_specific'):
        subject_types_list = [int(room) for room in form.getlist('subject_types_specific')]
        query = query.filter(Lesson.lesson_type_id.in_(subject_types_list))
        if school_classes != 'all' and form.getlist('school_classes_specific') and (
                school_type_id in subject_types_list):
            school_classes_list = [int(school_class) for school_class in form.getlist('school_classes_specific')]
            query = query.filter(Lesson.school_classes.any(SchoolClass.id.in_(school_classes_list)))
    if teachers != "all" and form.getlist('teachers_specific'):
        teachers_list = [int(teacher) for teacher in form.getlist('teachers_specific')]
        query = query.filter(Lesson.lesson_type_id.in_(teachers_list))

    filtered_lessons = query.all()

    return filtered_lessons, week_diff, next_week


def copy_filtered_lessons(filtered_lessons, week_diff):
    copied_lessons = 0
    conflicts = 0
    for lesson in filtered_lessons:
        date = lesson.date + timedelta(weeks=week_diff)
        start_time = lesson.start_time
        end_time = lesson.end_time
        classes = [cl.id for cl in lesson.school_classes]
        room = lesson.room_id
        teacher = lesson.teacher_id

        conflicting_lessons = check_conflicting_lessons(date, start_time, end_time, classes, room, teacher)

        if not conflicting_lessons:
            new_lesson = Lesson(
                date=date,
                start_time=start_time,
                end_time=end_time,
                room_id=room,
                subject_id=lesson.subject_id,
                teacher_id=teacher,
                lesson_type_id=lesson.lesson_type_id
            )
            db.session.add(new_lesson)
            if lesson.lesson_type.name == "school":
                new_lesson.school_classes = SchoolClass.query.filter(SchoolClass.id.in_(classes)).all()
                if lesson.students_registered.all():
                    lesson_students = lesson.students_registered.all()
                else:
                    lesson_students = Person.query.filter(Person.school_class_id.in_(classes)).all()
                new_lesson.students_registered = lesson_students

            db.session.flush()
            copied_lessons += 1

        else:
            conflicts += 1

    return copied_lessons, conflicts


def format_school_class_students(school_class):
    school_class.main_teacher = db.session.query(Person).join(teacher_class_table).filter(
        teacher_class_table.c.class_id == school_class.id,
        teacher_class_table.c.main_teacher).first()
    class_students = Person.query.filter_by(school_class_id=school_class.id).order_by(Person.last_name).all()
    for student in class_students:
        format_student_info(student)
        format_main_contact(student)
    school_class.class_students = class_students


def format_school_class_subjects(school_class):
    school_class_subjects = Subject.query.filter(
        Subject.school_classes.any(SchoolClass.id == school_class.id)
    ).order_by(Subject.name).all()
    for school_subject in school_class_subjects:
        school_teachers = Person.query.filter(
            Person.lessons.any(
                and_(
                    Lesson.subject_id == school_subject.id,
                    Lesson.school_classes.any(SchoolClass.id == 2)
                )
            ),
            Person.subjects_taught.any(Subject.id == school_subject.id)
        ).order_by(Person.last_name, Person.first_name).all()
        subject_teachers = school_subject.teachers

        school_subject.school_teachers = school_teachers if school_teachers else subject_teachers
    school_class.school_class_subjects = school_class_subjects


def prev_next_school_lessons(lesson):
    query = Lesson.query.filter(Lesson.subject_id == lesson.subject_id)
    for school_class in lesson.school_classes:
        query = query.filter(Lesson.school_classes.any(SchoolClass.id == school_class.id))
    previous_lesson = query.filter(
        or_(
            and_(
                Lesson.date == lesson.date,
                Lesson.start_time < lesson.start_time
            ),
            Lesson.date < lesson.date
        )
    ).order_by(Lesson.date.desc(), Lesson.start_time.desc()).first()
    next_lesson = query.filter(
        or_(
            and_(
                Lesson.date == lesson.date,
                Lesson.start_time > lesson.start_time
            ),
            Lesson.date > lesson.date
        )
    ).order_by(Lesson.date, Lesson.start_time).first()
    prev_id = previous_lesson.id if previous_lesson else None
    next_id = next_lesson.id if next_lesson else None
    return prev_id, next_id


def show_school_lesson(lesson_id):
    if not str(lesson_id).isdigit():
        school_class_id_str, subject_id_str = lesson_id.split('-')
        school_class_id = int(school_class_id_str) if school_class_id_str.isdigit() else None
        subject_id = int(subject_id_str) if subject_id_str.isdigit() else None
        last_lesson = Lesson.query.filter(
            Lesson.subject_id == subject_id,
            Lesson.school_classes.any(SchoolClass.id == school_class_id)
        ).order_by(Lesson.date.desc(), Lesson.start_time.desc()).first()
        coming_lesson = Lesson.query.filter(
            Lesson.date >= TODAY,
            Lesson.subject_id == subject_id,
            Lesson.school_classes.any(SchoolClass.id == school_class_id)
        ).order_by(Lesson.date, Lesson.start_time).first()
        sc_lesson = coming_lesson if coming_lesson else last_lesson if last_lesson else None
    else:
        sc_lesson = Lesson.query.filter_by(id=int(lesson_id)).first()
        subject_id = sc_lesson.subject_id if sc_lesson else None

    if sc_lesson:
        classes = [cl.id for cl in sc_lesson.school_classes]
        sc_lesson.classes_ids = classes
        sc_lesson.classes = ', '.join([cl.school_name for cl in sorted(sc_lesson.school_classes,
                                                                       key=lambda x: x.school_class)])

        if sc_lesson.students_registered.all():
            lesson_students = sorted(sc_lesson.students_registered.all(), key=lambda x: (x.last_name, x.first_name))
        else:
            lesson_students = Person.query.filter(Person.school_class_id.in_(classes))\
                .order_by(Person.last_name, Person.first_name).all()

        for student in lesson_students:
            journal_record = SchoolLessonJournal.query.filter_by(
                lesson_id=sc_lesson.id, student_id=student.id
            ).first()
            student.grade = journal_record.grade if journal_record else None
            student.lesson_comment = journal_record.lesson_comment if journal_record else None
            attending_status = db.session.query(student_lesson_attended_table.c.attending_status).filter(
                student_lesson_attended_table.c.student_id == student.id,
                student_lesson_attended_table.c.lesson_id == sc_lesson.id).scalar()
            student.attending_status = attending_status
        sc_lesson.lesson_students = lesson_students
        sc_lesson.prev, sc_lesson.next = prev_next_school_lessons(sc_lesson)

        sc_subject = sc_lesson.subject
        school_classes = sc_lesson.school_classes.all()

    else:
        sc_subject = Subject.query.filter_by(id=subject_id).first() if subject_id else None

    return sc_lesson, sc_subject


def handle_school_lesson(form, lesson):
    if 'del_student_btn' in form:
        del_student_id = int(form.get('del_student_btn'))
        del_student = Person.query.filter_by(id=del_student_id).first()
        if del_student in lesson.students_registered:
            lesson.students_registered.remove(del_student)
        if del_student in lesson.students_attended:
            lesson.students_attended.remove(del_student)
        db.session.flush()
    if 'add_student_btn' in form:
        new_student_id = int(form.get('added_student_id'))
        new_student = Person.query.filter_by(id=new_student_id).first()
        lesson.students_registered.append(new_student)
        db.session.flush()

    if 'complete_btn' in form:
        lesson.lesson_topic = form.get('lesson_topic')

        for student in lesson.lesson_students:
            if student not in lesson.students_registered:
                lesson.students_registered.append(student)

            attending_status = db.session.query(student_lesson_attended_table.c.attending_status).filter(
                student_lesson_attended_table.c.student_id == student.id,
                student_lesson_attended_table.c.lesson_id == lesson.id).scalar()
            new_attending_status = "attend" if form.get(f'attended_{student.id}') else "not_attend"
            if not attending_status:
                attendance = student_lesson_attended_table.insert().values(
                    student_id=student.id,
                    lesson_id=lesson.id,
                    attending_status=new_attending_status
                )
                db.session.execute(attendance)
            else:
                new_attendance = student_lesson_attended_table.update().where(
                    (student_lesson_attended_table.c.student_id == student.id) &
                    (student_lesson_attended_table.c.lesson_id == lesson.id)
                ).values(attending_status=new_attending_status)
                db.session.execute(new_attendance)

            grade = form.get(f'grade_{student.id}')
            lesson_comment = form.get(f'lesson_comment_{student.id}')
            journal_record = SchoolLessonJournal.query.filter_by(
                lesson_id=lesson.id,
                student_id=student.id
            ).first()
            if grade or lesson_comment:
                if journal_record:
                    journal_record.grade = grade
                    journal_record.lesson_comment = lesson_comment
                else:
                    new_journal_record = SchoolLessonJournal(
                        date=lesson.date,
                        lesson_id=lesson.id,
                        student_id=student.id,
                        school_class_id=student.school_class_id,
                        subject_id=lesson.subject_id,
                        grade=grade,
                        lesson_comment=lesson_comment
                    )
                    db.session.add(new_journal_record)
            else:
                if journal_record:
                    db.session.delete(journal_record)
            db.session.flush()
        lesson.lesson_completed = True

        return 'Журнал заполнен.'

    if 'change_btn' in form:
        lesson.lesson_completed = False

        return 'Внесение изменений.'

    if 'new_grade_btn' in form:
        grade_type = form.get('grade_type')
        grade_date = datetime.strptime(form.get('grade_date'), '%d.%m.%Y').date()
        for student in lesson.lesson_students:
            new_grade = form.get(f'new_grade_{student.id}')
            new_comment = form.get(f'new_comment_{student.id}')
            if new_grade or new_comment:
                journal_record = SchoolLessonJournal(
                    date=grade_date,
                    grade_type=grade_type,
                    student_id=student.id,
                    school_class_id=student.school_class_id,
                    subject_id=lesson.subject_id,
                    grade=new_grade,
                    lesson_comment=new_comment
                )
                db.session.add(journal_record)
                db.session.flush()
        return "Оценка внесена"


def employee_record(employees, week):
    week_start = get_date(0, week)
    week_end = get_date(6, week)
    primary_classes = SchoolClass.query.filter(SchoolClass.school_class < 5, SchoolClass.main_teacher_id).all()
    main_teachers = [(sc_cl.id, sc_cl.main_teacher_id) for sc_cl in primary_classes]
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
                                lessons_dict[lesson.subject.name][lesson_date] += 1
                            else:
                                lessons_dict[lesson.subject.name][lesson_date] = 1
                        else:
                            lessons_dict[lesson.subject.name] = {lesson_date: 1}
            else:
                for lesson in teacher_lessons:
                    lesson_date = f'{lesson.date:%d.%m}'
                    if lessons_dict.get(lesson.subject.name):
                        if lessons_dict[lesson.subject.name].get(lesson_date):
                            lessons_dict[lesson.subject.name][lesson_date] += 1
                        else:
                            lessons_dict[lesson.subject.name][lesson_date] = 1
                    else:
                        lessons_dict[lesson.subject.name] = {lesson_date: 1}
            for role, activity in lessons_dict.items():
                add_employee_dict(employee.id, f"{employee.last_name} {employee.first_name}", role, activity)

    dates = [f"{week_start + timedelta(day):%d.%m}" for day in range(7)]

    return employees_list, dates


def subject_record(subject_id, school_classes_ids, month_index):
    result_date = TODAY + relativedelta(months=month_index)
    first_date = datetime(result_date.year, result_date.month, 1).date()
    last_date = first_date + relativedelta(months=+1, days=-1)
    school_students = Person.query.filter(
        Person.school_class_id.in_(school_classes_ids)
    ).order_by(Person.last_name, Person.first_name).all()
    subject_records = SchoolLessonJournal.query.filter(
        SchoolLessonJournal.date >= first_date,
        SchoolLessonJournal.date <= last_date,
        SchoolLessonJournal.subject_id == subject_id,
        SchoolLessonJournal.school_class_id.in_(school_classes_ids)
    ).all()
    dates_topic_set = set()
    record_dict = {f"{student.last_name} {student.first_name}": {} for student in school_students}

    for record in subject_records:
        date_string = f"{record.date:%d.%m}"
        topic = record.grade_type if record.grade_type else record.lesson.lesson_topic
        dates_topic_set.add((date_string, topic))
        student_name = f"{record.student.last_name} {record.student.first_name}"
        if record.student in school_students:
            record_dict[student_name][(date_string, topic)] = {
                "grade": record.grade,
                "comment": record.lesson_comment
            }
    subject_lessons = Lesson.query.filter(
        Lesson.date >= first_date,
        Lesson.date <= last_date,
        Lesson.subject_id == subject_id,
        Lesson.school_classes.any(SchoolClass.id.in_(school_classes_ids)),
        Lesson.lesson_completed
    ).all()
    for lesson in subject_lessons:
        date_string = f"{lesson.date:%d.%m}"
        topic = lesson.lesson_topic
        dates_topic_set.add((date_string, topic))

    dates_topic = sorted(list(dates_topic_set))

    return record_dict, dates_topic


def calc_month_index(date):
    date1 = date.replace(day=1)
    date2 = TODAY.replace(day=1)

    return relativedelta(date1, date2).months


def student_record(student, month_index):
    result_date = TODAY + relativedelta(months=month_index)
    first_date = datetime(result_date.year, result_date.month, 1).date()
    last_date = first_date + relativedelta(months=+1, days=-1)
    student_records = SchoolLessonJournal.query.filter(
        SchoolLessonJournal.date >= first_date,
        SchoolLessonJournal.date <= last_date,
        SchoolLessonJournal.student_id == student.id
    ).all()
    student_subjects = Subject.query.filter(
      Subject.subject_type.has(SubjectType.name == "school"),
      Subject.students.any(Person.id == student.id)
    ).order_by(Subject.name).all()
    subjects_dict = {subject.name: {} for subject in student_subjects}
    dates_grade_type_set = set()
    for record in student_records:
        subject = Subject.query.filter_by(id=record.subject_id).first()
        date_str = f'{record.date:%d.%m}'
        grade_type = record.grade_type if record.grade_type else record.lesson.lesson_topic
        dates_grade_type_set.add((date_str, grade_type))
        if subject.name in subjects_dict.keys():
            subjects_dict[subject.name][(date_str, grade_type)] = {"grade": record.grade,
                                                                   "comment": record.lesson_comment}
        else:
            subjects_dict[subject.name] = {(date_str, grade_type): {"grade": record.grade,
                                                                    "comment": record.lesson_comment}}

    dates_grade_type = sorted(list(dates_grade_type_set))

    return subjects_dict, dates_grade_type


def get_after_school_students(month_index):
    current_period = (TODAY.month, TODAY.year)
    result_date = TODAY + relativedelta(months=month_index)
    period = (result_date.month, result_date.year)
    first_date = datetime(period[1], period[0], 1).date()
    last_date = first_date + relativedelta(months=+1, days=-1)
    after_school_subscriptions = Subscription.query.filter(
        Subscription.subject_id == after_school_subject().id,
        Subscription.purchase_date >= first_date,
        Subscription.purchase_date <= last_date
    ).all()
    after_school_students = []
    for subscription in after_school_subscriptions:
        after_school_student = subscription.student
        if after_school_student not in after_school_students:
            format_student_info(after_school_student)
            after_school_student.shift = subscription.shift if subscription.shift else 10
            if period == current_period:
                activities = sorted([subject.name for subject in after_school_student.subjects
                                     if subject.subject_type.name not in ["school", "after_school"]])
                after_school_student.activities = activities
            if subscription.period == "month":
                after_school_student.attendance = ["месяц"]
            elif subscription.period == "day":
                after_school_student.attendance = [f"день ({subscription.purchase_date:%d.%m})"]
            else:
                after_school_student.attendance = [f"{subscription.period} ({subscription.purchase_date:%d.%m})"]
            after_school_students.append(after_school_student)
        else:
            student_ind = after_school_students.index(after_school_student)
            after_school_student = after_school_students[student_ind]
            if subscription.period == "day":
                after_school_student.attendance.append(f"день ({subscription.purchase_date:%d.%m})")
            else:
                after_school_student.attendance.append(f"{subscription.period} ({subscription.purchase_date:%d.%m})")
    after_school_students = sorted(after_school_students, key=lambda x: (x.shift, x.last_name, x.first_name))

    return after_school_students, period, current_period


def get_after_school_prices():
    after_school_prices = SubscriptionType.query.filter(SubscriptionType.period.isnot('')).all()
    price_types = []
    for price_type in after_school_prices:
        price_dict = {
            "id": price_type.id,
            "price": float(price_type.price)
        }
        if price_type.period == "месяц":
            price_dict["period"] = "month"
        elif price_type.period == "день":
            price_dict["period"] = "day"
        else:
            price_dict["period"] = "hour"
        price_types.append(price_dict)

    return price_types


def handle_after_school_adding(student_id, form, period):
    term = form.get("term")
    if term == "month":
        shift = int(form.get("shift"))
        purchase_date = datetime(period[1], period[0], 1).date()
    else:
        shift = None
        purchase_date = datetime.strptime(form.get("attendance_date"), '%d.%m.%Y').date()
    if term == "hour":
        hours = int(form.get("hours"))
        term = conjugate_hours(hours)
    subscription_type_id = int(form.get("subscription_type"))
    new_after_school_subscription = Subscription(
        subject_id=after_school_subject().id,
        student_id=student_id,
        subscription_type_id=subscription_type_id,
        purchase_date=purchase_date,
        shift=shift,
        period=term
    )

    return new_after_school_subscription


def finance_operation(person_id, amount, description, date=TODAY):
    new_operation = Finance(
        person_id=person_id,
        date=date,
        amount=amount,
        description=description
    )
    db.session.add(new_operation)
    db.session.flush()


def download_timetable(week):
    workbook = Workbook()
    sheet = workbook.active
    central = Alignment(horizontal="center")
    thin_border = Border(left=Side(style='thin'),
                         right=Side(style='thin'),
                         top=Side(style='thin'),
                         bottom=Side(style='thin'))
    thick_border = Border(left=Side(style='thick'),
                          right=Side(style='thick'),
                          top=Side(style='thick'),
                          bottom=Side(style='thick'))
    large_font = Font(bold=True, size=16)
    bold_font = Font(bold=True)

    date_start = get_date(0, week)
    date_end = get_date(4, week)
    dates = get_date_range(week)
    max_length = 1
    last_row_ind = 1

    school_classes = SchoolClass.query.order_by(SchoolClass.school_class).all()
    for school_class in school_classes:
        timetable = Lesson.query.filter(
            Lesson.date >= date_start,
            Lesson.date <= date_end,
            Lesson.school_classes.any(SchoolClass.id == school_class.id)
        ).order_by(Lesson.start_time).all()

        start_end_time = []

        sheet.cell(last_row_ind + 1, 1).value = school_class.school_name
        sheet.cell(last_row_ind + 1, 1).alignment = central
        sheet.cell(last_row_ind + 1, 1).border = thick_border
        sheet.cell(last_row_ind + 1, 1).font = large_font

        for ind, date in enumerate(dates, start=2):
            sheet.cell(last_row_ind, ind).value = DAYS_OF_WEEK[ind - 2]
            sheet.cell(last_row_ind, ind).alignment = central
            sheet.cell(last_row_ind, ind).border = thick_border
            sheet.cell(last_row_ind, ind).font = bold_font
            sheet.cell(last_row_ind + 1, ind).value = date
            sheet.cell(last_row_ind + 1, ind).alignment = central
            sheet.cell(last_row_ind + 1, ind).border = thick_border

        last_row_ind = sheet.max_row

        for lesson in timetable:
            lesson_time = f"{lesson.start_time:%H:%M}-{lesson.end_time:%H:%M}"
            lesson_date = f"{lesson.date:%d.%m}"
            col_ind = dates.index(lesson_date) + 2
            if lesson_time not in start_end_time:
                start_end_time.append(lesson_time)
                ind = len(start_end_time) + last_row_ind
                sheet.cell(ind, 1).value = lesson_time
                sheet.cell(ind, 1).border = thick_border
                sheet.cell(ind, 1).alignment = central
            row_ind = start_end_time.index(lesson_time) + last_row_ind + 1
            sheet.cell(row_ind, col_ind).value = lesson.subject.name
            color = lesson.room.color.replace('#', '')
            sheet.cell(row_ind, col_ind).fill = PatternFill(start_color=color, end_color=color, fill_type="solid")
            sheet.cell(row_ind, col_ind).alignment = central

        new_last_row_ind = sheet.max_row

        for col_ind in range(2, len(dates) + 2):
            for row_ind in range(last_row_ind + 1, new_last_row_ind + 1):
                current_cell = sheet.cell(row_ind, col_ind)
                current_cell.border = thin_border
                if current_cell.value:
                    if len(str(current_cell.value)) > max_length:
                        max_length = len(current_cell.value)

        last_row_ind = new_last_row_ind + 2

    for col in range(1, sheet.max_column + 1):
        adjusted_width = 12 if col == 1 else max_length + 2
        sheet.column_dimensions[get_column_letter(col)].width = adjusted_width

    return workbook, dates


def get_date_range(week):
    date_start = get_date(0, week)
    dates = [f"{date_start + timedelta(day):%d.%m}" for day in range(5)]
    return dates