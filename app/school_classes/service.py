from datetime import datetime
from dateutil.relativedelta import relativedelta
from sqlalchemy import and_, or_
from app import db
from app.app_settings.service import user_action, calculate_school_year
from app.common_servicies.service import get_today_date, MONTHS
from app.school.models import Person
from app.school.subjects.models import Subject, SubjectType
from app.school_classes.models import SchoolClass, SchoolLessonJournal
from app.timetable.models import Lesson, StudentAttendance
from app.caching.service import get_cache_school_classes, get_cache_school_class_info, get_cache_class_students, \
    get_cache_school_class_subjects


def get_school_class(school_class):
    classes_school = get_cache_school_classes()

    school_class = int(school_class) if str(school_class).isdigit() else None
    school = classes_school[0] if school_class == 0 else (
        next((cls for cls in classes_school if cls.id == school_class), None))

    return school, classes_school


def format_school_class_students(school_class):
    class_info = get_cache_school_class_info(school_class.id)
    class_students = get_cache_class_students(school_class.id)
    school_class.main_teacher = class_info["main_teacher"]
    school_class.class_students = class_students


def format_school_class_subjects(school_class):
    class_info = get_cache_school_class_info(school_class.id)
    school_class_subjects = get_cache_school_class_subjects(school_class.id)
    school_class.main_teacher = class_info["main_teacher"]
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


def show_school_lesson(lesson_str):
    lesson_id_split = lesson_str.split('-')
    if len(lesson_id_split) != 2:
        sc_lesson = None
        subject_id = None
    else:
        if lesson_id_split[0] == '0':
            lesson_id = int(lesson_id_split[1]) if lesson_id_split[1].isdigit() else None
            sc_lesson = Lesson.query.filter(
                Lesson.id == lesson_id,
                Lesson.lesson_type.has(SubjectType.name == "school")
            ).first()
            subject_id = sc_lesson.subject_id if sc_lesson else None
        else:
            school_class_id = int(lesson_id_split[0]) if lesson_id_split[0].isdigit() else None
            subject_id = int(lesson_id_split[1]) if lesson_id_split[1].isdigit() else None
            last_lesson = Lesson.query.filter(
                Lesson.subject_id == subject_id,
                Lesson.lesson_type.has(SubjectType.name == "school"),
                Lesson.school_classes.any(SchoolClass.id == school_class_id)
            ).order_by(Lesson.date.desc(), Lesson.start_time.desc()).first()
            coming_lesson = Lesson.query.filter(
                Lesson.date >= get_today_date(),
                Lesson.subject_id == subject_id,
                Lesson.lesson_type.has(SubjectType.name == "school"),
                Lesson.school_classes.any(SchoolClass.id == school_class_id)
            ).order_by(Lesson.date, Lesson.start_time).first()
            sc_lesson = coming_lesson if coming_lesson else last_lesson if last_lesson else None

    if sc_lesson:
        classes = [cl.id for cl in sc_lesson.school_classes]
        sc_lesson.classes_ids = classes
        sc_lesson.classes = ', '.join([cl.school_name for cl in sorted(sc_lesson.school_classes,
                                                                       key=lambda x: x.school_class)])

        if sc_lesson.students_registered.all():
            lesson_students = Person.query.filter(
                Person.lessons_registered.any(Lesson.id == sc_lesson.id),
                Person.status == "Клиент"
            ).order_by(Person.last_name, Person.first_name).all()

        else:
            lesson_students = Person.query.filter(
                Person.school_class_id.in_(classes),
                Person.subjects.any(Subject.id == sc_lesson.subject_id),
                Person.status == "Клиент"
            ).order_by(Person.last_name, Person.first_name).all()

        for student in lesson_students:
            journal_record = SchoolLessonJournal.query.filter_by(
                lesson_id=sc_lesson.id, student_id=student.id
            ).first()
            student.grade = journal_record.grade if journal_record else None
            student.lesson_comment = journal_record.lesson_comment if journal_record else None
            attendance = StudentAttendance.query.filter_by(
                student_id=student.id,
                lesson_id=sc_lesson.id
            ).first()
            student.attending_status = attendance.attending_status if attendance else None
        sc_lesson.lesson_students = lesson_students
        sc_lesson.prev, sc_lesson.next = prev_next_school_lessons(sc_lesson)

        sc_subject = sc_lesson.subject

    else:
        sc_subject = Subject.query.filter_by(id=subject_id).first() if subject_id else None

    return sc_lesson, sc_subject


def handle_school_lesson(form, lesson, user):
    if 'del_student_btn' in form:
        del_student_id = int(form.get('del_student_btn'))
        del_student = Person.query.filter_by(id=del_student_id).first()
        attendance = StudentAttendance.query.filter_by(student_id=del_student.id, lesson_id=lesson.id).first()
        if del_student in lesson.students_registered:
            lesson.students_registered.remove(del_student)
        if attendance:
            db.session.delete(attendance)
        description = f"Удаление ученика {del_student.last_name} {del_student.first_name} " \
                      f"из списка учеников урока {lesson.subject.name} {lesson.date:%d.%m.%Y}"
        user_action(user, description)
        db.session.flush()

    if 'add_student_btn' in form:
        new_student_id = int(form.get('added_student_id')) if form.get('added_student_id') else None
        new_student = Person.query.filter_by(id=new_student_id).first()
        if new_student:
            new_student_lessons = Lesson.query.filter(
                Lesson.date == lesson.date,
                Lesson.start_time < lesson.end_time,
                Lesson.end_time > lesson.start_time,
                Lesson.students_registered.any(Person.id == new_student.id)
            ).all()
            if not new_student_lessons:
                if new_student not in lesson.students_registered.all():
                    lesson.students_registered.append(new_student)
                if lesson.subject not in new_student.subjects.all():
                    new_student.subjects.append(lesson.subject)
                description = f"Добавление ученика {new_student.last_name} {new_student.first_name} " \
                              f"в список учеников урока {lesson.subject.name} {lesson.date:%d.%m.%Y}"
                user_action(user, description)
                db.session.flush()
                return "Ученик добавлен", 'success'

            else:
                return f"Ученик записан на занятие {new_student_lessons[0].subject.name} в это же время", 'error'

    if 'complete_btn' in form:
        if not lesson.lesson_completed:
            lesson.lesson_topic = form.get('lesson_topic')
            lesson.lesson_comment = form.get('comment')

            for student in lesson.lesson_students:
                if student not in lesson.students_registered:
                    lesson.students_registered.append(student)

                attendance = StudentAttendance.query.filter_by(
                    student_id=student.id,
                    lesson_id=lesson.id
                ).first()
                new_attending_status = "attend" if form.get(f'attended_{student.id}') else "not_attend"
                if not attendance:
                    new_attendance = StudentAttendance(
                        student_id=student.id,
                        lesson_id=lesson.id,
                        attending_status=new_attending_status
                    )
                    db.session.add(new_attendance)
                    db.session.flush()
                else:
                    attendance.attending_status = new_attending_status
                    db.session.flush()

                grade = form.get(f'grade_{student.id}')
                lesson_comment = form.get(f'lesson_comment_{student.id}')
                journal_record = SchoolLessonJournal.query.filter_by(
                    lesson_id=lesson.id,
                    student_id=student.id
                ).first()
                if grade is not None or lesson_comment:
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
            user_action(user, f"Проведение урока {lesson.subject.name} {lesson.date:%d.%m.%Y} и заполнение журнала")

            return 'Журнал заполнен', 'success'

        else:
            return 'Журнал уже был заполнен', 'error'

    if 'change_btn' in form:
        lesson.lesson_completed = False
        description = f"Отмена проведения урока {lesson.subject.name} {lesson.date:%d.%m.%Y} для внесения изменений"
        user_action(user, description)

        return 'Внесение изменений', 'success'


def school_subject_record(subject_id, school_classes_ids, month_index):
    result_date = get_today_date() + relativedelta(months=month_index)
    first_date = datetime(result_date.year, result_date.month, 1).date()
    month = MONTHS[first_date.month - 1]
    last_date = first_date + relativedelta(months=+1, days=-1)
    school_students = Person.query.filter(
        Person.school_class_id.in_(school_classes_ids)
    ).order_by(Person.last_name, Person.first_name).all()
    subject_records = SchoolLessonJournal.query.filter(
        SchoolLessonJournal.date >= first_date,
        SchoolLessonJournal.date <= last_date,
        SchoolLessonJournal.subject_id == subject_id,
        SchoolLessonJournal.school_class_id.in_(school_classes_ids),
        ~SchoolLessonJournal.final_grade
    ).all()
    dates_topic_set = set()
    record_dict = {
        f"{student.last_name} {student.first_name}":
            {"student_id": student.id, "class_id": student.school_class_id} for student in school_students
    }

    for record in subject_records:
        date_string = f"{record.date:%d.%m.%Y}"
        topic = record.grade_type if record.grade_type else record.lesson.lesson_topic if record.lesson_id else '-'
        lesson_id = record.lesson_id if record.lesson_id else 0
        dates_topic_set.add((date_string, topic, lesson_id))
        student_name = f"{record.student.last_name} {record.student.first_name}"
        if record.student in school_students:
            record_dict[student_name][(date_string, topic, lesson_id)] = {
                "id": record.id,
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
        date_string = f"{lesson.date:%d.%m.%Y}"
        topic = lesson.lesson_topic
        dates_topic_set.add((date_string, topic, lesson.id))

    dates_topic = sorted(list(dates_topic_set))

    school_start_year = calculate_school_year(first_date)
    final_grades = SchoolLessonJournal.query.filter(
        SchoolLessonJournal.date >= datetime(school_start_year, 9, 1).date(),
        SchoolLessonJournal.date <= datetime(school_start_year + 1, 7, 1).date(),
        SchoolLessonJournal.subject_id == subject_id,
        SchoolLessonJournal.school_class_id.in_(school_classes_ids),
        SchoolLessonJournal.final_grade
    ).order_by(SchoolLessonJournal.date).all()

    final_grades_list = []
    if final_grades:
        final_grades_set = set()
        for final_grade in final_grades:
            date_string = f"{final_grade.date:%d.%m.%Y}"
            topic = final_grade.grade_type
            lesson_id = -1
            final_grades_set.add((date_string, topic, lesson_id))
            student_name = f"{final_grade.student.last_name} {final_grade.student.first_name}"
            if final_grade.student in school_students:
                record_dict[student_name][(date_string, topic, lesson_id)] = {
                    "id": final_grade.id,
                    "grade": final_grade.grade,
                    "comment": final_grade.lesson_comment
                }

        final_grades_list = sorted(list(final_grades_set))

    return record_dict, dates_topic, school_students, final_grades_list, month


def add_new_grade(form, students, subject_id, grade):
    grade_type = form.get('grade_type')
    grade_date = datetime.strptime(form.get('grade_date'), '%d.%m.%Y').date()
    if not grade_type:
        return grade_date, grade_type

    for student in students:
        new_grade = form.get(f'new_grade_{student.id}')
        new_comment = form.get(f'new_comment_{student.id}')
        if new_grade is not None or new_comment:
            journal_record = SchoolLessonJournal(
                date=grade_date,
                grade_type=grade_type,
                student_id=student.id,
                school_class_id=student.school_class_id,
                subject_id=subject_id,
                grade=new_grade,
                lesson_comment=new_comment
            )
            if grade == "final":
                journal_record.final_grade = True
            db.session.add(journal_record)
            db.session.flush()

    return grade_date, grade_type


def change_grade(form, subject, classes_ids, user):
    grade_id = int(form.get('grade_id')) if form.get('grade_id') else None
    final_grade = int(form.get('final_grade'))
    if grade_id is None:
        date, topic = form.get('grade_date_topic').split('-|-')
        record_date = datetime.strptime(date, '%d.%m.%Y').date()
        final_grade = bool(final_grade)
        grade_records = SchoolLessonJournal.query.filter(
            SchoolLessonJournal.date == record_date,
            SchoolLessonJournal.grade_type == topic,
            SchoolLessonJournal.subject_id == subject.id,
            SchoolLessonJournal.lesson_id.is_(None),
            SchoolLessonJournal.school_class_id.in_(classes_ids),
            SchoolLessonJournal.final_grade == final_grade
        ).all()
        for record in grade_records:
            db.session.delete(record)

        description = f"Удаление оценок по предмету {subject.name} от {record_date:%d.%m.%Y} ({topic})"
        user_action(user, description)
        db.session.flush()
        return 'Оценки удалены', 'success'

    new_grade = int(form.get('grade')) if form.get('grade') and form.get('grade').isdigit() else None
    new_comment = form.get('comment')
    if grade_id == 0:
        if new_grade is None and not new_comment:
            return 'Нет новой оценки или комментария', 'error'

        else:
            student_id, school_class_id = map(int, form.get('student').split('-'))
            date, topic = form.get('grade_date_topic').split('-|-')
            record_date = datetime.strptime(date, '%d.%m.%Y').date()
            lesson_id = None
            final_grade = bool(final_grade)
            new_record = SchoolLessonJournal(
                date=record_date,
                student_id=student_id,
                grade_type=topic,
                subject_id=subject.id,
                lesson_id=lesson_id,
                school_class_id=school_class_id,
                final_grade=final_grade,
                grade=new_grade,
                lesson_comment=new_comment
            )
            db.session.add(new_record)
            db.session.flush()
            grade_description = "Изменение оценки ученика" if final_grade else "Изменение итоговой оценки ученика"

            description = grade_description + f" {new_record.student.last_name} {new_record.student.first_name} " \
                                              f"по предмету {subject.name} от {record_date:%d.%m.%Y} ({topic})"

    else:
        grade_record = SchoolLessonJournal.query.filter_by(id=grade_id).first()
        if new_grade is None and not new_comment:
            db.session.delete(grade_record)
            db.session.flush()

        else:
            grade_record.grade = new_grade
            grade_record.lesson_comment = new_comment
            db.session.flush()
        grade_description = "Изменение оценки ученика" if grade_record.final_grade \
            else "Изменение итоговой оценки ученика"

        description = grade_description + f" {grade_record.student.last_name} {grade_record.student.first_name} " \
                                          f"по предмету {subject.name} от {grade_record.date:%d.%m.%Y} " \
                                          f"({grade_record.grade_type})"

    user_action(user, description)
    return 'Изменения внесены', 'success'


def student_record(student, month_index):
    result_date = get_today_date() + relativedelta(months=month_index)
    first_date = datetime(result_date.year, result_date.month, 1).date()
    last_date = first_date + relativedelta(months=+1, days=-1)
    month = MONTHS[first_date.month - 1]

    student_records = SchoolLessonJournal.query.filter(
        SchoolLessonJournal.date >= first_date,
        SchoolLessonJournal.date <= last_date,
        SchoolLessonJournal.student_id == student.id,
        ~SchoolLessonJournal.final_grade
    ).all()

    student_subjects = Subject.query.filter(
        Subject.subject_type.has(SubjectType.name == "school"),
        Subject.students.any(Person.id == student.id)
    ).order_by(Subject.name).all()
    subjects_dict = {subject.name: {} for subject in student_subjects}
    dates_grade_type_set = set()
    for record in student_records:
        date_str = f'{record.date:%d.%m}'
        grade_type = record.grade_type if record.grade_type else record.lesson.lesson_topic if record.lesson_id else '-'
        dates_grade_type_set.add((date_str, grade_type))
        if record.subject.name in subjects_dict.keys():
            subjects_dict[record.subject.name][(date_str, grade_type)] = {"grade": record.grade,
                                                                          "comment": record.lesson_comment}
        else:
            subjects_dict[record.subject.name] = {(date_str, grade_type): {"grade": record.grade,
                                                                           "comment": record.lesson_comment}}

    dates_grade_type = sorted(list(dates_grade_type_set))

    school_start_year = calculate_school_year(first_date)
    final_grades = SchoolLessonJournal.query.filter(
        SchoolLessonJournal.date >= datetime(school_start_year, 9, 1).date(),
        SchoolLessonJournal.date <= datetime(school_start_year + 1, 7, 1).date(),
        SchoolLessonJournal.student_id == student.id,
        SchoolLessonJournal.final_grade
    ).order_by(SchoolLessonJournal.date).all()

    final_grade_types = []
    for final_grade in final_grades:
        if final_grade.grade_type not in final_grade_types:
            final_grade_types.append(final_grade.grade_type)
        if final_grade.subject.name in subjects_dict.keys():
            subjects_dict[final_grade.subject.name][final_grade.grade_type] = {"grade": final_grade.grade,
                                                                               "comment": final_grade.lesson_comment}
        else:
            subjects_dict[final_grade.subject.name] = {final_grade.grade_type: {"grade": final_grade.grade,
                                                                                "comment": final_grade.lesson_comment}}

    return subjects_dict, dates_grade_type, final_grade_types, month
