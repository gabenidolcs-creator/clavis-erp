from django.db import migrations


class Migration(migrations.Migration):
    """
    Creates or extends the RowComment table for the free-core row comments feature.

    When baserow_premium is installed, this table is already created by the premium
    migration 0001_row_comments (with user_id, message, trashed, etc.). The RunSQL
    operations use IF NOT EXISTS guards so that this migration is a safe no-op in
    premium environments for the table creation part.

    The ``deleted_on`` column is added unconditionally (ADD COLUMN IF NOT EXISTS) so
    the free-core soft-delete mechanism is available regardless of whether the table
    was created here or by the premium migration.
    """

    dependencies = [
        ("database", "0225_mapview_mapviewfieldoptions"),
    ]

    operations = [
        # Create table only when premium has not already created it.
        migrations.RunSQL(
            sql="""
                CREATE TABLE IF NOT EXISTS database_rowcomment (
                    id          serial       PRIMARY KEY,
                    table_id    integer      NOT NULL REFERENCES database_table(id) ON DELETE CASCADE,
                    row_id      integer      NOT NULL CHECK (row_id > 0),
                    user_id     integer      REFERENCES auth_user(id) ON DELETE SET NULL,
                    message     jsonb        NOT NULL DEFAULT '{}',
                    trashed     boolean      NOT NULL DEFAULT false,
                    created_on  timestamptz  NOT NULL DEFAULT now(),
                    updated_on  timestamptz  NOT NULL DEFAULT now()
                );
                CREATE INDEX IF NOT EXISTS database_rowcomment_row_id_idx
                    ON database_rowcomment (row_id);
                CREATE INDEX IF NOT EXISTS database_rowcomment_created_on_idx
                    ON database_rowcomment (created_on);
                CREATE INDEX IF NOT EXISTS database_rowcomment_table_row_idx
                    ON database_rowcomment (table_id, row_id);
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
        # Add deleted_on for free-core soft-delete. Safe no-op on premium tables.
        migrations.RunSQL(
            sql="""
                ALTER TABLE database_rowcomment
                    ADD COLUMN IF NOT EXISTS deleted_on timestamptz NULL;
                CREATE INDEX IF NOT EXISTS database_rowcomment_deleted_on_idx
                    ON database_rowcomment (deleted_on);
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
