"""9/ Add mode to match page.

Revision ID: 38e5bbc1cd8f
Revises: 55b56ebe06b2
Create Date: 2017-01-06 15:59:44.268490

"""

# revision identifiers, used by Alembic.
revision = '38e5bbc1cd8f'
down_revision = '55b56ebe06b2'

from alembic import op
import sqlalchemy as sa


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('match', sa.Column('mode', sa.String(), server_default='', nullable=False))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('match', 'mode')
    # ### end Alembic commands ###
