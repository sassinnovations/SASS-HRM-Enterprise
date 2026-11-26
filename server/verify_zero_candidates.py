"""Read-only live MySQL candidate count check; no candidate data displayed."""
from main import DB_ENGINE, db

if __name__ == '__main__':
    if DB_ENGINE != 'mysql':
        raise SystemExit('FAIL: the active server is not using MySQL.')
    with db() as conn:
        counts={name:conn.execute(f'SELECT COUNT(*) AS n FROM {table}').fetchone()['n']
                for name,table in {'candidates':'candidates', 'profiles':'candidate_profiles',
                    'imports':'candidate_import_batches','archives':'candidate_import_chunks',
                    'reviews':'hiring_stage_reviews','events':'hiring_stage_events'}.items()}
    counts['candidate_job_roles'] = conn.execute("SELECT COUNT(DISTINCT job_title) AS n FROM candidates WHERE job_title IS NOT NULL AND job_title<>''").fetchone()['n']
    for name,number in counts.items():
        print(f'{name}: {int(number)}')
    if any(counts.values()):
        raise SystemExit('NOT EMPTY: candidate-related data remains. No changes were made.')
    print('PASS: candidate tables and job-role filter are empty. MySQL was not modified.')
