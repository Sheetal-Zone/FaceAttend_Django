from alembic import op
import sqlalchemy as sa

revision = 'a191c4934984'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    conn = op.get_bind()
    insp = sa.inspect(conn)
    cols = [c['name'] for c in insp.get_columns('attendance')]
    if 'confidence' in cols:
        with op.batch_alter_table('attendance') as batch_op:
            batch_op.drop_column('confidence')

def downgrade():
    pass
"""drop confidence from attendance

Revision ID: a191c4934984
Revises: 
Create Date: 2025-09-08 16:54:43.998795

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a191c4934984'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLite-safe drop column using batch_alter_table if column exists
    conn = op.get_bind()
    try:
        result = conn.execute(sa.text("PRAGMA table_info(attendance)"))
        columns = [row[1] for row in result.fetchall()]
        if "confidence" in columns:
            with op.batch_alter_table("attendance", recreate="always") as batch_op:
                batch_op.drop_column("confidence")
    except Exception:
        # Best-effort; ignore if table doesn't exist yet
        pass


def downgrade() -> None:
    # Re-add the column for downgrade (nullable float)
    try:
        with op.batch_alter_table("attendance", recreate="always") as batch_op:
            batch_op.add_column(sa.Column("confidence", sa.Float(), nullable=True))
    except Exception:
        pass
