from app.models import Person, Contact, parent_child_table, Subject, Subscription, \
    Lesson, SchoolClass, Room, SubjectType, student_lesson_attended_table
from datetime import datetime, timedelta
from app import db
from sqlalchemy import and_, or_


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
        subject = subscription.subject
        if subject.subject_type_id != SubjectType.query.filter_by(name='after_school').first().id:
            end_date = subscription.purchase_date + timedelta(days=subscription.subscription_type.duration)
            subscription_dict = {
                'subject_name': subject.name,
                'lessons_left': subscription.lessons_left,
                'end_date': end_date.strftime('%d.%m.%Y')
            }
            subscriptions.append(subscription_dict)
            subscriptions_set.add(subject.name)

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


def check_payment_option(student, subject_id):
    today = datetime.now().date()
    first_of_month = today.replace(day=1)
    after_school = Subject.query.filter(Subject.subject_type.has(SubjectType.name == 'after_school')).first()
    subscription = Subscription.query.filter_by(student_id=student.id,
                                                subject_id=subject_id)\
        .order_by(Subscription.purchase_date).first()
    after_school_sub = Subscription.query.filter(Subscription.student_id == student.id,
                                                 Subscription.subject_id == after_school.id,
                                                 Subscription.purchase_date == first_of_month).all()
    student_balance = round(student.balance, 1)
    payment_option = {'balance': student_balance}
    if subscription and subject_id != after_school.id:
        exp_date = (subscription.purchase_date +
                    timedelta(days=subscription.subscription_type.duration)).strftime('%d.%m')
        payment_option['type'] = 'Абонемент'
        payment_option['exp_date'] = exp_date
        payment_option['lessons'] = subscription.lessons_left
    elif after_school_sub:
        payment_option['type'] = 'Продленка'
    else:
        payment_option['type'] = 'Разовое'

    return payment_option


def carry_out_lesson(form, subject, lesson):
    for key in form.keys():
        if key.startswith('attending_status_'):
            client_id = int(key[len('attending_status_'):])
            attending_client = Person.query.filter_by(id=client_id).first()
            payment_option = check_payment_option(attending_client, subject.id)
            lesson_price = subject.one_time_price
            lesson_school_price = subject.school_price if subject.school_price else lesson_price

            if form[key] != 'not_attend':
                if payment_option['type'] == 'Абонемент':
                    subscription = Subscription.query.filter_by(student_id=client_id,
                                                                subject_id=subject.id) \
                        .order_by(Subscription.purchase_date).first()
                    subscription.lessons_left -= 1
                else:
                    attending_client.balance -= lesson_school_price if payment_option['type'] == 'Продленка' \
                        else lesson_price
                lesson.students_attended.append(attending_client)
                attendance = student_lesson_attended_table.update().where(
                    (student_lesson_attended_table.c.student_id == attending_client.id) &
                    (student_lesson_attended_table.c.lesson_id == lesson.id)
                ).values(attending_status=form[key])
                db.session.execute(attendance)
        lesson.lesson_completed = True
        db.session.commit()


def undo_lesson(form, subject, lesson):
    for client in lesson.students_attended:
        payment_option = check_payment_option(client, subject.id)
        lesson_price = subject.one_time_price
        lesson_school_price = subject.school_price if subject.school_price else lesson_price

        attending_status = db.session.query(student_lesson_attended_table.c.attending_status).filter(
            student_lesson_attended_table.c.student_id == client.id,
            student_lesson_attended_table.c.lesson_id == lesson.id).scalar()

        if attending_status:
            if payment_option['type'] == 'Абонемент':
                subscription = Subscription.query.filter_by(student_id=client.id,
                                                            subject_id=subject.id) \
                    .order_by(Subscription.purchase_date).first()
                subscription.lessons_left += 1
            else:
                client.balance += lesson_school_price if payment_option['type'] == 'Продленка' else lesson_price
            lesson.students_attended.remove(client)

    lesson.lesson_completed = False
    db.session.commit()


def show_lesson(subject, param):
    today = datetime.now().date()
    if param < 0:
        subject_lessons = Lesson.query.filter(Lesson.date < today,
                                              Lesson.subject_id == subject.id). \
            order_by(Lesson.date.desc(), Lesson.start_time.desc()).all()
        order_param = abs(param) - 1
    else:
        subject_lessons = Lesson.query.filter(Lesson.date >= today,
                                              Lesson.subject_id == subject.id). \
            order_by(Lesson.date, Lesson.start_time).all()
        order_param = param

    subject_lesson = subject_lessons[order_param] if order_param < len(subject_lessons) else None
    if subject.students:
        for student in subject.students:
            payment_option = check_payment_option(student, subject.id)
            if payment_option['type'] == 'Абонемент':
                student.subscription_info = f'{payment_option["type"]}: {payment_option["lessons"]} ' \
                                            f'(до {payment_option["exp_date"]})'
            else:
                student.subscription_info = f'{payment_option["type"]}: {payment_option["balance"]}'
            if subject_lesson and subject_lesson.lesson_completed:
                attendance = db.session.query(student_lesson_attended_table.c.attending_status).filter(
                    student_lesson_attended_table.c.student_id == student.id,
                    student_lesson_attended_table.c.lesson_id == subject_lesson.id).scalar()
                student.attended = attendance if attendance else 'not_attend'
    return subject_lesson


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


def create_lesson_dict(lesson):
    start_time = (lesson.start_time.hour - 9) * 60 + lesson.start_time.minute
    end_time = (lesson.end_time.hour - 9) * 60 + lesson.end_time.minute

    if lesson.lesson_type.name == 'school':
        num_classes = [cl.school_name[:2].strip() for cl in lesson.school_classes
                       if (cl.school_name[0].isdigit() or cl.school_name[:2].isdigit())]
        classes = [cl.school_name for cl in lesson.school_classes
                   if not (cl.school_name[0].isdigit() or cl.school_name[:2].isdigit())]
        lesson_type = (
            f"{'-'.join(num_classes)} класс, {', '.join(classes)}"
            if (classes and num_classes)
            else f"{'-'.join(num_classes)} класс"
            if num_classes
            else f"{', '.join(classes)}"
        )
    elif lesson.lesson_type.name == 'individual':
        lesson_type = 'индив'
    else:
        lesson_type = ''

    return {
        'id': lesson.id,
        'time': f'{lesson.start_time.strftime("%H:%M")} - {lesson.end_time.strftime("%H:%M")}',
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
        'time': f'{lesson.start_time.strftime("%H:%M")} - {lesson.end_time.strftime("%H:%M")}',
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


def week_school_lessons_dict(week, school_classes, days_of_week):
    week_lessons = {}
    for day, weekday in enumerate(days_of_week):
        lessons_date = get_date(day, week)
        lessons_date_str = lessons_date.strftime('%d.%m')
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


def filter_lessons(form):
    weekday = form.get('lessons_day')
    week = int(form.get('lessons_week'))
    new_week = int(form.get('next_lessons_week'))
    subject_type = form.get('subject_type')
    school_classes = form.getlist('school_classes') if form.getlist('school_classes') else ["all"]
    room = form.get('room')
    teacher = form.get('teacher')

    if weekday == "all":
        start_date = get_date(0, week)
        end_date = get_date(6, week)
        query = Lesson.query.filter(
            Lesson.date >= start_date,
            Lesson.date <= end_date)
    else:
        lessons_date = get_date(int(weekday), week)
        query = Lesson.query.filter(Lesson.date == lessons_date)

    if room != "all":
        query = query.filter(Lesson.room_id == int(room))
    if subject_type != "all":
        query = query.filter(Lesson.lesson_type_id == int(subject_type))
    if 'all' not in school_classes:
        classes = [int(cl) for cl in school_classes]
        query = query.filter(Lesson.school_classes.any(SchoolClass.id.in_(classes)))
    if teacher != "all":
        query = query.filter(Lesson.teacher_id == int(teacher))

    filtered_lessons = query.all()

    return filtered_lessons, new_week


def copy_lessons(filtered_lessons, new_week):
    copied_lessons = []
    conflicts = 0
    for lesson in filtered_lessons:
        date = lesson.date + timedelta(weeks=new_week)
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


