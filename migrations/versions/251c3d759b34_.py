"""empty message

Revision ID: 251c3d759b34
Revises: None
Create Date: 2016-10-21 13:19:33.175729

"""

# revision identifiers, used by Alembic.
revision = '251c3d759b34'
down_revision = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('match_vip',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('status', sa.Integer(), nullable=False),
    sa.Column('created', sa.DateTime(), nullable=False),
    sa.Column('password', sa.String(length=20), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_match_vip_created'), 'match_vip', ['created'], unique=False)
    op.create_index(op.f('ix_match_vip_status'), 'match_vip', ['status'], unique=False)
    user_permissions = op.create_table('user_permission',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=20), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('user',
    sa.Column('id', sa.String(length=40), nullable=False),
    sa.Column('nickname', sa.String(length=20), nullable=True),
    sa.Column('current_match', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['current_match'], ['match_vip.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_nickname'), 'user', ['nickname'], unique=False)
    op.create_table('permissions',
    sa.Column('permission_id', sa.Integer(), nullable=True),
    sa.Column('user_id', sa.String(length=40), nullable=True),
    sa.ForeignKeyConstraint(['permission_id'], ['user_permission.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], )
    )
    op.create_table('players',
    sa.Column('user_id', sa.String(length=40), nullable=True),
    sa.Column('match_vip_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['match_vip_id'], ['match_vip.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], )
    )
    op.create_table('queue_vip',
    sa.Column('id', sa.String(length=40), nullable=False),
    sa.Column('added', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_queue_vip_added'), 'queue_vip', ['added'], unique=False)
    ### end Alembic commands ###

    ### Add permissions ###
    op.bulk_insert(user_permissions,
                   [
                       {'name': 'admin'},
                       {'name': 'play_vip'},
                       {'name': 'vouch_vip'}
                   ])
    ##

def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_queue_vip_added'), table_name='queue_vip')
    op.drop_table('queue_vip')
    op.drop_table('players')
    op.drop_table('permissions')
    op.drop_index(op.f('ix_user_nickname'), table_name='user')
    op.drop_table('user')
    op.drop_table('user_permission')
    op.drop_index(op.f('ix_match_vip_status'), table_name='match_vip')
    op.drop_index(op.f('ix_match_vip_created'), table_name='match_vip')
    op.drop_table('match_vip')
    ### end Alembic commands ###
