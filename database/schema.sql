-- Fresh installations only. Existing installations: backend/migrate_db.py.
-- This script never drops tables or replaces existing records.
CREATE DATABASE IF NOT EXISTS mydb
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE mydb;

CREATE TABLE IF NOT EXISTS Users (
    name VARCHAR(45) NOT NULL,
    email VARCHAR(120) NOT NULL,
    type VARCHAR(45) NOT NULL,
    password VARCHAR(255) NULL,
    PRIMARY KEY (email),
    CHECK (type IN ('Recruiter', 'Client'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS Recruiter (
    RID INT NOT NULL AUTO_INCREMENT,
    REmail VARCHAR(120) NOT NULL,
    CompanyName VARCHAR(45) NOT NULL,
    CompanyLocation VARCHAR(45) NOT NULL,
    RGender VARCHAR(2) NOT NULL,
    PRIMARY KEY (RID),
    UNIQUE (REmail),
    CONSTRAINT fk_recruiter_user FOREIGN KEY (REmail) REFERENCES Users (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS Client (
    CID INT NOT NULL AUTO_INCREMENT,
    CEmail VARCHAR(120) NOT NULL,
    CAge INT NOT NULL,
    CLocation VARCHAR(45) NOT NULL,
    CGender VARCHAR(2) NOT NULL,
    CExp INT NOT NULL,
    CQualification VARCHAR(45) NOT NULL,
    PRIMARY KEY (CID),
    UNIQUE (CEmail),
    CONSTRAINT fk_client_user FOREIGN KEY (CEmail) REFERENCES Users (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ClientSkill (
    CID INT NOT NULL,
    Skill VARCHAR(45) COLLATE utf8mb4_bin NOT NULL,
    PRIMARY KEY (CID, Skill),
    CONSTRAINT fk_skill_client FOREIGN KEY (CID) REFERENCES Client (CID) ON DELETE CASCADE,
    CHECK (CHAR_LENGTH(TRIM(Skill)) > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS Job (
    RID INT NOT NULL,
    JID INT NOT NULL AUTO_INCREMENT,
    JobRole VARCHAR(45) NOT NULL,
    JobType VARCHAR(45) NOT NULL,
    Qualification VARCHAR(45) NOT NULL,
    MinExp INT NOT NULL,
    Salary INT NOT NULL,
    PRIMARY KEY (JID),
    FOREIGN KEY (RID) REFERENCES Recruiter (RID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS Application (
    AID INT NOT NULL AUTO_INCREMENT,
    JID INT NOT NULL,
    CID INT NOT NULL,
    PRIMARY KEY (AID),
    CONSTRAINT uq_application_client_job UNIQUE (CID, JID),
    FOREIGN KEY (JID) REFERENCES Job (JID),
    FOREIGN KEY (CID) REFERENCES Client (CID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
