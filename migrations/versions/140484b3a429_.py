"""empty message

Revision ID: 140484b3a429
Revises: ee08bbc21371
Create Date: 2024-01-31 18:46:10.912698

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '140484b3a429'
down_revision = 'ee08bbc21371'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('meter', schema=None) as batch_op:
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(), nullable=True))
        batch_op.alter_column('meter_number',
               existing_type=sa.TEXT(length=255),
               type_=sa.String(length=255),
               existing_nullable=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('meter', schema=None) as batch_op:
        batch_op.alter_column('meter_number',
               existing_type=sa.String(length=255),
               type_=sa.TEXT(length=255),
               existing_nullable=False)
        batch_op.drop_column('updated_at')

    # ### end Alembic commands ###
