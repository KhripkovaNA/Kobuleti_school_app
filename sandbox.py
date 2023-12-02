from app import app, db
from app.models import User, Person, Contact, Subject, Subscription, SubscriptionType, parent_child_table, Room, Lesson, \
    SchoolClass, SubjectType
from sqlalchemy.orm import class_mapper
from sqlalchemy import and_, or_
from datetime import datetime, timedelta

app.app_context().push()


def print_table(table_model):
    try:
        all_rows = table_model.query.all()

        if not all_rows:
            print(f"No rows found in the table: {table_model.__tablename__}")
            return

        mapper = class_mapper(table_model)
        columns = [column.key for column in mapper.columns]

        print(f"Table: {table_model.__tablename__}")
        print(columns)
        for row in all_rows:
            for column in columns:
                value = getattr(row, column)
                print(value, end='\t')
            print("")

    except Exception as e:
        print(f"Error fetching data: {str(e)}")


def print_parent_child_table():
    query = db.session.query(parent_child_table)
    rows = query.all()

    for row in rows:
        print(row)


def create_student(student_info):
    last_name = student_info["student"]["last_name"]
    first_name = student_info["student"]["first_name"]
    patronym = student_info["student"]["patronym"]
    dob = datetime.strptime(student_info["student"]["dob"], '%d.%m.%Y').date() \
        if student_info["student"]["dob"] else None
    status = student_info["student"]["status"]
    pause_date = datetime.strptime(student_info["student"]["pause_until"], '%d.%m.%Y').date() \
        if student_info["student"]["pause_until"] else None
    leaving_reason = student_info["student"]["leaving_reason"]

    new_student = Person(
        last_name=last_name,
        first_name=first_name,
        patronym=patronym,
        dob=dob,
        person_type="Ребенок",
        status=status,
        pause_until=pause_date,
        leaving_reason=leaving_reason
    )

    return new_student


def create_contact(student_info, i):
    telegram = student_info["contact"][i]["telegram"]
    phone = student_info["contact"][i]["phone"]
    other_contact = student_info["contact"][i]["other_contact"]

    new_contact = Contact(
        telegram=telegram,
        phone=phone,
        other_contact=other_contact
    )

    return new_contact


def create_parent(student_info, i):
    parent_last_name = student_info["parent"][i]["last_name"]
    parent_first_name = student_info["parent"][i]["first_name"]
    parent_patronym = student_info["parent"][i]["patronym"]

    new_parent = Person(
        last_name=parent_last_name,
        first_name=parent_first_name,
        patronym=parent_patronym,
        person_type="Взрослый"
    )

    return new_parent


def handle_contact_info(student_info, student, i):
    contact_select = student_info["contact_select"][i]
    relation_type = student_info["relation"][i]

    if relation_type == "Сам ребенок":
        contact = create_contact(student_info, i)
        db.session.add(contact)
        db.session.commit()

        student.contacts.append(contact)

    else:
        if contact_select == "Выбрать":
            parent_id = int(student_info["selected_contact"][i])
            parent = Person.query.filter_by(id=parent_id).first()
            contact = Contact.query.filter_by(person_id=parent_id).first()

        else:
            contact = create_contact(student_info, i)
            parent = create_parent(student_info, i)
            db.session.add(parent)
            db.session.add(contact)
            db.session.commit()

            parent.contacts.append(contact)
            parent.primary_contact = parent.id

        student.parents.append(parent)
        assign_relation_type(student_info, student, parent, i)

    if student_info['primary_contact'] == i:
        student.primary_contact = contact.person_id
    db.session.commit()


def assign_relation_type(student_info, student, parent, i):
    relation_type = student_info["relation"][i]

    if relation_type:
        relation_entry = parent_child_table.update().where(
            (parent_child_table.c.parent_id == parent.id) &
            (parent_child_table.c.child_id == student.id)
        ).values(relation=relation_type)

        db.session.execute(relation_entry)


def add_student(student_info):
    try:
        student = create_student(student_info)
        db.session.add(student)
        db.session.commit()

        contact_count = len(student_info["contact_select"])
        for i in range(1, contact_count + 1):
            handle_contact_info(student_info, student, i)
        print('Новый ученик добавлен в систему.')

    except Exception as e:
        db.session.rollback()
        print(f'Ошибка при добавлении ученика: {str(e)}')


def delete_record(table_model, record_id):
    record = table_model.query.filter_by(id=record_id).first()
    if record:
        db.session.delete(record)
        db.session.commit()


def create_teacher(teacher_info):
    teacher_last_name = teacher_info["teacher"]["last_name"]
    teacher_first_name = teacher_info["teacher"]["first_name"]
    teacher_patronym = teacher_info["teacher"]["patronym"]

    new_teacher = Person(
        last_name=teacher_last_name,
        first_name=teacher_first_name,
        patronym=teacher_patronym,
        person_type="Взрослый",
        teacher=True
    )

    return new_teacher


def create_teacher_contact(teacher_info):
    telegram = teacher_info["contact"]["telegram"]
    phone = teacher_info["contact"]["phone"]
    other_contact = teacher_info["contact"]["other_contact"]

    new_contact = Contact(
        telegram=telegram,
        phone=phone,
        other_contact=other_contact
    )

    return new_contact


def teachers_subjects(subjects_taught, teacher):
    for subj in subjects_taught:
        new_subj = Subject.query.filter_by(name=subj).first()
        teacher.subjects_taught.append(new_subj)
        db.session.commit()


def add_teacher(teacher_info):
    try:
        teacher = create_teacher(teacher_info)
        contact = create_teacher_contact(teacher_info)
        db.session.add(teacher)
        db.session.add(contact)
        db.session.commit()

        teacher.contacts.append(contact)
        teacher.primary_contact = teacher.id
        db.session.commit()
        if teacher_info["subjects"]:
            teachers_subjects(teacher_info["subjects"], teacher)

        print('Новый учитель добавлен в систему.')

    except Exception as e:
        db.session.rollback()
        print(f'Ошибка при добавлении учителя: {str(e)}')


def add_subject(subject):
    try:
        subject_name = subject["name"]
        subject_short_name = subject["short_name"]
        one_time_price = subject["one_time_price"]
        school_price = subject["school_price"]
        subject_type = subject["subject_type"]

        new_subject = Subject(
            name=subject_name,
            short_name=subject_short_name,
            one_time_price=one_time_price,
            school_price=school_price,
            subject_type=subject_type
        )

        db.session.add(new_subject)
        db.session.commit()

        print('Новое занятие добавлено в систему.')

    except Exception as e:
        db.session.rollback()
        print(f'Ошибка при добавлении занятия: {str(e)}')


def add_person(person):
    try:
        last_name = person["last_name"]
        first_name = person["first_name"]
        patronym = person["patronym"]
        dob = datetime.strptime(person["dob"], '%d.%m.%Y').date() if person["dob"] else None
        person_type = person["person_type"]
        status = person["status"]
        teacher = person["teacher"]
        pause_date = datetime.strptime(person["pause_until"], '%d.%m.%Y').date() if person["pause_until"] else None
        leaving_reason = person["leaving_reason"]

        new_person = Person(
            last_name=last_name,
            first_name=first_name,
            patronym=patronym,
            dob=dob,
            person_type=person_type,
            status=status,
            teacher=teacher,
            pause_until=pause_date,
            leaving_reason=leaving_reason
        )
        db.session.add(new_person)
        db.session.commit()

        print('Человек добавлен в систему.')

    except Exception as e:
        db.session.rollback()
        print(f'Ошибка при добавлении человека: {str(e)}')


def create_subscription(student_id, subject_id, subscription_type_id, lessons=8):
    try:
        new_subscription = Subscription(
            subject_id=subject_id,
            student_id=student_id,
            subscription_type_id=subscription_type_id,
            lessons_left=lessons
        )

        db.session.add(new_subscription)
        db.session.commit()

        print('Новый абонемент добавлен в систему.')

    except Exception as e:
        db.session.rollback()
        print(f'Ошибка при добавлении абонемента: {str(e)}')


def create_lesson(lesson_info):
    lesson_date = datetime.strptime(lesson_info['date'], '%d.%m.%Y').date()
    start_time = datetime.strptime(lesson_info['start_time'], '%H:%M').time()
    end_time = datetime.strptime(lesson_info['end_time'], '%H:%M').time()
    lesson_type = lesson_info['lesson_type']
    subject_id = lesson_info['subject_id']
    room_id = lesson_info['room_id']
    teacher_id = lesson_info['teacher_id']

    lesson = Lesson(
        date=lesson_date,
        start_time=start_time,
        end_time=end_time,
        lesson_type=lesson_type,
        room_id=room_id,
        subject_id=subject_id,
        teacher_id=teacher_id,
    )

    return lesson


def lesson_class(lesson, school_class):
    check_class = SchoolClass.query.filter_by(school_class=school_class).first()
    if check_class:
        lesson.school_classes.append(check_class)
    else:
        new_class = SchoolClass(school_class=school_class)
        db.session.add(new_class)
        db.session.commit()
        lesson.school_classes.append(new_class)
    db.session.commit()


def add_lesson(lesson_info):
    try:
        new_lesson = create_lesson(lesson_info)
        db.session.add(new_lesson)
        db.session.commit()
        if lesson_info['class']:
            for school_class in lesson_info['class']:
                lesson_class(new_lesson, school_class)
        print('Новый урок добавлен в систему.')

    except Exception as e:
        db.session.rollback()
        print(f'Ошибка при добавлении урока: {str(e)}')


# rooms = ["каб 1", "каб 2", "каб 3", "изо", "каб 5", "зал", "игровая", "кухня"]
#
# for room in rooms:
#     try:
#         new_room = Room(name=room)
#         db.session.add(new_room)
#         db.session.commit()
#
#         print('Новый кабинет добавлен в систему.')
#
#     except Exception as e:
#         db.session.rollback()
#         print(f'Ошибка при добавлении кабинета: {str(e)}')


days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

# existing_subjects = [f'{subject.id}\t{subject.name}\t{subject.short_name}' for subject in Subject.query.all()]
# print(*existing_subjects, sep='\n')
#
#
# existing_rooms = [str(room.id) + '\t' + room.name for room in Room.query.all()]
# print(*existing_rooms, sep='\n')


# existing_teachers = []
# for teacher in Person.query.filter_by(teacher=True).order_by(Person.last_name).all():
#     teacher_name = teacher.last_name + ' ' + teacher.first_name
#     teacher_subjects = ', '.join([subject.name for subject in teacher.subjects_taught.all()])
#     existing_teacher = str(teacher.id) + '\t' + teacher_name + '\t' + teacher_subjects
#     existing_teachers.append(existing_teacher)
#
# print(*existing_teachers, sep='\n')

# existing_subjects_types = [f'{subj_type.id}\t{subj_type.name}\t{subj_type.description}' for subj_type in SubjectType.query.all()]
# print(*existing_subjects_types, sep='\n')
#
#
# existing_classes = [str(cl.id) + '\t' + cl.school_name for cl in SchoolClass.query.all()]
# print(*existing_classes, sep='\n')

new_student_info = {
    "student": {
        "last_name": "Самойлова",
        "first_name": "Юлия",
        "patronym": "Михайловна",
        "dob": "10.08.2009",
        "status": "Клиент",
        "pause_until": "",
        "leaving_reason": ""
    },
    "parent": {
        1: {
            "last_name": "",
            "first_name": "",
            "patronym": ""
        }
    },
    "contact_select": {
        1: "Добавить"
    },
    "selected_contact": {
        1: ""
    },
    "contact": {
        1: {
            "telegram": "@samulya",
            "phone": "",
            "other_contact": ""
        }
    },
    "relation": {
        1: "Сам ребенок"
    },
    "primary_contact": 1
}

new_teacher_info = {
    "teacher": {
        "last_name": "Сильванская",
        "first_name": "Анна",
        "patronym": "Камильевна"
    },
    "contact": {
        "telegram": "",
        "phone": "",
        "other_contact": "Нет"
    },
    "subjects": ['3 класс']
}


def create_lesson_dict(lesson):
    start_time = (lesson.start_time.hour - 9) * 60 + lesson.start_time.minute
    end_time = (lesson.end_time.hour - 9) * 60 + lesson.end_time.minute

    if lesson.lesson_type == 'school':
        lesson_type = '-'.join([str(cl.school_class) for cl in lesson.school_classes.all()]) + ' класс'
    elif lesson.lesson_type == 'individual':
        lesson_type = 'индив'
    else:
        lesson_type = ''

    return {
        'time': f'{lesson.start_time.strftime("%H:%M")} - {lesson.end_time.strftime("%H:%M")}',
        'start_time': start_time,
        'end_time': end_time,
        'subject': lesson.subject_names,
        'teacher': lesson.teacher.first_name,
        'lesson_type': lesson_type,
    }


def get_date(day_of_week, week=0):
    today = datetime.now().date()
    day_of_week_date = today - timedelta(days=today.weekday()) + timedelta(days=day_of_week) + week * timedelta(weeks=1)
    return day_of_week_date


def day_lessons_list(day_room_lessons):
    lessons_for_day = []
    current_lesson = day_room_lessons[0]
    current_lesson.subject_names = [current_lesson.subject.short_name]

    for next_lesson in day_room_lessons[1:]:
        if (
                current_lesson.teacher.id == next_lesson.teacher.id
                and current_lesson.school_classes.all() == next_lesson.school_classes.all()
        ):
            current_lesson.subject_names.append(next_lesson.subject.short_name)
            current_lesson.end_time = next_lesson.end_time
        else:
            lessons_for_day.append(create_lesson_dict(current_lesson))
            next_lesson.subject_names = [next_lesson.subject.short_name]
            current_lesson = next_lesson

    lessons_for_day.append(create_lesson_dict(current_lesson))

    return lessons_for_day


def week_lessons_dict(week):
    rooms = Room.query.all()
    days_of_week = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"]
    week_lessons = {}

    for day, weekday in enumerate(days_of_week):
        lessons_date = get_date(week, day)
        lessons_date_str = lessons_date.strftime('%d.%m')
        day_lessons = {}
        for room in rooms:
            lessons_filtered = Lesson.query.filter_by(date=lessons_date, room_id=room.id).order_by(
                Lesson.start_time).all()
            day_lessons[room.name] = day_lessons_list(lessons_filtered) if lessons_filtered else []

        week_lessons[weekday] = (lessons_date_str, day_lessons)

    return week_lessons


# unique_rooms = Lesson.query.filter(Lesson.date == today).with_entities(Lesson.room_id).distinct().all()
# unique_rooms = [room[0] for room in unique_rooms]
# first_date = today - timedelta(days=2)
# last_date = today + timedelta(days=2)
# unique_rooms = (
#     db.session.query(Lesson.room_id)
#     .filter(Lesson.date >= first_date, Lesson.date <= last_date)
#     .distinct().all()
# )
# print([room[0] for room in unique_rooms])
# school_subjects = Subject.query.filter(~Subject.subject_types.any(name='school')).all()
# print(school_subjects)


def show_lesson(lesson):
    lesson_dict = {
        'id': lesson.id,
        'date': lesson.date.strftime("%d.%m"),
        'time': f'{lesson.start_time.strftime("%H:%M")} - {lesson.end_time.strftime("%H:%M")}',
        'room': Room.query.filter_by(id=lesson.room_id).first().name,
        'subject': Subject.query.filter_by(id=lesson.subject_id).first().name,
        'teacher': Person.query.filter_by(id=lesson.teacher_id).first().first_name,
        'lesson_type': SubjectType.query.filter_by(id=lesson.lesson_type_id).first().name,
        'classes': ', '.join([cl.school_name for cl in lesson.school_classes])
    }
    return lesson_dict


# new_lessons = copy_lessons(3, 'all', 1, 1, 'all', 0, 1)
# print(*[show_lesson(lesson) for lesson in new_lessons], sep='\n')


# Assuming new_date, start_time, end_time, room_id, teacher_id, lesson_type_id are defined

# Check if there are any lessons with the same date, overlapping time, and either the same room or the same teacher
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


#
# lesson = Lesson.query.filter_by(id=310).first()
# print(show_lesson(lesson))

new_lesson = {
    'date': datetime.strptime('27.11.2023', '%d.%m.%Y').date(),
    'start_time': datetime.strptime('09:10', '%H:%M').time(),
    'end_time': datetime.strptime('09:55', '%H:%M').time(),
    'school_classes': [5],
    'room_id': 1,
    'teacher_id': 23
}

# check_conflicting_lessons(new_lesson)
# some_lesson = Lesson.query.filter_by(id=7).first()
# print([cl.id for cl in some_lesson.school_classes])
# classes = [6, 7, 8, 9]
# filtered_lessons = Lesson.query.filter(Lesson.school_classes.any(SchoolClass.id.in_(classes))).all()
# print(*[show_lesson(lesson) for lesson in filtered_lessons], sep='\n')


def filter_lessons(copy_info):
    weekday = copy_info['lessons_day']
    week = int(copy_info['lessons_week'])
    new_week = int(copy_info['next_lessons_week'])
    subject_type = copy_info['subject_type']
    school_classes = copy_info['school_classes']
    room = copy_info['room']
    teacher = copy_info['teacher']

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


copy_inform = {
    'lessons_day': "all",
    'lessons_week': "0",
    'next_lessons_week': "1",
    'subject_type': "all",
    'school_classes': "all",
    'room': "all",
    'teacher': "all"
}
