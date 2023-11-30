from app.models import Person, Contact, parent_child_table, Lesson, Room
from datetime import datetime, timedelta
from app import db


def create_student(form):
    last_name = form.get('last_name')
    first_name = form.get('first_name')
    patronym = form.get('patronym')
    dob = datetime.strptime(form.get('dob'), '%d.%m.%Y').date() \
        if form.get('dob') else None
    status = form.get('status')
    pause_date = datetime.strptime(form.get('pause_until'), '%d.%m.%Y').date() \
        if form.get('pause_until') else None
    leaving_reason = form.get('leaving_reason')

    student = Person(
        last_name=last_name,
        first_name=first_name,
        patronym=patronym,
        dob=dob,
        person_type="Ребенок",
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
        person_type="Взрослый"
    )

    return parent


def handle_contact_info(form, student, i):
    contact_select = form.get(f'contact_select_{i}')
    relation_type = form.get(f'relation_{i}')

    if relation_type == "Сам ребенок":
        contact = create_contact(form, i)
        db.session.add(contact)
        db.session.commit()

        student.contacts.append(contact)

    else:
        if contact_select == "Выбрать":
            parent_id = int(form.get(f'selected_contact_{i}'))
            parent = Person.query.filter_by(id=parent_id).first()
            contact = Contact.query.filter_by(person_id=parent_id).first()

        else:
            contact = create_contact(form, i)
            parent = create_parent(form, i)
            db.session.add(parent)
            db.session.add(contact)
            db.session.commit()

            parent.contacts.append(contact)
            parent.primary_contact = parent.id

        student.parents.append(parent)
        assign_relation_type(form, student, parent, i)

    if form['primary_contact'] == f'contact_{i}':
        student.primary_contact = contact.person_id
    db.session.commit()


def assign_relation_type(form, student, parent, i):
    relation_type = form.get(f'relation_{i}')

    if relation_type == "Другое":
        relation_type = form.get(f'other_relation_{i}')

    relation_entry = parent_child_table.update().where(
        (parent_child_table.c.parent_id == parent.id) &
        (parent_child_table.c.child_id == student.id)
    ).values(relation=relation_type)

    db.session.execute(relation_entry)


def format_student_info(student):
    if student.dob:
        student.birth_date = student.dob.strftime('%d.%m.%Y')
    if student.pause_until:
        student.pause_date = student.pause_until.strftime('%d.%m.%Y')

    if student.status == "Закрыт":
        student.status_info = f"{student.status} причина: {student.leaving_reason}"
    elif student.status == "Пауза":
        student.status_info = f"{student.status} до {student.pause_date}"
    else:
        student.status_info = student.status


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
            student.main_contact.type = "Сам ребенок"
        else:
            student.type = "Сам ребенок"
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


def format_subjects_and_subscriptions(student):
    subscriptions = []
    subscriptions_set = set()

    for subscription in student.subscriptions.all():
        subject_name = subscription.subject.name
        end_date = subscription.purchase_date + timedelta(days=subscription.subscription_type.duration)
        subscription_dict = {
            'subject_name': subject_name,
            'lessons_left': subscription.lessons_left,
            'end_date': end_date.strftime('%d.%m.%Y')
        }
        subscriptions.append(subscription_dict)
        subscriptions_set.add(subject_name)

    student.subjects_info = [subject.name for subject in student.subjects.all()
                             if subject.name not in subscriptions_set]
    student.subscriptions_info = subscriptions


def basic_student_info(student):
    format_student_info(student)
    format_main_contact(student)
    format_subjects_and_subscriptions(student)


def extensive_student_info(student):
    format_student_info(student)
    format_all_contacts(student)
    format_subjects_and_subscriptions(student)


def clients_data():
    all_clients = Person.query.order_by(Person.last_name).all()
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


def create_lesson(form):
    lesson_date = datetime.strptime(form.get('lesson_date'), '%d.%m.%Y').date()
    lesson_time = datetime.strptime(form.get('lesson_time'), '%H:%M').time()
    subject_id = form.get('subject')
    room_id = form.get('room')
    teacher_id = form.get('teacher')

    lesson = Lesson(
        date=lesson_date,
        time=lesson_time,
        room_id=room_id,
        subject_id=subject_id,
        teacher_id=teacher_id
    )

    return lesson


def create_lesson_dict(lesson):
    start_time = (lesson.start_time.hour - 9) * 60 + lesson.start_time.minute
    end_time = (lesson.end_time.hour - 9) * 60 + lesson.end_time.minute

    if lesson.lesson_type.name == 'school':
        num_classes = [cl.school_name for cl in lesson.school_classes if cl.school_class]
        classes = [cl.school_name for cl in lesson.school_classes if not cl.school_class]
        lesson_type = (
            f"{'-'.join(num_classes)} класс, {', '.join(classes)}"
            if (classes and num_classes)
            else f"{'-'.join(num_classes)} класс"
            if num_classes
            else f"{', '.join(classes)}"
        )
    elif lesson.lesson_type.name == 'individual':
        lesson_type = 'индив'
    elif lesson.lesson_type.name == 'group':
        lesson_type = 'груп'
    else:
        lesson_type = ''

    return {
        'time': f'{lesson.start_time.strftime("%H:%M")} - {lesson.end_time.strftime("%H:%M")}',
        'start_time': start_time,
        'end_time': end_time,
        'subject': lesson.subject_names,
        'teacher': lesson.teacher.first_name,
        'color': lesson.teacher.color,
        'lesson_type': lesson_type,
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
    today = datetime.now().date()
    day_of_week_date = today - timedelta(days=today.weekday()) + timedelta(days=day_of_week) + week*timedelta(weeks=1)
    return day_of_week_date


def week_lessons_dict(week, rooms, days_of_week):
    week_lessons = {}
    for day, weekday in enumerate(days_of_week):
        lessons_date = get_date(day, week)
        lessons_date_str = lessons_date.strftime('%d.%m')
        day_lessons = {}
        for room in rooms:
            lessons_filtered = Lesson.query.filter_by(date=lessons_date, room_id=room.id).\
                order_by(Lesson.start_time).all()
            day_lessons[room.name] = day_lessons_list(lessons_filtered) if lessons_filtered else []

        week_lessons[weekday] = (lessons_date_str, day_lessons)

    return week_lessons

