-- One-off cleanup after self-chat feedback loop (run on notcoolio).
-- Review counts before committing; use ROLLBACK first if unsure.
--
--   docker exec -i monsoon-postgres psql -U monsoon -d monsoon < infra/scripts/cleanup_postgres.sql
--
-- Or interactive:
--   docker exec -it monsoon-postgres psql -U monsoon -d monsoon

BEGIN;

-- Preview loop-spam tasks (chained "Task #N created:" titles)
SELECT id, display_number, left(title, 80) AS title_preview, created_at
FROM tasks
WHERE title ~* '^Task #[0-9]+ created:.*Task #[0-9]+ created:'
   OR title ~* '^Note #[0-9]+ created:.*(Task|Note) #[0-9]+ created:'
ORDER BY display_number;

-- Uncomment after preview looks right:
-- DELETE FROM task_events
-- WHERE task_id IN (
--   SELECT id FROM tasks
--   WHERE title ~* '^Task #[0-9]+ created:.*Task #[0-9]+ created:'
--      OR title ~* '^Note #[0-9]+ created:.*(Task|Note) #[0-9]+ created:'
-- );
--
-- DELETE FROM tasks
-- WHERE title ~* '^Task #[0-9]+ created:.*Task #[0-9]+ created:'
--    OR title ~* '^Note #[0-9]+ created:.*(Task|Note) #[0-9]+ created:';

-- Optional: remove inbound rows from the loop window (adjust timestamp)
-- DELETE FROM inbound_messages WHERE received_at > '2026-07-07 17:50:00+00';

ROLLBACK;
