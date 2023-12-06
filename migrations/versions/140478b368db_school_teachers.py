"""school_teachers

Revision ID: 140478b368db
Revises: 813c44ca1cac
Create Date: 2023-12-05 12:37:44.987716

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '140478b368db'
down_revision = '813c44ca1cac'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('teacher_class_table',
    sa.Column('class_id', sa.Integer(), nullable=True),
    sa.Column('teacher_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['class_id'], ['school_classes.id'], name=op.f('fk_teacher_class_table_class_id_school_classes')),
    sa.ForeignKeyConstraint(['teacher_id'], ['persons.id'], name=op.f('fk_teacher_class_table_teacher_id_persons'))
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('teacher_class_table')
    # ### end Alembic commands ###
