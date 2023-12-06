"""class_students, attending_status

Revision ID: 813c44ca1cac
Revises: e9507e240ef4
Create Date: 2023-12-05 11:42:29.520867

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '813c44ca1cac'
down_revision = 'e9507e240ef4'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('persons', schema=None) as batch_op:
        batch_op.add_column(sa.Column('school_class_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(batch_op.f('fk_persons_school_class_id_school_classes'), 'school_classes', ['school_class_id'], ['id'])

    with op.batch_alter_table('student_lesson_attended_table', schema=None) as batch_op:
        batch_op.add_column(sa.Column('attending_status', sa.String(length=50), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('student_lesson_attended_table', schema=None) as batch_op:
        batch_op.drop_column('attending_status')

    with op.batch_alter_table('persons', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_persons_school_class_id_school_classes'), type_='foreignkey')
        batch_op.drop_column('school_class_id')

    # ### end Alembic commands ###
