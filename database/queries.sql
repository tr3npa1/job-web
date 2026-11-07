-- Select the recruitment database before executing this script.

-- Job listing: selection, projection, join and ordering.
SELECT j.JID, j.JobRole, j.JobType, r.CompanyName, r.CompanyLocation,
       j.Qualification, j.MinExp, j.Salary
FROM Job AS j
JOIN Recruiter AS r ON j.RID = r.RID
WHERE j.MinExp <= 3
ORDER BY j.JobRole;

-- Clients with at least one application.
SELECT u.name, c.CEmail
FROM Client AS c JOIN Users AS u ON u.email = c.CEmail
WHERE EXISTS (SELECT 1 FROM Application AS a WHERE a.CID = c.CID);

-- Jobs with no applications.
SELECT j.JID, j.JobRole
FROM Job AS j
WHERE NOT EXISTS (SELECT 1 FROM Application AS a WHERE a.JID = j.JID);

-- Include zero-count jobs when aggregating applications.
SELECT j.JID, j.JobRole, COUNT(a.AID) AS applications
FROM Job AS j
LEFT JOIN Application AS a ON j.JID = a.JID
GROUP BY j.JID, j.JobRole;

-- Recruiters with multiple postings.
SELECT r.RID, u.name, COUNT(j.JID) AS jobs
FROM Recruiter AS r
JOIN Users AS u ON u.email = r.REmail
JOIN Job AS j ON r.RID = j.RID
GROUP BY r.RID, u.name
HAVING COUNT(j.JID) > 1;

-- Most-applied-to jobs, including ties (MariaDB 10.2+ / MySQL 8+).
WITH counts AS (
    SELECT j.JID, j.JobRole, COUNT(a.AID) AS total
    FROM Job AS j
    LEFT JOIN Application AS a ON j.JID = a.JID
    GROUP BY j.JID, j.JobRole
)
SELECT * FROM counts WHERE total = (SELECT MAX(total) FROM counts);

-- Jobs above the average listed salary.
SELECT JID, JobRole, Salary
FROM Job
WHERE Salary > (SELECT AVG(Salary) FROM Job);

-- Relational division: clients who applied to every job, excluding an empty job set.
SELECT c.CID, u.name
FROM Client AS c JOIN Users AS u ON u.email = c.CEmail
WHERE EXISTS (SELECT 1 FROM Job)
AND NOT EXISTS (
    SELECT 1 FROM Job AS j
    WHERE NOT EXISTS (
        SELECT 1 FROM Application AS a WHERE a.CID = c.CID AND a.JID = j.JID
    )
);

-- Atomic skill values permit exact matching without parsing a list.
SELECT c.CID, u.name, s.Skill
FROM ClientSkill AS s
JOIN Client AS c ON c.CID = s.CID
JOIN Users AS u ON u.email = c.CEmail
WHERE s.Skill = 'Python';

-- Reconstruct application ownership without a redundant Application.RID.
SELECT a.AID, a.CID, a.JID, j.RID
FROM Application AS a JOIN Job AS j ON j.JID = a.JID;

-- Transactional DML example using a session-local table; real jobs are unchanged.
CREATE TEMPORARY TABLE JobLab LIKE Job;
START TRANSACTION;
INSERT INTO JobLab (RID, JobRole, JobType, Qualification, MinExp, Salary)
SELECT RID, 'Lab role', 'Intern', 'BE', 0, 100 FROM Recruiter LIMIT 1;
UPDATE JobLab SET Salary = 200 WHERE JobRole = 'Lab role';
DELETE FROM JobLab WHERE JobRole = 'Lab role';
ROLLBACK;
DROP TEMPORARY TABLE JobLab;

-- No date-range queries: the source schema has no date columns.
-- Optional administrator DCL example (not executed):
-- GRANT SELECT, INSERT, UPDATE, DELETE ON mydb.* TO 'job_web'@'127.0.0.1';
