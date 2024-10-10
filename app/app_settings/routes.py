from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from .models import Room, SubscriptionType
from .service import user_action
from app import db
from app.auth.models import User
from app.school.models import Person
from app.school_classes.models import SchoolClass


app_settings = Blueprint('settings', __name__)


@app_settings.route('/settings')
@login_required
def settings():
    if current_user.rights in ['admin', 'user']:
        rooms = Room.query.all()
        school_classes = SchoolClass.query.order_by(SchoolClass.school_class, SchoolClass.school_name).all()
        subscription_types = SubscriptionType.query.filter(SubscriptionType.lessons.isnot(None)).all()
        after_school_prices = SubscriptionType.query.filter(SubscriptionType.period != '').all()
        school_children = Person.query.filter(
            Person.school_class_id.is_not(None)
        ).order_by(Person.last_name, Person.first_name).all()
        parent_users = User.query.filter_by(rights="parent").all()

        return render_template('app_settings/settings.html', rooms=rooms, parents=parent_users,
                               children=school_children, school_classes=school_classes,
                               subscription_types=subscription_types, after_school_prices=after_school_prices,
                               )

    else:
        return render_template('app_settings/settings.html')


@app_settings.route('/change_parent', methods=['POST'])
@login_required
def change_parent():
    try:
        if current_user.rights == 'admin':
            if 'change_parent_btn' in request.form:
                parent_id = int(request.form.get('change_parent_btn'))
                children_ids = request.form.getlist(f'children_{parent_id}')
                parent = User.query.filter_by(id=parent_id).first()

                if parent and children_ids:
                    children_ids = [int(child_id) for child_id in children_ids]
                    children = Person.query.filter(
                        Person.id.in_(children_ids),
                        Person.school_class_id.is_not(None)
                    ).all()
                    if set(parent.user_persons) != set(children):
                        parent.user_persons = [child for child in children]
                        user_action(current_user, f"Изменение списка детей у родителя {parent.username}")
                        db.session.commit()
                        flash("Изменения внесены", 'success')

                elif parent and not children_ids:
                    flash("Не выбраны дети", 'error')

                else:
                    flash("Такого родителя нет", 'error')

            if 'delete_parent_btn' in request.form:
                parent_id = int(request.form.get('delete_parent_btn'))
                parent = User.query.filter_by(id=parent_id).first()
                db.session.delete(parent)
                user_action(current_user, f"Удаление родителя {parent.username}")
                db.session.commit()
                flash(f"Родитель {parent.username} удален", 'success')

        else:
            flash('Нет прав руководителя', 'error')

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при изменении родителя: {str(e)}', 'error')

    return redirect(url_for('settings.settings'))


@app_settings.route('/change-add-room', methods=['POST'])
@login_required
def change_add_room():
    try:
        if current_user.rights == 'admin':
            if 'change_room_btn' in request.form:
                room_id = int(request.form.get('change_room_btn')) if request.form.get('change_room_btn').isdigit() \
                    else None
                new_name = request.form.get(f'name_{room_id}')
                new_color = request.form.get(f'color_{room_id}')
                room = Room.query.filter_by(id=room_id).first()
                if room and new_name and new_color:
                    room.name = new_name
                    room.color = new_color
                    user_action(current_user, f"Внесение изменений в кабинет '{room.name}'")
                    db.session.commit()
                    flash(f"Кабинет '{room.name}' изменен", 'success')

            if 'delete_room_btn' in request.form:
                room_id = int(request.form.get('delete_room_btn')) if request.form.get('delete_room_btn').isdigit() \
                    else None
                room = Room.query.filter_by(id=room_id).first()
                if room:
                    db.session.delete(room)
                    user_action(current_user, f"Удаление кабинета '{room.name}'")
                    db.session.commit()
                    flash(f"Кабинет '{room.name}' удален", 'success')

            if 'add_room' in request.form:
                room_name = request.form.get('room_name')
                room_color = request.form.get('room_color')
                new_room = Room(name=room_name, color=room_color)
                db.session.add(new_room)
                user_action(current_user, f"Добавление кабинета '{new_room.name}'")
                db.session.commit()
                flash(f"Новый кабинет '{new_room.name}' добавлен в систему", 'success')

        else:
            flash('Нет прав руководителя', 'error')

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при добавлении/изменении кабинета: {str(e)}', 'error')

    return redirect(url_for('settings.settings'))


@app_settings.route('/change-add-class', methods=['POST'])
@login_required
def change_add_class():
    try:
        if current_user.rights == 'admin':
            if 'change_class_btn' in request.form:
                class_id = int(request.form.get('change_class_btn')) if request.form.get('change_class_btn').isdigit() \
                    else None
                new_school_class = int(request.form.get(f'class_{class_id}')) \
                    if request.form.get(f'class_{class_id}').isdigit() else None
                new_school_name = request.form.get(f'name_{class_id}')
                school_class = SchoolClass.query.filter_by(id=class_id).first()
                if school_class and new_school_class and new_school_name:
                    school_class.school_class = new_school_class
                    school_class.school_name = new_school_name
                    user_action(current_user, f"Внесение изменений в класс '{school_class.school_name}'")
                    db.session.commit()
                    flash(f"Класс '{school_class.school_name}' изменен", 'success')

            if 'delete_class_btn' in request.form:
                class_id = int(request.form.get('delete_class_btn')) if request.form.get('delete_class_btn').isdigit() \
                    else None
                school_class = SchoolClass.query.filter_by(id=class_id).first()
                if school_class:
                    db.session.delete(school_class)
                    user_action(current_user, f"Удаление класса '{school_class.school_name}'")
                    db.session.commit()
                    flash(f"Класс '{school_class.school_name}' удален", 'success')

            if 'add_class' in request.form:
                new_school_class = int(request.form.get('new_school_class')) \
                    if request.form.get('new_school_class').isdigit() else None
                new_school_name = request.form.get('new_school_name')
                new_class = SchoolClass(school_class=new_school_class, school_name=new_school_name)
                db.session.add(new_class)
                user_action(current_user, f"Добавление класса '{new_class.school_name}'")
                db.session.commit()
                flash(f"Новый класс '{new_class.school_name}' добавлен в систему", 'success')

        else:
            flash('Нет прав руководителя', 'error')

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при добавлении/изменении кабинета: {str(e)}', 'error')

    return redirect(url_for('settings.settings'))


@app_settings.route('/change-add-subscription', methods=['POST'])
@login_required
def change_add_subscription():
    try:
        if current_user.rights == 'admin':
            if 'change_subscription_btn' in request.form:
                subscription_type_id = int(request.form.get('change_class_subscription')) \
                    if request.form.get('change_class_subscription').isdigit() else None
                subscription_lessons = int(request.form.get(f'lessons_{subscription_type_id}')) \
                    if request.form.get(f'lessons_{subscription_type_id}').isdigit() else None
                subscription_duration = int(request.form.get(f'duration_{subscription_type_id}')) \
                    if request.form.get(f'duration_{subscription_type_id}').isdigit() else None
                subscription_price = request.form.get(f'price_{subscription_type_id}').replace(',', '.')
                if not subscription_price.replace('.', '').isdigit():
                    flash('Неправильный формат цены', 'error')
                    return redirect(url_for('settings.settings'))

                subscription_type = SubscriptionType.query.filter_by(id=subscription_type_id).first()
                if subscription_type and subscription_lessons and subscription_duration:
                    same_subscription_type = SubscriptionType.query.filter_by(
                        lessons=subscription_lessons,
                        duration=subscription_duration,
                        price=float(subscription_price)
                    ).all()
                    if not same_subscription_type:
                        subscription_type.lessons = subscription_lessons
                        subscription_type.duration = subscription_duration
                        subscription_type.price = float(subscription_price)
                        user_action(current_user, "Изменение абонемента")
                        db.session.commit()
                        flash('Абонемент изменен', 'success')
                    else:
                        flash('Такой абонемент уже есть', 'error')

            if 'delete_subscription_btn' in request.form:
                subscription_type_id = int(request.form.get('delete_subscription_btn')) \
                    if request.form.get('delete_subscription_btn').isdigit() else None
                subscription_type = SubscriptionType.query.filter_by(id=subscription_type_id).first()
                if subscription_type:
                    db.session.delete(subscription_type)
                    user_action(current_user, "Удаление абонемента")
                    db.session.commit()
                    flash('Абонемент удален', 'success')

            if 'add_subscription' in request.form:
                new_subscription_lessons = int(request.form.get('new_subscription_lessons')) \
                    if request.form.get('new_subscription_lessons').isdigit() else None
                new_subscription_duration = int(request.form.get('new_subscription_duration')) \
                    if request.form.get('new_subscription_duration').isdigit() else None
                new_subscription_price = request.form.get('new_subscription_price').replace(',', '.')
                if not new_subscription_price.replace('.', '').isdigit():
                    flash('Неправильный формат цены', 'error')
                    return redirect(url_for('settings.settings'))
                if new_subscription_lessons and new_subscription_duration:
                    same_subscription_type = SubscriptionType.query.filter_by(
                        lessons=new_subscription_lessons,
                        duration=new_subscription_duration,
                        price=float(new_subscription_price)
                    ).all()
                    if not same_subscription_type:
                        new_subscription = SubscriptionType(
                            lessons=new_subscription_lessons,
                            duration=new_subscription_duration,
                            price=float(new_subscription_price)
                        )
                        db.session.add(new_subscription)
                        user_action(current_user, "Добавление абонемента")
                        db.session.commit()
                        flash('Новый абонемент добавлен в систему', 'success')

                    else:
                        flash('Такой абонемент уже есть', 'error')

        else:
            flash('Нет прав руководителя', 'error')

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при добавлении/изменении абонемента: {str(e)}', 'error')

    return redirect(url_for('settings.settings'))


@app_settings.route('/change-add-after-school', methods=['POST'])
@login_required
def change_add_after_school():
    try:
        if current_user.rights == 'admin':
            if 'change_after_school_btn' in request.form:
                after_school_id = int(request.form.get('change_after_school_btn')) \
                    if request.form.get('change_after_school_btn').isdigit() else None
                after_school_period = request.form.get(f'period_{after_school_id}')
                after_school_price = request.form.get(f'price_{after_school_id}').replace(',', '.')
                if not after_school_price.replace('.', '').isdigit():
                    flash('Неправильный формат цены', 'error')
                    return redirect(url_for('settings.settings'))

                after_school_type = SubscriptionType.query.filter_by(id=after_school_id).first()
                if after_school_type and after_school_period:
                    same_subscription_type = SubscriptionType.query.filter_by(
                        period=after_school_period,
                        price=float(after_school_price)
                    ).all()
                    if not same_subscription_type:
                        after_school_type.period = after_school_period
                        after_school_type.price = float(after_school_price)
                        user_action(current_user, "Изменение цены на продленку")
                        db.session.commit()
                        flash('Цена на продленку изменена', 'success')
                    else:
                        flash('Такая цена на продленку уже есть', 'error')

            if 'delete_after_school_btn' in request.form:
                after_school_id = int(request.form.get('delete_after_school_btn')) \
                    if request.form.get('delete_after_school_btn').isdigit() else None
                after_school_type = SubscriptionType.query.filter_by(id=after_school_id).first()
                if after_school_type:
                    db.session.delete(after_school_type)
                    user_action(current_user, "Удаление цены на продленку")
                    db.session.commit()
                    flash('Цена на продленку удалена', 'success')

            if 'add_after_school' in request.form:
                new_after_school_period = request.form.get('new_period')
                new_after_school_price = request.form.get('new_price').replace(',', '.')
                if not new_after_school_price.replace('.', '').isdigit():
                    flash('Неправильный формат цены', 'error')
                    return redirect(url_for('settings.settings'))

                if new_after_school_period:
                    same_subscription_type = SubscriptionType.query.filter_by(
                        period=new_after_school_period,
                        price=float(new_after_school_price)
                    ).all()
                    if not same_subscription_type:
                        new_after_school_type = SubscriptionType(
                            period=new_after_school_period,
                            price=float(new_after_school_price)
                        )
                        db.session.add(new_after_school_type)
                        user_action(current_user, "Добавление цены на продленку")
                        db.session.commit()
                        flash('Новая цена на продленку добавлена в систему', 'success')

                    else:
                        flash('Такая цена на продленку уже есть', 'error')

        else:
            flash('Нет прав руководителя', 'error')

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при добавлении/изменении цены на продленку: {str(e)}', 'error')

    return redirect(url_for('settings.settings'))


@app_settings.route('/create-user', methods=['POST'])
@login_required
def create_user():
    try:
        if current_user.rights == 'admin':
            username = request.form.get('username')
            password = request.form.get('password')
            repeat_password = request.form.get('repeat_password')
            rights = request.form.get('rights')
            if password == repeat_password:
                same_username = User.query.filter_by(username=username).all()
                if not same_username:
                    new_user = User(username=username, rights=rights)
                    new_user.set_password(password)
                    db.session.add(new_user)
                    db.session.flush()
                    if rights == 'parent':
                        children_ids = [int(child) for child in request.form.getlist('children')] \
                            if request.form.getlist('children') else []
                        children = Person.query.filter(Person.id.in_(children_ids)).all()
                        for child in children:
                            new_user.user_persons.append(child)

                    user_action(current_user, f"Добавление пользователя {new_user.username}")
                    db.session.commit()
                    flash(f'Новый пользователь {new_user.username} зарегистрирован', 'success')
                else:
                    flash(f'Пользователь {username} уже существует. Выберете другое имя пользователя', 'error')
            else:
                flash('Пароли не совпадают', 'error')

        else:
            flash('Нет прав руководителя', 'error')

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при добавлении пользователя: {str(e)}', 'error')

    return redirect(url_for('settings.settings'))


@app_settings.route('/change_password', methods=['POST'])
@login_required
def change_password():
    try:
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        if current_user.check_password(old_password):
            current_user.password = current_user.set_password(new_password)
            user_action(current_user, f"Изменение пароля")
            db.session.commit()
            flash('Пароль успешно изменен', 'success')

        else:
            flash('Неправильный пароль', 'error')

    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при изменении пароля: {str(e)}', 'error')

    return redirect(url_for('settings.settings'))
