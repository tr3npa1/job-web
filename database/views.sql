USE mydb;

-- SQL SECURITY INVOKER uses the querying account's own table permissions.
CREATE SQL SECURITY INVOKER VIEW IF NOT EXISTS job_web_activity AS
SELECT j.JID, j.JobRole, r.RID, r.CompanyName, COUNT(a.AID) AS ApplicationCount
FROM Job AS j
JOIN Recruiter AS r ON j.RID = r.RID
LEFT JOIN Application AS a ON j.JID = a.JID
GROUP BY j.JID, j.JobRole, r.RID, r.CompanyName;
