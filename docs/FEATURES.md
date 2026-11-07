# Features

## Accounts

Both recruiters and clients can register, sign in, and sign out. Sessions persist across page refreshes and expire after eight hours without activity. Registration requires a name, email, password confirmation, gender, and location. Recruiters also provide a company name. Clients provide age and experience; qualification and skills are optional.

Server validation checks required fields, schema length limits, valid roles, numeric ranges, duplicate emails, and password confirmation. The source's gender choices (`M`, `F`) and employment types (`FullTime`, `PartTime`, `Intern`) are retained. New passwords are hashed. Existing plaintext credentials are upgraded after a successful login.

## Recruiters

- Create jobs with a role, employment type, qualification, minimum experience, and salary.
- List only their own postings and see each posting's application count.
- View applicants for their jobs, including name, email, age, gender, location, experience, skills, and qualification.
- Delete owned jobs after confirmation. The job and its applications are deleted in one transaction.

Recruiters cannot submit applications or access another recruiter's applicant list.

## Clients

- Browse jobs with company names, locations, qualifications, experience requirements, and salary.
- Submit one application per job. The UI marks submitted jobs as Applied, and the API rejects repeat submissions.
- List and withdraw their own applications after confirmation.
- Apply again after withdrawing an application.

Qualifications and experience are displayed rather than enforced as eligibility rules, matching the original workflow. Clients cannot create or delete jobs or withdraw another client's application.

## Search, sorting, and feedback

Search is case-insensitive across fetched record values. Job and client-application lists support employment-type filtering and sorting by role, type, or company location. Applicant lists support sorting by role, candidate name, or location. Default order is descending record ID; IDs are not displayed as dates.

The interface provides loading indicators, empty and filtered-empty states, success/error messages, retry, and disabled mutation controls while a request is pending. Requests time out after 15 seconds. Workspace state is discarded when an account signs out, and expired sessions return to sign-in. Layouts adapt to narrow screens; applicant tables scroll within their container. Form controls have labels and visible keyboard focus.

## Scope boundaries

Job editing, hiring statuses, notifications, resumes, profile editing, password recovery, and application timestamps are not implemented. Salary is a numeric amount without a currency or time-period field. Skills remain a comma-separated string. SQL examples and optional triggers are database resources, not additional UI modules.
