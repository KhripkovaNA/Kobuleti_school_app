from io import BytesIO
from flask import Blueprint, request, flash, redirect, url_for, render_template, send_file
from flask_login import login_required, current_user
from wtforms.validators import InputRequired
from app import db
from app.app_settings.models import Room
from app.app_settings.service import user_action
from app.common_servicies.service import get_date, DAYS_OF_WEEK, get_today_date, calculate_week, calc_month_index
from app.school.models import Person
from app.school.subjects.models import SubjectType, Subject
from app.school.subjects.service import subjects_data
from app.school_classes.models import SchoolClass
from .forms import AddLessonsForm, EditLessonForm
from .models import Lesson
from .service import (
    student_lesson_register, week_lessons_dict, add_new_event, change_lessons_date, filter_lessons,
    copy_filtered_lessons, add_new_lessons, lesson_edit, show_lesson, handle_lesson
)
from app.common_servicies.excel_generators import download_timetable


timetable = Blueprint('timetable', __name__)


@timetable.route('/lesson-register/<string:student_id>', methods=['POST'])
@login_required
def lesson_register(student_id):
    try:
        if current_user.rights in ["admin", "user"]:
            student_id = int(student_id) if str(student_id).isdigit() else None
            student = Person.query.filter_by(id=student_id, status="Клиент").first()
            lesson, message = student_lesson_register(request.form, student)
            if lesson:
                description = f"Запись клиента {student.last_name} {student.first_name} " \
                              f"на занятие {lesson.subject.name} {lesson.date:%d.%m.%Y}"
                user_action(current_user, description)
                db.session.commit()
                flash(message, 'success')

                return redirect(url_for('timetable.lesson', lesson_str=f'1-{lesson.id}'))

            else:
                flash(message, 'error')

        else:
            flash('Нет прав администратора', 'error')

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при записи клиента: {str(e)}', 'error')

    return redirect(request.referrer)


# timetable.full_timetable
@timetable.route('/timetable/<string:week>')
@login_required
def full_timetable(week):
    week = int(week) if str(week).lstrip('-').isdigit() else 0
    week_range = [f'{get_date(day, week):%d.%m}' for day in range(7)]
    all_rooms = Room.query.all()
    week_lessons, week_dates, used_rooms, time_range = week_lessons_dict(week, all_rooms)
    rooms = [room.name for room in all_rooms if room.name in used_rooms]
    cols = len(week_dates) * len(rooms)
    subject_types = SubjectType.query.all()
    events = Subject.query.filter(Subject.subject_type.has(SubjectType.name == 'event')).order_by(Subject.name).all()

    return render_template(
        'timetable/timetable.html', days=DAYS_OF_WEEK, rooms=rooms, cols=cols, week=week,
        start_time=time_range[0], end_time=time_range[1], classes=week_lessons, week_dates=week_dates,
        all_rooms=all_rooms, events=events, subject_types=subject_types, week_range=week_range
    )


@timetable.route('/extra-timetable/<string:week>')
@login_required
def extra_timetable(week):
    week = int(week) if str(week).lstrip('-').isdigit() else 0
    all_rooms = Room.query.all()
    week_lessons, week_dates, used_rooms, time_range = week_lessons_dict(week, all_rooms, 'extra')
    rooms = [room.name for room in all_rooms if room.name in used_rooms]
    cols = len(week_dates) * len(rooms)

    return render_template(
        'timetable/extra_timetable.html', days=DAYS_OF_WEEK, rooms=rooms, cols=cols,
        start_time=time_range[0], end_time=time_range[1], classes=week_lessons, week=week,
        week_dates=week_dates, timetable_type='extra'
    )


@timetable.route('/individual-timetable/<string:week>')
@login_required
def individual_timetable(week):
    week = int(week) if str(week).lstrip('-').isdigit() else 0
    all_rooms = Room.query.all()
    week_lessons, week_dates, used_rooms, time_range = week_lessons_dict(week, all_rooms, 'individual')
    rooms = [room.name for room in all_rooms if room.name in used_rooms]
    cols = len(week_dates) * len(rooms)

    return render_template(
        'timetable/extra_timetable.html', days=DAYS_OF_WEEK, rooms=rooms, cols=cols,
        start_time=time_range[0], end_time=time_range[1], classes=week_lessons, week=week, week_dates=week_dates,
        timetable_type='individual'
    )


@timetable.route('/teacher-timetable/<string:teacher_id>/<string:week>')
@login_required
def teacher_timetable(teacher_id, week):
    if current_user.rights in ["admin", "user", "teacher"]:
        teacher_id = int(teacher_id) if str(teacher_id).isdigit() else None
        teacher = Person.query.filter_by(id=teacher_id, teacher=True).first()
        if teacher:
            week = int(week) if str(week).lstrip('-').isdigit() else 0
            all_rooms = Room.query.all()
            week_lessons, week_dates, used_rooms, time_range = week_lessons_dict(
                week, all_rooms, f'teacher_{teacher_id}'
            )
            rooms = [room.name for room in all_rooms if room.name in used_rooms]
            cols = len(week_dates) * len(rooms)

            return render_template(
                'timetable/teacher_timetable.html', days=DAYS_OF_WEEK, rooms=rooms, cols=cols,
                start_time=time_range[0], end_time=time_range[1], classes=week_lessons, week=week,
                week_dates=week_dates, lessons_teacher=teacher
            )

    else:
        flash('Нет прав администратора', 'error')
        return redirect(url_for('main.index'))


@timetable.route('/add-event', methods=['POST'])
@login_required
def add_event():
    try:
        if current_user.rights in ["admin", "user"]:
            message, event = add_new_event(request.form)
            description = f"Добавление мероприятия '{event.subject.name}' {event.date:%d.%m.%y}"
            user_action(current_user, description)
            db.session.commit()
            flash(message[0], message[1])

        else:
            flash('Нет прав администратора', 'error')

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при добавлении мероприятия: {str(e)}', 'error')

    return redirect(request.referrer)


@timetable.route('/change-lessons', methods=['POST'])
@login_required
def change_lessons():
    try:
        if current_user.rights in ["admin", "user"]:
            new_week, message, dates = change_lessons_date(request.form)
            db.session.commit()
            for msg in message:
                flash(msg[0], msg[1])
            if new_week is not None:
                description = f"Перенос занятий с {dates[0]:%d.%m.%y} на {dates[1]:%d.%m.%y}"
                user_action(current_user, description)
                db.session.commit()
                return redirect(url_for('timetable.full_timetable', week=new_week))

        else:
            flash('Нет прав администратора', 'error')

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при переносе занятий: {str(e)}', 'error')

    return redirect(request.referrer)


@timetable.route('/copy-lessons', methods=['GET', 'POST'])
@login_required
def copy_lessons():
    if current_user.rights in ["admin", "user"]:
        if request.method == 'POST':
            try:
                filtered_lessons, week_diff, next_week = filter_lessons(request.form)
                if filtered_lessons:
                    new_lessons, conflicts = copy_filtered_lessons(filtered_lessons, week_diff)
                    if new_lessons > 0:
                        week_range = (f'{get_date(0, next_week):%d.%m}-'
                                      f'{get_date(6, next_week):%d.%m.%Y}')
                        description = f'Копирование уроков в расписание на неделю {week_range}'
                        user_action(current_user, description)
                    db.session.commit()

                    if conflicts == 0:
                        flash('Все занятия добавлены в расписание.', 'success')
                    elif new_lessons == 0:
                        flash(f'Занятия не добавлены, т.к. есть занятия в это же время.', 'error')
                    else:
                        flash(f'Добавлено занятий: {new_lessons}', 'success')
                        flash(
                            f'Не добавлено занятий: {conflicts}, т.к. есть занятия в это же время', 'error'
                        )
                    return redirect(url_for('timetable.full_timetable', week=next_week))

                else:
                    flash('Нет занятий, удовлетворяющих заданным параметрам', 'error')
                    return redirect(url_for('timetable.copy_lessons'))

            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при добавлении новых занятий: {str(e)}', 'error')
                return redirect(url_for('timetable.copy_lessons'))

        subject_types = SubjectType.query.filter(SubjectType.name != 'event').all()
        rooms = Room.query.all()
        school_classes = SchoolClass.query.order_by(SchoolClass.school_class).all()
        all_teachers = Person.query.filter_by(teacher=True).order_by(Person.last_name, Person.first_name).all()
        school = SubjectType.query.filter_by(name='school').first()

        return render_template(
            'timetable/copy_lessons.html', days=DAYS_OF_WEEK, subject_types=subject_types,
            rooms=rooms, school_classes=school_classes, teachers=all_teachers, school=school
        )

    else:
        flash('Нет прав администратора', 'error')
        return redirect(url_for('timetable.full_timetable', week=0))


@timetable.route('/add-lessons', methods=['GET', 'POST'])
@login_required
def add_lessons():
    if current_user.rights in ["admin", "user"]:
        all_subjects = subjects_data()
        rooms = Room.query.all()
        school_type = SubjectType.query.filter_by(name='school').first().id
        form = AddLessonsForm()
        form.lessons[0].subject.choices = [(f"{subject['id']}-{subject['subject_type']}",
                                            f"{subject['name']} ({subject['description']})")
                                           for subject in all_subjects]
        form.lessons[0].room.choices = [(room.id, room.name) for room in rooms]
        if request.method == 'POST':
            try:
                if form.validate_on_submit():
                    messages, date, new_lessons = add_new_lessons(form)
                    if new_lessons > 0:
                        week = calculate_week(date)
                        description = f"Добавление новых занятий в расписание {date:%d.%m.%Y}"
                        user_action(current_user, description)
                        db.session.commit()
                        for message in messages:
                            flash(message[0], message[1])

                        return redirect(url_for('timetable.full_timetable', week=week))

                    else:
                        for message in messages:
                            flash(message[0], message[1])

                else:
                    flash(f'Ошибка в форме добавления занятий', 'error')

            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при добавлении новых занятий: {str(e)}', 'error')
                return redirect(url_for('timetable.add_lessons'))

        school_classes = SchoolClass.query.order_by(SchoolClass.school_class).all()
        school_classes_data = [{school_class.id: school_class.school_name} for school_class in school_classes]
        all_teachers = Person.query.filter_by(teacher=True).order_by(Person.last_name, Person.first_name).all()
        teachers_data = [{teacher.id: f"{teacher.last_name} {teacher.first_name}"} for teacher in all_teachers]

        return render_template('timetable/add_lessons.html', subjects=all_subjects, school_classes=school_classes_data,
                               form=form, teachers=teachers_data, school_type=school_type)

    else:
        flash('Нет прав администратора', 'error')
        return redirect(url_for('timetable.full_timetable', week=0))


@timetable.route('/edit-lesson/<string:lesson_id>', methods=['GET', 'POST'])
@login_required
def edit_lesson(lesson_id):
    if current_user.rights in ["admin", "user"]:
        edited_lesson = Lesson.query.filter_by(id=lesson_id).first()
        if not edited_lesson:
            flash("Такого занятия нет", 'error')
            return redirect(url_for('timetable.full_timetable', week=0))

        if edited_lesson.lesson_completed:
            flash("Занятие уже проведено, невозможно изменить", 'error')
            return redirect(request.referrer)

        week = calculate_week(edited_lesson.date)
        rooms = Room.query.all()
        all_teachers = Person.query.filter_by(teacher=True).order_by(Person.last_name, Person.first_name).all()
        lesson_classes = sorted(edited_lesson.school_classes, key=lambda x: (x.school_class, x.school_name))
        lesson_classes_data = [cl.id for cl in lesson_classes] if lesson_classes else None
        form = EditLessonForm(
            lesson_date=f'{edited_lesson.date:%d.%m.%Y}',
            start_time=f'{edited_lesson.start_time:%H : %M}',
            end_time=f'{edited_lesson.end_time:%H : %M}',
            room=edited_lesson.room_id,
            school_classes=lesson_classes_data,
            split_classes=edited_lesson.split_classes,
            teacher=edited_lesson.teacher_id
        )
        form.subject.validators = []
        if edited_lesson.lesson_type.name == 'event':
            form.teacher.validators = []
        if edited_lesson.lesson_type.name == "school":
            all_classes = SchoolClass.query.order_by(
                SchoolClass.school_class, SchoolClass.school_name
            ).all()
            form.school_classes.choices = [(sc_cl.id, sc_cl.school_name) for sc_cl in all_classes]
            form.school_classes.validators = [InputRequired(message='Заполните это поле')]
            edited_lesson.classes = ', '.join([cl.school_name for cl in lesson_classes])

        form.room.choices = [(room.id, room.name) for room in rooms]
        form.teacher.choices = [(teacher.id, f'{teacher.last_name} {teacher.first_name}') for teacher in all_teachers]

        if request.method == 'POST':
            try:
                if form.validate_on_submit():
                    message = lesson_edit(form, edited_lesson)
                    if message[1] == 'error':
                        flash(message[0], message[1])
                        return redirect(url_for('timetable.edit_lesson', lesson_id=edited_lesson.id))

                    if message[1] == 'success':
                        description = f"Внесение изменений в занятие {edited_lesson.subject.name} " \
                                      f"{edited_lesson.date:%d.%m.%Y}"
                        user_action(current_user, description)
                        db.session.commit()
                        week = calculate_week(edited_lesson.date)
                        flash(message[0], message[1])

                        if edited_lesson.lesson_type.name == "school":
                            day = edited_lesson.date.weekday() + 1
                            return redirect(url_for('school_classes.school_timetable', week=week, day=day))
                        else:
                            return redirect(url_for('timetable.full_timetable', week=week))
                else:
                    flash('Ошибка в форме изменения занятия', 'error')

            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при внесении изменений: {str(e)}', 'error')
                return redirect(url_for('timetable.edit_lesson', lesson_id=edited_lesson.id))

        return render_template('timetable/edit_lesson.html', lesson=edited_lesson, form=form, week=week)

    else:
        flash('Нет прав администратора', 'error')
        return redirect(url_for('timetable.full_timetable', week=0))


@timetable.route('/lesson/<string:lesson_str>', methods=['GET', 'POST'])
@login_required
def lesson(lesson_str):
    if current_user.rights in ["admin", "user", "teacher"]:
        subject_lesson, lesson_subject = show_lesson(lesson_str)

        if subject_lesson:
            if request.method == 'POST':
                try:
                    message = handle_lesson(request.form, lesson_subject, subject_lesson, current_user)
                    if 'registered_btn' in request.form:
                        db.session.commit()
                        if message:
                            flash(message[0], message[1])

                    else:
                        if message:
                            if message[1] == 'success':
                                db.session.commit()
                                flash(message[0], message[1])
                            else:
                                db.session.rollback()
                                flash(message[0], message[1])
                        else:
                            db.session.commit()

                except Exception as e:
                    db.session.rollback()
                    flash(f'Ошибка при проведении занятия: {str(e)}', 'error')

                return redirect(url_for('timetable.lesson', lesson_str=f'1-{subject_lesson.id}'))

            all_clients = Person.query.filter(Person.status.in_(["Клиент", "Лид"])).order_by(Person.last_name,
                                                                                             Person.first_name).all()
            possible_clients = [client for client in all_clients if client not in subject_lesson.students]

            other_lessons = Subject.query.filter(
                Subject.id != lesson_subject.id,
                ~Subject.subject_type.has(SubjectType.name.in_(['school', 'event']))
            ).order_by(Subject.name).all()
            month_index = calc_month_index(subject_lesson.date)

            return render_template('timetable/lesson.html', subject_lesson=subject_lesson, clients=possible_clients,
                                   lesson_subject=lesson_subject, other_lessons=other_lessons,
                                   today=get_today_date(), month_index=month_index)

        else:
            if lesson_subject.subject_type.name == 'after_school':
                return redirect(url_for('after_school.after_school_month', month_index=0))

            elif lesson_subject:
                other_lessons = Subject.query.filter(
                    Subject.id != lesson_subject.id,
                    ~Subject.subject_type.has(SubjectType.name.in_(['school', 'event']))
                ).order_by(Subject.name).all()

                return render_template('timetable.lesson.html', subject_lesson=subject_lesson, lesson_subject=lesson_subject,
                                       other_lessons=other_lessons)

            else:
                flash("Такого занятия нет", 'error')
                return redirect(url_for('school.subjects.subjects'))

    else:
        flash('Нет прав администратора', 'error')
        return redirect(url_for('main.index'))


@timetable.route('/generate-timetable/<string:week>')
@login_required
def generate_timetable(week):
    try:
        workbook, dates = download_timetable(int(week), current_user)

        filename = f"timetable_{dates[0].replace('.', '_')}_{dates[-1].replace('.', '_')}.xlsx"
        excel_buffer = BytesIO()
        workbook.save(excel_buffer)
        excel_buffer.seek(0)
        return send_file(excel_buffer, download_name=filename, as_attachment=True)

    except Exception as e:
        flash(f'Ошибка при скачивании файла: {str(e)}', 'error')
        return
