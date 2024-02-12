from flask import request
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, PasswordField, SelectField, RadioField, FormField, FieldList
from wtforms.validators import ValidationError, DataRequired, Length, InputRequired, Optional
from app.models import Person
from app import db
from datetime import datetime


class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(message='Заполните это поле')])
    password = PasswordField(validators=[DataRequired(message='Заполните это поле')])


def validate_date_format(form, field):
    try:
        datetime.strptime(field.data, '%d.%m.%Y')
    except ValueError:
        raise ValidationError('Неправильный формат даты')


def validate_parent_name(form, field):
    if form.contact_select.data == 'Добавить' and form.relation.data != 'Сам ребенок' and not field.data:
        raise ValidationError('Заполните это поле')


def validate_parent_select(form, field):
    if form.contact_select.data == 'Выбрать' and not field.data:
        raise ValidationError('Выберете контакт')


class ContactForm(FlaskForm):
    relation = SelectField(choices=[('Мама', 'Мама'), ('Папа', 'Папа'),
                                    ('Сам ребенок', 'Сам ребенок'), ('Другое', 'Другое контактное лицо')])
    other_relation = StringField()
    contact_select = SelectField(choices=[('Добавить', 'Добавить'), ('Выбрать', 'Выбрать из списка')])
    selected_contact = SelectField(choices=[], validate_choice=False)
    parent_last_name = StringField(validators=[validate_parent_name])
    parent_first_name = StringField(validators=[validate_parent_name])
    parent_patronym = StringField()
    telegram = StringField()
    phone = StringField()
    other_contact = StringField()


class ChildForm(FlaskForm):
    last_name = StringField(validators=[InputRequired(message='Заполните это поле')])
    first_name = StringField(validators=[InputRequired(message='Заполните это поле')])
    patronym = StringField()
    dob = StringField(validators=[Optional(), validate_date_format])
    status = SelectField(choices=[('Клиент', 'Клиент'), ('Лид', 'Лид')])
    contacts = FieldList(FormField(ContactForm), min_entries=1)
