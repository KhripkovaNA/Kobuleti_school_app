from datetime import datetime, timedelta
from sqlalchemy import or_, and_
from app import db, cache
from app.common_servicies.service import (
    DAYS_OF_WEEK, get_date, calc_month_index, conjugate_lessons, calculate_week, get_weekday_date, get_today_date
)
from app.school.models import Person
from app.school.subjects.models import Subject, SubjectType
from app.school_classes.models import SchoolClass
from .models import Lesson, StudentAttendance
from app.app_settings.service import user_action
from app.finance.models import Finance
from app.finance.service import finance_operation
from app.school.subscriptions.models import Subscription
from app.school.subscriptions.service import check_subscription


def student_lesson_register(form, student):
    subject_id = int(form.get('selected_subject')) if form.get('selected_subject') else None
    subject = Subject.query.filter_by(id=subject_id).first()
    lesson_id = int(form.get('lesson')) if form.get('lesson') else None
    lesson = Lesson.query.filter_by(id=lesson_id).first()
    if student and subject and lesson:
        student_lessons = Lesson.query.filter(
            Lesson.date == lesson.date,
            Lesson.start_time < lesson.end_time,
            Lesson.end_time > lesson.start_time,
            Lesson.students_registered.any(Person.id == student.id)
        ).all()
        if student_lessons:
            return None, "Клиент уже записан на занятие в это же время"

        if student not in subject.students:
            subject.students.append(student)
        if student not in lesson.students_registered:
            lesson.students_registered.append(student)

        return lesson, "Клиент записан на занятие"

    else:
        return None, "Ошибка при записи клиента"


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


def create_lesson_dict(lesson, timetable_type):
    start_time = (lesson.start_time.hour - 9) * 60 + lesson.start_time.minute
    end_time = (lesson.end_time.hour - 9) * 60 + lesson.end_time.minute

    lesson_dict = {
        'id': lesson.id,
        'time': f'{lesson.start_time:%H:%M} - {lesson.end_time:%H:%M}',
        'start_time': start_time,
        'end_time': end_time,
        'teacher': lesson.teacher.first_name if lesson.teacher else '-',
        'completed': lesson.lesson_completed,
        'month_index': calc_month_index(lesson.date),
        'subject_full': lesson.subject.name
    }
    if timetable_type in ['general', 'teacher']:
        if lesson.lesson_type.name == 'school':
            lesson_type = format_school_classes_names(lesson.school_classes)
        elif lesson.lesson_type.name == 'individual':
            lesson_type = 'индив'
        else:
            lesson_type = ''
        if lesson.lesson_type.name == 'event':
            lesson_dict['teacher'] = ''
            lesson_dict['color'] = '#ED42C2'
        else:
            lesson_dict['color'] = lesson.teacher.color
        lesson_dict['lesson_type'] = lesson_type
        lesson_dict['subject'] = lesson.subject_names if timetable_type == 'general' else lesson.subject.name
        lesson_dict['lesson_type_name'] = lesson.lesson_type.name

    else:
        lesson_dict['room'] = lesson.room.name
        lesson_dict['room_color'] = lesson.room.color
        lesson_dict['subject'] = lesson.subject.short_name
        lesson_dict['split'] = lesson.split_classes

    return lesson_dict


def day_lessons_list(day_room_lessons):
    lessons_for_day = []
    current_lesson = day_room_lessons[0]
    current_lesson.subject_names = [current_lesson.subject.short_name]

    for next_lesson in day_room_lessons[1:]:
        if (
                current_lesson.teacher_id == next_lesson.teacher_id
                and current_lesson.school_classes.all() == next_lesson.school_classes.all()
                and current_lesson.lesson_type.name == 'school'
                and current_lesson.lesson_type.name == 'school'
        ):
            if current_lesson.subject_names[-1] != next_lesson.subject.short_name:
                current_lesson.subject_names.append(next_lesson.subject.short_name)
            current_lesson.end_time = next_lesson.end_time
        else:
            lessons_for_day.append(create_lesson_dict(current_lesson, 'general'))
            next_lesson.subject_names = [next_lesson.subject.short_name]
            current_lesson = next_lesson

    lessons_for_day.append(create_lesson_dict(current_lesson, 'general'))

    return lessons_for_day


def week_lessons_dict(week, rooms, lessons_type='general'):
    week_lessons = {}
    used_rooms = set()
    week_dates = []
    week_start_hour = 22
    week_end_hour = 8
    for day, weekday in enumerate(DAYS_OF_WEEK):
        lessons_date = get_date(day, week)
        lessons_date_str = f'{lessons_date:%d.%m}'
        week_dates.append(lessons_date_str)
        day_lessons = {}
        for room in rooms:
            if lessons_type == 'general':
                lessons_filtered = Lesson.query.filter_by(
                    date=lessons_date, room_id=room.id
                ).order_by(Lesson.start_time).all()
            elif lessons_type.startswith('teacher'):
                teacher_id = int(lessons_type[len('teacher_'):])
                lessons_filtered = Lesson.query.filter(
                    Lesson.date == lessons_date,
                    Lesson.room_id == room.id,
                    Lesson.teacher_id == teacher_id
                ).order_by(Lesson.start_time).all()
            elif lessons_type == 'extra':
                lessons_filtered = Lesson.query.filter(
                    Lesson.date == lessons_date,
                    Lesson.room_id == room.id,
                    Lesson.lesson_type.has(SubjectType.name == 'extra')
                ).order_by(Lesson.start_time).all()
            else:
                lessons_filtered = Lesson.query.filter(
                    Lesson.date == lessons_date,
                    Lesson.room_id == room.id,
                    Lesson.lesson_type.has(SubjectType.name == 'individual')
                ).order_by(Lesson.start_time).all()
            if lessons_filtered:
                start_hour = lessons_filtered[0].start_time.hour
                week_start_hour = start_hour if start_hour < week_start_hour else week_start_hour
                end_hour = lessons_filtered[-1].end_time.hour + 1 * bool(lessons_filtered[-1].end_time.minute)
                week_end_hour = end_hour if end_hour > week_end_hour else week_end_hour
                used_rooms.add(room.name)
                if lessons_type.startswith('teacher'):
                    lessons_for_day = []
                    for lesson in lessons_filtered:
                        lessons_for_day.append(create_lesson_dict(lesson, 'teacher'))
                    day_lessons[room.name] = lessons_for_day
                else:
                    day_lessons[room.name] = day_lessons_list(lessons_filtered) if lessons_filtered else []
        if day_lessons:
            week_lessons[weekday] = day_lessons
    if not week_lessons.get(DAYS_OF_WEEK[-1]):
        week_dates.pop(-1)
        if not week_lessons.get(DAYS_OF_WEEK[-2]):
            week_dates.pop(-1)
    return week_lessons, week_dates, used_rooms, (week_start_hour, week_end_hour)


def day_school_lessons_dict(day, week, school_classes):
    lesson_date = get_date(day - 1, week)
    lesson_date_str = f'{lesson_date:%d.%m}'
    day_start_hour = 22
    day_end_hour = 8

    class_lessons = {}
    for school_class in school_classes:
        lessons_filtered = Lesson.query.filter(
            Lesson.lesson_type.has(SubjectType.name == "school"),
            Lesson.date == lesson_date,
            Lesson.school_classes.any(SchoolClass.id == school_class.id)
        ).order_by(Lesson.start_time).all()
        if lessons_filtered:
            start_hour = lessons_filtered[0].start_time.hour
            day_start_hour = start_hour if start_hour < day_start_hour else day_start_hour
            end_hour = lessons_filtered[-1].end_time.hour + 1 * bool(lessons_filtered[-1].end_time.minute)
            day_end_hour = end_hour if end_hour > day_end_hour else day_end_hour

            class_lessons[school_class.school_name] = [create_lesson_dict(school_lesson, "school")
                                                       for school_lesson in lessons_filtered if lessons_filtered]

    return class_lessons, lesson_date_str, (day_start_hour, day_end_hour)


def check_conflicting_lessons(lessons, date, start_time, end_time, classes,
                              room, teacher, split_classes, lesson_id=None):
    filter_conditions = [
        lambda lesson: lesson.start_time < end_time and lesson.end_time > start_time and lesson.room_id == room,
        lambda lesson: lesson.start_time < end_time and lesson.end_time > start_time and lesson.teacher_id == teacher
    ]

    if not split_classes:
        filter_conditions.append(
            lambda lesson: lesson.start_time < end_time and lesson.end_time > start_time and any(
                cl.id in classes for cl in lesson.school_classes
            )
        )

    conflicting_lessons = [
        lesson for lesson in lessons
        if lesson.id != lesson_id and lesson.date == date and any(cond(lesson) for cond in filter_conditions)
    ]

    return conflicting_lessons


def analyze_conflicts(conflicting_lessons, room_id, teacher_id, classes):
    intersection = set()

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

    return intersection


def create_check_lesson(lesson_date, form, i):
    start_time = datetime.strptime(form.start_time.data, '%H : %M').time()
    end_time = datetime.strptime(form.end_time.data, '%H : %M').time()
    subject_id, lesson_type_id = form.subject.data.split('-')
    room_id = int(form.room.data)
    classes = [int(school_class) for school_class in form.school_classes.data]
    split_classes = form.split_classes.data
    teacher_id = int(form.teacher.data)
    school_type = SubjectType.query.filter_by(name='school').first().id
    day_lessons = Lesson.query.filter(
        Lesson.date == lesson_date
    ).all()

    if end_time <= start_time:
        lesson = None
        message_text = f'Занятие {i} не добавлено в расписание. Ошибка во времени проведения'
        return lesson, message_text

    if int(lesson_type_id) == school_type and not classes:
        lesson = None
        message_text = f'Занятие {i} не добавлено в расписание. Классы не выбраны'
        return lesson, message_text

    if day_lessons:
        conflicting_lessons = check_conflicting_lessons(day_lessons, lesson_date, start_time, end_time,
                                                        classes, room_id, teacher_id, split_classes)
        if conflicting_lessons:
            intersection = analyze_conflicts(conflicting_lessons, room_id, teacher_id, classes)

            message_text = f'Занятие {i} не добавлено в расписание. Пересечения по ' + ', '.join(intersection)
            lesson = None
            return lesson, message_text

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
    if school_classes:
        lesson.school_classes.extend(school_classes)
        lesson.split_classes = split_classes
        school_students = Person.query.filter(
            Person.status == "Клиент",
            Person.school_class_id.in_(classes)
        ).all()
        for student in school_students:
            student_lessons = Lesson.query.filter(
                Lesson.date == lesson.date,
                Lesson.start_time < lesson.end_time,
                Lesson.end_time > lesson.start_time,
                Lesson.students_registered.any(Person.id == student.id)
            ).all()
            if not student_lessons:
                lesson.students_registered.append(student)

    message_text = f'Занятие {i} добавлено в расписание'

    return lesson, message_text


def add_new_event(form):
    lessons_week = int(form.get('lessons_week'))
    event_day = int(form.get('event_day'))
    event_date = get_date(event_day, lessons_week)
    start_time = datetime.strptime(form.get('event_start_time'), '%H : %M').time()
    end_time = datetime.strptime(form.get('event_end_time'), '%H : %M').time()
    if end_time <= start_time:
        return ('Мероприятие не добавлено. Ошибка во времени проведения', 'error'), None

    room_id = int(form.get('room'))
    conflicts = Lesson.query.filter(
        Lesson.date == event_date,
        Lesson.start_time < end_time,
        Lesson.end_time > start_time,
        Lesson.room_id == room_id
    ).all()
    if not conflicts:
        event_name = form.get('event_name')
        if not event_name:
            return ('Мероприятие не добавлено. Нет названия', 'error'), None

        event_type = SubjectType.query.filter_by(name='event').first()
        existing_event_name = Subject.query.filter_by(name=event_name, subject_type_id=event_type.id).first()
        if existing_event_name:
            event_id = existing_event_name.id
        else:
            new_event_subject = Subject(name=event_name, short_name=event_name, subject_type_id=event_type.id)
            db.session.add(new_event_subject)
            db.session.flush()
            event_id = new_event_subject.id
        new_event = Lesson(
            date=event_date,
            start_time=start_time,
            end_time=end_time,
            lesson_type_id=event_type.id,
            room_id=room_id,
            subject_id=event_id
        )
        db.session.add(new_event)
        db.session.flush()
        return ('Мероприятие добавлено в расписание', 'success'), new_event

    else:
        return ('Мероприятие не добавлено, есть занятия в это же время', 'error'), None


def filter_day_lessons(form):
    lessons_week = int(form.get('lessons_week'))
    lessons_day = int(form.get('lessons_day'))
    date = get_date(lessons_day, lessons_week)
    query = Lesson.query.filter(Lesson.date == date)
    subject_types = form.get('subject_types')
    if subject_types != "all":
        subject_types_list = [int(subject_type) for subject_type in form.getlist('subject_types_specific')
                              if form.getlist('subject_types_specific')]
        query = query.filter(Lesson.lesson_type_id.in_(subject_types_list))
    lessons = query.all()

    return lessons, date


def change_lessons_date(form):
    change_lessons, old_date = filter_day_lessons(form)
    new_date = datetime.strptime(form.get('new_date'), '%d.%m.%Y').date()
    new_week = calculate_week(new_date)
    if change_lessons:
        les = len(change_lessons)
        change_les = 0
        new_date_lessons = Lesson.query.filter(
            Lesson.date == new_date
        ).all()

        for lesson in change_lessons:
            if not lesson.lesson_completed:
                start_time = lesson.start_time
                end_time = lesson.end_time
                classes = [cl.id for cl in lesson.school_classes]
                room = lesson.room_id
                teacher = lesson.teacher_id
                split_classes = lesson.split_classes

                if new_date_lessons:
                    conflicting_lessons = check_conflicting_lessons(new_date_lessons, new_date, start_time, end_time,
                                                                    classes, room, teacher, split_classes)
                    if conflicting_lessons:
                        continue

                lesson.date = new_date
                change_les += 1
                db.session.flush()

        if change_les == les:
            message = [("Все занятия перенесены", 'success')]

        elif change_les != 0:
            message1 = (f"{conjugate_lessons(change_les)} перенесено", 'success')
            message2 = (f"{conjugate_lessons(change_les)} невозможно перенести", 'error')
            message = [message1, message2]

        else:
            new_week = None
            message = [("Занятия невозможно перенести", 'error')]

    else:
        new_week = None
        message = [("Нет занятий,  удовлетворяющих критериям", 'error')]

    return new_week, message, (old_date, new_date)


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
    next_week = int((next_start_date - get_weekday_date(0, get_today_date())).days / 7)

    weekday = form.get('lessons_days')
    weekdays = form.getlist('lessons_days_specific')

    subject_types = form.get('subject_types')
    school_classes = form.get('school_classes')
    rooms = form.get('rooms')
    teachers = form.get('teachers')
    school_type_id = SubjectType.query.filter_by(name='school').first().id

    if weekday == "all":
        end_date = get_weekday_date(6, start_date)
        query = Lesson.query.filter(Lesson.date >= start_date,
                                    Lesson.date <= end_date)
    else:
        lessons_dates = [get_weekday_date(int(day), start_date) for day in weekdays if weekdays]
        query = Lesson.query.filter(Lesson.date.in_(lessons_dates))

    if rooms != "all":
        rooms_list = [int(room) for room in form.getlist('rooms_specific') if form.getlist('rooms_specific')]
        query = query.filter(Lesson.room_id.in_(rooms_list))

    if subject_types != "all":
        subject_types_list = [int(subject_type) for subject_type in form.getlist('subject_types_specific')
                              if form.getlist('subject_types_specific')]
        query = query.filter(Lesson.lesson_type_id.in_(subject_types_list))

        if school_classes != 'all' and (school_type_id in subject_types_list):
            school_classes_list = [int(school_class) for school_class in form.getlist('school_classes_specific')
                                   if form.getlist('school_classes_specific')]
            query = query.filter(Lesson.school_classes.any(SchoolClass.id.in_(school_classes_list)))

    if teachers != "all":
        teachers_list = [int(teacher) for teacher in form.getlist('teachers_specific')
                         if form.getlist('teachers_specific')]
        query = query.filter(Lesson.teacher_id.in_(teachers_list))

    filtered_lessons = query.all()

    return filtered_lessons, week_diff, next_week


def copy_filtered_lessons(filtered_lessons, week_diff):
    copied_lessons = 0
    conflicts = 0
    start_date = min(lesson.date for lesson in filtered_lessons) + timedelta(weeks=week_diff)
    end_date = max(lesson.date for lesson in filtered_lessons) + timedelta(weeks=week_diff)
    all_lessons_in_period = Lesson.query.filter(
        Lesson.date.between(start_date, end_date)
    ).all()

    for lesson in filtered_lessons:
        date = lesson.date + timedelta(weeks=week_diff)
        start_time = lesson.start_time
        end_time = lesson.end_time
        classes = [cl.id for cl in lesson.school_classes]
        room = lesson.room_id
        teacher = lesson.teacher_id
        split_classes = lesson.split_classes

        if all_lessons_in_period:
            conflicting_lessons = check_conflicting_lessons(all_lessons_in_period, date, start_time, end_time,
                                                            classes, room, teacher, split_classes)
            if conflicting_lessons:
                conflicts += 1
                continue

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
            new_lesson.split_classes = split_classes
            if lesson.students_registered.all():
                lesson_students = lesson.students_registered.all()
            else:
                lesson_students = Person.query.filter(Person.school_class_id.in_(classes)).all()
            for student in lesson_students:
                if student.status == "Клиент":
                    student_lessons = Lesson.query.filter(
                        Lesson.date == new_lesson.date,
                        Lesson.start_time < new_lesson.end_time,
                        Lesson.end_time > new_lesson.start_time,
                        Lesson.students_registered.any(Person.id == student.id)
                    ).all()
                    if not student_lessons:
                        new_lesson.students_registered.append(student)

        db.session.flush()
        copied_lessons += 1

    return copied_lessons, conflicts


def add_new_lessons(form):
    lesson_date = datetime.strptime(form.lesson_date.data, '%d.%m.%Y').date()
    messages = []
    new_lessons = 0
    for i, lesson_form in enumerate(form.lessons, 1):
        new_lesson, text = create_check_lesson(lesson_date, lesson_form, i)
        if new_lesson:
            new_lessons += 1
            message = (text, 'success')
            messages.append(message)
            db.session.add(new_lesson)
            db.session.flush()
        else:
            message = (text, 'error')
            messages.append(message)

    return messages, lesson_date, new_lessons


def lesson_edit(form, lesson):
    lesson_date = datetime.strptime(form.lesson_date.data, '%d.%m.%Y').date()
    start_time = datetime.strptime(form.start_time.data, '%H : %M').time()
    end_time = datetime.strptime(form.end_time.data, '%H : %M').time()
    room_id = int(form.room.data)
    before_classes = set([school_class.id for school_class in lesson.school_classes])
    classes = [int(school_class) for school_class in form.school_classes.data] \
        if lesson.lesson_type.name == 'school' else []
    split_classes = form.split_classes.data
    teacher_id = int(form.teacher.data) if form.teacher.data else None
    day_lessons = Lesson.query.filter(
        Lesson.date == lesson_date
    ).all()

    if end_time <= start_time:
        message = ('Ошибка во времени проведения', 'error')
        return message

    if day_lessons:
        conflicting_lessons = check_conflicting_lessons(day_lessons, lesson_date, start_time, end_time, classes,
                                                        room_id, teacher_id, split_classes, lesson.id)

        if conflicting_lessons:
            intersection = analyze_conflicts(conflicting_lessons, room_id, teacher_id, classes)

            message = ('Занятие не изменено. Пересечения по ' + ', '.join(intersection), 'error')

            return message

    lesson.date = lesson_date
    lesson.start_time = start_time
    lesson.end_time = end_time
    lesson.room_id = room_id
    lesson.teacher_id = teacher_id
    if lesson.lesson_type.name == 'school':
        lesson.split_classes = split_classes
        classes_set = set(classes)
        if before_classes != classes_set:
            added_classes = list(classes_set.difference(before_classes))
            removed_classes = list(before_classes.difference(classes_set))
            school_classes = SchoolClass.query.filter(SchoolClass.id.in_(classes)).all()
            lesson.school_classes = [school_class for school_class in school_classes]

            school_students = Person.query.filter(
                Person.status == "Клиент",
                Person.school_class_id.in_(added_classes + removed_classes)
            ).all()

            for student in school_students:
                if student.school_class_id in removed_classes and student in lesson.students_registered:
                    lesson.students_registered.remove(student)
                    attendance = StudentAttendance.query.filter_by(
                        student_id=student.id, lesson_id=lesson.id
                    ).first()
                    if attendance:
                        db.session.delete(attendance)
                    db.session.flush()

                if student.school_class_id in added_classes and student not in lesson.students_registered:
                    student_lessons = Lesson.query.filter(
                        Lesson.date == lesson.date,
                        Lesson.start_time < lesson.end_time,
                        Lesson.end_time > lesson.start_time,
                        Lesson.students_registered.any(Person.id == student.id)
                    ).all()
                    if not student_lessons:
                        lesson.students_registered.append(student)
                    db.session.flush()

    message = ('Занятие изменено', 'success')

    return message


def get_payment_options(student, subject_id, lesson):
    check_subscription(student, lesson, subject_id)
    after_school_sub = Subscription.query.filter_by(student_id=student.id,
                                                    is_after_school=True,
                                                    active=True).first()
    subscriptions = Subscription.query.filter(
        Subscription.student_id == student.id,
        Subscription.subject_id == subject_id,
        Subscription.lessons_left > 0,
        Subscription.active
    ).order_by(Subscription.purchase_date).all()

    payment_options = []
    if subscriptions:
        for subscription in subscriptions:
            payment_option = {
                'value': f'subscription_{subscription.id}',
                'type': 'Абонемент',
                'info': f'({subscription.lessons_left} до {subscription.end_date:%d.%m})'
            }
            payment_options.append(payment_option)
    elif after_school_sub:
        payment_option = {
            'value': 'after_school',
            'type': 'Продленка',
            'info': ''
        }
        payment_options.append(payment_option)
    else:
        payment_option = {
            'value': 'one_time',
            'type': 'Разовое',
            'info': ''
        }
        payment_options.append(payment_option)
    return payment_options


def get_lesson_students(lesson):
    if lesson.lesson_completed:
        lesson_students = Person.query.filter(
            Person.lessons_attended.any(StudentAttendance.lesson_id == lesson.id)
        ).order_by(Person.last_name, Person.first_name).all()
    else:
        lesson_students = Person.query.filter(
            Person.status == "Клиент",
            or_(
                Person.lessons_registered.any(Lesson.id == lesson.id),
                Person.subjects.any(Subject.id == lesson.subject_id)
            )
        ).order_by(
            Person.lessons_registered.any(Lesson.id == lesson.id).desc(),
            Person.last_name, Person.first_name
        ).all()

    if lesson_students:
        for student in lesson_students:
            student.payment_options = get_payment_options(student, lesson.subject_id, lesson)
            if lesson.lesson_completed:
                attendance = StudentAttendance.query.filter_by(
                    student_id=student.id,
                    lesson_id=lesson.id
                ).first()
                student.attended = attendance.attending_status if attendance else 'not_attend'
                if attendance.payment_method:
                    student_payment_method = attendance.payment_method
                    student_subscription_info = f"({attendance.subscription_lessons})" \
                        if attendance.subscription_lessons is not None else ''
                    student_payment = student_payment_method + student_subscription_info
                else:
                    student_payment = "?"
                student.payment = student_payment

    return lesson_students


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


def show_lesson(lesson_str):
    lesson_id_split = lesson_str.split('-')
    if len(lesson_id_split) != 2:
        subject_lesson = None
        subject_id = None
    else:
        if lesson_id_split[0] == '0':
            subject_id = int(lesson_id_split[1]) if lesson_id_split[1].isdigit() else None
            last_lesson = Lesson.query.filter(
                Lesson.subject_id == subject_id,
                ~Lesson.lesson_type.has(SubjectType.name.in_(["school", "after_school", "event"]))
            ).order_by(Lesson.date.desc(), Lesson.start_time.desc()).first()
            coming_lesson = Lesson.query.filter(
                Lesson.date >= get_today_date(),
                Lesson.subject_id == subject_id,
                ~Lesson.lesson_type.has(SubjectType.name.in_(["school", "after_school", "event"]))
            ).order_by(Lesson.date, Lesson.start_time).first()
            subject_lesson = coming_lesson if coming_lesson else last_lesson if last_lesson else None
        else:
            lesson_id = int(lesson_id_split[1]) if lesson_id_split[1].isdigit() else None
            subject_lesson = Lesson.query.filter(
                Lesson.id == lesson_id,
                ~Lesson.lesson_type.has(SubjectType.name.in_(["school", "after_school", "event"]))
            ).first()
            subject_id = subject_lesson.subject_id if subject_lesson else None

    if subject_lesson:
        subject_lesson.students = get_lesson_students(subject_lesson)
        subject_lesson.prev, subject_lesson.next = prev_next_lessons(subject_lesson)
        lesson_subject = subject_lesson.subject

    else:
        lesson_subject = Subject.query.filter_by(id=subject_id).first()

    return subject_lesson, lesson_subject


def carry_out_lesson(form, subject, lesson, user):
    if not lesson.lesson_completed:
        lesson_price = subject.one_time_price
        lesson_school_price = subject.school_price if subject.school_price else lesson_price
        if not lesson.students_registered.all():
            return 'Нет записанных клиентов', 'error'

        for student in lesson.students_registered.all():
            if form.get(f'attending_status_{student.id}') in ['attend', 'unreasonable']:
                payment_option = form.get(f'payment_option_{student.id}')
                if payment_option.startswith('subscription'):
                    subscription_id = int(payment_option[len('subscription_'):])
                    subscription = Subscription.query.filter_by(id=subscription_id).first()
                    if subscription.lessons_left > 0:
                        subscription.lessons_left -= 1
                        price_paid = subscription.subscription_type.price / subscription.subscription_type.lessons
                        payment_info = ("Абонемент", price_paid, subscription.lessons_left)
                    else:
                        description = f"Списание за занятие {subject.name}"
                        finance_operation(student, -lesson_price, 'balance', description, 'lesson',
                                          lesson.id, subject_id=subject.id)
                        payment_info = ("Разовое", lesson_price, None)
                else:
                    price = lesson_school_price if payment_option == 'after_school' else lesson_price
                    description = f"Списание за занятие {subject.name} {lesson.date:%d.%m.%y}"
                    finance_operation(student, -price, 'balance', description, 'lesson',
                                      lesson.id, subject_id=subject.id)
                    payment_info = ("Продленка", price, None) if payment_option == 'after_school' \
                        else ("Разовое", price, None)
                    subscription_id = None

                attendance = StudentAttendance(
                    date=lesson.date,
                    lesson_time=lesson.start_time,
                    student_id=student.id,
                    lesson_id=lesson.id,
                    subject_id=subject.id,
                    attending_status=form.get(f'attending_status_{student.id}'),
                    payment_method=payment_info[0],
                    price_paid=payment_info[1],
                    subscription_lessons=payment_info[2],
                    subscription_id=subscription_id
                )
                db.session.add(attendance)
                db.session.flush()

        lesson.lesson_completed = True
        user_action(user, f"Проведение занятия {subject.name} {lesson.date:%d.%m.%Y}")
        return 'Занятие проведено', 'success'

    else:
        return 'Занятие уже проведено', 'error'


def undo_lesson(subject, lesson):
    if lesson.lesson_completed:
        lesson_price = subject.one_time_price
        lesson_school_price = subject.school_price if subject.school_price else lesson_price
        for student in lesson.students:
            attendance = StudentAttendance.query.filter_by(
                student_id=student.id,
                lesson_id=lesson.id
            ).first()

            if attendance:
                if attendance.attending_status in ['attend', 'unreasonable']:
                    payment_option = attendance.payment_method
                    if payment_option == 'Абонемент':
                        subscription_id = int(attendance.subscription_id) if attendance.subscription_id else None
                        if not subscription_id:
                            subscription = Subscription.query.filter(
                                Subscription.student_id == student.id,
                                Subscription.subject_id == subject.id,
                                Subscription.purchase_date <= lesson.date,
                                Subscription.end_date >= lesson.date
                            ).order_by(Subscription.purchase_date.desc()).first()
                        else:
                            subscription = Subscription.query.filter_by(id=subscription_id).first()
                        if subscription:
                            subscription.lessons_left += 1

                    else:
                        price = attendance.price_paid if attendance.price_paid else lesson_school_price \
                            if payment_option == 'Продленка' else lesson_price
                        record = Finance.query.filter(
                            Finance.person_id == student.id,
                            Finance.service == "lesson",
                            Finance.service_id == lesson.id
                        ).first()
                        description = f"Возврат за занятие {subject.name} {lesson.date:%d.%m.%y}"
                        if record:
                            record.service_id = None
                        finance_operation(student, price, 'balance', description,
                                          'del_lesson', None, subject_id=subject.id)

                        db.session.flush()
                db.session.delete(attendance)

        lesson.lesson_completed = False
        return 'Проведение занятия отменено', 'success'

    else:
        return 'Занятие еще не проведено', 'error'


def handle_lesson(form, subject, lesson, user):
    month_index = calc_month_index(lesson.date)
    if 'del_client_btn' in form:
        del_client_id = int(form.get('del_client_btn'))
        del_client = Person.query.filter_by(id=del_client_id).first()
        attendance = StudentAttendance.query.filter_by(student_id=del_client_id, lesson_id=lesson.id).first()
        if del_client in subject.students:
            subject.students.remove(del_client)
        if del_client in lesson.students_registered:
            lesson.students_registered.remove(del_client)
        if attendance:
            db.session.delete(attendance)
        description = f"Удаление клиента {del_client.last_name} {del_client.first_name} c занятия {subject.name}"
        user_action(user, description)
        db.session.flush()
        cache.delete(f'subject_record_{subject.id}_{month_index}')
        return 'Клиент удален', 'success'

    if 'add_client_btn' in form:
        new_client_id = int(form.get('added_client_id')) if form.get('added_client_id') else None
        if new_client_id:
            new_client = Person.query.filter_by(id=new_client_id).first()
            subject.students.append(new_client)
            description = f"Добавление клиента {new_client.last_name} {new_client.first_name} " \
                          f"на занятие {subject.name}"
            user_action(user, description)
            db.session.flush()
            return 'Клиент добавлен', 'success'
        else:
            return 'Клиент не выбран', 'error'

    if 'registered_btn' in form:
        messages = []
        for student in lesson.students:
            if (
                    student not in lesson.students_registered
                    and form.get(f'registered_{student.id}') == 'on'
            ):
                student_lessons = Lesson.query.filter(
                    Lesson.date == lesson.date,
                    Lesson.start_time < lesson.end_time,
                    Lesson.end_time > lesson.start_time,
                    Lesson.students_registered.any(Person.id == student.id)
                ).all()
                if not student_lessons:
                    lesson.students_registered.append(student)
                    description = f"Запись клиента {student.last_name} {student.first_name} " \
                                  f"на занятие {subject.name} {lesson.date:%d.%m.%Y}"
                    user_action(user, description)
                else:
                    messages.append(f"Клиент {student.last_name} {student.first_name}" +
                                    f" уже записан на занятие {student_lessons[0].subject.name} в это же время")
            elif (
                    student in lesson.students_registered
                    and not form.get(f'registered_{student.id}')
            ):
                lesson.students_registered.remove(student)
                description = f"Отмена записи клиента {student.last_name} {student.first_name} " \
                              f"на занятие {subject.name} {lesson.date:%d.%m.%Y}"
                user_action(user, description)

        if messages:
            message_text = '. '.join(messages)
            return message_text, 'error'

    if 'attended_btn' in form and user.rights in ["admin", "user"]:
        message = carry_out_lesson(form, subject, lesson, user)
        cache.delete(f'subject_record_{subject.id}_{month_index}')
        return message

    if 'change_btn' in form and user.rights in ["admin", "user"]:
        message = undo_lesson(subject, lesson)
        user_action(user, f"Отмена проведения занятия {subject.name} {lesson.date:%d.%m.%Y}")
        cache.delete(f'subject_record_{subject.id}_{month_index}')
        return message
