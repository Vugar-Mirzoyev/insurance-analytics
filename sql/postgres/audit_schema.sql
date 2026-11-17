-- Tables behind the data quality procedure. Created once and kept: every run
-- adds rows, so the history of each check survives a rebuild of the data.
--
-- dq_rule    one row per check: the SQL that counts its exceptions, and why
-- dq_run     one row per run of run_dq_checks()
-- dq_result  one row per check and run: the exception count, or the error
-- dq_latest  each check's latest count next to the previous run's

CREATE TABLE IF NOT EXISTS dq_rule (
    rule_id    integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    area       text    NOT NULL,
    rule_name  text    NOT NULL UNIQUE,
    check_sql  text    NOT NULL,
    why        text    NOT NULL,
    active     boolean NOT NULL DEFAULT true
);

CREATE TABLE IF NOT EXISTS dq_run (
    run_id                 bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    started_at             timestamptz NOT NULL DEFAULT clock_timestamp(),
    finished_at            timestamptz,
    rules_run              integer,
    rules_with_exceptions  integer,
    rules_failed           integer
);

CREATE TABLE IF NOT EXISTS dq_result (
    run_id          bigint  NOT NULL REFERENCES dq_run (run_id),
    rule_id         integer NOT NULL REFERENCES dq_rule (rule_id),
    exception_rows  bigint,
    status          text    NOT NULL CHECK (status IN ('clean', 'exceptions', 'error')),
    error_message   text,
    PRIMARY KEY (run_id, rule_id),
    CHECK ((status = 'error') = (exception_rows IS NULL))
);

CREATE OR REPLACE VIEW dq_latest AS
WITH ranked AS (
    SELECT r.*,
           d.started_at,
           DENSE_RANK() OVER (PARTITION BY r.rule_id ORDER BY r.run_id DESC) AS recency
    FROM dq_result r
    JOIN dq_run d USING (run_id)
)
SELECT ru.area,
       ru.rule_name,
       cur.status,
       cur.exception_rows,
       prev.exception_rows                       AS previous_rows,
       cur.exception_rows - prev.exception_rows  AS change,
       cur.error_message,
       cur.started_at                            AS checked_at
FROM ranked cur
JOIN dq_rule ru USING (rule_id)
LEFT JOIN ranked prev ON prev.rule_id = cur.rule_id AND prev.recency = 2
WHERE cur.recency = 1
  AND ru.active
ORDER BY ru.rule_id;
