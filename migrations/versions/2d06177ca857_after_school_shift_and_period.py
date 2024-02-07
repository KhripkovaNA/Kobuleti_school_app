"""after school shift and period

Revision ID: 2d06177ca857
Revises: d26428e51941
Create Date: 2024-02-07 17:17:23.749797

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2d06177ca857'
down_revision = 'd26428e51941'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('subscriptions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('shift', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('period', sa.String(length=50), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('subscriptions', schema=None) as batch_op:
        batch_op.drop_column('period')
        batch_op.drop_column('shift')

    # ### end Alembic commands ###
