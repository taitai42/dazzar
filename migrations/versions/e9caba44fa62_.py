"""Add avatar and verified.

Revision ID: e9caba44fa62
Revises: da31f53317e6
Create Date: 2016-11-12 12:57:46.362096

"""

# revision identifiers, used by Alembic.
revision = 'e9caba44fa62'
down_revision = 'da31f53317e6'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('profile_scan_info', 'last_scan',
               existing_type=postgresql.TIMESTAMP(),
               nullable=False)
    op.alter_column('profile_scan_info', 'last_scan_request',
               existing_type=postgresql.TIMESTAMP(),
               nullable=False)
    op.add_column('user', sa.Column('avatar', sa.String(), nullable=True))
    op.add_column('user', sa.Column('avatar_full', sa.String(), nullable=True))
    op.add_column('user', sa.Column('avatar_medium', sa.String(), nullable=True))
    op.add_column('user', sa.Column('verified', sa.Boolean(), server_default='False', nullable=False))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('user', 'verified')
    op.drop_column('user', 'avatar_medium')
    op.drop_column('user', 'avatar_full')
    op.drop_column('user', 'avatar')
    op.alter_column('profile_scan_info', 'last_scan_request',
               existing_type=postgresql.TIMESTAMP(),
               nullable=True)
    op.alter_column('profile_scan_info', 'last_scan',
               existing_type=postgresql.TIMESTAMP(),
               nullable=True)
    ### end Alembic commands ###
