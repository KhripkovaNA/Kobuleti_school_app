from datetime import datetime
from dateutil.relativedelta import relativedelta
from sqlalchemy import and_
from app import cache
from app.app_settings.models import Room, SubscriptionType, SchoolSemester
from app.auth.models import User
from app.common_servicies.service import conjugate_lessons, conjugate_days, get_today_date, MONTHS
from app.school.subscriptions.service import format_subscription_types
from app.school_classes.models import SchoolClass
from app.school.subjects.models import Subject, SubjectType
from app.school.models import Person
from app.school.students.service import format_student_info, format_main_contact
from app.timetable.models import Lesson, StudentAttendance


def delete_cache(cache_items):
    if len(cache_items) == 1:
        cache.delete(cache_items[0])
    else:
        cache.delete_many(*cache_items)


def get_cache_school_classes():
    classes_school = cache.get('classes_school')
    if classes_school is None:
        classes_school = SchoolClass.query.order_by(
            SchoolClass.school_class,
            SchoolClass.school_name
        ).all()
        for school_class in classes_school:
            school_class.class_lessons = school_class.class_lessons
        cache.set('classes_school', classes_school)

    return classes_school


def get_cache_school_subjects():
    school_subjects = cache.get('school_subjects')
    if school_subjects is None:
        school_subjects = Subject.query.filter(
            Subject.subject_type.has(SubjectType.name == "school")
        ).order_by(Subject.name).all()
        cache.set('school_subjects', school_subjects)

    return school_subjects


def get_cache_school_attending_students():
    school_attending_students = cache.get('school_attending_students')
    if school_attending_students is None:
        school_attending_students = Person.query.filter(
            Person.status == "Клиент",
            Person.school_class_id.is_not(None)
        ).order_by(Person.last_name, Person.first_name).all()
        cache.set('school_attending_students', school_attending_students)

    return school_attending_students


def get_cache_school_class_info(school_class_id):
    class_info = cache.get(f'class_info_{school_class_id}')
    if class_info is None:
        school_class = SchoolClass.query.filter_by(id=school_class_id).first()
        main_teacher = Person.query.filter_by(id=school_class.main_teacher_id).first()
        class_info = {
            'school_class': school_class,
            'main_teacher': main_teacher
        }
        cache.set(f'class_info_{school_class_id}', class_info)

    return class_info


def get_cache_class_students(school_class_id):
    class_students = cache.get(f'class_{school_class_id}_students')
    if class_students is None:

        class_students = Person.query.filter_by(
            school_class_id=school_class_id,
            status="Клиент"
        ).order_by(Person.last_name, Person.last_name).all()

        for student in class_students:
            format_student_info(student)
            format_main_contact(student)
        cache.set(f'class_{school_class_id}_students', class_students)

    return class_students


def get_cache_school_class_subjects(school_class_id):
    school_class_subjects = cache.get(f'class_{school_class_id}_subjects')
    if school_class_subjects is None:
        school_class_subjects = Subject.query.filter(
            Subject.school_classes.any(SchoolClass.id == school_class_id)
        ).order_by(Subject.name).all()

        for school_subject in school_class_subjects:
            school_teachers = Person.query.filter(
                Person.lessons.any(
                    and_(
                        Lesson.subject_id == school_subject.id,
                        Lesson.school_classes.any(SchoolClass.id == school_class_id)
                    )
                ),
                Person.subjects_taught.any(Subject.id == school_subject.id)
            ).order_by(Person.last_name, Person.first_name).all()
            subject_teachers = Person.query.filter(
                Person.teaching_classes.any(SchoolClass.id == school_class_id),
                Person.subjects_taught.any(Subject.id == school_subject.id)
            ).order_by(Person.last_name, Person.first_name).all()

            school_subject.school_teachers = school_teachers if school_teachers else subject_teachers
        cache.set(f'class_{school_class_id}_subjects', school_class_subjects)

    return school_class_subjects


def get_cache_possible_students():
    possible_students = cache.get('possible_students')
    if not possible_students:
        possible_students = Person.query.filter(
            Person.person_type == 'Ребенок',
            Person.status == 'Клиент',
            Person.school_class_id.is_(None)
        ).order_by(Person.last_name, Person.first_name).all()
        cache.set('possible_students', possible_students)

    return possible_students


def get_cache_teachers():
    teachers = cache.get('teachers')
    if not teachers:
        teachers = Person.query.filter_by(teacher=True).order_by(Person.last_name, Person.first_name).all()
        cache.set('teachers', teachers)

    return teachers


def get_cache_subscription_subjects():
    subscription_subjects = cache.get('subscription_subjects')
    if subscription_subjects:
        return subscription_subjects

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
    cache.set('subscription_subjects', subscription_subjects)

    return subscription_subjects


def get_cache_all_subjects():
    all_subjects = cache.get('all_subjects')
    if not all_subjects:
        all_subjects = Subject.query.filter(
            Subject.subject_type.has(SubjectType.name.in_(['extra', 'individual']))
        ).order_by(Subject.name).all()
        for subject in all_subjects:
            subject.subject_description = subject.subject_type.description
            subject.teachers = subject.teachers
            subject.types_of_subscription = format_subscription_types(subject.subscription_types.all())
        cache.set('all_subjects', all_subjects)

    return all_subjects


def get_cache_subject_record(subject_id, month_index):
    subject_record_dict = cache.get(f'subject_record_{subject_id}_{month_index}')
    if subject_record_dict is None:
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

        subject_record_dict = {
            'record_dict': record_dict,
            'lesson_datetimes': lesson_datetimes,
            'sorted_subject_students': sorted(subject_students, key=lambda x: x[0]),
            'month': MONTHS[first_date.month - 1]
        }
        cache.set(f'subject_record_{subject_id}_{month_index}', subject_record_dict)

    return subject_record_dict


def get_cache_rooms():
    rooms = cache.get('rooms')
    if not rooms:
        rooms = Room.query.all()
        for room in rooms:
            room.lessons = room.lessons
        cache.set('rooms', rooms)

    return rooms


def get_cache_subscription_types():
    subscription_types = cache.get('subscription_types')
    if not subscription_types:
        subscription_types = SubscriptionType.query.filter(SubscriptionType.lessons.isnot(None)).all()
        for subscription_type in subscription_types:
            subscription_type.subscriptions = subscription_type.subscriptions
        cache.set('subscription_types', subscription_types)

    return subscription_types


def get_cache_after_school_prices():
    after_school_prices = cache.get('after_school_prices')
    if not after_school_prices:
        after_school_prices = SubscriptionType.query.filter(SubscriptionType.period != '').all()
        for after_school_price in after_school_prices:
            after_school_price.subscriptions = after_school_price.subscriptions
        cache.set('after_school_prices', after_school_prices)

    return after_school_prices


def get_cache_parent_users():
    parent_users = cache.get('parent_users')
    if not parent_users:
        parent_users = User.query.filter_by(rights="parent").all()
        for parent in parent_users:
            parent.children = parent.user_persons.all()
        cache.set('parent_users', parent_users)

    return parent_users


def get_cache_semesters():
    semesters = cache.get('semesters')
    if semesters is None:
        semesters = SchoolSemester.query.order_by(SchoolSemester.start_date).all()
        cache.set('semesters', semesters)

    return semesters
