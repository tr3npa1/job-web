-- Import as a database administrator. Back up an existing database first.
CREATE DATABASE IF NOT EXISTS mydb
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE mydb;

CREATE TABLE IF NOT EXISTS Users (
    name VARCHAR(45) NOT NULL,
    email VARCHAR(120) NOT NULL,
    type VARCHAR(45) NOT NULL,
    password VARCHAR(255) NULL,
    PRIMARY KEY (email),
    UNIQUE INDEX email_UNIQUE (email),
    CHECK (type IN ('Recruiter', 'Client'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS Recruiter (
    RID INT NOT NULL AUTO_INCREMENT,
    RName VARCHAR(45) NOT NULL,
    REmail VARCHAR(45) NOT NULL,
    CompanyName VARCHAR(45) NOT NULL,
    CompanyLocation VARCHAR(45) NOT NULL,
    RGender VARCHAR(2) NOT NULL,
    PRIMARY KEY (RID),
    UNIQUE (REmail)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS Client (
    CID INT NOT NULL AUTO_INCREMENT,
    CName VARCHAR(45) NOT NULL,
    CEmail VARCHAR(45) NOT NULL,
    CAge INT NOT NULL,
    CLocation VARCHAR(45) NOT NULL,
    CGender VARCHAR(2) NOT NULL,
    CExp INT NOT NULL,
    CSkills VARCHAR(45) NOT NULL,
    CQualification VARCHAR(45) NOT NULL,
    PRIMARY KEY (CID),
    UNIQUE (CEmail)
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
    RID INT NOT NULL,
    JID INT NOT NULL,
    CID INT NOT NULL,
    PRIMARY KEY (AID),
    FOREIGN KEY (RID) REFERENCES Recruiter (RID),
    FOREIGN KEY (JID) REFERENCES Job (JID),
    FOREIGN KEY (CID) REFERENCES Client (CID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Upgrade the original VARCHAR(45) password column without changing its values.
-- Only widen narrower columns; preserve customized wider password storage.
SET @password_width = (
    SELECT CHARACTER_MAXIMUM_LENGTH FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'Users' AND COLUMN_NAME = 'password'
);
SET @password_migration = IF(@password_width < 255,
    'ALTER TABLE Users MODIFY COLUMN password VARCHAR(255) NULL', 'SELECT 1');
PREPARE password_migration FROM @password_migration;
EXECUTE password_migration;
DEALLOCATE PREPARE password_migration;
