from flask import Blueprint, flash, redirect, url_for, request, render_template
from flask_login import login_required, current_user
from sqlalchemy import distinct
from .models import SchoolClass, SchoolLessonJournal
from .service import (
    get_school_class, format_school_class_subjects, show_school_lesson, handle_school_lesson,
    school_subject_record, add_new_grade, change_grade, student_record, format_school_class_students
)
from app import db, cache
from app.app_settings.service import user_action
from app.common_servicies.service import DAYS_OF_WEEK, get_today_date, get_date_range, calc_month_index, calculate_week
from app.school.models import Person
from app.school.subjects.models import Subject, SubjectType
from app.school.subjects.service import add_new_subject
from app.timetable.service import day_school_lessons_dict

school_classes = Blueprint('school_classes', __name__)


@school_classes.route('/school-students/<string:school_class>', methods=['GET', 'POST'])
@login_required
def school_students(school_class):
    if current_user.rights in ["admin", "user", "teacher"]:
        school, classes_school = get_school_class(school_class)

        if not classes_school:
            flash("Школьных классов еще нет", 'error')
            return redirect(url_for('main.index'))

        if school is not None:
            format_school_class_students(school)
        else:
            flash("Такого класса нет", 'error')
            return redirect(url_for('school_classes.school_students', school_class=0))

        if request.method == 'POST':
            if 'add_client_btn' in request.form:
                try:
                    if current_user.rights in ["admin", "user"]:
                        added_student_id = int(request.form.get('added_student_id')) \
                            if request.form.get('added_student_id') else None
                        if added_student_id:
                            new_school_student = Person.query.filter_by(id=added_student_id).first()
                            new_school_student.school_class_id = school.id
                            for subject in school.school_subjects:
                                if subject not in new_school_student.subjects.all():
                                    new_school_student.subjects.append(subject)

                            description = f"Добавление ученика {new_school_student.last_name} " \
                                          f"{new_school_student.first_name} в класс '{school.school_name}'"
                            user_action(current_user, description)
                            db.session.commit()
                            cache.delete_many('school_attending_students',
                                              'possible_students',
                                              f'class_{school.id}_students')
                            flash(f'Новый ученик добавлен в класс', 'success')
                        else:
                            flash('Ученик не выбран', 'error')

                    else:
                        flash('Нет прав администратора', 'error')

                except Exception as e:
                    db.session.rollback()
                    flash(f'Ошибка при добавлении нового ученика: {str(e)}', 'error')

            if 'change_teacher_btn' in request.form:
                try:
                    if current_user.rights in ["admin", "user"]:
                        main_teacher = int(request.form.get('main_teacher')) if request.form.get('main_teacher') else None
                        school.main_teacher_id = main_teacher
                        description = f"Изменение классного руководителя класса '{school.school_name}'"
                        user_action(current_user, description)
                        db.session.commit()
                        cache.delete(f'class_info_{school.id}')
                        flash('Классный руководитель изменен', 'success')

                    else:
                        flash('Нет прав администратора', 'error')

                except Exception as e:
                    db.session.rollback()
                    flash(f'Ошибка при внесении изменений: {str(e)}', 'error')

            return redirect(request.referrer)

        possible_students = cache.get('possible_students')
        if not possible_students:
            possible_students = Person.query.filter(
                Person.person_type == 'Ребенок',
                Person.status == 'Клиент',
                Person.school_class_id.is_(None)
            ).order_by(Person.last_name, Person.first_name).all()
            cache.set('possible_students', possible_students)

        teachers = cache.get('teachers')
        if not teachers:
            teachers = Person.query.filter_by(teacher=True).order_by(Person.last_name, Person.first_name).all()
            cache.set('teachers', teachers)

        return render_template(
            'school_classes/school.html', school_classes=classes_school, school_class=school,
            possible_students=possible_students, teachers=teachers, render_type="students"
        )

    else:
        flash('Нет прав администратора', 'error')
        return redirect(url_for('main.index'))


@school_classes.route('/school-subjects/<string:school_class>', methods=['GET', 'POST'])
@login_required
def school_subjects(school_class):
    if current_user.rights in ["admin", "user", "teacher"]:
        school, classes_school = get_school_class(school_class)

        if not classes_school:
            flash("Школьных классов еще нет", 'error')
            return redirect(url_for('main.index'))

        if school is not None:
            format_school_class_subjects(school)
        else:
            flash("Такого класса нет", 'error')
            return redirect(url_for('school_classes.school_subjects', school_class=0))

        if request.method == 'POST':
            try:
                if current_user.rights in ["admin", "user"]:
                    if 'new_subject' in request.form:
                        new_subject, classes = add_new_subject(request.form, "school")
                        if new_subject:
                            db.session.add(new_subject)
                            description = f"Добавление нового школьного предмета {new_subject.name}"
                            user_action(current_user, description)
                            db.session.commit()
                            cache.delete('school_subjects')
                            for class_id in classes:
                                cache.delete(f'class_{class_id}_subjects')

                            flash('Новый предмет добавлен в систему', 'success')

                        else:
                            flash('Школьный предмет с таким названием уже есть', 'error')

                    if 'choose_subject' in request.form:
                        new_subject_id = int(request.form.get("selected_subject")) if \
                            request.form.get("selected_subject") else None
                        new_subject = Subject.query.filter(
                            Subject.id == new_subject_id,
                            Subject.subject_type.has(SubjectType.name == 'school')
                        ).first()
                        if new_subject:
                            if school not in new_subject.school_classes:
                                new_subject.school_classes.append(school)
                            teacher_ids = [int(teacher) for teacher in request.form.getlist("teachers")
                                           if request.form.getlist("teachers")]
                            teachers = Person.query.filter(Person.id.in_(teacher_ids), Person.teacher).all()
                            for teacher in teachers:
                                if school not in teacher.teaching_classes:
                                    teacher.teaching_classes.append(school)
                                if new_subject not in teacher.subjects_taught.all():
                                    teacher.subjects_taught.append(new_subject)
                            description = (f"Добавление школьного предмета {new_subject.name} "
                                           f"в класс '{school.school_name}'")
                            user_action(current_user, description)
                            db.session.commit()
                            cache.delete_many('school_subjects', f'class_{school.id}_subjects')
                            flash('Предмет добавлен классу', 'success')

                        else:
                            flash('Не выбран предмет', 'error')

                else:
                    flash('Нет прав администратора', 'error')

            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при внесении изменений: {str(e)}', 'error')

            return redirect(request.referrer)

        all_teachers = Person.query.filter_by(teacher=True).order_by(Person.last_name, Person.first_name).all()
        possible_subjects = Subject.query.filter(
            ~Subject.school_classes.any(SchoolClass.id == school.id),
            Subject.subject_type.has(SubjectType.name == 'school')
        ).order_by(Subject.name).all()

        return render_template(
            'school_classes/school.html', school_classes=classes_school, school_class=school,
            teachers=all_teachers, possible_subjects=possible_subjects, render_type="subjects"
        )

    else:
        flash('Нет прав администратора', 'error')
        return redirect(url_for('main.index'))


@school_classes.route('/edit-school-subject/<string:subject_id>', methods=['POST'])
@login_required
def edit_school_subject(subject_id):
    try:
        if current_user.rights in ["admin", "user"]:
            subject_id = int(subject_id) if str(subject_id).isdigit() else None
            school_subjects = cache.get('school_subjects')
            if school_subjects:
                school_subject = next((subject for subject in school_subjects if subject.id == subject_id), None)
            else:
                school_subject = Subject.query.filter(
                    Subject.id == subject_id,
                    Subject.subject_type.has(SubjectType.name == 'school')
                ).first()
            if school_subject:
                subject_new_name = request.form.get('subject_name')
                subject_new_short_name = request.form.get('subject_short_name')
                school_subject.name = subject_new_name
                school_subject.short_name = subject_new_short_name
                user_action(current_user, f'Внесение изменений в школьный предмет {school_subject.name}')
                db.session.commit()
                cache.delete('school_subjects')
                for school_class in school_subject.school_classes:
                    cache.delete(f'class_{school_class.id}_subjects')
                flash('Школьный предмет изменен', 'success')

            else:
                flash('Такого предмета нет', 'error')

        else:
            flash('Нет прав администратора', 'error')

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при внесении изменений: {str(e)}', 'error')

    return redirect(request.referrer)


@school_classes.route('/school-timetable/<string:week>/<string:day>')
@login_required
def school_timetable(week, day):
    week = int(week) if str(week).lstrip('-').isdigit() else None
    week_day = int(day) if str(day).isdigit() else None
    if week is None or week_day is None:
        flash(f'Неправильный адрес сайта', 'error')
        return redirect(url_for('school_classes.school_timetable', week=0, day=0))

    if week_day == 0:
        week_day = get_today_date().weekday() + 1
    if week_day > 7:
        return redirect(url_for('school_classes.school_timetable', week=week+1, day=1))

    school_classes_query = SchoolClass.query.order_by(
        SchoolClass.school_class,
        SchoolClass.school_name
    )
    if current_user.rights == "parent":
        class_list = [person.school_class_id for person in current_user.user_persons.all()]
        classes_school = school_classes_query.filter(SchoolClass.id.in_(class_list)).all()
    else:
        classes_school = school_classes_query.all()
    day_school_lessons, date_str, time_range = day_school_lessons_dict(week_day, week, classes_school)
    dates = get_date_range(week)
    filename = f"timetable_{dates[0].replace('.', '_')}_{dates[-1].replace('.', '_')}.xlsx"

    return render_template(
        'school_classes/school_timetable.html', days=DAYS_OF_WEEK, school_classes=classes_school,
        dates=dates, classes=day_school_lessons, date=date_str, start_time=time_range[0], end_time=time_range[1],
        week=week, week_day=week_day, filename=filename
    )


@school_classes.route('/school-lesson/<string:lesson_str>', methods=['GET', 'POST'])
@login_required
def school_lesson(lesson_str):
    sc_lesson, sc_subject = show_school_lesson(lesson_str)
    if sc_lesson:
        subject_classes = str(sc_lesson.subject_id) + '-' + '-'.join(map(str, sc_lesson.classes_ids))
        month_index = calc_month_index(sc_lesson.date)

        if request.method == 'POST' and current_user.rights in ["admin", "user", "teacher"]:
            try:
                message = handle_school_lesson(request.form, sc_lesson, current_user)
                db.session.commit()
                if message:
                    flash(message[0], message[1])

            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при проведении занятия: {str(e)}', 'error')

            return redirect(url_for('school_classes.school_lesson', lesson_str=f'0-{sc_lesson.id}'))

        sc_students = Person.query.filter(
            Person.school_class_id.is_not(None),
            ~Person.id.in_([student.id for student in sc_lesson.lesson_students])
        ).order_by(Person.last_name, Person.first_name).all()
        distinct_grade_types = db.session.query(
            distinct(SchoolLessonJournal.grade_type)
        ).filter(
            SchoolLessonJournal.final_grade.is_(False)
        ).all()
        grade_types = [grade_type[0] for grade_type in distinct_grade_types if grade_type[0]]
        days_dict = {day_num: day for (day_num, day) in enumerate(DAYS_OF_WEEK)}
        week = calculate_week(sc_lesson.date)

        return render_template(
            'school_classes/school_lesson.html', school_lesson=sc_lesson, days_dict=days_dict,
            week=week, school_students=sc_students, grade_types=grade_types, school_subject=sc_subject,
            subject_classes=subject_classes, month_index=month_index, today=get_today_date()
        )

    else:
        if sc_subject:
            return render_template('school_classes/school_lesson.html', school_lesson=sc_lesson,
                                   school_subject=sc_subject)
        else:
            flash("Такого урока нет", 'error')
            return redirect(url_for('school_classes.school_subjects', school_class=0))


@school_classes.route('/school-subject/<subject_classes>/<string:month_index>', methods=['GET', 'POST'])
@login_required
def school_subject(subject_classes, month_index):
    if current_user.rights in ["admin", "user", "teacher"]:
        subject_classes_ids = subject_classes.split('-')
        subject_id = int(subject_classes_ids[0]) if subject_classes_ids[0].isdigit() else None
        classes_ids = [int(sc_cl) for sc_cl in subject_classes_ids[1:] if sc_cl.isdigit()]
        month_index = int(month_index) if str(month_index).lstrip('-').isdigit() else None
        if not subject_id or not classes_ids or month_index is None:
            flash("Журнал не найден", 'error')
            return redirect(url_for('main.index'))

        subject = Subject.query.filter_by(id=subject_id).first()
        classes_school = SchoolClass.query.filter(
            SchoolClass.id.in_(classes_ids),
            SchoolClass.school_subjects.any(Subject.id == subject_id)
        ).order_by(SchoolClass.school_class).all()
        if not classes_school:
            flash(f"Журнал не найден", 'error')
            return redirect(url_for('main.index'))

        school_classes_names = ', '.join([cl.school_name for cl in classes_school])
        subject_records, dates_topics, sc_students, final_grades_list, month = school_subject_record(subject_id,
                                                                                                     classes_ids,
                                                                                                     month_index)
        if request.method == 'POST':
            try:
                if 'new_grade_btn' in request.form:
                    grade_info = add_new_grade(request.form, sc_students, subject_id, "grade")

                    if not grade_info[1]:
                        flash("Не выбрано за что оценка", 'error')
                        return redirect(request.referrer)

                    grade_month_index = calc_month_index(grade_info[0])
                    description = f"Добавление оценок по предмету {subject.name} {grade_info[0]:%d.%m.%Y} " \
                                  f"({school_classes_names}, {grade_info[1]})"
                    user_action(current_user, description)
                    db.session.commit()
                    flash("Оценки выставлены", 'success')

                    return redirect(url_for('school_classes.school_subject', subject_classes=subject_classes,
                                            month_index=grade_month_index))

                if 'new_final_grade_btn' in request.form:
                    grade_info = add_new_grade(request.form, sc_students, subject_id, "final")
                    if not grade_info[1]:
                        flash("Не выбрано за что оценка", 'error')
                        return redirect(request.referrer)

                    description = f"Добавление итоговых оценок по предмету {subject.name} {grade_info[0]:%d.%m.%Y} " \
                                  f"({school_classes_names}, {grade_info[1]})"
                    user_action(current_user, description)
                    db.session.commit()
                    flash("Оценки выставлены", 'success')

                if 'change_grade_btn' in request.form:
                    message = change_grade(request.form, subject, classes_ids, current_user)
                    db.session.commit()
                    flash(message[0], message[1])

                if 'delete_grade_btn' in request.form:
                    message = change_grade(request.form, subject, classes_ids, current_user)
                    db.session.commit()
                    flash(message[0], message[1])

                return redirect(url_for('school_classes.school_subject', subject_classes=subject_classes,
                                        month_index=month_index))

            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при выставлении оценок: {str(e)}', 'error')

                return redirect(url_for('school_classes.school_subject', subject_classes=subject_classes,
                                        month_index=month_index))

        distinct_grade_types = db.session.query(
            distinct(SchoolLessonJournal.grade_type)
        ).filter(
            SchoolLessonJournal.final_grade.is_(False)
        ).all()
        grade_types = [grade_type[0] for grade_type in distinct_grade_types if grade_type[0]]
        finals = ["1 четверть", "2 четверть", "3 четверть", "4 четверть", "год"]
        distinct_finals = db.session.query(
            distinct(SchoolLessonJournal.grade_type)
        ).filter(
            SchoolLessonJournal.final_grade.is_(True)
        ).all()
        final_grade_types = [grade_type[0] for grade_type in distinct_finals
                             if grade_type[0] and grade_type[0] not in finals]

        finals += final_grade_types
        dates_topics += final_grades_list

        return render_template(
            'school_classes/school_subject.html', subject_records=subject_records, month=month,
            dates_topics=dates_topics, final_grades_list=final_grades_list, students=sc_students, subject=subject,
            school_classes=school_classes_names, month_index=month_index, today=get_today_date(), finals=finals,
            subject_classes=subject_classes, grade_types=grade_types
        )

    else:
        flash('Нет прав администратора', 'error')
        return redirect(url_for('main.index'))


@school_classes.route('/student-record/<string:student_id>/<string:month_index>')
@login_required
def student_school_record(student_id, month_index):
    student_id = int(student_id) if str(student_id).isdigit() else None
    month_index = int(month_index) if str(month_index).lstrip('-').isdigit() else None
    school_student = Person.query.filter(
        Person.id == int(student_id),
        Person.school_class_id.is_not(None)
    ).first()
    if school_student and month_index is not None:
        if current_user.rights == "parent" and school_student not in current_user.user_persons.all():
            flash('Нет прав администратора', 'error')
            return redirect(url_for('main.index'))

        student_records, dates_topics, finals, month = student_record(school_student, int(month_index))
        student_subjects = list(student_records.keys())

        return render_template(
            'school_classes/school_student.html', student=school_student, dates_topics=dates_topics,
            student_records=student_records, student_subjects=student_subjects, finals=finals, month_index=month_index,
            month=month
        )

    else:
        flash("Такого ученика нет", 'error')
        return redirect(url_for('main.index'))


@school_classes.route('/school-journal/<string:option>', methods=['POST'])
@login_required
def school_journal(option):
    if current_user.rights in ["admin", "user", "teacher"]:
        if option == "student":
            student_id = request.form.get("school_student")
            if student_id:
                return redirect(url_for('school_classes.student_school_record',
                                        student_id=student_id, month_index=0))

            else:
                message = 'Не выбран ученик'

        else:
            subject_id = int(request.form.get("selected_subject")) if request.form.get("selected_subject") else None
            school_class_id = int(request.form.get("school_class")) if request.form.get("school_class") else None

            if subject_id and school_class_id:
                return redirect(url_for('school_classes.school_subject',
                                        subject_classes=f'{subject_id}-{school_class_id}',
                                        month_index=0))

            else:
                message = 'Не выбран предмет или класс'
    else:
        message = 'Нет прав администратора'

    flash(message, 'error')
    return redirect(request.referrer)
