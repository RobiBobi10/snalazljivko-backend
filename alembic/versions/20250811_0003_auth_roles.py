# backend/alembic/versions/20250811_0003_auth_roles.py
"""Add auth columns to partners and create customers"""

from alembic import op
import sqlalchemy as sa

# Match your chain: 0001 -> 397070310ac7 -> THIS
revision = "20250811_0003"
down_revision = "397070310ac7"
branch_labels = None
depends_on = None

def upgrade():
    # partners – add auth columns + index/unique
    with op.batch_alter_table("partners") as b:
        b.add_column(sa.Column("email", sa.String(), nullable=True))
        b.add_column(sa.Column("login_username", sa.String(), nullable=True))
        b.add_column(sa.Column("password_hash", sa.String(), nullable=True))
        b.add_column(sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
        b.create_index("ix_partners_login_username", ["login_username"], unique=True)

    # customers
    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=True),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_customers_email", "customers", ["email"], unique=True)

def downgrade():
    op.drop_index("ix_customers_email", table_name="customers")
    op.drop_table("customers")
    with op.batch_alter_table("partners") as b:
        b.drop_index("ix_partners_login_username")
        b.drop_column("is_active")
        b.drop_column("password_hash")
        b.drop_column("login_username")
        b.drop_column("email")
