"""phase1_foundation

Revision ID: 0002_phase1_foundation
Revises: 0001_initial_schema
Create Date: 2026-08-19 12:48:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0002_phase1_foundation'
down_revision: Union[str, Sequence[str], None] = '0001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update users (add firebase_uid)
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('firebase_uid', sa.String(), nullable=True))
        batch_op.create_index(batch_op.f('ix_users_firebase_uid'), ['firebase_uid'], unique=True)

    # 2. Update courses (add short_description, original_price, level, instructor, is_free, updated_at)
    with op.batch_alter_table('courses', schema=None) as batch_op:
        batch_op.add_column(sa.Column('short_description', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('original_price', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('level', sa.String(), server_default='Beginner', nullable=True))
        batch_op.add_column(sa.Column('instructor', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('is_free', sa.Boolean(), server_default='0', nullable=True))
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True))
        batch_op.alter_column('title', existing_type=sa.VARCHAR(), nullable=False)
        batch_op.alter_column('price', existing_type=sa.FLOAT(), nullable=False)

    # 3. Update lessons (add description, circuit_diagram, is_free_preview)
    with op.batch_alter_table('lessons', schema=None) as batch_op:
        batch_op.add_column(sa.Column('description', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('circuit_diagram', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('is_free_preview', sa.Boolean(), server_default='0', nullable=True))
        batch_op.alter_column('course_id', existing_type=sa.INTEGER(), nullable=False)
        batch_op.alter_column('title', existing_type=sa.VARCHAR(), nullable=False)

    # 4. Update products (add original_price, is_active, updated_at)
    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.add_column(sa.Column('original_price', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('is_active', sa.Boolean(), server_default='1', nullable=True))
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True))
        batch_op.alter_column('name', existing_type=sa.VARCHAR(), nullable=False)
        batch_op.alter_column('price', existing_type=sa.FLOAT(), nullable=False)

    # 5. Update orders (add razorpay fields, make shipping_address_json nullable)
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.add_column(sa.Column('razorpay_order_id', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('razorpay_payment_id', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('razorpay_signature', sa.String(), nullable=True))
        batch_op.alter_column('shipping_address_json', existing_type=sa.TEXT(), nullable=True)
        batch_op.create_index(batch_op.f('ix_orders_razorpay_order_id'), ['razorpay_order_id'], unique=False)

    # 6. Update order_items (add name_snapshot, fulfillment_status)
    with op.batch_alter_table('order_items', schema=None) as batch_op:
        batch_op.add_column(sa.Column('name_snapshot', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('fulfillment_status', sa.String(), server_default='PENDING', nullable=True))

    # 7. Update payments (unique indexes on gateway_order_id and gateway_payment_id)
    with op.batch_alter_table('payments', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_payments_gateway_order_id'))
        batch_op.create_index(batch_op.f('ix_payments_gateway_order_id'), ['gateway_order_id'], unique=True)
        batch_op.drop_index(batch_op.f('ix_payments_gateway_payment_id'))
        batch_op.create_index(batch_op.f('ix_payments_gateway_payment_id'), ['gateway_payment_id'], unique=True)

    # 8. Update course_entitlements (add status, expires_at, revoked_at, updated_at, and unique constraint)
    with op.batch_alter_table('course_entitlements', schema=None) as batch_op:
        batch_op.add_column(sa.Column('status', sa.String(), server_default='ACTIVE', nullable=False))
        batch_op.add_column(sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True))
        batch_op.create_index(batch_op.f('ix_course_entitlements_status'), ['status'], unique=False)
        batch_op.create_unique_constraint('uq_user_course_entitlement', ['user_id', 'course_id'])


def downgrade() -> None:
    with op.batch_alter_table('course_entitlements', schema=None) as batch_op:
        batch_op.drop_constraint('uq_user_course_entitlement', type_='unique')
        batch_op.drop_index(batch_op.f('ix_course_entitlements_status'))
        batch_op.drop_column('updated_at')
        batch_op.drop_column('revoked_at')
        batch_op.drop_column('expires_at')
        batch_op.drop_column('status')

    with op.batch_alter_table('payments', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_payments_gateway_payment_id'))
        batch_op.create_index(batch_op.f('ix_payments_gateway_payment_id'), ['gateway_payment_id'], unique=False)
        batch_op.drop_index(batch_op.f('ix_payments_gateway_order_id'))
        batch_op.create_index(batch_op.f('ix_payments_gateway_order_id'), ['gateway_order_id'], unique=False)

    with op.batch_alter_table('order_items', schema=None) as batch_op:
        batch_op.drop_column('fulfillment_status')
        batch_op.drop_column('name_snapshot')

    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_orders_razorpay_order_id'))
        batch_op.drop_column('razorpay_signature')
        batch_op.drop_column('razorpay_payment_id')
        batch_op.drop_column('razorpay_order_id')
        batch_op.alter_column('shipping_address_json', existing_type=sa.TEXT(), nullable=False)

    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.alter_column('price', existing_type=sa.FLOAT(), nullable=True)
        batch_op.alter_column('name', existing_type=sa.VARCHAR(), nullable=True)
        batch_op.drop_column('updated_at')
        batch_op.drop_column('is_active')
        batch_op.drop_column('original_price')

    with op.batch_alter_table('lessons', schema=None) as batch_op:
        batch_op.alter_column('title', existing_type=sa.VARCHAR(), nullable=True)
        batch_op.alter_column('course_id', existing_type=sa.INTEGER(), nullable=True)
        batch_op.drop_column('is_free_preview')
        batch_op.drop_column('circuit_diagram')
        batch_op.drop_column('description')

    with op.batch_alter_table('courses', schema=None) as batch_op:
        batch_op.alter_column('price', existing_type=sa.FLOAT(), nullable=True)
        batch_op.alter_column('title', existing_type=sa.VARCHAR(), nullable=True)
        batch_op.drop_column('updated_at')
        batch_op.drop_column('is_free')
        batch_op.drop_column('instructor')
        batch_op.drop_column('level')
        batch_op.drop_column('original_price')
        batch_op.drop_column('short_description')

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_users_firebase_uid'))
        batch_op.drop_column('firebase_uid')
