from datetime import datetime
from dateutil.relativedelta import relativedelta
from sqlalchemy import and_, or_
from app.app_settings.models import SubscriptionType
from app.common_servicies.service import (
    MONTHS, DAYS_OF_WEEK, LOCAL_TZ, conjugate_lessons, conjugate_days, get_today_date
)
from app.school.models import Person
from app.school.subjects.models import Subject, SubjectType
from app.school_classes.models import SchoolClass
from app.timetable.models import Lesson, StudentAttendance


def subscription_subjects_data():
    filtered_subjects = Subject.query.filter(
        Subject.subject_type.has(SubjectType.name != 'after_school'),
        Subject.subscription_types.any(SubscriptionType.id.isnot(None))
    ).order_by(Subject.name).all()

    subscription_subjects = []
    for subject in filtered_subjects:
        subject_data = {
            "id": subject.id,
            "name": subject.name,
            "price_info": {subscription_type.id: f"{subscription_type.price:.0f} Лари"
                           for subscription_type in subject.subscription_types},
            "subscription_types_info": {
                subscription_type.id: f"{conjugate_lessons(subscription_type.lessons)} " +
                                      f"на {conjugate_days(subscription_type.duration)} " +
                                      f"({subscription_type.price:.0f} Лари)"

                for subscription_type in subject.subscription_types
            }
        }
        subscription_subjects.append(subject_data)

    return subscription_subjects


def lesson_subjects_data():
    now = datetime.now(LOCAL_TZ).time()
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
                        Lesson.date == get_today_date(),
                        Lesson.start_time > now
                    ),
                    Lesson.date > get_today_date()
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


def subjects_data():
    all_subjects = Subject.query.filter(
        Subject.subject_type.has(SubjectType.name != 'event')
    ).order_by(Subject.name).all()
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


def add_new_subject(form, subject_type):
    if subject_type == "extra_school":
        name = form.subject_name.data
        subject_name = name[0].upper() + name[1:]
        short_name = form.subject_short_name.data
        subject_short_name = short_name[0].upper() + short_name[1:]
        teacher_ids = [int(teacher) for teacher in form.teachers.data]
        teachers = Person.query.filter(Person.id.in_(teacher_ids), Person.teacher).all()
        subject_type_id = int(form.subject_type.data)
        one_time_price = float(form.subject_price.data)
        if not form.no_subject_school_price.data:
            subject_school_price = float(form.subject_school_price.data)
            school_price = subject_school_price if int(subject_school_price) > 0 else None
        else:
            school_price = None
        if not form.no_subscription.data:
            subscription_type_ids = [int(st) for st in form.subscription_types.data]
            subscription_types = SubscriptionType.query.filter(SubscriptionType.id.in_(subscription_type_ids)).all()
        else:
            subscription_types = []

        new_subject = Subject(
            name=subject_name,
            short_name=subject_short_name,
            subject_type_id=subject_type_id,
            one_time_price=one_time_price,
            school_price=school_price,
        )
        new_subject.subscription_types.extend(subscription_types)
        new_subject.teachers.extend(teachers)

    else:
        name = form.get("subject_name")
        subject_name = name[0].upper() + name[1:]
        short_name = form.get("subject_short_name")
        subject_short_name = short_name[0].upper() + short_name[1:]
        teacher_ids = [int(teacher) for teacher in form.getlist("teachers") if form.getlist("teachers")]
        teachers = Person.query.filter(Person.id.in_(teacher_ids), Person.teacher).all()
        school_type = SubjectType.query.filter_by(name="school").first()
        classes = [int(school_class) for school_class in form.getlist("school_classes")]
        school_classes = SchoolClass.query.filter(SchoolClass.id.in_(classes)).all()

        new_subject = Subject(
            name=subject_name,
            short_name=subject_short_name,
            subject_type_id=school_type.id
        )
        new_subject.school_classes.extend(school_classes)
        new_subject.teachers.extend(teachers)
        classes_students = Person.query.filter(Person.school_class_id.in_(classes)).all()
        new_subject.students.extend(classes_students)
        for teacher in teachers:
            [teacher.teaching_classes.append(sc_cl) for sc_cl in school_classes
             if sc_cl not in teacher.teaching_classes]

    same_subject = Subject.query.filter_by(
        name=new_subject.name,
        subject_type_id=new_subject.subject_type_id
    ).all()

    return new_subject if not same_subject else None


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


def subject_record(subject_id, month_index):
    result_date = get_today_date() + relativedelta(months=month_index)
    first_date = datetime(result_date.year, result_date.month, 1).date()
    last_date = first_date + relativedelta(months=+1, days=-1)

    subject_records = StudentAttendance.query.filter(
        StudentAttendance.date >= first_date,
        StudentAttendance.date <= last_date,
        StudentAttendance.subject_id == subject_id
    ).order_by(StudentAttendance.date, StudentAttendance.lesson_time).all()

    subject_students = []
    lesson_datetimes = []
    record_dict = {}
    for record in subject_records:
        date_time_string = f"{record.date:%d.%m} {record.lesson_time:%H:%M}"
        lesson_date_time = (date_time_string, record.lesson_id)
        subject_student = (f"{record.student.last_name} {record.student.first_name}", record.student_id)
        if record.payment_method:
            student_payment_method = record.payment_method
            student_subscription_info = f"({record.subscription_lessons})" \
                if record.subscription_lessons is not None else ''
            student_payment = student_payment_method + student_subscription_info
        else:
            student_payment = "?"
        if subject_student not in subject_students:
            subject_students.append(subject_student)
            record_dict[subject_student] = {lesson_date_time: student_payment}
        else:
            record_dict[subject_student][lesson_date_time] = student_payment
        if lesson_date_time not in lesson_datetimes:
            lesson_datetimes.append(lesson_date_time)

    sorted_subject_students = sorted(subject_students, key=lambda x: x[0])
    month = MONTHS[first_date.month - 1]

    return record_dict, lesson_datetimes, sorted_subject_students, month
