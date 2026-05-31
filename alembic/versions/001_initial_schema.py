"""initial schema

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-04-12 21:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # === categories ===
    op.create_table('categories',
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('name', sa.String(length=255), nullable=False),
                    sa.Column('slug', sa.String(length=255), nullable=False),
                    sa.Column('description', sa.Text(), nullable=True),
                    sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
                    sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
                    sa.Column('created_at', sa.DateTime(), nullable=True),
                    sa.Column('updated_at', sa.DateTime(), nullable=True),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('slug')
                    )
    op.create_index(op.f('ix_categories_slug'), 'categories', ['slug'], unique=True)
    op.create_index(op.f('ix_categories_parent_id'), 'categories', ['parent_id'], unique=False)

    # === products ===
    op.create_table('products',
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('slug', sa.String(length=255), nullable=False),
                    sa.Column('title', sa.String(length=512), nullable=False),
                    sa.Column('description', sa.Text(), nullable=True),
                    sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=True),
                    sa.Column('status',
                              sa.Enum('CREATED', 'ON_MODERATED', 'MODERATED', 'BLOCKED', name='productstatus'),
                              nullable=False),
                    sa.Column('seller_id', postgresql.UUID(as_uuid=True), nullable=True),
                    sa.Column('created_at', sa.DateTime(), nullable=True),
                    sa.Column('updated_at', sa.DateTime(), nullable=True),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('slug')
                    )
    op.create_index(op.f('ix_products_slug'), 'products', ['slug'], unique=True)
    op.create_index(op.f('ix_products_category_id'), 'products', ['category_id'], unique=False)
    op.create_index(op.f('ix_products_seller_id'), 'products', ['seller_id'], unique=False)
    op.create_foreign_key(None, 'products', 'categories', ['category_id'], ['id'])

    # === product_images ===
    op.create_table('product_images',
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('url', sa.String(length=512), nullable=False),
                    sa.Column('order', sa.Integer(), nullable=False),
                    sa.Column('created_at', sa.DateTime(), nullable=True),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_index(op.f('ix_product_images_product_id'), 'product_images', ['product_id'], unique=False)
    op.create_foreign_key(None, 'product_images', 'products', ['product_id'], ['id'], ondelete='CASCADE')

    # === product_characteristics ===
    op.create_table('product_characteristics',
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('name', sa.String(length=255), nullable=False),
                    sa.Column('value', sa.Text(), nullable=False),
                    sa.Column('created_at', sa.DateTime(), nullable=True),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_index(op.f('ix_product_characteristics_product_id'), 'product_characteristics', ['product_id'],
                    unique=False)
    op.create_foreign_key(None, 'product_characteristics', 'products', ['product_id'], ['id'], ondelete='CASCADE')

    # === skus ===
    op.create_table('skus',
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('name', sa.String(length=512), nullable=False),
                    sa.Column('price', sa.Float(), nullable=False),
                    sa.Column('quantity', sa.Integer(), nullable=False),
                    sa.Column('created_at', sa.DateTime(), nullable=True),
                    sa.Column('updated_at', sa.DateTime(), nullable=True),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_index(op.f('ix_skus_product_id'), 'skus', ['product_id'], unique=False)
    op.create_foreign_key(None, 'skus', 'products', ['product_id'], ['id'], ondelete='CASCADE')

    # === sku_images ===
    op.create_table('sku_images',
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('sku_id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('url', sa.String(length=512), nullable=False),
                    sa.Column('order', sa.Integer(), nullable=False),
                    sa.Column('created_at', sa.DateTime(), nullable=True),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_index(op.f('ix_sku_images_sku_id'), 'sku_images', ['sku_id'], unique=False)
    op.create_foreign_key(None, 'sku_images', 'skus', ['sku_id'], ['id'], ondelete='CASCADE')

    # === sku_characteristics ===
    op.create_table('sku_characteristics',
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('sku_id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('name', sa.String(length=255), nullable=False),
                    sa.Column('value', sa.Text(), nullable=False),
                    sa.Column('created_at', sa.DateTime(), nullable=True),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_index(op.f('ix_sku_characteristics_sku_id'), 'sku_characteristics', ['sku_id'], unique=False)
    op.create_foreign_key(None, 'sku_characteristics', 'skus', ['sku_id'], ['id'], ondelete='CASCADE')

    # === collections ===
    op.create_table('collections',
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('name', sa.String(length=255), nullable=False),
                    sa.Column('slug', sa.String(length=255), nullable=False),
                    sa.Column('description', sa.Text(), nullable=True),
                    sa.Column('image_url', sa.String(length=512), nullable=True),
                    sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
                    sa.Column('sort_order', sa.Integer(), nullable=False),
                    sa.Column('created_at', sa.DateTime(), nullable=True),
                    sa.Column('updated_at', sa.DateTime(), nullable=True),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('slug')
                    )
    op.create_index(op.f('ix_collections_slug'), 'collections', ['slug'], unique=True)

    # === collection_products (M:M) ===
    op.create_table('collection_products',
                    sa.Column('collection_id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.PrimaryKeyConstraint('collection_id', 'product_id'),
                    sa.ForeignKeyConstraint(['collection_id'], ['collections.id'], ondelete='CASCADE'),
                    sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE')
                    )

    # === invoices (Seller) ===
    # Создаём ENUM, если его нет
    invoice_status = postgresql.ENUM(
        'DRAFT', 'SENT', 'ACCEPTED', 'REJECTED', 'PARTIALLY_ACCEPTED',
        name='invoice_status_enum',
        create_type=True
    )
    invoice_status.create(op.get_bind(), checkfirst=True)

    op.create_table('invoices',
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('seller_id', postgresql.UUID(as_uuid=True), nullable=True),
                    sa.Column('warehouse_id', postgresql.UUID(as_uuid=True), nullable=True),
                    sa.Column('status', postgresql.ENUM('DRAFT', 'SENT', 'ACCEPTED', 'REJECTED', 'PARTIALLY_ACCEPTED',
                                                        name='invoice_status_enum', create_type=False), nullable=False),
                    sa.Column('total_amount', sa.Float(), nullable=False, default=0.0),
                    sa.Column('comment', sa.Text(), nullable=True),
                    sa.Column('created_at', sa.DateTime(), nullable=True),
                    sa.Column('updated_at', sa.DateTime(), nullable=True),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_index(op.f('ix_invoices_seller_id'), 'invoices', ['seller_id'], unique=False)
    op.create_index(op.f('ix_invoices_status'), 'invoices', ['status'], unique=False)

    # === invoice_items ===
    op.create_table('invoice_items',
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('invoice_id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('sku_id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('quantity', sa.Integer(), nullable=False),
                    sa.Column('price', sa.Float(), nullable=False),
                    sa.Column('total', sa.Float(), nullable=False),
                    sa.Column('created_at', sa.DateTime(), nullable=True),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_index(op.f('ix_invoice_items_invoice_id'), 'invoice_items', ['invoice_id'], unique=False)
    op.create_index(op.f('ix_invoice_items_sku_id'), 'invoice_items', ['sku_id'], unique=False)
    op.create_foreign_key(None, 'invoice_items', 'invoices', ['invoice_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key(None, 'invoice_items', 'skus', ['sku_id'], ['id'], ondelete='RESTRICT')

    # === sellers (если нужно) ===
    op.create_table('sellers',
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('name', sa.String(length=255), nullable=False),
                    sa.Column('email', sa.String(length=255), nullable=False),
                    sa.Column('phone', sa.String(length=20), nullable=True),
                    sa.Column('company_name', sa.String(length=255), nullable=True),
                    sa.Column('inn', sa.String(length=12), nullable=True),
                    sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
                    sa.Column('created_at', sa.DateTime(), nullable=True),
                    sa.Column('updated_at', sa.DateTime(), nullable=True),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('email')
                    )
    op.create_index(op.f('ix_sellers_email'), 'sellers', ['email'], unique=True)


def downgrade() -> None:
    # Обратный порядок удаления
    op.drop_table('sellers')
    op.drop_table('invoice_items')
    op.drop_table('invoices')
    op.drop_table('collection_products')
    op.drop_table('collections')
    op.drop_table('sku_characteristics')
    op.drop_table('sku_images')
    op.drop_table('skus')
    op.drop_table('product_characteristics')
    op.drop_table('product_images')
    op.drop_table('products')
    op.drop_table('categories')

    # Удаляем ENUM
    op.execute("DROP TYPE IF EXISTS invoice_status_enum")
    op.execute("DROP TYPE IF EXISTS productstatus")
