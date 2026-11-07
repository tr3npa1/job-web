import React, { useState } from "react";
import Field from "../components/Field";
import { api } from "../api";
export default function Auth({ onLogin, initialError = "" }) {
  const [register, setRegister] = useState(false),
    [role, setRole] = useState("client"),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(initialError);
  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await api(
        register ? "/register" : "/login",
        "POST",
        Object.fromEntries(new FormData(e.currentTarget)),
      );
      onLogin(result.user);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="auth">
      <section className="auth-story">
        <a className="brand" href="/">
          j<span>↗</span> <b>job-web</b>
        </a>
        <div>
          <p className="eyebrow">PEOPLE. POTENTIAL. POSSIBILITY.</p>
          <h1>
            The next chapter
            <br />
            starts here.
          </h1>
          <p>
            A thoughtful space for talent and opportunity to meet. Find your
            next role, or the person who makes a difference.
          </p>
          <div className="orbit" aria-hidden="true">
            <span>↗</span>
            <i />
            <b>Made for what’s next.</b>
          </div>
        </div>
        <small>YOUR RECRUITMENT WORKSPACE</small>
      </section>
      <main className="auth-form">
        <div className="auth-top">
          {register ? "Already part of job-web?" : "New to job-web?"}{" "}
          <button
            className="text-button"
            disabled={busy}
            onClick={() => {
              setRegister(!register);
              setError("");
            }}
          >
            {register ? "Sign in" : "Create an account"} ↗
          </button>
        </div>
        <div className="auth-inner">
          <p className="eyebrow">LET’S GET STARTED</p>
          <h2>{register ? "Make your next move." : "Welcome back."}</h2>
          <p className="muted">
            {register
              ? "A few details to connect you with opportunity."
              : "Sign in to your recruitment workspace."}
          </p>
          {error && (
            <div role="alert" className="notice error">
              {error}
            </div>
          )}
          <form onSubmit={submit} key={String(register)}>
            {register && (
              <>
                <div className="role-switch">
                  <button
                    type="button"
                    disabled={busy}
                    aria-pressed={role === "client"}
                    className={role === "client" ? "selected" : ""}
                    onClick={() => setRole("client")}
                  >
                    I’m looking for work
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    aria-pressed={role === "recruiter"}
                    className={role === "recruiter" ? "selected" : ""}
                    onClick={() => setRole("recruiter")}
                  >
                    I’m hiring
                  </button>
                </div>
                <input type="hidden" name="type" value={role} />
                <Field name="name" label="Full name" autoComplete="name" />
              </>
            )}
            <Field
              name="email"
              label="Email address"
              type="email"
              autoComplete="email"
              maxLength={register ? 45 : 120}
            />
            <div className={register ? "form-grid" : ""}>
              <Field
                name="password"
                label="Password"
                type="password"
                autoComplete={register ? "new-password" : "current-password"}
              />
              {register && (
                <Field
                  name="confirm"
                  label="Confirm password"
                  type="password"
                  autoComplete="new-password"
                />
              )}
            </div>
            {register && (
              <>
                <div className="form-grid">
                  <Field
                    name="gender"
                    label="Gender"
                    options={[
                      ["", "Select"],
                      ["M", "Male"],
                      ["F", "Female"],
                    ]}
                  />
                  <Field name="location" label="Location" />
                  {role === "recruiter" ? (
                    <Field name="company" label="Company name" />
                  ) : (
                    <>
                      <Field
                        name="age"
                        label="Age"
                        type="number"
                        min="1"
                        max="150"
                      />
                      <Field
                        name="experience"
                        label="Experience (years)"
                        type="number"
                        min="0"
                        max="2147483647"
                      />
                      <Field
                        name="qualification"
                        label="Qualification (optional)"
                        required={false}
                      />
                      <Field
                        name="skills"
                        label="Skills (optional)"
                        required={false}
                      />
                    </>
                  )}
                </div>
              </>
            )}
            <button className="primary full" disabled={busy}>
              {busy
                ? "Please wait…"
                : register
                  ? "Create account →"
                  : "Sign in →"}
            </button>
          </form>
          <p className="auth-note">One workspace. Meaningful connections.</p>
        </div>
      </main>
    </div>
  );
}
