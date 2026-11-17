-- run_dq_checks(): run every active rule in dq_rule and log the result.
--
-- Each rule's SQL returns one number, the count of rows that break it. The
-- procedure opens a run, executes the rules one by one, writes one dq_result
-- row per rule and closes the run with its totals.
--
-- A rule whose SQL fails (a renamed column, a missing table) is logged with
-- status 'error' and its message, and the run carries on: one broken check must
-- not hide the results of the others. The rules come from src/data_quality.py
-- through src/postgres_audit.py, never from user input.
--
--   CALL run_dq_checks(NULL);   -- returns the new run_id

CREATE OR REPLACE PROCEDURE run_dq_checks(INOUT p_run_id bigint DEFAULT NULL)
LANGUAGE plpgsql
AS $$
DECLARE
    r        record;
    n        bigint;
    total    integer := 0;
    flagged  integer := 0;
    failed   integer := 0;
BEGIN
    INSERT INTO dq_run DEFAULT VALUES RETURNING run_id INTO p_run_id;

    FOR r IN SELECT rule_id, check_sql FROM dq_rule WHERE active ORDER BY rule_id LOOP
        total := total + 1;
        BEGIN
            EXECUTE r.check_sql INTO n;
            INSERT INTO dq_result (run_id, rule_id, exception_rows, status)
            VALUES (p_run_id, r.rule_id, n,
                    CASE WHEN n = 0 THEN 'clean' ELSE 'exceptions' END);
            IF n > 0 THEN
                flagged := flagged + 1;
            END IF;
        EXCEPTION WHEN OTHERS THEN
            INSERT INTO dq_result (run_id, rule_id, status, error_message)
            VALUES (p_run_id, r.rule_id, 'error', SQLERRM);
            failed := failed + 1;
        END;
    END LOOP;

    UPDATE dq_run
    SET finished_at = clock_timestamp(),
        rules_run = total,
        rules_with_exceptions = flagged,
        rules_failed = failed
    WHERE run_id = p_run_id;
END;
$$;
