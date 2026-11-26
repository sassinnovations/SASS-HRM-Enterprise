"""Check the bundled Docker launcher logic without running Windows or MySQL."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import os
import sys

batch = (Path(__file__).resolve().parents[1] / 'CREATE_ADMIN.bat').read_text(encoding='ascii')
commands = [line.split(' python -c "', 1)[1][:-1]
            for line in batch.splitlines() if ' python -c "' in line]
assert len(commands) == 2
for command in commands:
    compile(command, 'CREATE_ADMIN.bat', 'exec')
assert '/api/ready' in commands[0]
assert 'exec -T api' in batch and 'exec api' in batch
assert 'pip install' not in batch and '--developer' not in batch


class Cursor:
    def __init__(self, occupied, lock):
        self.responses = iter([{'db_name': 'test_database', 'has_employees': occupied}, {'acquired': lock}])

    def execute(self, sql):
        assert sql.startswith('SELECT '), sql

    def fetchone(self):
        return next(self.responses)


def run(*, tty=True, engine='mysql', occupied=0, lock=1, answers=None, failure=None):
    cursor = Cursor(occupied, lock)
    seen = []
    stream = SimpleNamespace(isatty=lambda: tty)
    modules = {
        'mysql_backend': SimpleNamespace(raw_mysql_connection=lambda: SimpleNamespace(cursor=lambda: cursor)),
        'create_admin': SimpleNamespace(main=lambda: seen.append(sys.argv[:]))
    }
    with patch.dict(sys.modules, modules), patch.dict(os.environ, {'DB_ENGINE': engine}), \
         patch.object(sys, 'stdin', stream), patch.object(sys, 'stderr', stream), \
         patch.object(sys, 'argv', []), patch('builtins.input', side_effect=answers or AssertionError('Unexpected prompt')):
        try:
            exec(commands[1], {})
        except SystemExit as exc:
            assert failure and failure in str(exc) and not seen, str(exc)
        else:
            assert not failure
            assert seen == [['create_admin.py', '--email=qa@example.invalid', '--name=QA & Team | Test',
                             '--code=SASS-ADM-001', '--location=QA Office % Team']]


run(tty=False, failure='interactive')
run(engine='sqlite', failure='not configured for MySQL')
run(occupied=1, failure='already has employee records')
run(lock=0, failure='Another first-admin setup')
run(answers=['', 'QA', '', 'Office'], failure='are required')
run(answers=['qa@example.invalid', 'QA & Team | Test', '', 'QA Office % Team'])
print('PASS Docker launcher: readiness command, terminal safety, engine/scope, lock, and input handling.')
