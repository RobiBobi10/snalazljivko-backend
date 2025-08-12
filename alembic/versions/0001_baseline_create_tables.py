from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "partners",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("naziv", sa.String(), nullable=False),
        sa.Column("adresa", sa.String(), nullable=True),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lng", sa.Float(), nullable=True),
    )

    op.create_table(
        "bags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("naziv", sa.String(), nullable=False),
        sa.Column("opis", sa.String(), nullable=True),
        sa.Column("cena", sa.Float(), nullable=False),
        sa.Column("kolicina", sa.Integer(), nullable=False),
        sa.Column("vreme_preuzimanja", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("partner_id", sa.Integer(), sa.ForeignKey("partners.id"), nullable=False),
        sa.Column("adresa", sa.String(), nullable=True),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lng", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )


def downgrade():
    op.drop_table("bags")
    op.drop_table("partners")
