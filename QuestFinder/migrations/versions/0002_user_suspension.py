"""user suspension and quest_update notifications

Revision ID: 0002_user_suspension
Revises: 0001_initial
Create Date: 2026-11-26 11:10:00

"""
from alembic import op
import sqlalchemy as sa


revision = '0002_user_suspension'
down_revision = '0001_initial'
branch_labels = None
depends_on = None

OLD_KINDS = ("quest_accepted_by_worker", "worker_confirmed", "quest_completed", "verification_result")
NEW_KINDS = OLD_KINDS + ("quest_update",)


def _kinds(values):
    return "kind IN (" + ", ".join(f"'{v}'" for v in values) + ")"


def upgrade():
    with op.batch_alter_table('users') as batch:
        batch.add_column(sa.Column('suspended_until', sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column('suspended_at', sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column('suspension_reason', sa.String(length=255), nullable=True))
    op.create_index('ix_users_suspended_until', 'users', ['suspended_until'])

    op.drop_constraint('ck_notifications_kind', 'notifications', type_='check')
    op.create_check_constraint('ck_notifications_kind', 'notifications', _kinds(NEW_KINDS))


def downgrade():
    op.execute("DELETE FROM notifications WHERE kind = 'quest_update'")
    op.drop_constraint('ck_notifications_kind', 'notifications', type_='check')
    op.create_check_constraint('ck_notifications_kind', 'notifications', _kinds(OLD_KINDS))

    op.drop_index('ix_users_suspended_until', table_name='users')
    with op.batch_alter_table('users') as batch:
        batch.drop_column('suspension_reason')
        batch.drop_column('suspended_at')
        batch.drop_column('suspended_until')
