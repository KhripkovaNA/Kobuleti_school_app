from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, BooleanField, SelectMultipleField, DecimalField
from wtforms.validators import InputRequired, NumberRange, StopValidation, ValidationError


def validate_subject_school_price(form, field):
    if form.no_subject_school_price.data:
        field.errors[:] = []
        raise StopValidation()


def validate_subscription_types(form, field):
    if not form.no_subscription.data and not field.data:
        raise ValidationError('Заполните это поле')


class SubjectForm(FlaskForm):
    subject_name = StringField(validators=[InputRequired(message='Заполните это поле')])
    subject_short_name = StringField(validators=[InputRequired(message='Заполните это поле')])
    teachers = SelectMultipleField(choices=[])


class EditExtraSubjectForm(SubjectForm):
    subject_price = DecimalField(places=1, default=20.0,
                                 validators=[InputRequired(message='Заполните это поле'),
                                             NumberRange(0, 1000, message='Неправильный формат')])
    subject_school_price = DecimalField(places=1, default=20.0,
                                        validators=[validate_subject_school_price,
                                                    InputRequired(message='Заполните это поле'),
                                                    NumberRange(0, 1000, message='Неправильный формат')])

    no_subject_school_price = BooleanField()


class ExtraSubjectForm(EditExtraSubjectForm):
    subject_type = SelectField(choices=[])
    subscription_types = SelectMultipleField(choices=[], validators=[validate_subscription_types])
    no_subscription = BooleanField()
