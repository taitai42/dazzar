"""/6 Remove not necessary vip_mmr

Revision ID: 5660023a270f
Revises: 7b46ed274746
Create Date: 2016-11-29 00:11:51.665685

"""

# revision identifiers, used by Alembic.
revision = '5660023a270f'
down_revision = '7b46ed274746'

from alembic import op
import sqlalchemy as sa


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('ix_user_vip_mmr', table_name='user')
    op.drop_column('user', 'vip_mmr')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user', sa.Column('vip_mmr', sa.INTEGER(), autoincrement=False, nullable=True))
    op.create_index('ix_user_vip_mmr', 'user', ['vip_mmr'], unique=False)
    # ### end Alembic commands ###