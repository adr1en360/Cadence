"""enable_rls

Revision ID: 972fd98a10dd
Revises: ebfcfeebc406
Create Date: 2026-07-07 21:52:02.651871

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '972fd98a10dd'
down_revision: Union[str, Sequence[str], None] = 'ebfcfeebc406'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable RLS on all tables
    op.execute("ALTER TABLE merchants ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE projects ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE plans ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE payments ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE events ENABLE ROW LEVEL SECURITY;")

    # Check if 'auth' schema and 'authenticated' role exist (Supabase-specific)
    connection = op.get_bind()
    has_supabase = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_roles WHERE rolname = 'authenticated'
        ) AND EXISTS (
            SELECT 1 FROM information_schema.schemata WHERE schema_name = 'auth'
        );
    """)).scalar()

    if has_supabase:
        # 2. Create security policies for merchants table
        op.execute("""
            CREATE POLICY merchant_self_access ON merchants
            FOR ALL
            TO authenticated
            USING (email = (auth.jwt() ->> 'email'))
            WITH CHECK (email = (auth.jwt() ->> 'email'));
        """)

        # 3. Create security policies for projects table
        op.execute("""
            CREATE POLICY project_merchant_access ON projects
            FOR ALL
            TO authenticated
            USING (
                merchant_id IN (
                    SELECT id FROM merchants WHERE email = (auth.jwt() ->> 'email')
                )
            )
            WITH CHECK (
                merchant_id IN (
                    SELECT id FROM merchants WHERE email = (auth.jwt() ->> 'email')
                )
            );
        """)

        # 4. Create security policies for api_keys table
        op.execute("""
            CREATE POLICY api_key_merchant_access ON api_keys
            FOR ALL
            TO authenticated
            USING (
                project_id IN (
                    SELECT id FROM projects WHERE merchant_id IN (
                        SELECT id FROM merchants WHERE email = (auth.jwt() ->> 'email')
                    )
                )
            )
            WITH CHECK (
                project_id IN (
                    SELECT id FROM projects WHERE merchant_id IN (
                        SELECT id FROM merchants WHERE email = (auth.jwt() ->> 'email')
                    )
                )
            );
        """)

        # 5. Create security policies for plans table
        op.execute("""
            CREATE POLICY plan_merchant_access ON plans
            FOR ALL
            TO authenticated
            USING (
                project_id IN (
                    SELECT id FROM projects WHERE merchant_id IN (
                        SELECT id FROM merchants WHERE email = (auth.jwt() ->> 'email')
                    )
                )
            )
            WITH CHECK (
                project_id IN (
                    SELECT id FROM projects WHERE merchant_id IN (
                        SELECT id FROM merchants WHERE email = (auth.jwt() ->> 'email')
                    )
                )
            );
        """)

        # 6. Create security policies for subscriptions table
        op.execute("""
            CREATE POLICY subscription_merchant_access ON subscriptions
            FOR ALL
            TO authenticated
            USING (
                project_id IN (
                    SELECT id FROM projects WHERE merchant_id IN (
                        SELECT id FROM merchants WHERE email = (auth.jwt() ->> 'email')
                    )
                )
            )
            WITH CHECK (
                project_id IN (
                    SELECT id FROM projects WHERE merchant_id IN (
                        SELECT id FROM merchants WHERE email = (auth.jwt() ->> 'email')
                    )
                )
            );
        """)

        # 7. Create security policies for payments table
        op.execute("""
            CREATE POLICY payment_merchant_access ON payments
            FOR ALL
            TO authenticated
            USING (
                project_id IN (
                    SELECT id FROM projects WHERE merchant_id IN (
                        SELECT id FROM merchants WHERE email = (auth.jwt() ->> 'email')
                    )
                )
            )
            WITH CHECK (
                project_id IN (
                    SELECT id FROM projects WHERE merchant_id IN (
                        SELECT id FROM merchants WHERE email = (auth.jwt() ->> 'email')
                    )
                )
            );
        """)

        # 8. Create security policies for events table
        op.execute("""
            CREATE POLICY event_merchant_access ON events
            FOR ALL
            TO authenticated
            USING (
                project_id IN (
                    SELECT id FROM projects WHERE merchant_id IN (
                        SELECT id FROM merchants WHERE email = (auth.jwt() ->> 'email')
                    )
                )
            )
            WITH CHECK (
                project_id IN (
                    SELECT id FROM projects WHERE merchant_id IN (
                        SELECT id FROM merchants WHERE email = (auth.jwt() ->> 'email')
                    )
                )
            );
        """)
    else:
        # Since standard SQL database doesn't have authenticated role or auth schema,
        # we skip creating those policies. RLS will still be enabled on the tables,
        # and standard PostgreSQL client connection (usually owner/superuser) will bypass RLS.
        pass


def downgrade() -> None:
    # 1. Drop policies
    op.execute("DROP POLICY IF EXISTS merchant_self_access ON merchants;")
    op.execute("DROP POLICY IF EXISTS project_merchant_access ON projects;")
    op.execute("DROP POLICY IF EXISTS api_key_merchant_access ON api_keys;")
    op.execute("DROP POLICY IF EXISTS plan_merchant_access ON plans;")
    op.execute("DROP POLICY IF EXISTS subscription_merchant_access ON subscriptions;")
    op.execute("DROP POLICY IF EXISTS payment_merchant_access ON payments;")
    op.execute("DROP POLICY IF EXISTS event_merchant_access ON events;")

    # 2. Disable RLS
    op.execute("ALTER TABLE merchants DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE projects DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE api_keys DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE plans DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE subscriptions DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE payments DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE events DISABLE ROW LEVEL SECURITY;")
