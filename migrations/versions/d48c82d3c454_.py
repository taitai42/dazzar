""" 7/ Add ban date to user model.

Revision ID: d48c82d3c454
Revises: 5660023a270f
Create Date: 2016-12-22 14:56:54.668307

"""

# revision identifiers, used by Alembic.
revision = 'd48c82d3c454'
down_revision = '5660023a270f'

from alembic import op
import sqlalchemy as sa


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user', sa.Column('ban_date', sa.DateTime(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('user', 'ban_date')
    # ### end Alembic commands ###
