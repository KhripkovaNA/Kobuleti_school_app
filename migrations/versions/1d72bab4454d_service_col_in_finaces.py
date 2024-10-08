"""service col in finaces

Revision ID: 1d72bab4454d
Revises: 506002c5072f
Create Date: 2024-06-06 16:09:51.064643

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1d72bab4454d'
down_revision = '506002c5072f'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('finance', schema=None) as batch_op:
        batch_op.add_column(sa.Column('service', sa.String(length=16), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('finance', schema=None) as batch_op:
        batch_op.drop_column('service')

    # ### end Alembic commands ###
