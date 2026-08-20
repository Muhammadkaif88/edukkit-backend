"""initial_baseline_schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-08-19 12:47:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0001_initial_schema'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('phone', sa.String(), nullable=True),
        sa.Column('password_hash', sa.String(), nullable=True),
        sa.Column('role', sa.String(), server_default='student', nullable=True),
        sa.Column('approval_status', sa.String(), server_default='pending', nullable=True),
        sa.Column('is_verified', sa.Boolean(), server_default='0', nullable=True),
        sa.Column('profile_image', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    )
    op.create_index('ix_users_id', 'users', ['id'], unique=False)
    op.create_index('ix_users_name', 'users', ['name'], unique=False)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # 2. courses
    op.create_table(
        'courses',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('thumbnail', sa.String(), nullable=True),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('bunny_collection_id', sa.String(), nullable=True),
        sa.Column('teacher_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('is_published', sa.Boolean(), server_default='0', nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    )
    op.create_index('ix_courses_id', 'courses', ['id'], unique=False)
    op.create_index('ix_courses_title', 'courses', ['title'], unique=False)
    op.create_index('ix_courses_category', 'courses', ['category'], unique=False)

    # 3. lessons
    op.create_table(
        'lessons',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('course_id', sa.Integer(), sa.ForeignKey('courses.id'), nullable=True),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('video_stream_id', sa.String(), nullable=True),
        sa.Column('duration', sa.Integer(), nullable=True),
        sa.Column('notes_pdf', sa.String(), nullable=True),
        sa.Column('order_index', sa.Integer(), server_default='0', nullable=True),
    )
    op.create_index('ix_lessons_id', 'lessons', ['id'], unique=False)
    op.create_index('ix_lessons_title', 'lessons', ['title'], unique=False)

    # 4. products
    op.create_table(
        'products',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('stock', sa.Integer(), server_default='0', nullable=True),
        sa.Column('images', sa.String(), nullable=True),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('type', sa.String(), server_default='diy_kit', nullable=False),
        sa.Column('linked_course_id', sa.Integer(), sa.ForeignKey('courses.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    )
    op.create_index('ix_products_id', 'products', ['id'], unique=False)
    op.create_index('ix_products_name', 'products', ['name'], unique=False)
    op.create_index('ix_products_category', 'products', ['category'], unique=False)

    # 5. orders
    op.create_table(
        'orders',
        sa.Column('id', sa.String(), primary_key=True, nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('customer_name', sa.String(), nullable=False),
        sa.Column('customer_email', sa.String(), nullable=False),
        sa.Column('customer_phone', sa.String(), nullable=False),
        sa.Column('items_json', sa.Text(), nullable=False),
        sa.Column('items_total', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('delivery_fee', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('delivery_region', sa.String(), server_default='Digital/DIY', nullable=False),
        sa.Column('delivery_fee_rule', sa.String(), server_default='FREE_DELIVERY', nullable=False),
        sa.Column('discount_amount', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('total_payable', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('currency', sa.String(), server_default='INR', nullable=False),
        sa.Column('shipping_address_json', sa.Text(), nullable=False),
        sa.Column('payment_status', sa.String(), server_default='PAYMENT_PENDING', nullable=False),
        sa.Column('order_status', sa.String(), server_default='PENDING_PAYMENT', nullable=False),
        sa.Column('cashfree_order_id', sa.String(), nullable=True),
        sa.Column('cashfree_session_id', sa.String(), nullable=True),
        sa.Column('cashfree_payment_id', sa.String(), nullable=True),
        sa.Column('payment_method', sa.String(), server_default='Cashfree Online', nullable=True),
        sa.Column('payment_attempt_count', sa.Integer(), server_default='1', nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    )
    op.create_index('ix_orders_id', 'orders', ['id'], unique=False)
    op.create_index('ix_orders_user_id', 'orders', ['user_id'], unique=False)
    op.create_index('ix_orders_payment_status', 'orders', ['payment_status'], unique=False)
    op.create_index('ix_orders_order_status', 'orders', ['order_status'], unique=False)
    op.create_index('ix_orders_cashfree_order_id', 'orders', ['cashfree_order_id'], unique=True)

    # 6. order_items
    op.create_table(
        'order_items',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('order_id', sa.String(), sa.ForeignKey('orders.id'), nullable=False),
        sa.Column('item_type', sa.String(), nullable=False),
        sa.Column('item_id', sa.Integer(), nullable=False),
        sa.Column('price', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('quantity', sa.Integer(), server_default='1', nullable=False),
    )
    op.create_index('ix_order_items_id', 'order_items', ['id'], unique=False)

    # 7. payments
    op.create_table(
        'payments',
        sa.Column('id', sa.String(), primary_key=True, nullable=False),
        sa.Column('order_id', sa.String(), sa.ForeignKey('orders.id'), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('gateway', sa.String(), server_default='cashfree', nullable=False),
        sa.Column('gateway_order_id', sa.String(), nullable=True),
        sa.Column('gateway_payment_id', sa.String(), nullable=True),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(), server_default='INR', nullable=False),
        sa.Column('status', sa.String(), server_default='PENDING', nullable=False),
        sa.Column('payment_method', sa.String(), nullable=True),
        sa.Column('raw_response', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    )
    op.create_index('ix_payments_id', 'payments', ['id'], unique=False)
    op.create_index('ix_payments_order_id', 'payments', ['order_id'], unique=False)
    op.create_index('ix_payments_user_id', 'payments', ['user_id'], unique=False)
    op.create_index('ix_payments_gateway_order_id', 'payments', ['gateway_order_id'], unique=False)
    op.create_index('ix_payments_gateway_payment_id', 'payments', ['gateway_payment_id'], unique=False)
    op.create_index('ix_payments_status', 'payments', ['status'], unique=False)

    # 8. payment_events
    op.create_table(
        'payment_events',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('order_id', sa.String(), nullable=False),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('event_data', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    )
    op.create_index('ix_payment_events_id', 'payment_events', ['id'], unique=False)
    op.create_index('ix_payment_events_order_id', 'payment_events', ['order_id'], unique=False)
    op.create_index('ix_payment_events_event_type', 'payment_events', ['event_type'], unique=False)

    # 9. course_entitlements
    op.create_table(
        'course_entitlements',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('course_id', sa.Integer(), sa.ForeignKey('courses.id'), nullable=False),
        sa.Column('order_id', sa.String(), sa.ForeignKey('orders.id'), nullable=True),
        sa.Column('granted_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    )
    op.create_index('ix_course_entitlements_id', 'course_entitlements', ['id'], unique=False)
    op.create_index('ix_course_entitlements_user_id', 'course_entitlements', ['user_id'], unique=False)

    # 10. user_addresses
    op.create_table(
        'user_addresses',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('label', sa.String(), server_default='Home', nullable=False),
        sa.Column('full_name', sa.String(), nullable=False),
        sa.Column('phone', sa.String(), nullable=False),
        sa.Column('address_line1', sa.String(), nullable=False),
        sa.Column('address_line2', sa.String(), nullable=True),
        sa.Column('landmark', sa.String(), nullable=True),
        sa.Column('city', sa.String(), nullable=False),
        sa.Column('state', sa.String(), nullable=False),
        sa.Column('postal_code', sa.String(), nullable=False),
        sa.Column('country', sa.String(), server_default='India', nullable=False),
        sa.Column('is_default', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    )
    op.create_index('ix_user_addresses_id', 'user_addresses', ['id'], unique=False)
    op.create_index('ix_user_addresses_user_id', 'user_addresses', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_table('user_addresses')
    op.drop_table('course_entitlements')
    op.drop_table('payment_events')
    op.drop_table('payments')
    op.drop_table('order_items')
    op.drop_table('orders')
    op.drop_table('products')
    op.drop_table('lessons')
    op.drop_table('courses')
    op.drop_table('users')
