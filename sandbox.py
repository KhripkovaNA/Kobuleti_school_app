from app import app, db
from app.models import User, Person, Contact, Subject, Subscription, SubscriptionType, \
    parent_child_table, Room, Lesson, SchoolClass, SubjectType, teacher_class_table, \
    student_lesson_registered_table, student_lesson_attended_table, student_subject_table, \
    teacher_subject_table, subscription_types_table, class_lesson_table, Employee
from sqlalchemy.orm import class_mapper
from sqlalchemy import and_, or_
from datetime import datetime, timedelta
from app.app_functions import clients_data, conjugate_years


app.app_context().push()

days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]


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


def print_association_table(table):
    query = db.session.query(table)
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
        subject_type_id = subject["subject_type_id"]

        new_subject = Subject(
            name=subject_name,
            short_name=subject_short_name,
            one_time_price=one_time_price,
            school_price=school_price,
            subject_type_id=subject_type_id
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


def print_subjects():
    existing_subjects = [f'{subject.id}\t{subject.name}\t{subject.short_name}\t{subject.subject_type.description}' +
                         '\tабонемент ' + ('+' if subject.subscription_types.all() else '-')
                         for subject in Subject.query.all()]
    print(*existing_subjects, sep='\n')


def print_rooms():
    existing_rooms = [str(room.id) + '\t' + room.name for room in Room.query.all()]
    print(*existing_rooms, sep='\n')


def print_teachers():
    existing_teachers = []
    for teacher in Person.query.filter_by(teacher=True).order_by(Person.last_name).all():
        teacher_name = teacher.last_name + ' ' + teacher.first_name
        teacher_subjects = ', '.join([subject.name for subject in teacher.subjects_taught.all()])
        existing_teacher = str(teacher.id) + '\t' + teacher_name + '\t' + teacher_subjects
        existing_teachers.append(existing_teacher)

    print(*existing_teachers, sep='\n')


def print_subscriptions():
    existing_subscriptions = []
    for subscr in Subscription.query.all():
        basic_info = f'{subscr.id}\t{subscr.student.last_name} {subscr.student.first_name}\t{subscr.subject.name}\t'
        lessons_left = f'{subscr.lessons_left} lessons' if subscr.lessons_left else ''
        date = 'finish: ' + \
               (subscr.purchase_date + timedelta(days=subscr.subscription_type.duration)).strftime('%d.%m.%y') \
            if subscr.subscription_type.duration else 'start: ' + subscr.purchase_date.strftime('%d.%m.%y')
        subscr_info = basic_info + '\t' + lessons_left + '\t' + date + '\t' + str(subscr.active)
        existing_subscriptions.append(subscr_info)

    print(*existing_subscriptions, sep='\n')


def print_subjects_types():
    existing_subjects_types = [f'{subj_type.id}\t{subj_type.name}\t{subj_type.description}' for subj_type in SubjectType.query.all()]
    print(*existing_subjects_types, sep='\n')


def print_classes():
    existing_classes = [str(cl.id) + '\t' + cl.school_name for cl in SchoolClass.query.all()]
    print(*existing_classes, sep='\n')


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


def create_school_lesson_dict(lesson):
    start_time = (lesson.start_time.hour - 9) * 60 + lesson.start_time.minute
    end_time = (lesson.end_time.hour - 9) * 60 + lesson.end_time.minute
    return {
        'time': f'{lesson.start_time.strftime("%H:%M")} - {lesson.end_time.strftime("%H:%M")}',
        'start_time': start_time,
        'end_time': end_time,
        'subject': lesson.subject.short_name,
        'teacher': lesson.teacher.first_name,
        'room': lesson.room.name,
        'room_color': lesson.room.color
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


def week_school_lessons_dict(week):
    school_classes = SchoolClass.query.all()
    days_of_week = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница"]
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


new_student_info = {
    "student": {
        "last_name": "Никитина",
        "first_name": "Анастасия",
        "patronym": "Константиновна",
        "dob": "11.07.2015",
        "status": "Клиент",
        "pause_until": "",
        "leaving_reason": ""
    },
    "parent": {
        1: {
            "last_name": "Никитина",
            "first_name": "Марина",
            "patronym": "Васильевна"
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
            "telegram": "",
            "phone": "+79161189355",
            "other_contact": ""
        }
    },
    "relation": {
        1: "Мама"
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

new_subject = {
    "name": "Музыка",
    "short_name": "Музыка",
    "one_time_price": 50,
    "school_price": None,
    "subject_type_id": 3
}

new_lesson = {
    'date': datetime.strptime('27.11.2023', '%d.%m.%Y').date(),
    'start_time': datetime.strptime('09:10', '%H:%M').time(),
    'end_time': datetime.strptime('09:55', '%H:%M').time(),
    'school_classes': [5],
    'room_id': 1,
    'teacher_id': 23
}

copy_inform = {
    'lessons_day': "all",
    'lessons_week': "0",
    'next_lessons_week': "1",
    'subject_type': "1",
    'school_classes': "all",
    'room': "all",
    'teacher': "all"
}

first_grade_list = [
    {'student': {'last_name': 'Казанцева', 'first_name': 'Вероника', 'patronym': 'Алексеевна', 'dob': '14.03.2016', 'status': 'Клиент', 'pause_until': '', 'leaving_reason': ''}, 'parent': {1: {'last_name': 'Казанцева', 'first_name': 'Анастасия', 'patronym': 'Юрьевна'}, 2: {'last_name': 'Казанцев', 'first_name': 'Алексей', 'patronym': 'Николаевич'}}, 'contact_select': {1: 'Выбрать', 2: 'Добавить'}, 'selected_contact': {1: '34', 2: ''}, 'contact': {1: {'telegram': '', 'phone': '79120121035', 'other_contact': ''}, 2: {'telegram': '', 'phone': '995555973320', 'other_contact': ''}}, 'relation': {1: 'Мама', 2: 'Папа'}, 'primary_contact': 1},
    {'student': {'last_name': 'Бекиров', 'first_name': 'Илья', 'patronym': 'Павлович', 'dob': '04.10.2016', 'status': 'Клиент', 'pause_until': '', 'leaving_reason': ''}, 'parent': {1: {'last_name': 'Бекирова', 'first_name': 'Дарья', 'patronym': 'Юрьевна'}, 2: {'last_name': 'Бекиров', 'first_name': 'Павел', 'patronym': 'Смайлович'}}, 'contact_select': {1: 'Добавить', 2: 'Добавить'}, 'selected_contact': {1: '', 2: ''}, 'contact': {1: {'telegram': '', 'phone': '', 'other_contact': 'Нет'}, 2: {'telegram': '', 'phone': '595 124 799', 'other_contact': ''}}, 'relation': {1: 'Мама', 2: 'Папа'}, 'primary_contact': 1},
    {'student': {'last_name': 'Железняк', 'first_name': 'Полина', 'patronym': 'Николаевна', 'dob': '07.09.2016', 'status': 'Клиент', 'pause_until': '', 'leaving_reason': ''}, 'parent': {1: {'last_name': 'Кириллина', 'first_name': 'Наталия', 'patronym': 'Сергеевна'}, 2: {'last_name': 'Железняк', 'first_name': 'Николай', 'patronym': 'Валерьевич'}}, 'contact_select': {1: 'Добавить', 2: 'Добавить'}, 'selected_contact': {1: '', 2: ''}, 'contact': {1: {'telegram': '', 'phone': '', 'other_contact': 'Нет'}, 2: {'telegram': '', 'phone': '995 555 182 656', 'other_contact': '7 951 686 27 12'}}, 'relation': {1: 'Мама', 2: 'Папа'}, 'primary_contact': 1},
    {'student': {'last_name': 'Гросман', 'first_name': 'Светлана', 'patronym': 'Георгиевна', 'dob': '13.11.2016', 'status': 'Клиент', 'pause_until': '', 'leaving_reason': ''}, 'parent': {1: {'last_name': 'Гросман', 'first_name': 'Екатерина', 'patronym': 'Владимировна'}, 2: {'last_name': 'Гросман', 'first_name': 'Георгий', 'patronym': 'Сергеевич'}}, 'contact_select': {1: 'Добавить', 2: 'Добавить'}, 'selected_contact': {1: '', 2: ''}, 'contact': {1: {'telegram': '', 'phone': '', 'other_contact': 'Нет'}, 2: {'telegram': '', 'phone': '995 595 071 893, ', 'other_contact': '7 988 990 73 45'}}, 'relation': {1: 'Мама', 2: 'Папа'}, 'primary_contact': 1},
    {'student': {'last_name': 'Москаленко', 'first_name': 'Лев', 'patronym': 'Юльевич', 'dob': None, 'status': 'Клиент', 'pause_until': '', 'leaving_reason': ''}, 'parent': {1: {'last_name': 'Москаленко', 'first_name': 'Мария', 'patronym': 'Семеновна'}, 2: {'last_name': 'Москаленко', 'first_name': 'Юлий', 'patronym': 'Владимирович'}}, 'contact_select': {1: 'Добавить', 2: 'Добавить'}, 'selected_contact': {1: '', 2: ''}, 'contact': {1: {'telegram': '', 'phone': '995 555 561 384', 'other_contact': '7 916 707 45 93'}, 2: {'telegram': '', 'phone': '9 995 555 560 183', 'other_contact': '7 916 507 19 71'}}, 'relation': {1: 'Мама', 2: 'Папа'}, 'primary_contact': 1},
    {'student': {'last_name': 'Авдеев', 'first_name': 'Дмитрий', 'patronym': 'Иванович', 'dob': '24.04.2017', 'status': 'Клиент', 'pause_until': '', 'leaving_reason': ''}, 'parent': {1: {'last_name': 'Авдеева', 'first_name': 'Ольга', 'patronym': 'Юрьевна'}, 2: {'last_name': 'Авдеев', 'first_name': 'Иван', 'patronym': 'Дмитриевич'}}, 'contact_select': {1: 'Добавить', 2: 'Добавить'}, 'selected_contact': {1: '', 2: ''}, 'contact': {1: {'telegram': '', 'phone': '995 551 026 306', 'other_contact': ''}, 2: {'telegram': '', 'phone': '', 'other_contact': 'Нет'}}, 'relation': {1: 'Мама', 2: 'Папа'}, 'primary_contact': 1},
    {'student': {'last_name': 'Трифонов', 'first_name': 'Матвей', 'patronym': '', 'dob': '23.05.2017', 'status': 'Клиент', 'pause_until': '', 'leaving_reason': ''}, 'parent': {1: {'last_name': 'Ковалева', 'first_name': 'Ирина', 'patronym': 'Андреевна'}, 2: {'last_name': 'Трифонов', 'first_name': 'Никита', 'patronym': 'Сергеевич'}}, 'contact_select': {1: 'Добавить', 2: 'Добавить'}, 'selected_contact': {1: '', 2: ''}, 'contact': {1: {'telegram': '', 'phone': '995595022159', 'other_contact': ''}, 2: {'telegram': '', 'phone': '995599120475', 'other_contact': ''}}, 'relation': {1: 'Мама', 2: 'Папа'}, 'primary_contact': 1},
    {'student': {'last_name': 'Гришин', 'first_name': 'Алексей', 'patronym': 'Сергеевич', 'dob': None, 'status': 'Клиент', 'pause_until': '', 'leaving_reason': ''}, 'parent': {1: {'last_name': 'Гришин', 'first_name': 'Сергей', 'patronym': 'Сергеевич'}, 2: {'last_name': 'гришина', 'first_name': 'Екатерина', 'patronym': 'Сергеевна'}}, 'contact_select': {1: 'Добавить', 2: 'Добавить'}, 'selected_contact': {1: '', 2: ''}, 'contact': {1: {'telegram': '', 'phone': '', 'other_contact': 'Нет'}, 2: {'telegram': '', 'phone': '', 'other_contact': 'Нет'}}, 'relation': {1: 'Мама', 2: 'Папа'}, 'primary_contact': 1},
    {'student': {'last_name': 'Шаповалова', 'first_name': 'Алина', 'patronym': 'Олеговна', 'dob': '12.11.2016', 'status': 'Клиент', 'pause_until': '', 'leaving_reason': ''}, 'parent': {1: {'last_name': 'Хрипкова', 'first_name': 'Наталья', 'patronym': 'Александровна'}, 2: {'last_name': 'Шаповалов', 'first_name': 'Олег', 'patronym': 'Вячеславович'}}, 'contact_select': {1: 'Добавить', 2: 'Добавить'}, 'selected_contact': {1: '', 2: ''}, 'contact': {1: {'telegram': '', 'phone': '7 916 295 62 74', 'other_contact': ''}, 2: {'telegram': '', 'phone': '7 916 903 97 42', 'other_contact': ''}}, 'relation': {1: 'Мама', 2: 'Папа'}, 'primary_contact': 1}
]


second_grade_list = [
    {'student': {'last_name': 'Зайцева', 'first_name': 'Кира', 'patronym': 'Владимировна', 'dob': '18.03.2016', 'status': 'Клиент', 'pause_until': '', 'leaving_reason': ''}, 'parent': {1: {'last_name': 'Зайцева', 'first_name': 'Елена', 'patronym': 'Владиславовна'}}, 'contact_select': {1: 'Добавить'}, 'selected_contact': {1: ''}, 'contact': {1: {'telegram': '', 'phone': '599012840', 'other_contact': ''}}, 'relation': {1: 'Мама'}, 'primary_contact': 1},
    {'student': {'last_name': 'Миронов', 'first_name': 'Андрей', 'patronym': 'Антонович', 'dob': None, 'status': 'Клиент', 'pause_until': '', 'leaving_reason': ''}, 'parent': {1: {'last_name': 'Миронов', 'first_name': 'Антон', 'patronym': ''}}, 'contact_select': {1: 'Добавить'}, 'selected_contact': {1: ''}, 'contact': {1: {'telegram': '', 'phone': '', 'other_contact': 'Нет'}}, 'relation': {1: 'Папа'}, 'primary_contact': 1},
    {'student': {'last_name': 'Бекиров', 'first_name': 'Кирилл', 'patronym': 'Павлович', 'dob': '04.05.2015', 'status': 'Клиент', 'pause_until': '', 'leaving_reason': ''}, 'parent': {1: {'last_name': 'Бекирова', 'first_name': 'Дарья', 'patronym': 'Юрьевна'}, 2: {'last_name': 'Бекиров', 'first_name': 'Павел', 'patronym': 'Смайлович'}}, 'contact_select': {1: 'Выбрать', 2: 'Выбрать'}, 'selected_contact': {1: '50', 2: '51'}, 'contact': {1: {'telegram': '', 'phone': '', 'other_contact': 'Нет'}, 2: {'telegram': '', 'phone': '595 124 799', 'other_contact': ''}}, 'relation': {1: 'Мама', 2: 'Папа'}, 'primary_contact': 2},
    {'student': {'last_name': 'Заставный', 'first_name': 'Савелий', 'patronym': 'Дмитриевич', 'dob': '30.01.2015', 'status': 'Клиент', 'pause_until': '', 'leaving_reason': ''}, 'parent': {1: {'last_name': 'Заставная', 'first_name': 'Наталья', 'patronym': 'Сергеевна'}, 2: {'last_name': 'Заставный', 'first_name': 'Дмитрий', 'patronym': 'Владимирович'}}, 'contact_select': {1: 'Добавить', 2: 'Добавить'}, 'selected_contact': {1: '', 2: ''}, 'contact': {1: {'telegram': '', 'phone': '', 'other_contact': 'Нет'}, 2: {'telegram': '', 'phone': '892 64229112', 'other_contact': ''}}, 'relation': {1: 'Мама', 2: 'Папа'}, 'primary_contact': 2},
    {'student': {'last_name': 'Земцова', 'first_name': 'Виктория', 'patronym': 'Олеговна', 'dob': '18.03.2015', 'status': 'Клиент', 'pause_until': '', 'leaving_reason': ''}, 'parent': {1: {'last_name': 'Земцова', 'first_name': 'Алена', 'patronym': 'Алексеевна'}, 2: {'last_name': 'Земцов', 'first_name': 'Олег', 'patronym': 'Олександрович'}}, 'contact_select': {1: 'Добавить', 2: 'Добавить'}, 'selected_contact': {1: '', 2: ''}, 'contact': {1: {'telegram': '', 'phone': '995 599 521 026', 'other_contact': ''}, 2: {'telegram': '', 'phone': '995 599 066 651', 'other_contact': ''}}, 'relation': {1: 'Мама', 2: 'Папа'}, 'primary_contact': 1}
]

third_grade_list = [
    {'student': {'last_name': 'Калашникова', 'first_name': 'Анна', 'patronym': 'Александровна', 'dob': '14.11.2015', 'status': 'Клиент', 'pause_until': '', 'leaving_reason': ''}, 'parent': {1: {'last_name': 'Калашникова', 'first_name': 'Варвара', 'patronym': 'Викторовна'}, 2: {'last_name': 'Калашников', 'first_name': 'Александр', 'patronym': 'Олегович'}}, 'contact_select': {1: 'Добавить', 2: 'Добавить'}, 'selected_contact': {1: '', 2: ''}, 'contact': {1: {'telegram': '', 'phone': '7 926 270 53 42', 'other_contact': ''}, 2: {'telegram': '', 'phone': '', 'other_contact': 'Нет'}}, 'relation': {1: 'Мама', 2: 'Папа'}, 'primary_contact': 1},
    {'student': {'last_name': 'Серяков', 'first_name': 'Михаил', 'patronym': 'Максимович', 'dob': '05.07.2014', 'status': 'Клиент', 'pause_until': '', 'leaving_reason': ''}, 'parent': {1: {'last_name': 'Молчанова', 'first_name': 'Русулана', 'patronym': 'Ивановна'}, 2: {'last_name': 'Серяков', 'first_name': 'Максим', 'patronym': 'Сергеевич'}}, 'contact_select': {1: 'Добавить', 2: 'Добавить'}, 'selected_contact': {1: '', 2: ''}, 'contact': {1: {'telegram': '', 'phone': '995 505 556 791', 'other_contact': ''}, 2: {'telegram': '', 'phone': '995 505 55 67 65', 'other_contact': ''}}, 'relation': {1: 'Мама', 2: 'Папа'}, 'primary_contact': 1},
    {'student': {'last_name': 'Калашников', 'first_name': 'Федор', 'patronym': 'Александрович', 'dob': '04.03.2014', 'status': 'Клиент', 'pause_until': '', 'leaving_reason': ''}, 'parent': {1: {'last_name': 'Калашникова', 'first_name': 'Варвара', 'patronym': 'Викторовна'}, 2: {'last_name': 'Калашников', 'first_name': 'Александр', 'patronym': 'Олегович'}}, 'contact_select': {1: 'Добавить', 2: 'Добавить'}, 'selected_contact': {1: '', 2: ''}, 'contact': {1: {'telegram': '', 'phone': '7 926 270 53 42', 'other_contact': ''}, 2: {'telegram': '', 'phone': '7 909 158 13 88', 'other_contact': ''}}, 'relation': {1: 'Мама', 2: 'Папа'}, 'primary_contact': 1},
    {'student': {'last_name': 'Полищук', 'first_name': 'Аделина', 'patronym': 'Евгеньевна', 'dob': '24.08.2014', 'status': 'Клиент', 'pause_until': '', 'leaving_reason': ''}, 'parent': {1: {'last_name': 'Полищук-Молодоженя', 'first_name': 'Татьяна', 'patronym': 'Романовна'}, 2: {'last_name': 'Полищук', 'first_name': 'Евгений', 'patronym': 'Витальевич'}}, 'contact_select': {1: 'Добавить', 2: 'Добавить'}, 'selected_contact': {1: '', 2: ''}, 'contact': {1: {'telegram': '', 'phone': '995593789646', 'other_contact': '79095647573'}, 2: {'telegram': '', 'phone': '995558669855', 'other_contact': ''}}, 'relation': {1: 'Мама', 2: 'Папа'}, 'primary_contact': 1},
    {'student': {'last_name': 'Платонов', 'first_name': 'Кирилл', 'patronym': 'Алексеевич', 'dob': '31.01.2014', 'status': 'Клиент', 'pause_until': '', 'leaving_reason': ''}, 'parent': {1: {'last_name': 'Платонова', 'first_name': 'Мария', 'patronym': 'Григорьевна'}}, 'contact_select': {1: 'Добавить'}, 'selected_contact': {1: ''}, 'contact': {1: {'telegram': '', 'phone': '995557135212', 'other_contact': ''}}, 'relation': {1: 'Мама'}, 'primary_contact': 1}
]

andrew = {'student': {'last_name': 'Гросман', 'first_name': 'Андрей', 'patronym': 'Георгиевич', 'dob': '29.09.2014', 'status': 'Клиент', 'pause_until': '', 'leaving_reason': ''}, 'parent': {1: {'last_name': 'Гросман', 'first_name': 'Екатерина', 'patronym': 'Владимировна'}, 2: {'last_name': 'Гросман', 'first_name': 'Георгий', 'patronym': 'Сергеевич'}}, 'contact_select': {1: 'Выбрать', 2: 'Выбрать'}, 'selected_contact': {1: '56', 2: '57'}, 'contact': {1: {'telegram': '', 'phone': '', 'other_contact': 'Нет'}, 2: {'telegram': '', 'phone': '995 595 07 18 93', 'other_contact': '7 988 990 73 45'}}, 'relation': {1: 'Мама', 2: 'Папа'}, 'primary_contact': 2}


fourth_grade_list = [
    {'student': {'last_name': 'Казанцева', 'first_name': 'Алисия', 'patronym': 'Алексеевна', 'dob': '23.11.2012', 'status': 'Клиент', 'pause_until': '', 'leaving_reason': ''}, 'parent': {1: {'last_name': 'Казанцева', 'first_name': 'Анастасия', 'patronym': 'Юрьевна'}, 2: {'last_name': 'Казанцев', 'first_name': 'Алексей', 'patronym': 'Николаевич'}}, 'contact_select': {1: 'Выбрать', 2: 'Выбрать'}, 'selected_contact': {1: '34', 2: '48'}, 'contact': {1: {'telegram': '', 'phone': '79120121035', 'other_contact': ''}, 2: {'telegram': '', 'phone': '79128703412', 'other_contact': '995555973320'}}, 'relation': {1: 'Мама', 2: 'Папа'}, 'primary_contact': 1},
    {'student': {'last_name': 'Чернина', 'first_name': 'Евгения', 'patronym': 'Вадимовна', 'dob': '11.11.2013', 'status': 'Клиент', 'pause_until': '', 'leaving_reason': ''}, 'parent': {1: {'last_name': 'Чернина', 'first_name': 'Вера', 'patronym': 'Алексеевна'}, 2: {'last_name': 'Чернин', 'first_name': 'Вадим', 'patronym': 'Борисович'}}, 'contact_select': {1: 'Добавить', 2: 'Добавить'}, 'selected_contact': {1: '', 2: ''}, 'contact': {1: {'telegram': '', 'phone': '595 420 847', 'other_contact': ''}, 2: {'telegram': '', 'phone': '595 082 114', 'other_contact': ''}}, 'relation': {1: 'Мама', 2: 'Папа'}, 'primary_contact': 1},
    {'student': {'last_name': 'Волковыский', 'first_name': 'Захар', 'patronym': 'Юрьевич', 'dob': '30.07.2013', 'status': 'Клиент', 'pause_until': '', 'leaving_reason': ''}, 'parent': {1: {'last_name': 'Лизина', 'first_name': 'Марина', 'patronym': 'Ростиславовна'}, 2: {'last_name': 'Волковыский', 'first_name': 'Юрий', 'patronym': 'Михайлович'}}, 'contact_select': {1: 'Выбрать', 2: 'Добавить'}, 'selected_contact': {1: '27', 2: ''}, 'contact': {1: {'telegram': '', 'phone': '995 595 082 057', 'other_contact': '7 904 631 47 42'}, 2: {'telegram': '', 'phone': '7 921 744 04 34', 'other_contact': '995 591 71 51 59'}}, 'relation': {1: 'Мама', 2: 'Папа'}, 'primary_contact': 1},
    {'student': {'last_name': 'Тришина', 'first_name': 'Милана', 'patronym': 'Денисова', 'dob': '05.07.2013', 'status': 'Клиент', 'pause_until': '', 'leaving_reason': ''}, 'parent': {1: {'last_name': 'Тришина', 'first_name': 'Яна', 'patronym': 'Николаевна'}, 2: {'last_name': 'Тришин', 'first_name': 'Денис', 'patronym': 'Игоревич'}}, 'contact_select': {1: 'Добавить', 2: 'Добавить'}, 'selected_contact': {1: '', 2: ''}, 'contact': {1: {'telegram': '', 'phone': '995591634486', 'other_contact': ''}, 2: {'telegram': '', 'phone': '995599061427', 'other_contact': ''}}, 'relation': {1: 'Мама', 2: 'Папа'}, 'primary_contact': 1},
    {'student': {'last_name': 'Полищук', 'first_name': 'Инна', 'patronym': 'Евгеньевна', 'dob': '22.04.2013', 'status': 'Клиент', 'pause_until': '', 'leaving_reason': ''}, 'parent': {1: {'last_name': 'Полищук-Молодоженя', 'first_name': 'Татьяна', 'patronym': 'Романовна'}, 2: {'last_name': 'Полищук', 'first_name': 'Евгений', 'patronym': 'Витальевич'}}, 'contact_select': {1: 'Выбрать', 2: 'Выбрать'}, 'selected_contact': {1: '91', 2: '92'}, 'contact': {1: {'telegram': '', 'phone': '995593789646', 'other_contact': '79095647573'}, 2: {'telegram': '', 'phone': '995558669855', 'other_contact': ''}}, 'relation': {1: 'Мама', 2: 'Папа'}, 'primary_contact': 1},
    {'student': {'last_name': 'Лушанкина', 'first_name': 'Владислава', 'patronym': 'Павловна', 'dob': '06.11.2014', 'status': 'Клиент', 'pause_until': '', 'leaving_reason': ''}, 'parent': {1: {'last_name': 'Лушанкина', 'first_name': 'Юлия', 'patronym': 'Юрьевна'}, 2: {'last_name': 'Лушанкин', 'first_name': 'Павел', 'patronym': 'Вячеславович'}}, 'contact_select': {1: 'Добавить', 2: 'Добавить'}, 'selected_contact': {1: '', 2: ''}, 'contact': {1: {'telegram': '', 'phone': '995 595 081 186', 'other_contact': ''}, 2: {'telegram': '', 'phone': '995 598 127 922 ', 'other_contact': ''}}, 'relation': {1: 'Мама', 2: 'Папа'}, 'primary_contact': 1}
]

petr = {'student': {'last_name': 'Ляшкевич', 'first_name': 'Петр', 'patronym': 'Константинович', 'dob': '22.02.2013', 'status': 'Клиент', 'pause_until': '', 'leaving_reason': ''}, 'parent': {1: {'last_name': 'Ляшкевич', 'first_name': 'Евгения', 'patronym': 'Валерьевна'}, 2: {'last_name': 'Ляшкевич', 'first_name': 'Константин', 'patronym': 'Владимирович'}}, 'contact_select': {1: 'Добавить', 2: 'Добавить'}, 'selected_contact': {1: '', 2: ''}, 'contact': {1: {'telegram': '', 'phone': '995 571 051 683', 'other_contact': ''}, 2: {'telegram': '', 'phone': '995 568 819 706', 'other_contact': ''}}, 'relation': {1: 'Мама', 2: 'Папа'}, 'primary_contact': 1}

sixth_grade_list = [
    {'student': {'last_name': 'Котова', 'first_name': 'Анна', 'patronym': 'Васильевна', 'dob': '25.06.2011', 'status': 'Клиент', 'pause_until': '', 'leaving_reason': ''}, 'parent': {1: {'last_name': 'Котова', 'first_name': 'Елена', 'patronym': 'Геннадьевна'}, 2: {'last_name': 'Котов', 'first_name': 'Василий', 'patronym': 'Александрович'}}, 'contact_select': {1: 'Добавить', 2: 'Добавить'}, 'selected_contact': {1: '', 2: ''}, 'contact': {1: {'telegram': '', 'phone': '8 916 969 62 45 ', 'other_contact': '995 555 33 40 79'}, 2: {'telegram': '', 'phone': '555 33 54 27 ', 'other_contact': ''}}, 'relation': {1: 'Мама', 2: 'Папа'}, 'primary_contact': 1},
    {'student': {'last_name': 'Гудкова', 'first_name': 'Ева', 'patronym': 'Сергеевна', 'dob': '02.03.2011', 'status': 'Клиент', 'pause_until': '', 'leaving_reason': ''}, 'parent': {1: {'last_name': 'Гудкова', 'first_name': 'Татьяна', 'patronym': 'Юрьевна'}, 2: {'last_name': 'Гудков', 'first_name': 'Сергей', 'patronym': 'Сергеевич'}}, 'contact_select': {1: 'Добавить', 2: 'Добавить'}, 'selected_contact': {1: '', 2: ''}, 'contact': {1: {'telegram': '', 'phone': '8 929 683 93 99', 'other_contact': ''}, 2: {'telegram': '', 'phone': '995599026049', 'other_contact': ''}}, 'relation': {1: 'Мама', 2: 'Папа'}, 'primary_contact': 1},
    {'student': {'last_name': 'Миронов', 'first_name': 'Лев', 'patronym': 'Антонович', 'dob': '24.04.2011', 'status': 'Клиент', 'pause_until': '', 'leaving_reason': ''}, 'parent': {1: {'last_name': 'Миронов', 'first_name': 'Антон', 'patronym': ''}}, 'contact_select': {1: 'Выбрать'}, 'selected_contact': {1: '73'}, 'contact': {1: {'telegram': '', 'phone': '', 'other_contact': 'Нет'}}, 'relation': {1: 'Папа'}, 'primary_contact': 1},
    {'student': {'last_name': 'Перова', 'first_name': 'Эва', 'patronym': '', 'dob': None, 'status': 'Клиент', 'pause_until': '', 'leaving_reason': ''}, 'parent': {1: {'last_name': 'Савойлайнен', 'first_name': 'Анна', 'patronym': 'Геннадьевна'}}, 'contact_select': {1: 'Добавить'}, 'selected_contact': {1: ''}, 'contact': {1: {'telegram': '', 'phone': '', 'other_contact': 'Нет'}}, 'relation': {1: 'Мама'}, 'primary_contact': 1},
    {'student': {'last_name': 'Ковалев', 'first_name': 'Данил', 'patronym': 'Андреевич', 'dob': '20.09.2011', 'status': 'Клиент', 'pause_until': '', 'leaving_reason': ''}, 'parent': {1: {'last_name': 'Ковалева', 'first_name': 'Ирина', 'patronym': 'Андреевна'}}, 'contact_select': {1: 'Выбрать'}, 'selected_contact': {1: '65'}, 'contact': {1: {'telegram': '', 'phone': '995595022159', 'other_contact': ''}}, 'relation': {1: 'Мама'}, 'primary_contact': 1},
    {'student': {'last_name': 'Козлова', 'first_name': 'Татьяна', 'patronym': 'Евгеньевна', 'dob': '24.01.2012', 'status': 'Клиент', 'pause_until': '', 'leaving_reason': ''}, 'parent': {1: {'last_name': 'Козлова', 'first_name': 'Наталья', 'patronym': 'Валерьевна'}, 2: {'last_name': 'Козлов', 'first_name': 'Евгений', 'patronym': 'Александрович'}}, 'contact_select': {1: 'Добавить', 2: 'Добавить'}, 'selected_contact': {1: '', 2: ''}, 'contact': {1: {'telegram': '', 'phone': '995555453279', 'other_contact': ''}, 2: {'telegram': '', 'phone': '79269566313', 'other_contact': ''}}, 'relation': {1: 'Мама', 2: 'Папа'}, 'primary_contact': 1},
    {'student': {'last_name': 'Семенова', 'first_name': 'Мария', 'patronym': 'Андреевна', 'dob': '17.06.2011', 'status': 'Клиент', 'pause_until': '', 'leaving_reason': ''}, 'parent': {1: {'last_name': 'Семенов', 'first_name': 'Андрей', 'patronym': 'Константинович'}}, 'contact_select': {1: 'Добавить'}, 'selected_contact': {1: ''}, 'contact': {1: {'telegram': '', 'phone': '', 'other_contact': 'Нет'}}, 'relation': {1: 'Папа'}, 'primary_contact': 1}
]

seventh_grade_list = [
    {'student': {'last_name': 'Ляшкевич', 'first_name': 'Элина', 'patronym': 'Константиновна', 'dob': '13.08.2010', 'status': 'Клиент', 'pause_until': '', 'leaving_reason': ''}, 'parent': {1: {'last_name': 'Ляшкевич', 'first_name': 'Евгения', 'patronym': 'Валерьевна'}, 2: {'last_name': 'Ляшкевич', 'first_name': 'Константин', 'patronym': 'Владимирович'}}, 'contact_select': {1: 'Выбрать', 2: 'Выбрать'}, 'selected_contact': {1: '110', 2: '111'}, 'contact': {1: {'telegram': '', 'phone': 'nan', 'other_contact': ''}, 2: {'telegram': '', 'phone': '995568816706', 'other_contact': ''}}, 'relation': {1: 'Мама', 2: 'Папа'}, 'primary_contact': 1},
    {'student': {'last_name': 'Куксинский', 'first_name': 'Платон', 'patronym': 'Дмитриевич', 'dob': '28.08.2010', 'status': 'Клиент', 'pause_until': '', 'leaving_reason': ''}, 'parent': {1: {'last_name': 'Ганичева', 'first_name': 'Марьяна', 'patronym': 'Петровна'}, 2: {'last_name': 'Куксинский', 'first_name': 'Дмитрий', 'patronym': 'Глебович'}}, 'contact_select': {1: 'Добавить', 2: 'Добавить'}, 'selected_contact': {1: '', 2: ''}, 'contact': {1: {'telegram': '', 'phone': '595 35 94 77', 'other_contact': ''}, 2: {'telegram': '', 'phone': '595 04 95 37', 'other_contact': ''}}, 'relation': {1: 'Мама', 2: 'Папа'}, 'primary_contact': 1},
    {'student': {'last_name': 'Федорова', 'first_name': 'Милана', 'patronym': 'Вадимовна', 'dob': None, 'status': 'Клиент', 'pause_until': '', 'leaving_reason': ''}, 'parent': {1: {'last_name': 'Федорова', 'first_name': 'Ксения', 'patronym': 'Александровна'}}, 'contact_select': {1: 'Добавить'}, 'selected_contact': {1: ''}, 'contact': {1: {'telegram': '', 'phone': 'nan', 'other_contact': ''}}, 'relation': {1: 'Мама'}, 'primary_contact': 1}
]

eighth_grade = {'student': {'last_name': 'Петручак', 'first_name': 'Владислав', 'patronym': 'Викторович', 'dob': '25.10.2009', 'status': 'Клиент', 'pause_until': '', 'leaving_reason': ''}, 'parent': {1: {'last_name': 'Петручак', 'first_name': 'Ольга', 'patronym': 'Евгеньевна'}, 2: {'last_name': 'Петручак', 'first_name': 'Виктор', 'patronym': 'Николаевич'}}, 'contact_select': {1: 'Добавить', 2: 'Добавить'}, 'selected_contact': {1: '', 2: ''}, 'contact': {1: {'telegram': '', 'phone': '995 593 45 27 80', 'other_contact': ''}, 2: {'telegram': '', 'phone': '995 593 45 52 87 ', 'other_contact': ''}}, 'relation': {1: 'Мама', 2: 'Папа'}, 'primary_contact': 1}

ninth_grade_list = [
    {'student': {'last_name': 'Давыдова', 'first_name': 'Ульяна', 'patronym': 'Ивановна', 'dob': '09.11.2008', 'status': 'Клиент', 'pause_until': '', 'leaving_reason': ''}, 'parent': {1: {'last_name': 'Давыдов', 'first_name': 'Иван', 'patronym': 'Дмитриевич'}}, 'contact_select': {1: 'Добавить'}, 'selected_contact': {1: ''}, 'contact': {1: {'telegram': '', 'phone': '995 599 019 679', 'other_contact': ''}}, 'relation': {1: 'Папа'}, 'primary_contact': 1},
    {'student': {'last_name': 'Ляшкевич', 'first_name': 'Алексей', 'patronym': 'Константинович', 'dob': '15.07.2008', 'status': 'Клиент', 'pause_until': '', 'leaving_reason': ''}, 'parent': {1: {'last_name': 'Ляшкевич', 'first_name': 'Евгения', 'patronym': 'Валерьевна'}, 2: {'last_name': 'Ляшкевич', 'first_name': 'Константин', 'patronym': 'Владимирович'}}, 'contact_select': {1: 'Выбрать', 2: 'Выбрать'}, 'selected_contact': {1: '110', 2: '111'}, 'contact': {1: {'telegram': '', 'phone': '995 571 051 683', 'other_contact': ''}, 2: {'telegram': '', 'phone': '995 568 81 97 06', 'other_contact': ''}}, 'relation': {1: 'Мама', 2: 'Папа'}, 'primary_contact': 1},
    {'student': {'last_name': 'Данилова', 'first_name': 'Александра', 'patronym': 'Алексеевна', 'dob': '14.01.2008', 'status': 'Клиент', 'pause_until': '', 'leaving_reason': ''}, 'parent': {1: {'last_name': 'Глазырина', 'first_name': 'Мария', 'patronym': 'Александровна'}}, 'contact_select': {1: 'Добавить'}, 'selected_contact': {1: ''}, 'contact': {1: {'telegram': '', 'phone': '79162163460,', 'other_contact': '995591756793'}}, 'relation': {1: 'Мама'}, 'primary_contact': 1}
]
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


def print_employees():
    existing_employees = [f'{empl.id}\t{empl.person.last_name}\t{empl.person.first_name}\t{empl.role}'
                          for empl in Employee.query.all()]
    print(*existing_employees, sep='\n')


adult_persons = Person.query.filter_by(person_type='Взрослый').all()


def format_children(person):
    children = []
    for child in person.children.all():
        today = datetime.now().date()
        child_age = (today.year - child.dob.year - ((today.month, today.day) < (child.dob.month, child.dob.day))) \
            if child.dob else None
        child_info = f'{child.last_name} {child.first_name} ({conjugate_years(child_age)})' \
            if child_age else f'{child.last_name} {child.first_name}'
        children.append(child_info)
    person.children_info = ', '.join(children)


# for person in adult_persons:
#     print(person.last_name, person.first_name)
#     if person.children.all():
#         format_children(person)
#         print('Дети: ', person.children_info)
#


def get_weekday_date(day_of_week, date):
    date_of_week_day = date - timedelta(days=date.weekday()) + timedelta(days=day_of_week)
    return date_of_week_day


week_list = ["0", "-1", "26.12.2023"]
next_week_list = ["1", "0", "30.01.2024"]
week = "2"
next_week = "0"
if week.lstrip('-').isdigit() and next_week.isdigit():
    week_diff = int(next_week) - int(week)
else:
    week_start = get_date(0, int(week)) if week.lstrip('-').isdigit() \
        else get_weekday_date(0, datetime.strptime(week, '%d.%m.%Y').date())
    next_week_start = get_date(0, int(next_week)) if next_week.isdigit() \
        else get_weekday_date(0, datetime.strptime(next_week, '%d.%m.%Y').date())
    week_diff = int((next_week_start - week_start).days / 7)
print(week, next_week, week_diff)


def get_week_dates():
    week_dates = [get_date(0).strftime('%d.%m.%Y'),
                  get_date(0, 1).strftime('%d.%m.%Y'),
                  get_date(0, -1).strftime('%d.%m.%Y')]
    return week_dates


def get_week_diff(date_1, date_2):
    week_1_start = get_weekday_date(0, date_1)
    week_2_start = get_weekday_date(0, date_2)
    week_diff = (week_2_start - week_1_start).days / 7
    return int(week_diff)


today = datetime.now().date()
next_week = datetime.strptime('30.01.2024', '%d.%m.%Y').date()
print(get_week_diff(today, next_week))