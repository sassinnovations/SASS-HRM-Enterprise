"""Read-only safety and missing-table/column/privilege regression."""
from schema_audit import get_required_schema
from workspace_database_readiness import relevant_schema, inspect_live

expected = relevant_schema(get_required_schema())
names = set(expected)
fields = {(name, col) for name, cols in expected.items() for col in cols}


class FakeConnection:
    def __init__(self, blocked=None):
        self.sql = []
        self.blocked = blocked

    def cursor(self):
        conn = self

        class Cursor:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def execute(self, sql):
                assert sql == 'START TRANSACTION READ ONLY' or (
                    sql.startswith('SELECT 1 FROM `') and sql.endswith('` LIMIT 0')
                ), sql
                conn.sql.append(sql)
                if conn.blocked and f'`{conn.blocked}`' in sql:
                    raise PermissionError
        return Cursor()


with_missing = 'employee_calendar_categories'
with_missing_column = 'employee_security_checklist_settings'
with_block = 'leave_coverage_manual_plans'
missing_pair = (with_missing_column, 'employee_id')
conn = FakeConnection(blocked=with_block)
issues = inspect_live(conn, 'hrm_qa', expected, inventory=lambda _: (
    'hrm_qa', names - {with_missing}, fields - {missing_pair}
))
assert issues == {
    with_missing: ['table missing'],
    with_missing_column: ['missing columns: employee_id'],
    with_block: ['table cannot be opened with the configured account'],
}, issues
assert len(conn.sql) == 1 + len(expected) - 2
assert inspect_live(FakeConnection(), 'hrm_qa', expected, inventory=lambda _: (
    'hrm_qa', names, fields
)) == {}
mismatch = FakeConnection()
try:
    inspect_live(mismatch, 'hrm_qa', expected, inventory=lambda _: ('wrong_db', names, fields))
except ValueError:
    assert mismatch.sql == ['START TRANSACTION READ ONLY']
else:
    raise AssertionError('Wrong MySQL database must be rejected')
print(f'PASS {len(expected)} workspace dependencies; read-only metadata, zero-row probes, and target validation')
