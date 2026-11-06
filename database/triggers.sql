USE mydb;

-- Optional: reject applications whose recruiter does not own the referenced job.
-- These guards cover Application writes, not direct changes to Job.RID.
-- Import once; existing triggers and records are left unchanged.
DELIMITER //
CREATE TRIGGER job_web_application_owner_insert
BEFORE INSERT ON Application
FOR EACH ROW
BEGIN
    IF NOT EXISTS (SELECT 1 FROM Job WHERE JID = NEW.JID AND RID = NEW.RID) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Application recruiter must own the job';
    END IF;
END//

CREATE TRIGGER job_web_application_owner_update
BEFORE UPDATE ON Application
FOR EACH ROW
BEGIN
    IF NOT EXISTS (SELECT 1 FROM Job WHERE JID = NEW.JID AND RID = NEW.RID) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Application recruiter must own the job';
    END IF;
END//
DELIMITER ;
