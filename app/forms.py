from flask import request
from flask_wtf import FlaskForm, Form
from wtforms import StringField, TextAreaField, PasswordField, SelectField, \
    FormField, FieldList, HiddenField, BooleanField, IntegerField, SelectMultipleField, ColorField
from wtforms.validators import ValidationError, DataRequired, InputRequired, Optional, NumberRange
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


def validate_client_name(form, field):
    if form.client_select.data == 'Добавить' and not field.data:
        raise ValidationError('Заполните это поле')


class ContactForm(FlaskForm):
    telegram = StringField()
    phone = StringField()
    other_contact = StringField()


class ContForm(ContactForm):
    relation = SelectField(choices=[('Мама', 'Мама'), ('Папа', 'Папа'),
                                    ('Сам ребенок', 'Сам ребенок'), ('Другое', 'Другое контактное лицо')])
    other_relation = StringField()
    contact_select = SelectField(choices=[('Добавить', 'Добавить'), ('Выбрать', 'Выбрать из списка')])
    selected_contact = SelectField(choices=[], validate_choice=False)
    parent_last_name = StringField(validators=[validate_parent_name])
    parent_first_name = StringField(validators=[validate_parent_name])
    parent_patronym = StringField()

    def validate_selected_contact(self, field):
        if self.contact_select.data == 'Выбрать' and not field.data:
            raise ValidationError('Выберете контакт')


class ContactPersonForm(ContForm):
    primary_contact = HiddenField()


class PersonForm(FlaskForm):
    last_name = StringField(validators=[InputRequired(message='Заполните это поле')])
    first_name = StringField(validators=[InputRequired(message='Заполните это поле')])
    patronym = StringField()


class ChildForm(PersonForm):
    dob = StringField(validators=[Optional(), validate_date_format])
    status = SelectField(choices=[('Клиент', 'Клиент'), ('Лид', 'Лид')])
    contacts = FieldList(FormField(ContactPersonForm), min_entries=1)


class AdultPersonForm(ContactForm):
    client_select = SelectField(choices=[('Добавить', 'Добавить'), ('Выбрать', 'Выбрать из списка')])
    selected_client = selected_contact = SelectField(choices=[], validate_choice=False)
    last_name = StringField(validators=[validate_client_name])
    first_name = StringField(validators=[validate_client_name])
    patronym = StringField()


class AdultForm(AdultPersonForm):
    status = SelectField(choices=[('Клиент', 'Клиент'), ('Лид', 'Лид')])


class EditStudentForm(PersonForm):
    dob = StringField(validators=[Optional(), validate_date_format])
    status = SelectField(choices=[('Клиент', 'Клиент'), ('Лид', 'Лид'), ("Пауза", "Пауза"), ("Закрыт", "Закрыт")])
    pause_until = StringField(validators=[Optional(), validate_date_format])
    leaving_reason = TextAreaField()


class EditContactPersonForm(PersonForm):
    telegram = StringField()
    phone = StringField()
    other_contact = StringField()


class EditAddContPersonForm(EditContactPersonForm):
    primary_contact = BooleanField()


class AddContForm(ContactForm):
    primary_contact = BooleanField()


class NewContactPersonForm(ContForm):
    primary_contact = BooleanField()


class SubscriptionForm(Form):
    subscription_id = HiddenField()
    subject_name = StringField()
    lessons = IntegerField(validators=[InputRequired(message='Заполните это поле'),
                                       NumberRange(0, 20, message='Неправильный формат')])
    end_date = StringField(validators=[InputRequired(message='Заполните это поле'), validate_date_format])


class SubscriptionsEditForm(FlaskForm):
    subscriptions = FieldList(FormField(SubscriptionForm), min_entries=0, max_entries=100)


class EmployeeForm(AdultPersonForm):
    roles = SelectMultipleField(choices=[], validators=[InputRequired(message='Выберете должность')],
                                validate_choice=False)
    subjects = SelectMultipleField(choices=[], validate_choice=False)
    teacher_color = ColorField(default="#D9D9D9")

