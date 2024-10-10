from wtforms import SelectMultipleField, ColorField
from wtforms.validators import InputRequired
from app.school.forms import AdultPersonForm


class EmployeeForm(AdultPersonForm):
    roles = SelectMultipleField(choices=[], validators=[InputRequired(message='Выберете должность')],
                                validate_choice=False)
    subjects = SelectMultipleField(choices=[], validate_choice=False)
    school_classes = SelectMultipleField(choices=[], validate_choice=False)
    teacher_color = ColorField(default="#D9D9D9")
