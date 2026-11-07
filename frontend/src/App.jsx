import React, { useEffect, useRef, useState } from "react";
import Auth from "./pages/Auth";
import Field from "./components/Field";
import { api } from "./api";
const types = [
  ["FullTime", "Full time"],
  ["PartTime", "Part time"],
  ["Intern", "Internship"],
];
const typeLabel = (value) => types.find(([v]) => v === value)?.[1] || value;
export default function App() {
  const [user, setUser] = useState(null);
  const [starting, setStarting] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    api("/me")
      .then((result) => {
        if (active) setUser(result.user);
      })
      .catch((error) => {
        if (active && error.status !== 401) setError(error.message);
      })
      .finally(() => {
        if (active) setStarting(false);
      });
    return () => {
      active = false;
    };
  }, []);

  if (starting)
    return (
      <div className="boot" role="status">
        Opening job-web…
      </div>
    );
  if (!user)
    return (
      <Auth
        initialError={error}
        onLogin={(account) => {
          setError("");
          setUser(account);
        }}
      />
    );
  return (
    <Workspace
      key={user.email}
      user={user}
      onLogout={(message = "") => {
        setError(message);
        setUser(null);
      }}
    />
  );
}

function Workspace({ user, onLogout }) {
  const [page, setPage] = useState("jobs");
  const [jobs, setJobs] = useState([]);
  const [apps, setApps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [query, setQuery] = useState("");
  const [kind, setKind] = useState("");
  const [sort, setSort] = useState("");
  const requestVersion = useRef(0);

  async function refresh() {
    const version = ++requestVersion.current;
    setLoading(true);
    setError("");
    try {
      const [jobResult, applicationResult] = await Promise.all([
        api("/jobs"),
        api("/applications"),
      ]);
      if (version !== requestVersion.current) return;
      setJobs(jobResult.jobs);
      setApps(applicationResult.applications);
    } catch (error) {
      if (version !== requestVersion.current) return;
      setError(error.message);
      if (error.status === 401)
        onLogout("Your session expired. Please sign in again.");
    } finally {
      if (version === requestVersion.current) setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    // Ignore late responses after sign-out or an account change.
    return () => {
      requestVersion.current++;
    };
  }, []);
  function navigate(next) {
    setPage(next);
    setQuery("");
    setKind("");
    setSort("");
    setError("");
    setSuccess("");
  }
  async function act(path, method, body, message) {
    setBusy(true);
    setError("");
    setSuccess("");
    try {
      await api(path, method, body);
      setSuccess(message);
      await refresh();
      return true;
    } catch (e) {
      setError(e.message);
      if (e.status === 401)
        onLogout("Your session expired. Please sign in again.");
      return false;
    } finally {
      setBusy(false);
    }
  }
  const recruiter = user.type === "recruiter";
  let rows = page === "applications" ? apps : jobs;
  rows = rows.filter(
    (r) =>
      (!kind || r.JobType === kind) &&
      Object.values(r).join(" ").toLowerCase().includes(query.toLowerCase()),
  );
  if (sort)
    rows = [...rows].sort((a, b) =>
      String(a[sort] ?? "").localeCompare(String(b[sort] ?? ""), undefined, {
        numeric: true,
      }),
    );
  async function post(e) {
    e.preventDefault();
    if (
      await act(
        "/jobs",
        "POST",
        Object.fromEntries(new FormData(e.currentTarget)),
        "Your job is now available to clients.",
      )
    )
      setPage("jobs");
  }
  return (
    <div className="workspace">
      <aside className="sidebar">
        <a className="brand" href="/">
          j<span>↗</span> <b>job-web</b>
        </a>
        <p className="nav-caption">WORKSPACE</p>
        <nav aria-label="Workspace">
          <button
            aria-current={page === "jobs" ? "page" : undefined}
            className={page === "jobs" ? "active" : ""}
            onClick={() => navigate("jobs")}
          >
            <span>▦</span>
            {recruiter ? "Posted jobs" : "Discover jobs"}
          </button>
          <button
            aria-current={page === "applications" ? "page" : undefined}
            className={page === "applications" ? "active" : ""}
            onClick={() => navigate("applications")}
          >
            <span>▤</span>
            {recruiter ? "Applicants" : "My applications"}
            <small>{apps.length}</small>
          </button>
          {recruiter && (
            <button
              className={page === "create" ? "active" : ""}
              onClick={() => navigate("create")}
            >
              <span>＋</span>Post a job
            </button>
          )}
        </nav>
        <div className="sidebar-note">
          <span>↗</span>
          <h3>
            A little ambition.
            <br />A new possibility.
          </h3>
          <p>
            {recruiter
              ? "Your next great hire starts with an opportunity."
              : "Your skills deserve the right opportunity."}
          </p>
        </div>
        <div className="identity">
          <div className="avatar">{user.name.slice(0, 1).toUpperCase()}</div>
          <div>
            <b>{user.name}</b>
            <small>{recruiter ? "Recruiter" : "Client"} account</small>
          </div>
        </div>
        <button
          className="logout"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            try {
              await api("/logout", "POST");
              onLogout();
            } catch (e) {
              setError(e.message);
            } finally {
              setBusy(false);
            }
          }}
        >
          Sign out ↗
        </button>
      </aside>
      <div className="main-area">
        <header className="topbar">
          <span>
            Workspace <span className="slash">/</span>{" "}
            {page === "applications"
              ? "Applications"
              : page === "create"
                ? "New opportunity"
                : "Jobs"}
          </span>
          <span className="account-chip">
            {recruiter ? user.profile.CompanyName : user.profile.CLocation}
          </span>
        </header>
        <main className="content">
          <div className="page-heading">
            <div>
              <p className="eyebrow">
                {recruiter ? "BUILD YOUR TEAM" : "FIND YOUR NEXT CHAPTER"}
              </p>
              <h1>
                {page === "create"
                  ? "Open a new door."
                  : page === "applications"
                    ? recruiter
                      ? "Meet your applicants."
                      : "Your next steps."
                    : recruiter
                      ? "Great teams start here."
                      : "Good work starts here."}
              </h1>
              <p className="muted">
                {page === "create"
                  ? "Share the essentials. Connect with the right people."
                  : page === "applications"
                    ? "Every application is a new possibility."
                    : recruiter
                      ? "Manage your opportunities and the people behind them."
                      : "Explore opportunities that match your ambition."}
              </p>
            </div>
            {recruiter && page !== "create" && (
              <button className="primary" onClick={() => navigate("create")}>
                ＋ Post a job
              </button>
            )}
          </div>
          <section className="stats">
            <div>
              <span>
                {recruiter ? "Your posted jobs" : "Available opportunities"}
              </span>
              <strong>{jobs.length.toString().padStart(2, "0")}</strong>
              <small>Ready for the next step ↗</small>
            </div>
            <div>
              <span>
                {recruiter ? "Applications received" : "Your applications"}
              </span>
              <strong>{apps.length.toString().padStart(2, "0")}</strong>
              <small>Connections in the making</small>
            </div>
            <div className="stat-accent">
              <span>YOUR WORKSPACE</span>
              <h3>
                {recruiter
                  ? "Find the people.\nBuild the future."
                  : "Bring your potential.\nFind your place."}
              </h3>
              <span className="big-arrow" aria-hidden="true">
                ↗
              </span>
            </div>
          </section>
          {error && (
            <div className="notice error" role="alert">
              {error}{" "}
              <button className="text-button" onClick={refresh}>
                Retry
              </button>
            </div>
          )}
          {success && (
            <div className="notice success" role="status">
              {success}
            </div>
          )}
          {page === "create" ? (
            <section className="panel post-panel">
              <h2>The opportunity</h2>
              <p className="muted">
                All fields are required. Salary uses your organization’s chosen
                currency and period.
              </p>
              <form onSubmit={post}>
                <div className="form-grid">
                  <Field
                    name="JobRole"
                    label="Job role"
                    placeholder="e.g. Frontend developer"
                  />
                  <Field
                    name="JobType"
                    label="Employment type"
                    options={types}
                  />
                  <Field
                    name="Qualification"
                    label="Qualification"
                    placeholder="e.g. BTech / BE"
                  />
                  <Field
                    name="MinExp"
                    label="Minimum experience (years)"
                    type="number"
                    min="0"
                    max="2147483647"
                  />
                  <Field
                    name="Salary"
                    label="Salary"
                    type="number"
                    min="0"
                    max="2147483647"
                  />
                </div>
                <div className="form-actions">
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => navigate("jobs")}
                  >
                    Cancel
                  </button>
                  <button disabled={busy} className="primary">
                    {busy ? "Publishing…" : "Publish opportunity →"}
                  </button>
                </div>
              </form>
            </section>
          ) : (
            <>
              <div className="section-heading">
                <h2>
                  {page === "applications"
                    ? recruiter
                      ? "All applicants"
                      : "My applications"
                    : recruiter
                      ? "Your opportunities"
                      : "Explore opportunities"}{" "}
                  <span className="count">{rows.length}</span>
                </h2>
                <button
                  className="text-button"
                  disabled={loading || busy}
                  onClick={refresh}
                >
                  ↻ Refresh
                </button>
              </div>
              <div className="filters">
                <input
                  aria-label="Search opportunities or applicants"
                  placeholder="Search by role, company, location…"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
                {!(recruiter && page === "applications") && (
                  <select
                    aria-label="Filter job type"
                    value={kind}
                    onChange={(e) => setKind(e.target.value)}
                  >
                    <option value="">All job types</option>
                    {types.map(([v, l]) => (
                      <option key={v} value={v}>
                        {l}
                      </option>
                    ))}
                  </select>
                )}
                <select
                  aria-label="Sort results"
                  value={sort}
                  onChange={(e) => setSort(e.target.value)}
                >
                  <option value="">Newest first</option>
                  {(recruiter && page === "applications"
                    ? [
                        ["JobRole", "Role"],
                        ["CName", "Name"],
                        ["CLocation", "Location"],
                      ]
                    : [
                        ["JobRole", "Role"],
                        ["JobType", "Type"],
                        ["CompanyLocation", "Location"],
                      ]
                  ).map(([v, l]) => (
                    <option key={v} value={v}>
                      Sort by {l}
                    </option>
                  ))}
                </select>
              </div>
              {loading ? (
                <div className="empty" role="status">
                  Loading your workspace…
                </div>
              ) : rows.length === 0 ? (
                <div className="empty">
                  <span>↗</span>
                  <h3>
                    {query || kind
                      ? "No matching results."
                      : page === "applications"
                        ? "No applications yet."
                        : "Room for new opportunities."}
                  </h3>
                  <p>
                    {query || kind
                      ? "Try a different search or filter."
                      : recruiter
                        ? "Post a job to begin connecting with candidates."
                        : "Check back for jobs, or explore available opportunities."}
                  </p>
                  <button
                    className="secondary"
                    onClick={() => {
                      if (query || kind) {
                        setQuery("");
                        setKind("");
                      } else navigate(recruiter ? "create" : "jobs");
                    }}
                  >
                    {query || kind
                      ? "Clear filters"
                      : recruiter
                        ? "Post a job"
                        : "Explore jobs"}
                  </button>
                </div>
              ) : recruiter && page === "applications" ? (
                <div
                  className="table-wrap"
                  role="region"
                  aria-label="Applicants"
                  tabIndex={0}
                >
                  <table>
                    <thead>
                      <tr>
                        {[
                          "Candidate",
                          "Applied for",
                          "Location",
                          "Experience",
                          "Qualification & skills",
                          "Age / gender",
                        ].map((h) => (
                          <th scope="col" key={h}>
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((r) => (
                        <tr key={r.AID}>
                          <td>
                            <b>{r.CName}</b>
                            <small>{r.CEmail}</small>
                          </td>
                          <td>{r.JobRole}</td>
                          <td>{r.CLocation}</td>
                          <td>{r.CExp} years</td>
                          <td>
                            {r.CQualification}
                            <small>{r.CSkills || "No skills provided"}</small>
                          </td>
                          <td>
                            {r.CAge} / {r.CGender}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="job-grid">
                  {rows.map((r) => {
                    const applied = apps.some((a) => a.JID === r.JID);
                    return (
                      <article className="job-card" key={r.AID || r.JID}>
                        <div className="card-top">
                          <div className="company-icon">
                            {r.CompanyName.slice(0, 1)}
                          </div>
                          <span className="badge">{typeLabel(r.JobType)}</span>
                        </div>
                        <p className="company">
                          {r.CompanyName} <span>· {r.CompanyLocation}</span>
                        </p>
                        <h3>{r.JobRole}</h3>
                        <div className="job-details">
                          <span>◷ {r.MinExp}+ years experience</span>
                          <span>◇ {r.Qualification}</span>
                        </div>
                        <div className="card-bottom">
                          <div>
                            <strong>{Number(r.Salary).toLocaleString()}</strong>
                            <small>Listed salary</small>
                          </div>
                          {recruiter ? (
                            <button
                              className="secondary danger"
                              disabled={busy}
                              onClick={() => {
                                if (
                                  window.confirm(
                                    "Delete this job and all its applications?",
                                  )
                                )
                                  act(
                                    `/jobs/${r.JID}`,
                                    "DELETE",
                                    {},
                                    "Job and its applications deleted.",
                                  );
                              }}
                            >
                              Delete job
                            </button>
                          ) : page === "applications" ? (
                            <button
                              className="secondary"
                              disabled={busy}
                              onClick={() => {
                                if (
                                  window.confirm("Withdraw this application?")
                                )
                                  act(
                                    `/applications/${r.AID}`,
                                    "DELETE",
                                    {},
                                    "Application withdrawn.",
                                  );
                              }}
                            >
                              Withdraw
                            </button>
                          ) : (
                            <button
                              className={applied ? "secondary" : "primary"}
                              disabled={busy || applied}
                              onClick={() =>
                                act(
                                  `/jobs/${r.JID}/apply`,
                                  "POST",
                                  {},
                                  "Application submitted. Good luck!",
                                )
                              }
                            >
                              {applied ? "✓ Applied" : "Apply now ↗"}
                            </button>
                          )}
                        </div>
                        {recruiter && (
                          <small className="app-count">
                            {r.application_count} applications received
                          </small>
                        )}
                      </article>
                    );
                  })}
                </div>
              )}
            </>
          )}
          <footer>
            job-web <span>Where potential meets possibility.</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
