"""001 Subscription is_after_school_field

Revision ID: b5f0960ec72f
Revises: 10a34b35ccb4
Create Date: 2024-10-11 13:35:51.211239

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b5f0960ec72f'
down_revision = '10a34b35ccb4'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('subscriptions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_after_school', sa.Boolean(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('subscriptions', schema=None) as batch_op:
        batch_op.drop_column('is_after_school')

    # ### end Alembic commands ###
