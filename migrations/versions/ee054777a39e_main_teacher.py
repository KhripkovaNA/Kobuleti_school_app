"""main_teacher

Revision ID: ee054777a39e
Revises: 140478b368db
Create Date: 2023-12-05 13:13:27.057008

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ee054777a39e'
down_revision = '140478b368db'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('teacher_class_table', schema=None) as batch_op:
        batch_op.add_column(sa.Column('main_teacher', sa.Boolean(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('teacher_class_table', schema=None) as batch_op:
        batch_op.drop_column('main_teacher')

    # ### end Alembic commands ###