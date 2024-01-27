from app.models import Person, Contact, parent_child_table, Employee, Subject, Subscription, Lesson, \
    SchoolClass, Room, SubjectType, SubscriptionType, student_lesson_attended_table, teacher_class_table
from datetime import datetime, timedelta
from app import db
from sqlalchemy import and_, or_
from typing import List, Dict, Any

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


def person_age(dob):
    age = TODAY.year - dob.year - ((TODAY.month, TODAY.day) < (dob.month, dob.day))
    return conjugate_years(age)


def create_student(form, student_type):
    last_name = form.get('last_name')
    first_name = form.get('first_name')
    patronym = form.get('patronym')
    dob = datetime.strptime(form.get('dob'), '%d.%m.%Y').date() \
        if form.get('dob') else None
    status = form.get('status')
    pause_date = datetime.strptime(form.get('pause_until'), '%d.%m.%Y').date() \
        if form.get('pause_until') else None
    leaving_reason = form.get('leaving_reason')
    person_type = CHILD if student_type == 'child' else ADULT

    student = Person(
        last_name=last_name,
        first_name=first_name,
        patronym=patronym,
        dob=dob,
        person_type=person_type,
        status=status,
        pause_until=pause_date,
        leaving_reason=leaving_reason
    )

    return student


def create_contact(form, i):
    telegram = form.get(f'telegram_{i}')
    phone = form.get(f'phone_{i}')
    other_contact = form.get(f'other_contact_{i}')

    contact = Contact(
        telegram=telegram,
        phone=phone,
        other_contact=other_contact
    )

    return contact


def create_parent(form, i):
    parent_last_name = form.get(f'parent_last_name_{i}')
    parent_first_name = form.get(f'parent_first_name_{i}')
    parent_patronym = form.get(f'parent_patronym_{i}')

    parent = Person(
        last_name=parent_last_name,
        first_name=parent_first_name,
        patronym=parent_patronym,
        person_type=ADULT
    )

    return parent


def handle_contact_info(form, student, i):
    contact_select = form.get(f'contact_select_{i}')
    relation_type = form.get(f'relation_{i}')
    student_contacts = Contact.query.filter_by(person_id=student.id).first()
    if relation_type == CHILD_SELF and not student_contacts:
        contact = create_contact(form, i)
        db.session.add(contact)
        db.session.flush()

        student.contacts.append(contact)

    elif relation_type != CHILD_SELF:
        if contact_select == CHOOSE:
            parent_id = int(form.get(f'selected_contact_{i}'))
            parent = Person.query.filter_by(id=parent_id).first()
            contact = Contact.query.filter_by(person_id=parent_id).first()

        else:
            contact = create_contact(form, i)
            parent = create_parent(form, i)
            db.session.add(parent)
            db.session.add(contact)
            db.session.flush()

            parent.contacts.append(contact)
            parent.primary_contact = parent.id

        student.parents.append(parent)
        assign_relation_type(form, student, parent, i)
    else:
        return

    if form.get('primary_contact') == f'contact_{i}':
        student.primary_contact = contact.person_id
    db.session.flush()


def assign_relation_type(form, student, parent, i):
    relation_type = form.get(f'relation_{i}')

    if relation_type == OTHER:
        relation_type = form.get(f'other_relation_{i}')

    relation_entry = parent_child_table.update().where(
        (parent_child_table.c.parent_id == parent.id) &
        (parent_child_table.c.child_id == student.id)
    ).values(relation=relation_type)

    db.session.execute(relation_entry)


def add_child(form):
    student = create_student(form, 'child')
    db.session.add(student)
    db.session.flush()

    contact_count = int(form.get('contact_count'))
    for i in range(1, contact_count + 1):
        handle_contact_info(form, student, i)

    return student


def add_adult(form):
    client_select = form.get('client_select')
    if client_select == CHOOSE:
        client_id = int(form.get('selected_client'))
        client = Person.query.filter_by(id=client_id).first()
        client.status = form.get('status')
        client.pause_date = datetime.strptime(form.get('pause_until'), '%d.%m.%Y').date() \
            if form.get('pause_until') else None
        client.leaving_reason = form.get('leaving_reason')

    else:
        client = create_student(form, 'adult')
        contact = create_contact(form, '')
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
            new_employee = Employee(
                person_id=employee.id,
                role=role.capitalize()
            )
            db.session.add(new_employee)
            if role == TEACHER:
                employee.teacher = True
                subject_ids = [int(subject_id) for subject_id in form.getlist('subjects')]
                subjects = Subject.query.filter(Subject.id.in_(subject_ids)).all()
                employee.subjects_taught.extend(subjects)

    return employee


def clients_data(person_type):
    if person_type == 'child':
        all_clients = Person.query.order_by(Person.last_name, Person.first_name).all()
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


def format_student_info(student):
    if student.dob:
        dob = student.dob
        student.birth_date = f'{dob:%d.%m.%Y}'
        student.age = person_age(dob)
    if student.pause_until:
        student.pause_date = f'{student.pause_until:%d.%m.%y}'

    if student.status == "Закрыт":
        student.status_info = f"{student.status} причина: {student.leaving_reason}"
    elif student.status == "Пауза":
        student.status_info = f"{student.status} до {student.pause_date}" if student.pause_date else student.status
    else:
        student.status_info = student.status
        if student.balance > 0:
            student.balance_plus = round(student.balance, 1)
        elif student.balance < 0:
            student.balance_minus = round(student.balance, 1)
    if student.children.all():
        format_children(student)


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

    school = [student.school_class.school_name] if student.school_class else []

    for subscription in student.subscriptions:
        subject = subscription.subject
        is_after_school = subject == after_school_subject()
        is_active = subscription.active

        if is_active:
            subscription_dict = {
                'subscription_id': subscription.id,
                'subject_name': subject.name,
                'lessons_left': subscription.lessons_left if not is_after_school else None,
                'end_date': f'{subscription.end_date:%d.%m.%Y}' if not is_after_school
                else MONTHS[subscription.purchase_date.month - 1]
            }
            if is_after_school:
                subscriptions.insert(0, subscription_dict)
                subscriptions_list.insert(0, f'{subject.name}({subscription_dict["end_date"]})')
            else:
                subscriptions.append(subscription_dict)
                subscriptions_list.append(f'{subject.name}({subscription.lessons_left})')
            subscriptions_set.add(subject.id)

    all_subjects_list = sorted(
        [(subject.name, subject.id) for subject in student.subjects if subject.subject_type.name != "school"])
    extra_subjects = sorted([subject.name for subject in student.subjects if
                             subject.id not in subscriptions_set and subject.subject_type.name != "school"])

    student.extra_subjects = extra_subjects
    student.subjects_info = ', '.join(school + subscriptions_list + extra_subjects)
    student.subscriptions_info = subscriptions
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

    return subject_id, lesson_id


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
    return new_subscription


def handle_student_edit(form, student):
    if 'form_student_submit' in form:
        student.last_name = form.get('last_name')
        student.first_name = form.get('first_name')
        student.patronym = form.get('patronym')
        student.dob = datetime.strptime(form.get('dob'), '%d.%m.%Y').date() \
            if form.get('dob') else None
        student.status = form.get('status')
        if student.status == "Закрыт":
            student.subjects = []
            student.subscriptions = []
        student.pause_date = datetime.strptime(form.get('pause_until'), '%d.%m.%Y').date() \
            if form.get('pause_until') else None
        student.leaving_reason = form.get('leaving_reason')
        db.session.flush()

    if 'form_main_contact_submit' in form:
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
        handle_contact_info(form, student, 'new')

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


def add_new_subject(form):
    subject_name = form.get("subject_name").capitalize()
    subject_short_name = form.get("subject_short_name").capitalize()
    subject_type_id = form.get("subject_type")
    description = form.get("description")

    if not form.get('no_subject_price'):
        subject_price = float(form.get('subject_price'))
        one_time_price = subject_price if int(subject_price) > 0 else None
    else:
        one_time_price = None
    if not form.get('no_subject_school_price'):
        subject_school_price = float(form.get('subject_school_price'))
        school_price = subject_school_price if int(subject_school_price) > 0 else None
    else:
        school_price = None

    new_subject = Subject(
        name=subject_name,
        short_name=subject_short_name,
        subject_type_id=subject_type_id,
        description=description,
        one_time_price=one_time_price,
        school_price=school_price
    )

    subscription_type_ids = [int(st) for st in form.getlist('subscription_types')]
    subscription_types = SubscriptionType.query.filter(SubscriptionType.id.in_(subscription_type_ids)).all()
    new_subject.subscription_types.extend(subscription_types)
    teacher_ids = [int(st) for st in form.getlist('teachers')]
    teachers = Person.query.filter(Person.id.in_(teacher_ids)).all()
    new_subject.teachers.extend(teachers)

    return new_subject


def format_subscription_types(subscription_types):
    types_of_subscription = []
    for subscription_type in subscription_types:
        if subscription_type.lessons:
            type_of_subscription = f"{subscription_type.lessons} занятий за {subscription_type.price:.0f} " \
                                   f"({subscription_type.duration} дней)"
            types_of_subscription.append((subscription_type.id, type_of_subscription))
        elif subscription_type.period:
            type_of_subscription = f"{subscription_type.price:.0f} за {subscription_type.period}"
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
            subscription.active = True if (cond1 or (cond2 and cond)) else False
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
            else:
                student.balance -= lesson_school_price if payment_option == 'after_school' \
                    else lesson_price

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
                student.balance += lesson_school_price if payment_option == 'after_school' else lesson_price
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


def show_lesson(subject_id, lesson_id):
    if int(lesson_id) == 0:
        last_lesson = Lesson.query.filter_by(subject_id=subject_id). \
            order_by(Lesson.date.desc(), Lesson.start_time.desc()).first()
        coming_lesson = Lesson.query.filter(Lesson.date >= TODAY,
                                            Lesson.subject_id == subject_id). \
            order_by(Lesson.date, Lesson.start_time).first()
        subject_lesson = coming_lesson if coming_lesson else last_lesson if last_lesson else None
    else:
        subject_lesson = Lesson.query.filter_by(id=int(lesson_id)).first()
    if subject_lesson:
        subject_lesson.students = get_lesson_students(subject_lesson)
        subject_lesson.prev, subject_lesson.next = prev_next_lessons(subject_lesson)

    return subject_lesson


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


def week_school_lessons_dict(week, school_classes, days_of_week):
    week_lessons = {}
    for day, weekday in enumerate(days_of_week):
        lessons_date = get_date(day, week)
        lessons_date_str = f'{lessons_date:%d.%m}'
        day_lessons = {}
        for school_class in school_classes:
            lessons_filtered = Lesson.query.filter(
                Lesson.lesson_type_id == 1,
                Lesson.date == lessons_date,
                Lesson.school_classes.any(SchoolClass.id == school_class.id)
            ).order_by(Lesson.start_time).all()
            day_lessons[school_class.school_name] = [create_school_lesson_dict(school_lesson)
                                                     for school_lesson in lessons_filtered]

        week_lessons[weekday] = (lessons_date_str, day_lessons)

    return week_lessons


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
    school_classes = [int(school_class) for school_class in form.getlist(f'school_classes_{i}')]
    teacher_id = int(form.get(f'teacher_{i}'))

    conflicting_lessons = check_conflicting_lessons(lesson_date, start_time, end_time,
                                                    school_classes, room_id, teacher_id)
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
            intersected_classes = conflict_classes.intersection(school_classes)
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

        school_classes = SchoolClass.query.filter(SchoolClass.id.in_(school_classes)).all()
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


def copy_lessons(filtered_lessons, week_diff):
    copied_lessons = []
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
            new_lesson.school_classes = SchoolClass.query.filter(SchoolClass.id.in_(classes)).all()
            copied_lessons.append(new_lesson)

        else:
            conflicts += 1

    return copied_lessons, conflicts


def format_school_classes(school_class):
    school_class.main_teacher = db.session.query(Person).join(teacher_class_table).filter(
        teacher_class_table.c.class_id == school_class.id,
        teacher_class_table.c.main_teacher).first()
    class_students = Person.query.filter_by(school_class_id=school_class.id).order_by(Person.last_name).all()
    for student in class_students:
        format_student_info(student)
        format_main_contact(student)
    school_class.class_students = class_students


def format_subject_classes(subject):
    classes = format_school_classes_names(subject.school_classes)
    return classes
