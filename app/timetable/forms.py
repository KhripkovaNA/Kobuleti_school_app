from flask_wtf import FlaskForm
from wtforms import StringField, SelectMultipleField, SelectField, BooleanField, FieldList, FormField
from wtforms.validators import InputRequired, Optional
from app.school.forms import validate_time_format, validate_date_format


class LessonForm(FlaskForm):
    start_time = StringField(validators=[InputRequired(message='Заполните это поле'), validate_time_format])
    end_time = StringField(validators=[InputRequired(message='Заполните это поле'), validate_time_format])
    subject = SelectField(choices=[], validators=[InputRequired(message='Заполните это поле')], validate_choice=False)
    school_classes = SelectMultipleField(choices=[], validators=[Optional()], validate_choice=False)
    split_classes = BooleanField()
    room = SelectField(choices=[], validators=[InputRequired(message='Заполните это поле')], validate_choice=False)
    teacher = SelectField(choices=[], validators=[InputRequired(message='Заполните это поле')], validate_choice=False)


class AddLessonsForm(FlaskForm):
    lesson_date = StringField(validators=[InputRequired(message='Заполните это поле'), validate_date_format])
    lessons = FieldList(FormField(LessonForm), min_entries=1)


class EditLessonForm(LessonForm):
    lesson_date = StringField(validators=[InputRequired(message='Заполните это поле'), validate_date_format])
