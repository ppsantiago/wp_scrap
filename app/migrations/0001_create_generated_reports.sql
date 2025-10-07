-- Migration: create generated_reports table
-- Use with SQLite. Run via: sqlite3 data/wp_scrap.db < app/migrations/0001_create_generated_reports.sql

BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS generated_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL,
    type VARCHAR(50) NOT NULL,
    markdown TEXT NOT NULL,
    tags TEXT NULL,
    metadata TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
    updated_at DATETIME NOT NULL DEFAULT (datetime('now')),
    CONSTRAINT fk_generated_reports_report_id
        FOREIGN KEY (report_id)
        REFERENCES reports (id)
        ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_generated_report_unique
    ON generated_reports (report_id, type);

CREATE INDEX IF NOT EXISTS ix_generated_reports_report_id
    ON generated_reports (report_id);

CREATE INDEX IF NOT EXISTS ix_generated_reports_type
    ON generated_reports (type);

-- Trigger to maintain updated_at
CREATE TRIGGER IF NOT EXISTS trg_generated_reports_updated_at
AFTER UPDATE ON generated_reports
FOR EACH ROW
BEGIN
    UPDATE generated_reports
    SET updated_at = datetime('now')
    WHERE id = NEW.id;
END;

COMMIT;
