USE mydb;

-- Foreign keys guarantee an account exists; these guards verify its role.
-- MariaDB OR REPLACE permits repeatable installation without changing records.
DELIMITER //
CREATE OR REPLACE TRIGGER job_web_recruiter_insert
BEFORE INSERT ON Recruiter FOR EACH ROW
BEGIN
    IF NOT EXISTS (SELECT 1 FROM Users WHERE email = NEW.REmail AND type = 'Recruiter') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Recruiter profile requires a recruiter account';
    END IF;
END//
CREATE OR REPLACE TRIGGER job_web_recruiter_update
BEFORE UPDATE ON Recruiter FOR EACH ROW
BEGIN
    IF NOT EXISTS (SELECT 1 FROM Users WHERE email = NEW.REmail AND type = 'Recruiter') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Recruiter profile requires a recruiter account';
    END IF;
END//
CREATE OR REPLACE TRIGGER job_web_client_insert
BEFORE INSERT ON Client FOR EACH ROW
BEGIN
    IF NOT EXISTS (SELECT 1 FROM Users WHERE email = NEW.CEmail AND type = 'Client') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Client profile requires a client account';
    END IF;
END//
CREATE OR REPLACE TRIGGER job_web_client_update
BEFORE UPDATE ON Client FOR EACH ROW
BEGIN
    IF NOT EXISTS (SELECT 1 FROM Users WHERE email = NEW.CEmail AND type = 'Client') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Client profile requires a client account';
    END IF;
END//
CREATE OR REPLACE TRIGGER job_web_account_role_update
BEFORE UPDATE ON Users FOR EACH ROW
BEGIN
    IF NEW.type <> OLD.type AND (
        EXISTS (SELECT 1 FROM Recruiter WHERE REmail = OLD.email)
        OR EXISTS (SELECT 1 FROM Client WHERE CEmail = OLD.email)
    ) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Account role cannot change while its profile exists';
    END IF;
END//
DELIMITER ;
