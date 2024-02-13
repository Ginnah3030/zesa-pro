"""Add daily_consumption column

Revision ID: ee08bbc21371
Revises: 591d5916130f
Create Date: 2024-01-24 23:24:19.592242

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ee08bbc21371'
down_revision = '591d5916130f'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('meter', schema=None) as batch_op:
        batch_op.add_column(sa.Column('daily_consumption', sa.Float(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('meter', schema=None) as batch_op:
        batch_op.drop_column('daily_consumption')

    # ### end Alembic commands ###