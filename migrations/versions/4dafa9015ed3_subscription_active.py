"""subscription active

Revision ID: 4dafa9015ed3
Revises: 9cb2a1eec37c
Create Date: 2023-12-19 16:49:53.182663

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4dafa9015ed3'
down_revision = '9cb2a1eec37c'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('subscriptions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('active', sa.Boolean(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('subscriptions', schema=None) as batch_op:
        batch_op.drop_column('active')

    # ### end Alembic commands ###