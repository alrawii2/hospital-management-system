import { useState, useEffect } from "react";
import "./App.css";

const API = "http://localhost:8000";

async function apiFetch(path, options = {}, token = null) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Token ${token}`;
  const res = await fetch(`${API}${path}`, { ...options, headers });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Request failed");
  return data;
}

// =========================================================================
// LoginPage — single-form split-card. One form for every role; the backend
// returns user.role and the App component routes accordingly.
// =========================================================================
function LoginPage({ onLogin }) {
  const [form, setForm] = useState({ username: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    if (!form.username || !form.password) {
      setError("Please fill in all fields.");
      return;
    }
    setLoading(true);
    try {
      const data = await apiFetch("/api/login/", {
        method: "POST",
        body: JSON.stringify({
          username: form.username.trim(),
          password: form.password,
        }),
      });
      onLogin(data.user, data.token);
    } catch (err) {
      setError("Invalid credentials. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-bg">
      <div className="login-card">
        {/* Left form column */}
        <div className="login-panel login-panel-form">
          <div className="login-logo">
            <span className="login-logo-mark">✦</span>
            <span className="login-logo-text">MediCare</span>
          </div>
          <p className="login-subtitle">PATIENT PORTAL</p>
          <h1 className="login-heading">Welcome back</h1>

          {error && (
            <div className="alert alert-error" role="alert">{error}</div>
          )}

          <form onSubmit={handleSubmit} className="login-form" noValidate>
            <div className="login-field">
              <label htmlFor="login-username">Username</label>
              <input
                id="login-username"
                type="text"
                autoComplete="username"
                value={form.username}
                onChange={(e) => setForm({ ...form, username: e.target.value })}
              />
            </div>
            <div className="login-field">
              <label htmlFor="login-password">Password</label>
              <input
                id="login-password"
                type="password"
                autoComplete="current-password"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
              />
            </div>
            <button type="submit" className="login-submit-btn" disabled={loading}>
              {loading ? "Signing in..." : "Sign In"}
            </button>
          </form>
        </div>

        {/* Right gradient marketing column */}
        <div className="login-panel login-panel-hero">
          <div className="panel-content">
            <div className="panel-icon">🏥</div>
            <h2 className="panel-heading">Your Health, Our Priority</h2>
            <p className="panel-tagline">
              Book appointments, track your health records, and connect with top specialists.
            </p>
            <ul className="panel-features">
              <li><span className="panel-check">✔</span> Instant appointment booking</li>
              <li><span className="panel-check">✔</span> Expert doctors across specialties</li>
              <li><span className="panel-check">✔</span> Secure health records</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

// =========================================================================
// PATIENT FLOW — appointment cards, availability-driven booking, cancellation
// =========================================================================

function AppointmentCard({ appt, onCancel }) {
  const isCancelled = appt.status === "CANCELLED";
  const isCompleted = appt.status === "COMPLETED";
  const isUpcoming = !isCancelled && !isCompleted;

  let statusClass = "badge-blue";
  let statusLabel = "Upcoming";
  if (isCancelled) { statusClass = "badge-red"; statusLabel = "Cancelled"; }
  else if (isCompleted) { statusClass = "badge-green"; statusLabel = "Completed"; }

  return (
    <div className="appt-card">
      <div className="appt-avatar">
        {appt.doctor_name?.split(" ").slice(-2).map(n => n[0]).join("") || "DR"}
      </div>
      <div className="appt-info">
        <div className="appt-doctor">{appt.doctor_name}</div>
        <div className="appt-specialty">{appt.specialty}</div>
        <div className="appt-reason">{appt.reason}</div>
      </div>
      <div className="appt-meta">
        <div className="appt-date">{appt.date}</div>
        <div className="appt-time">{appt.time}</div>
        <span className={`badge ${statusClass}`}>{statusLabel}</span>
      </div>
      {isUpcoming && onCancel && (
        <div className="appt-card-actions">
          <button
            type="button"
            className="btn btn-ghost-danger"
            onClick={() => onCancel(appt)}
          >
            Cancel
          </button>
        </div>
      )}
    </div>
  );
}

function ConfirmCancelDialog({ appt, onConfirm, onClose, busy }) {
  if (!appt) return null;
  return (
    <div className="modal-overlay" role="dialog" aria-modal="true">
      <div className="modal-card">
        <h3>Cancel this appointment?</h3>
        <p>
          You are about to cancel your visit with <strong>{appt.doctor_name}</strong>
          {" "}on {appt.date} at {appt.time}. This cannot be undone.
        </p>
        <div className="modal-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose} disabled={busy}>
            Keep it
          </button>
          <button type="button" className="btn btn-danger" onClick={onConfirm} disabled={busy}>
            {busy ? "Cancelling..." : "Yes, cancel"}
          </button>
        </div>
      </div>
    </div>
  );
}

function PatientDashboard({ appointments, doctors, setPage }) {
  const upcoming  = appointments.filter(a => a.status === "PENDING" || a.status === "CONFIRMED");
  const completed = appointments.filter(a => a.status === "COMPLETED");
  return (
    <div className="page">
      <div className="page-header">
        <h1>Dashboard</h1>
        <p>Here is an overview of your health activity.</p>
      </div>
      <div className="stats-row">
        <div className="stat-card stat-blue"><div className="stat-number">{upcoming.length}</div><div className="stat-label">Upcoming Appointments</div></div>
        <div className="stat-card stat-green"><div className="stat-number">{completed.length}</div><div className="stat-label">Completed Visits</div></div>
        <div className="stat-card stat-teal"><div className="stat-number">{doctors.length}</div><div className="stat-label">Available Doctors</div></div>
      </div>
      <div className="section">
        <div className="section-header">
          <h2>Upcoming Appointments</h2>
          <button className="btn btn-ghost" onClick={() => setPage("appointments")}>View all</button>
        </div>
        {upcoming.length === 0 ? (
          <div className="empty-state">
            <p>No upcoming appointments.</p>
            <button className="btn btn-primary" onClick={() => setPage("book")}>Book Now</button>
          </div>
        ) : (
          <div className="appt-list">{upcoming.slice(0, 3).map(appt => <AppointmentCard key={appt.id} appt={appt} />)}</div>
        )}
      </div>
      <div className="section">
        <div className="section-header">
          <h2>Our Specialists</h2>
          <button className="btn btn-ghost" onClick={() => setPage("book")}>Book Appointment</button>
        </div>
        <div className="doctors-grid">
          {doctors.slice(0, 3).map(doc => {
            const years = doc.years_of_experience;
            const summary = [
              doc.name,
              years != null ? `${years} yrs` : null,
              doc.specialization,
            ].filter(Boolean).join(" · ");
            return (
              <div key={doc.id} className="doctor-card">
                <div className="avatar avatar-md">{doc.name.split(" ").slice(-2).map(n => n[0]).join("")}</div>
                <div className="doctor-info">
                  <div className="doctor-name">{summary}</div>
                  <div className="doctor-specialty">{doc.specialization}</div>
                  <div className="doctor-days"><span className="day-badge">{doc.department?.name}</span></div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// =========================================================================
// BookingCalendar — month grid that highlights only the days the selected
// doctor is available on. Built on the native Date API; no date library.
// =========================================================================

const MONTHS = ["January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"];
const DOW_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function isoDate(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${dd}`;
}

function sameDay(a, b) {
  return a.getFullYear() === b.getFullYear()
      && a.getMonth() === b.getMonth()
      && a.getDate() === b.getDate();
}

// JS getDay(): 0=Sun..6=Sat. DoctorAvailability.weekday: 0=Mon..6=Sun. Map them.
function jsDayToBackendWeekday(jsDay) {
  return jsDay === 0 ? 6 : jsDay - 1;
}

function BookingCalendar({ doctorId, token, value, onChange }) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const initialMonth = new Date(today.getFullYear(), today.getMonth(), 1);
  const [viewMonth, setViewMonth] = useState(initialMonth);
  const [activeWeekdays, setActiveWeekdays] = useState(null); // Set of backend weekday ints

  useEffect(() => {
    if (!doctorId) { setActiveWeekdays(null); return; }
    let cancelled = false;
    apiFetch(`/api/doctors/${doctorId}/availability/`, {}, token)
      .then(rows => {
        if (cancelled) return;
        const wd = new Set(rows.filter(r => r.active).map(r => r.weekday));
        setActiveWeekdays(wd);
      })
      .catch(() => { if (!cancelled) setActiveWeekdays(new Set()); });
    return () => { cancelled = true; };
  }, [doctorId, token]);

  const maxMonth = new Date(today.getFullYear(), today.getMonth() + 3, 1);
  function prevMonth() {
    const candidate = new Date(viewMonth.getFullYear(), viewMonth.getMonth() - 1, 1);
    if (candidate >= new Date(today.getFullYear(), today.getMonth(), 1)) setViewMonth(candidate);
  }
  function nextMonth() {
    const candidate = new Date(viewMonth.getFullYear(), viewMonth.getMonth() + 1, 1);
    if (candidate <= maxMonth) setViewMonth(candidate);
  }

  // Build the 6-row grid starting at the Sunday on/before the 1st of viewMonth
  const cells = [];
  const firstOfMonth = new Date(viewMonth.getFullYear(), viewMonth.getMonth(), 1);
  const startSunday = new Date(firstOfMonth);
  startSunday.setDate(firstOfMonth.getDate() - firstOfMonth.getDay());
  for (let i = 0; i < 42; i++) {
    const d = new Date(startSunday);
    d.setDate(startSunday.getDate() + i);
    cells.push(d);
  }

  if (!doctorId) {
    return <div className="avail-empty">Pick a doctor first to see their calendar.</div>;
  }

  const valueDate = value ? new Date(value + "T00:00:00") : null;
  const canPrev = viewMonth > new Date(today.getFullYear(), today.getMonth(), 1);
  const canNext = viewMonth < maxMonth;

  return (
    <div className="calendar">
      <div className="calendar-header">
        <button type="button" className="calendar-nav" onClick={prevMonth}
                disabled={!canPrev} aria-label="Previous month">‹</button>
        <div className="calendar-title">{MONTHS[viewMonth.getMonth()]} {viewMonth.getFullYear()}</div>
        <button type="button" className="calendar-nav" onClick={nextMonth}
                disabled={!canNext} aria-label="Next month">›</button>
      </div>
      <div className="calendar-grid calendar-dow">
        {DOW_LABELS.map(l => <div key={l} className="calendar-dow-cell">{l}</div>)}
      </div>
      <div className="calendar-grid">
        {cells.map((d, i) => {
          const inMonth = d.getMonth() === viewMonth.getMonth();
          const past = d < today;
          const weekday = jsDayToBackendWeekday(d.getDay());
          const available = activeWeekdays && activeWeekdays.has(weekday);
          const disabled = past || !available;
          const selected = valueDate && sameDay(d, valueDate);
          return (
            <button
              key={i}
              type="button"
              disabled={disabled}
              onClick={() => !disabled && onChange(isoDate(d))}
              className={[
                "calendar-cell",
                !inMonth && "calendar-cell-muted",
                disabled && "calendar-cell-disabled",
                !disabled && !selected && "calendar-cell-available",
                selected && "calendar-cell-selected",
              ].filter(Boolean).join(" ")}
              aria-label={isoDate(d)}
            >
              <span className="calendar-cell-num">{d.getDate()}</span>
              {!available && !past && <span className="calendar-cell-dash">—</span>}
            </button>
          );
        })}
      </div>
      <div className="calendar-legend">
        <span><span className="legend-dot legend-dot-available" /> Available</span>
        <span><span className="legend-dot legend-dot-selected" /> Selected</span>
        <span><span className="legend-dot legend-dot-disabled" /> Unavailable</span>
      </div>
    </div>
  );
}

function BookAppointment({ doctors, token, onBook }) {
  const [form, setForm] = useState({ doctorId: "", date: "", time: "", reason: "" });
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [slots, setSlots] = useState([]);
  const [slotsLoading, setSlotsLoading] = useState(false);
  const selectedDoctor = doctors.find(d => d.id === parseInt(form.doctorId));

  useEffect(() => {
    if (!form.doctorId || !form.date) { setSlots([]); return; }
    let cancelled = false;
    setSlotsLoading(true);
    apiFetch(
      `/api/doctors/${form.doctorId}/slots/?date=${form.date}`,
      {}, token,
    )
      .then(data => { if (!cancelled) setSlots(data); })
      .catch(() => { if (!cancelled) setSlots([]); })
      .finally(() => { if (!cancelled) setSlotsLoading(false); });
    return () => { cancelled = true; };
  }, [form.doctorId, form.date, token]);

  async function handleBook(e) {
    e.preventDefault();
    setError("");
    if (!form.doctorId || !form.date || !form.time || !form.reason.trim()) {
      setError("Please complete all fields.");
      return;
    }
    setLoading(true);
    try {
      const dateObj = new Date(form.date);
      const yyyy = dateObj.getFullYear();
      const mm = String(dateObj.getMonth() + 1).padStart(2, "0");
      const dd = String(dateObj.getDate()).padStart(2, "0");
      const scheduled_at = `${yyyy}-${mm}-${dd}T${form.time}:00`;
      const appt = await apiFetch(
        `/api/appointments/book/${form.doctorId}/`,
        { method: "POST", body: JSON.stringify({ scheduled_at, reason: form.reason }) },
        token,
      );
      onBook(appt);
      setSuccess(true);
      setForm({ doctorId: "", date: "", time: "", reason: "" });
    } catch (err) {
      setError(err.message || "Booking failed.");
    } finally {
      setLoading(false);
    }
  }

  if (success) {
    return (
      <div className="page">
        <div className="success-box">
          <div className="success-icon">✓</div>
          <h2>Appointment Booked!</h2>
          <p>Your appointment has been confirmed. You can view it in My Appointments.</p>
          <button className="btn btn-primary" onClick={() => setSuccess(false)}>Book Another</button>
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>Book an Appointment</h1>
        <p>Choose a doctor, date, and time that works for you.</p>
      </div>
      <div className="book-layout">
        <div className="book-form-card">
          {error && <div className="alert alert-error">{error}</div>}
          <form onSubmit={handleBook}>
            <div className="field">
              <label>Select Doctor</label>
              <select value={form.doctorId} onChange={e => setForm({ ...form, doctorId: e.target.value })}>
                <option value="">Choose a specialist</option>
                {doctors.map(doc => (
                  <option key={doc.id} value={doc.id}>
                    {doc.name} – {doc.specialization}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Preferred Date</label>
              <BookingCalendar
                doctorId={form.doctorId ? parseInt(form.doctorId) : null}
                token={token}
                value={form.date}
                onChange={(d) => setForm({ ...form, date: d, time: "" })}
              />
            </div>
            <div className="field">
              <label>Time Slot</label>
              {!form.doctorId || !form.date ? (
                <div className="avail-empty">Pick a doctor and date to see open slots.</div>
              ) : slotsLoading ? (
                <div className="avail-empty">Loading availability…</div>
              ) : slots.length === 0 ? (
                <div className="avail-empty">No availability on this date — please pick another.</div>
              ) : (
                <div className="time-grid">
                  {slots.map(s => (
                    <button
                      key={s.time}
                      type="button"
                      className={`time-slot ${form.time === s.time ? "time-slot-active" : ""}`}
                      onClick={() => setForm({ ...form, time: s.time })}
                    >
                      {s.time}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <div className="field">
              <label>Reason for Visit</label>
              <textarea
                placeholder="Briefly describe your symptoms"
                value={form.reason}
                rows={3}
                onChange={e => setForm({ ...form, reason: e.target.value })}
              />
            </div>
            <button type="submit" className="btn btn-primary btn-full" disabled={loading}>
              {loading ? "Booking..." : "Confirm Booking"}
            </button>
          </form>
        </div>
        <div className="doctor-preview">
          <h3>Doctor Details</h3>
          {selectedDoctor ? (
            <div className="preview-card">
              <div className="avatar avatar-xl">
                {selectedDoctor.name.split(" ").slice(-2).map(n => n[0]).join("")}
              </div>
              <div className="doctor-name">{selectedDoctor.name}</div>
              <div className="doctor-specialty">{selectedDoctor.specialization}</div>
              <div className="preview-days">
                <strong>Specialization:</strong>
                <div>{selectedDoctor.specialization}</div>
              </div>
              <div className="preview-days">
                <strong>Experience:</strong>
                <div>{selectedDoctor.years_of_experience ?? 0} years</div>
              </div>
              <div className="preview-days">
                <strong>Department:</strong>
                <div><span className="day-badge">{selectedDoctor.department?.name}</span></div>
              </div>
            </div>
          ) : (
            <div className="preview-empty">Select a doctor to see details here.</div>
          )}
        </div>
      </div>
    </div>
  );
}

function ViewAppointments({ appointments, setPage, token, onCancelled }) {
  const [filter, setFilter] = useState("All");
  const [target, setTarget] = useState(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const filters = ["All", "Upcoming", "Completed", "Cancelled"];
  const filtered = appointments.filter(a => {
    if (filter === "All") return true;
    if (filter === "Upcoming") return a.status === "PENDING" || a.status === "CONFIRMED";
    if (filter === "Completed") return a.status === "COMPLETED";
    if (filter === "Cancelled") return a.status === "CANCELLED";
    return true;
  });

  async function handleConfirmCancel() {
    if (!target) return;
    setBusy(true); setError("");
    try {
      const updated = await apiFetch(
        `/api/appointments/${target.id}/cancel/`,
        { method: "POST" },
        token,
      );
      onCancelled(updated);
      setMessage(`Appointment with ${target.doctor_name} on ${target.date} was cancelled.`);
      setTarget(null);
    } catch (err) {
      setError(err.message || "Could not cancel appointment.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>My Appointments</h1>
        <p>Track all your scheduled and past visits.</p>
      </div>
      {message && <div className="alert-success" role="status">{message}</div>}
      {error && <div className="alert alert-error" role="alert">{error}</div>}
      <div className="filter-row">
        {filters.map(f => (
          <button
            key={f}
            className={`filter-btn ${filter === f ? "filter-btn-active" : ""}`}
            onClick={() => setFilter(f)}
          >{f}</button>
        ))}
      </div>
      {filtered.length === 0 ? (
        <div className="empty-state">
          <p>No {filter.toLowerCase()} appointments found.</p>
          <button className="btn btn-primary" onClick={() => setPage("book")}>Book Appointment</button>
        </div>
      ) : (
        <div className="appt-list">
          {filtered.map(appt => (
            <AppointmentCard
              key={appt.id}
              appt={appt}
              onCancel={setTarget}
            />
          ))}
        </div>
      )}
      <ConfirmCancelDialog
        appt={target}
        busy={busy}
        onClose={() => { if (!busy) setTarget(null); }}
        onConfirm={handleConfirmCancel}
      />
    </div>
  );
}

function PatientSidebar({ activePage, setPage, user, onLogout, sidebarOpen, setSidebarOpen }) {
  const navItems = [
    { id: "dashboard",    label: "Dashboard",        icon: "⊡" },
    { id: "book",         label: "Book Appointment", icon: "＋" },
    { id: "appointments", label: "My Appointments",  icon: "◫" },
  ];
  return (
    <>
      {sidebarOpen && <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />}
      <aside className={`sidebar ${sidebarOpen ? "sidebar-open" : ""}`}>
        <div className="sidebar-logo"><span className="logo-icon">✦</span><span className="logo-text">MediCore</span></div>
        <div className="sidebar-patient">
          <div className="avatar avatar-lg">
            {user.name?.split(" ").map(n => n[0]).join("") || "P"}
          </div>
          <div>
            <div className="patient-name">{user.name}</div>
            <div className="patient-id">ID: {user.id}</div>
          </div>
        </div>
        <nav className="sidebar-nav">
          {navItems.map(item => (
            <button
              key={item.id}
              className={`nav-item ${activePage === item.id ? "nav-item-active" : ""}`}
              onClick={() => { setPage(item.id); setSidebarOpen(false); }}
            >
              <span className="nav-icon">{item.icon}</span><span>{item.label}</span>
            </button>
          ))}
        </nav>
        <button className="nav-item nav-logout" onClick={onLogout}>
          <span className="nav-icon">⇤</span><span>Log Out</span>
        </button>
      </aside>
    </>
  );
}

// =========================================================================
// GENERIC ROLE SHELL — reusable sidebar + content area for non-patient roles.
// Every role flow renders through this component using the same patient blue
// palette. No role-tinted accents anywhere.
// =========================================================================

function RoleSidebar({ items, activePage, setPage, user, onLogout, roleLabel, sidebarOpen, setSidebarOpen }) {
  return (
    <>
      {sidebarOpen && <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />}
      <aside className={`sidebar ${sidebarOpen ? "sidebar-open" : ""}`}>
        <div className="sidebar-logo"><span className="logo-icon">✦</span><span className="logo-text">MediCore</span></div>
        <div className="sidebar-patient">
          <div className="avatar avatar-lg">
            {user.name?.split(" ").map(n => n[0]).join("") || "U"}
          </div>
          <div>
            <div className="patient-name">{user.name}</div>
            <div className="patient-id">{roleLabel} · ID {user.id}</div>
          </div>
        </div>
        <nav className="sidebar-nav">
          {items.map(item => (
            <button
              key={item.id}
              className={`nav-item ${activePage === item.id ? "nav-item-active" : ""}`}
              onClick={() => { setPage(item.id); setSidebarOpen(false); }}
            >
              <span className="nav-icon">{item.icon}</span><span>{item.label}</span>
            </button>
          ))}
        </nav>
        <button className="nav-item nav-logout" onClick={onLogout}>
          <span className="nav-icon">⇤</span><span>Log Out</span>
        </button>
      </aside>
    </>
  );
}

const WEEKDAY_LABELS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

function MyAvailability({ user, token }) {
  // Doctor's own ID is not currently sent on the /api/login response, so we
  // fetch the doctor list and find ourselves by name match. A future iteration
  // would surface user.doctor_id directly from the login payload.
  const [doctorId, setDoctorId] = useState(null);
  const [rows, setRows] = useState(() => WEEKDAY_LABELS.map((_, i) => ({
    weekday: i, start_time: "09:00", end_time: "17:00",
    slot_minutes: 30, active: i < 5,
  })));
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    (async () => {
      try {
        const docs = await apiFetch("/api/doctors/", {}, token);
        const me = docs.find(d => d.name === `Dr. ${user.name}` || d.name.endsWith(user.name));
        if (cancelled || !me) return;
        setDoctorId(me.id);
        const existing = await apiFetch(`/api/doctors/${me.id}/availability/`, {}, token);
        if (cancelled) return;
        if (existing.length) {
          const byDay = new Map(existing.map(r => [r.weekday, r]));
          setRows(WEEKDAY_LABELS.map((_, i) => {
            const r = byDay.get(i);
            if (r) {
              return {
                weekday: i,
                start_time: r.start_time.slice(0, 5),
                end_time: r.end_time.slice(0, 5),
                slot_minutes: r.slot_minutes,
                active: r.active,
              };
            }
            return { weekday: i, start_time: "09:00", end_time: "17:00", slot_minutes: 30, active: false };
          }));
        }
      } catch {
        // Doctor profile not found via name match — leave defaults, save will fail clearly.
      }
    })();
    return () => { cancelled = true; };
  }, [token, user.name]);

  function updateRow(i, patch) {
    setRows(prev => prev.map((r, idx) => idx === i ? { ...r, ...patch } : r));
  }

  async function handleSave() {
    if (!doctorId) { setError("Could not locate your doctor profile."); return; }
    setBusy(true); setError(""); setMessage("");
    try {
      const payload = rows
        .filter(r => r.active)
        .map(r => ({
          weekday: r.weekday,
          start_time: r.start_time,
          end_time: r.end_time,
          slot_minutes: Number(r.slot_minutes) || 30,
          active: true,
        }));
      await apiFetch(
        `/api/doctors/${doctorId}/availability/`,
        { method: "PUT", body: JSON.stringify(payload) },
        token,
      );
      setMessage("Availability saved.");
    } catch (err) {
      setError(err.message || "Save failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <p style={{color: "var(--text-muted)", marginBottom: 12}}>
        Patients only see open slots inside the windows you mark active.
      </p>
      {message && <div className="alert-success" role="status">{message}</div>}
      {error && <div className="alert alert-error" role="alert">{error}</div>}
      <table className="avail-table">
        <thead>
          <tr>
            <th>Day</th>
            <th>Start</th>
            <th>End</th>
            <th>Slot (min)</th>
            <th>Active</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              <td>{WEEKDAY_LABELS[i]}</td>
              <td><input type="time" value={r.start_time} onChange={e => updateRow(i, {start_time: e.target.value})} /></td>
              <td><input type="time" value={r.end_time} onChange={e => updateRow(i, {end_time: e.target.value})} /></td>
              <td><input type="number" min="5" max="240" value={r.slot_minutes} onChange={e => updateRow(i, {slot_minutes: e.target.value})} /></td>
              <td><input type="checkbox" checked={r.active} onChange={e => updateRow(i, {active: e.target.checked})} /></td>
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{marginTop: 16}}>
        <button className="btn btn-primary" onClick={handleSave} disabled={busy}>
          {busy ? "Saving..." : "Save availability"}
        </button>
      </div>
    </div>
  );
}

// =========================================================================
// DOCTOR shell — Dashboard, My Schedule (+ MedicalRecordModal), Availability, Stock
// =========================================================================

function DoctorDashboardPage({ user, schedule }) {
  const todayStr = new Date().toISOString().slice(0, 10);
  const today = schedule.filter(a => a.date === todayStr);
  const pending = schedule.filter(a => (a.status === "PENDING" || a.status === "CONFIRMED") && !a.has_record);
  const completed = schedule.filter(a => a.status === "COMPLETED");
  return (
    <div className="page">
      <div className="page-header">
        <h1>Good day, Dr. {user.name.split(" ").slice(-1)[0]}.</h1>
        <p>Your clinical workspace for today.</p>
      </div>
      <div className="stats-row">
        <div className="stat-card stat-blue"><div className="stat-number">{today.length}</div><div className="stat-label">Today's Appointments</div></div>
        <div className="stat-card stat-teal"><div className="stat-number">{pending.length}</div><div className="stat-label">Pending Records</div></div>
        <div className="stat-card stat-green"><div className="stat-number">{completed.length}</div><div className="stat-label">Completed Visits</div></div>
      </div>
      <div className="section">
        <div className="section-header"><h2>Today's Appointments</h2></div>
        {today.length === 0 ? (
          <div className="empty-state"><p>No appointments scheduled for today.</p></div>
        ) : (
          <div className="appt-list">
            {today.map(a => (
              <div key={a.id} className="appt-card">
                <div className="appt-avatar">
                  {a.patient_name?.split(" ").map(n => n[0]).join("") || "P"}
                </div>
                <div className="appt-info">
                  <div className="appt-doctor">{a.patient_name}</div>
                  <div className="appt-reason">{a.reason}</div>
                </div>
                <div className="appt-meta">
                  <div className="appt-time">{a.time}</div>
                  <span className={`badge ${a.status === "COMPLETED" ? "badge-green" : "badge-blue"}`}>
                    {a.status[0] + a.status.slice(1).toLowerCase()}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function MedicalRecordModal({ appointment, token, drugs, onClose, onSaved }) {
  const [form, setForm] = useState({ diagnosis: "", notes: "", treatment: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [recordId, setRecordId] = useState(null);
  const [prescriptions, setPrescriptions] = useState([]);
  const [rxForm, setRxForm] = useState({ drug_name: "", dosage: "", frequency: "", duration: "", instructions: "" });

  if (!appointment) return null;

  async function saveRecord(e) {
    e.preventDefault();
    setError(""); setBusy(true);
    try {
      const data = await apiFetch(
        `/api/appointments/${appointment.id}/record/`,
        { method: "POST", body: JSON.stringify(form) },
        token,
      );
      setRecordId(data.id);
      onSaved();
    } catch (err) {
      setError(err.message || "Could not save record.");
    } finally {
      setBusy(false);
    }
  }

  async function addPrescription(e) {
    e.preventDefault();
    if (!recordId) return;
    if (!rxForm.drug_name.trim()) { setError("Drug name is required."); return; }
    setError(""); setBusy(true);
    try {
      const rx = await apiFetch(
        `/api/records/${recordId}/prescribe/`,
        { method: "POST", body: JSON.stringify(rxForm) },
        token,
      );
      setPrescriptions(prev => [...prev, rx]);
      setRxForm({ drug_name: "", dosage: "", frequency: "", duration: "", instructions: "" });
    } catch (err) {
      setError(err.message || "Could not add prescription.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true">
      <div className="modal-card modal-card-wide">
        <h3>Record visit — {appointment.patient_name} · {appointment.date} {appointment.time}</h3>
        {error && <div className="alert alert-error" role="alert">{error}</div>}
        {!recordId ? (
          <form onSubmit={saveRecord} className="record-form">
            <div className="field">
              <label>Diagnosis</label>
              <input type="text" value={form.diagnosis} onChange={e => setForm({...form, diagnosis: e.target.value})} required />
            </div>
            <div className="field">
              <label>Notes</label>
              <textarea rows={3} value={form.notes} onChange={e => setForm({...form, notes: e.target.value})} />
            </div>
            <div className="field">
              <label>Treatment</label>
              <textarea rows={2} value={form.treatment} onChange={e => setForm({...form, treatment: e.target.value})} />
            </div>
            <div className="modal-actions">
              <button type="button" className="btn btn-ghost" onClick={onClose} disabled={busy}>Cancel</button>
              <button type="submit" className="btn btn-primary" disabled={busy}>
                {busy ? "Saving..." : "Save record"}
              </button>
            </div>
          </form>
        ) : (
          <>
            <div className="alert-success">Record saved. Add prescriptions below or close.</div>
            <h4 style={{marginTop: 16}}>Add Prescription</h4>
            <form onSubmit={addPrescription} className="record-form">
              <div className="field">
                <label>Drug</label>
                <input list="rx-drugs" type="text" value={rxForm.drug_name}
                       onChange={e => setRxForm({...rxForm, drug_name: e.target.value})}
                       required />
                <datalist id="rx-drugs">
                  {drugs.map(d => <option key={d.id} value={d.name} />)}
                </datalist>
              </div>
              <div className="rx-row">
                <div className="field"><label>Dosage</label>
                  <input type="text" value={rxForm.dosage} onChange={e => setRxForm({...rxForm, dosage: e.target.value})} /></div>
                <div className="field"><label>Frequency</label>
                  <input type="text" value={rxForm.frequency} onChange={e => setRxForm({...rxForm, frequency: e.target.value})} /></div>
                <div className="field"><label>Duration</label>
                  <input type="text" value={rxForm.duration} onChange={e => setRxForm({...rxForm, duration: e.target.value})} /></div>
              </div>
              <div className="field">
                <label>Instructions</label>
                <input type="text" value={rxForm.instructions} onChange={e => setRxForm({...rxForm, instructions: e.target.value})} />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-ghost" onClick={onClose} disabled={busy}>Close</button>
                <button type="submit" className="btn btn-primary" disabled={busy}>
                  {busy ? "Adding..." : "Add prescription"}
                </button>
              </div>
            </form>
            {prescriptions.length > 0 && (
              <div style={{marginTop: 12}}>
                <h4>Added this visit</h4>
                <ul className="rx-list">
                  {prescriptions.map(p => (
                    <li key={p.id}><strong>{p.drug_name}</strong> {p.dosage} · {p.frequency} · {p.duration}</li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function DoctorSchedule({ token }) {
  const [schedule, setSchedule] = useState([]);
  const [drugs, setDrugs] = useState([]);
  const [target, setTarget] = useState(null);

  function reload() {
    apiFetch("/api/me/schedule/", {}, token).then(setSchedule).catch(() => {});
  }
  useEffect(() => {
    reload();
    apiFetch("/api/drugs/", {}, token).then(setDrugs).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  return (
    <div className="page">
      <div className="page-header">
        <h1>My Schedule</h1>
        <p>Every appointment booked with you. Click one to record the visit.</p>
      </div>
      {schedule.length === 0 ? (
        <div className="empty-state"><p>No appointments yet.</p></div>
      ) : (
        <div className="appt-list">
          {schedule.map(a => (
            <div key={a.id} className="appt-card appt-card-clickable" onClick={() => !a.has_record && a.status !== "CANCELLED" && setTarget(a)}>
              <div className="appt-avatar">
                {a.patient_name?.split(" ").map(n => n[0]).join("") || "P"}
              </div>
              <div className="appt-info">
                <div className="appt-doctor">{a.patient_name}</div>
                <div className="appt-reason">{a.reason}</div>
              </div>
              <div className="appt-meta">
                <div className="appt-date">{a.date}</div>
                <div className="appt-time">{a.time}</div>
                <span className={`badge ${
                  a.status === "COMPLETED" ? "badge-green"
                  : a.status === "CANCELLED" ? "badge-red"
                  : "badge-blue"
                }`}>
                  {a.has_record ? "Record saved" : a.status[0] + a.status.slice(1).toLowerCase()}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
      <MedicalRecordModal
        appointment={target}
        token={token}
        drugs={drugs}
        onClose={() => { setTarget(null); reload(); }}
        onSaved={reload}
      />
    </div>
  );
}

function DoctorStock({ token }) {
  const [stock, setStock] = useState([]);
  useEffect(() => {
    apiFetch("/api/me/department/stock/", {}, token).then(setStock).catch(() => setStock([]));
  }, [token]);
  return (
    <div className="page">
      <div className="page-header">
        <h1>Department Drug Stock</h1>
        <p>Read-only view of your department's medication levels. Adjustments belong to the pharmacist.</p>
      </div>
      <div className="section">
        <table className="data-table">
          <thead>
            <tr><th>Drug</th><th>Qty</th><th>Unit</th><th>Reorder level</th><th>Status</th></tr>
          </thead>
          <tbody>
            {stock.map(s => (
              <tr key={s.id}>
                <td>{s.drug_name}</td>
                <td>{s.quantity}</td>
                <td>{s.drug_unit}</td>
                <td>{s.reorder_level}</td>
                <td>
                  <span className={`badge ${s.is_low ? "badge-red" : "badge-green"}`}>
                    {s.is_low ? "Low" : "OK"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function MyAvailabilityPage({ user, token }) {
  return (
    <div className="page">
      <div className="page-header">
        <h1>My Availability</h1>
        <p>Set the weekday windows when patients can book you. Patients only see the open slots inside an active window.</p>
      </div>
      <div className="section">
        <MyAvailability user={user} token={token} />
      </div>
    </div>
  );
}

function DoctorShell({ user, token, onLogout }) {
  const [page, setPage] = useState("dashboard");
  const [schedule, setSchedule] = useState([]);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    if (!token) return;
    apiFetch("/api/me/schedule/", {}, token).then(setSchedule).catch(() => {});
  }, [token, page]);

  const items = [
    { id: "dashboard",    label: "Dashboard",      icon: "⊡" },
    { id: "schedule",     label: "My Schedule",    icon: "◫" },
    { id: "availability", label: "My Availability",icon: "⌚" },
    { id: "stock",        label: "Department Stock", icon: "▤" },
  ];

  return (
    <div className="app-shell">
      <header className="mobile-bar">
        <button className="hamburger" onClick={() => setSidebarOpen(true)}>☰</button>
        <span className="logo-text">MediCore</span>
        <div className="avatar avatar-sm">{user.name?.split(" ").map(n => n[0]).join("") || "D"}</div>
      </header>
      <RoleSidebar items={items} activePage={page} setPage={setPage}
                   user={user} onLogout={onLogout} roleLabel="Doctor"
                   sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <main className="main-content">
        {page === "dashboard"    && <DoctorDashboardPage user={user} schedule={schedule} />}
        {page === "schedule"     && <DoctorSchedule token={token} />}
        {page === "availability" && <MyAvailabilityPage user={user} token={token} />}
        {page === "stock"        && <DoctorStock token={token} />}
      </main>
    </div>
  );
}

// =========================================================================
// NURSE pages — read-only views scoped to the nurse's department
// =========================================================================

function NurseDashboardPage({ user, token }) {
  const [counts, setCounts] = useState({ rx: 0, stock: 0, equip: 0 });
  useEffect(() => {
    if (!token) return;
    Promise.all([
      apiFetch("/api/me/department/prescriptions/", {}, token).catch(() => []),
      apiFetch("/api/me/department/stock/", {}, token).catch(() => []),
      apiFetch("/api/me/department/equipment/", {}, token).catch(() => []),
    ]).then(([rx, st, eq]) => setCounts({
      rx: rx.length,
      stock: st.filter(s => s.is_low).length,
      equip: eq.filter(e => e.status === "MAINTENANCE").length,
    }));
  }, [token]);
  return (
    <div className="page">
      <div className="page-header">
        <h1>Welcome, {user.name.split(" ")[0]}.</h1>
        <p>Department-scoped read-only overview.</p>
      </div>
      <div className="stats-row">
        <div className="stat-card stat-blue"><div className="stat-number">{counts.rx}</div><div className="stat-label">Department Prescriptions</div></div>
        <div className="stat-card stat-teal"><div className="stat-number">{counts.stock}</div><div className="stat-label">Drugs Low on Stock</div></div>
        <div className="stat-card stat-green"><div className="stat-number">{counts.equip}</div><div className="stat-label">Equipment in Maintenance</div></div>
      </div>
    </div>
  );
}

function NursePrescriptions({ token }) {
  const [rxs, setRxs] = useState([]);
  useEffect(() => {
    apiFetch("/api/me/department/prescriptions/", {}, token).then(setRxs).catch(() => setRxs([]));
  }, [token]);
  return (
    <div className="page">
      <div className="page-header">
        <h1>Department Prescriptions</h1>
        <p>Every prescription written for patients seen by a doctor in your department.</p>
      </div>
      <div className="section">
        {rxs.length === 0 ? (
          <div className="empty-state"><p>No prescriptions to dispense yet.</p></div>
        ) : (
          <table className="data-table">
            <thead>
              <tr><th>Drug</th><th>Dosage</th><th>Frequency</th><th>Duration</th><th>Patient</th><th>Doctor</th><th>Diagnosis</th></tr>
            </thead>
            <tbody>
              {rxs.map(r => (
                <tr key={r.id}>
                  <td>{r.drug_name}</td>
                  <td>{r.dosage}</td>
                  <td>{r.frequency}</td>
                  <td>{r.duration}</td>
                  <td>{r.patient_name}</td>
                  <td>{r.doctor_name}</td>
                  <td>{r.diagnosis}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function NurseEquipment({ token }) {
  const [eq, setEq] = useState([]);
  useEffect(() => {
    apiFetch("/api/me/department/equipment/", {}, token).then(setEq).catch(() => setEq([]));
  }, [token]);
  return (
    <div className="page">
      <div className="page-header">
        <h1>Department Equipment</h1>
        <p>Operational status of every device assigned to your department.</p>
      </div>
      <div className="section">
        <table className="data-table">
          <thead>
            <tr><th>Name</th><th>Serial</th><th>Model</th><th>Status</th><th>Last serviced</th></tr>
          </thead>
          <tbody>
            {eq.map(e => (
              <tr key={e.id}>
                <td>{e.name}</td>
                <td>{e.serial_number}</td>
                <td>{e.model_number}</td>
                <td>
                  <span className={`badge ${
                    e.status === "AVAILABLE" ? "badge-green"
                    : e.status === "MAINTENANCE" ? "badge-red"
                    : "badge-blue"
                  }`}>
                    {e.status_display}
                  </span>
                </td>
                <td>{e.last_serviced || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// =========================================================================
// ADMIN pages
// =========================================================================

function AdminDashboardPage({ user, setPage }) {
  return (
    <div className="page">
      <div className="page-header">
        <h1>Welcome back, {user.name.split(" ")[0]}.</h1>
        <p>System overview and administrative controls.</p>
      </div>
      <div className="stats-row">
        <div className="stat-card stat-blue"><div className="stat-number">35</div><div className="stat-label">Total Users</div></div>
        <div className="stat-card stat-teal"><div className="stat-number">5</div><div className="stat-label">Departments</div></div>
        <div className="stat-card stat-green"><div className="stat-number">OK</div><div className="stat-label">System Status</div></div>
      </div>
      <div className="section">
        <div className="section-header"><h2>Administrative Tools</h2></div>
        <div className="doctors-grid">
          <div className="doctor-card">
            <div className="doctor-info">
              <div className="doctor-name">User &amp; Role Management</div>
              <div className="doctor-specialty">Create accounts, assign departments. Django admin owns this surface.</div>
              <a className="btn btn-ghost" href={`${API}/admin/`} target="_blank" rel="noreferrer">Open Django admin →</a>
            </div>
          </div>
          <div className="doctor-card">
            <div className="doctor-info">
              <div className="doctor-name">Departments</div>
              <div className="doctor-specialty">Manage clinical departments. New departments unlock doctor/nurse/equipment scopes.</div>
              <a className="btn btn-ghost" href={`${API}/admin/accounts/department/`} target="_blank" rel="noreferrer">Manage departments →</a>
            </div>
          </div>
          <div className="doctor-card">
            <div className="doctor-info">
              <div className="doctor-name">Audit &amp; Reports</div>
              <div className="doctor-specialty">Read-only operational KPIs — low stock, equipment, appointments by department.</div>
              <button className="btn btn-primary" onClick={() => setPage("kpis")}>View KPIs</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// =========================================================================
// MANAGEMENT KPIs — shared between AdminShell and ManagementShell
// =========================================================================

function ManagementKPIs({ token }) {
  const [data, setData] = useState({ low_stock: [], equipment_by_status: [], appointments_by_department: [] });
  useEffect(() => {
    if (!token) return;
    apiFetch("/api/management/kpis/", {}, token).then(setData).catch(() => {});
  }, [token]);
  return (
    <div className="page">
      <div className="page-header">
        <h1>Operational KPIs</h1>
        <p>Hospital-wide read-only metrics. No PHI — operations only.</p>
      </div>
      <div className="section">
        <div className="section-header"><h2>Low Stock</h2></div>
        {data.low_stock.length === 0 ? (
          <div className="empty-state"><p>No low-stock alerts. All medications are at or above reorder level.</p></div>
        ) : (
          <table className="data-table">
            <thead><tr><th>Drug</th><th>Department</th><th>Qty</th><th>Reorder</th></tr></thead>
            <tbody>
              {data.low_stock.map(s => (
                <tr key={s.id}>
                  <td>{s.drug_name}</td>
                  <td>{s.department_name}</td>
                  <td><strong>{s.quantity}</strong> {s.drug_unit}</td>
                  <td>{s.reorder_level}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <div className="section">
        <div className="section-header"><h2>Equipment by Status</h2></div>
        <div className="kpi-bars">
          {data.equipment_by_status.map(e => (
            <div key={e.status} className="kpi-bar-row">
              <div className="kpi-bar-label">{e.status}</div>
              <div className="kpi-bar-track">
                <div className="kpi-bar-fill" style={{width: `${Math.min(100, e.n * 12)}%`}} />
              </div>
              <div className="kpi-bar-value">{e.n}</div>
            </div>
          ))}
        </div>
      </div>
      <div className="section">
        <div className="section-header"><h2>Appointments by Department</h2></div>
        <div className="kpi-bars">
          {data.appointments_by_department.map(a => (
            <div key={a.department} className="kpi-bar-row">
              <div className="kpi-bar-label">{a.department}</div>
              <div className="kpi-bar-track">
                <div className="kpi-bar-fill" style={{width: `${Math.min(100, a.count * 12)}%`}} />
              </div>
              <div className="kpi-bar-value">{a.count}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// =========================================================================
// PHARMACIST pages
// =========================================================================

function PharmacistDashboardPage({ user, token }) {
  const [stats, setStats] = useState({ drugs: 0, stockRows: 0, low: 0 });
  useEffect(() => {
    if (!token) return;
    Promise.all([
      apiFetch("/api/drugs/", {}, token).catch(() => []),
      apiFetch("/api/stock/", {}, token).catch(() => []),
    ]).then(([drugs, stock]) => setStats({
      drugs: drugs.length,
      stockRows: stock.length,
      low: stock.filter(s => s.is_low).length,
    }));
  }, [token]);
  return (
    <div className="page">
      <div className="page-header">
        <h1>Welcome, {user.name.split(" ")[0]}.</h1>
        <p>Drug catalog and hospital-wide stock at a glance.</p>
      </div>
      <div className="stats-row">
        <div className="stat-card stat-blue"><div className="stat-number">{stats.drugs}</div><div className="stat-label">Drugs in Catalog</div></div>
        <div className="stat-card stat-teal"><div className="stat-number">{stats.stockRows}</div><div className="stat-label">Stock Rows</div></div>
        <div className="stat-card stat-green"><div className="stat-number">{stats.low}</div><div className="stat-label">Low Stock Alerts</div></div>
      </div>
    </div>
  );
}

function PharmacistCatalog({ token }) {
  const [drugs, setDrugs] = useState([]);
  const [form, setForm] = useState({ name: "", generic_name: "", category: "OTHER", manufacturer: "", unit: "tablet" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  function reload() {
    apiFetch("/api/drugs/", {}, token).then(setDrugs).catch(() => {});
  }
  useEffect(() => { reload(); /* eslint-disable-next-line */ }, [token]);

  async function handleCreate(e) {
    e.preventDefault();
    if (!form.name.trim()) { setError("Name is required."); return; }
    setBusy(true); setError(""); setMessage("");
    try {
      await apiFetch("/api/drugs/", { method: "POST", body: JSON.stringify(form) }, token);
      setMessage(`Added "${form.name}" to the catalog.`);
      setForm({ name: "", generic_name: "", category: "OTHER", manufacturer: "", unit: "tablet" });
      reload();
    } catch (err) {
      setError(err.message || "Could not add drug.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>Drug Catalog</h1>
        <p>Master list of medications. Add new drugs below; stock per department lives on its own page.</p>
      </div>
      {message && <div className="alert-success" role="status">{message}</div>}
      {error && <div className="alert alert-error" role="alert">{error}</div>}
      <div className="section">
        <div className="section-header"><h2>Add Drug</h2></div>
        <form onSubmit={handleCreate} className="record-form">
          <div className="rx-row">
            <div className="field"><label>Name</label>
              <input type="text" value={form.name} onChange={e => setForm({...form, name: e.target.value})} required /></div>
            <div className="field"><label>Generic name</label>
              <input type="text" value={form.generic_name} onChange={e => setForm({...form, generic_name: e.target.value})} /></div>
          </div>
          <div className="rx-row">
            <div className="field"><label>Category</label>
              <select value={form.category} onChange={e => setForm({...form, category: e.target.value})}>
                <option value="ANALGESIC">Analgesic / Pain</option>
                <option value="ANTIBIOTIC">Antibiotic</option>
                <option value="ANTIVIRAL">Antiviral</option>
                <option value="CARDIO">Cardiovascular</option>
                <option value="ENDOCRINE">Endocrine / Diabetes</option>
                <option value="GI">Gastrointestinal</option>
                <option value="RESP">Respiratory</option>
                <option value="PSYCH">Psychiatric</option>
                <option value="OTHER">Other</option>
              </select>
            </div>
            <div className="field"><label>Manufacturer</label>
              <input type="text" value={form.manufacturer} onChange={e => setForm({...form, manufacturer: e.target.value})} /></div>
            <div className="field"><label>Unit</label>
              <input type="text" value={form.unit} onChange={e => setForm({...form, unit: e.target.value})} /></div>
          </div>
          <button type="submit" className="btn btn-primary" disabled={busy}>
            {busy ? "Adding..." : "Add to catalog"}
          </button>
        </form>
      </div>
      <div className="section">
        <div className="section-header"><h2>All Drugs ({drugs.length})</h2></div>
        <table className="data-table">
          <thead><tr><th>Name</th><th>Generic</th><th>Category</th><th>Manufacturer</th><th>Unit</th></tr></thead>
          <tbody>
            {drugs.map(d => (
              <tr key={d.id}>
                <td>{d.name}</td>
                <td>{d.generic_name || "—"}</td>
                <td>{d.category_display}</td>
                <td>{d.manufacturer || "—"}</td>
                <td>{d.unit}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function PharmacistStock({ token }) {
  const [stock, setStock] = useState([]);
  const [busyId, setBusyId] = useState(null);

  function reload() {
    apiFetch("/api/stock/", {}, token).then(setStock).catch(() => setStock([]));
  }
  useEffect(() => { reload(); /* eslint-disable-next-line */ }, [token]);

  async function adjust(id, delta) {
    setBusyId(id);
    try {
      const row = stock.find(s => s.id === id);
      const next = Math.max(0, row.quantity + delta);
      await apiFetch(`/api/stock/${id}/`, { method: "PATCH", body: JSON.stringify({ quantity: next }) }, token);
      setStock(prev => prev.map(s => s.id === id ? { ...s, quantity: next, is_low: next <= s.reorder_level } : s));
    } catch {
      // leave row unchanged on error
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>Drug Stock — Hospital Wide</h1>
        <p>One row per (drug, department). Use the + / − buttons to adjust quantity.</p>
      </div>
      <div className="section">
        <table className="data-table">
          <thead><tr><th>Drug</th><th>Department</th><th>Qty</th><th>Reorder</th><th>Status</th><th>Adjust</th></tr></thead>
          <tbody>
            {stock.map(s => (
              <tr key={s.id}>
                <td>{s.drug_name}</td>
                <td>{s.department_name}</td>
                <td><strong>{s.quantity}</strong> {s.drug_unit}</td>
                <td>{s.reorder_level}</td>
                <td>
                  <span className={`badge ${s.is_low ? "badge-red" : "badge-green"}`}>
                    {s.is_low ? "Low" : "OK"}
                  </span>
                </td>
                <td>
                  <button className="btn btn-ghost" disabled={busyId === s.id || s.quantity === 0}
                          onClick={() => adjust(s.id, -1)}>−</button>{" "}
                  <button className="btn btn-ghost" disabled={busyId === s.id}
                          onClick={() => adjust(s.id, +1)}>+</button>{" "}
                  <button className="btn btn-ghost" disabled={busyId === s.id}
                          onClick={() => adjust(s.id, +10)}>+10</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// =========================================================================
// Role shells — Nurse / Admin / Management / Pharmacist
// =========================================================================

function NurseShell({ user, token, onLogout }) {
  const [page, setPage] = useState("dashboard");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const items = [
    { id: "dashboard",     label: "Dashboard",                icon: "⊡" },
    { id: "prescriptions", label: "Department Prescriptions", icon: "Rx" },
    { id: "stock",         label: "Department Stock",         icon: "▤" },
    { id: "equipment",     label: "Equipment",                icon: "⚙" },
  ];
  return (
    <div className="app-shell">
      <header className="mobile-bar">
        <button className="hamburger" onClick={() => setSidebarOpen(true)}>☰</button>
        <span className="logo-text">MediCore</span>
        <div className="avatar avatar-sm">{user.name?.split(" ").map(n => n[0]).join("") || "N"}</div>
      </header>
      <RoleSidebar items={items} activePage={page} setPage={setPage}
                   user={user} onLogout={onLogout} roleLabel="Nurse"
                   sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <main className="main-content">
        {page === "dashboard"     && <NurseDashboardPage user={user} token={token} />}
        {page === "prescriptions" && <NursePrescriptions token={token} />}
        {page === "stock"         && <DoctorStock token={token} />}
        {page === "equipment"     && <NurseEquipment token={token} />}
      </main>
    </div>
  );
}

function AdminShell({ user, onLogout }) {
  const [page, setPage] = useState("dashboard");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const items = [
    { id: "dashboard", label: "Dashboard", icon: "⊡" },
    { id: "kpis",      label: "KPIs",      icon: "▤" },
  ];
  return (
    <div className="app-shell">
      <header className="mobile-bar">
        <button className="hamburger" onClick={() => setSidebarOpen(true)}>☰</button>
        <span className="logo-text">MediCore</span>
        <div className="avatar avatar-sm">{user.name?.split(" ").map(n => n[0]).join("") || "A"}</div>
      </header>
      <RoleSidebar items={items} activePage={page} setPage={setPage}
                   user={user} onLogout={onLogout} roleLabel="Admin"
                   sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <main className="main-content">
        {page === "dashboard" && <AdminDashboardPage user={user} setPage={setPage} />}
        {page === "kpis"      && <ManagementKPIs token={null} adminToken={onLogout && undefined} />}
      </main>
    </div>
  );
}

function ManagementShell({ user, token, onLogout }) {
  const [page, setPage] = useState("dashboard");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const items = [{ id: "dashboard", label: "KPI Dashboard", icon: "⊡" }];
  return (
    <div className="app-shell">
      <header className="mobile-bar">
        <button className="hamburger" onClick={() => setSidebarOpen(true)}>☰</button>
        <span className="logo-text">MediCore</span>
        <div className="avatar avatar-sm">{user.name?.split(" ").map(n => n[0]).join("") || "M"}</div>
      </header>
      <RoleSidebar items={items} activePage={page} setPage={setPage}
                   user={user} onLogout={onLogout} roleLabel="Management"
                   sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <main className="main-content">
        <ManagementKPIs token={token} />
      </main>
    </div>
  );
}

function PharmacistShell({ user, token, onLogout }) {
  const [page, setPage] = useState("dashboard");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const items = [
    { id: "dashboard", label: "Dashboard",    icon: "⊡" },
    { id: "catalog",   label: "Drug Catalog", icon: "Rx" },
    { id: "stock",     label: "Stock",        icon: "▤" },
  ];
  return (
    <div className="app-shell">
      <header className="mobile-bar">
        <button className="hamburger" onClick={() => setSidebarOpen(true)}>☰</button>
        <span className="logo-text">MediCore</span>
        <div className="avatar avatar-sm">{user.name?.split(" ").map(n => n[0]).join("") || "P"}</div>
      </header>
      <RoleSidebar items={items} activePage={page} setPage={setPage}
                   user={user} onLogout={onLogout} roleLabel="Pharmacist"
                   sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />
      <main className="main-content">
        {page === "dashboard" && <PharmacistDashboardPage user={user} token={token} />}
        {page === "catalog"   && <PharmacistCatalog token={token} />}
        {page === "stock"     && <PharmacistStock token={token} />}
      </main>
    </div>
  );
}

// =========================================================================
// App root — routes by role after login
// =========================================================================
export default function App() {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [page, setPage] = useState("dashboard");
  const [appointments, setAppointments] = useState([]);
  const [doctors, setDoctors] = useState([]);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Patient-specific data fetch
  useEffect(() => {
    if (!token || !user || user.role !== "PATIENT") return;
    apiFetch("/api/doctors/", {}, token).then(setDoctors).catch(() => {});
    apiFetch("/api/appointments/", {}, token).then(setAppointments).catch(() => {});
  }, [token, user]);

  function handleLogin(u, tok) { setUser(u); setToken(tok); }

  function handleLogout() {
    if (token) apiFetch("/api/logout/", { method: "POST" }, token).catch(() => {});
    setUser(null); setToken(null); setPage("dashboard");
    setAppointments([]); setDoctors([]);
  }

  function handleBook(newAppt) { setAppointments(prev => [newAppt, ...prev]); }

  function handleCancelled(updated) {
    setAppointments(prev => prev.map(a => a.id === updated.id ? updated : a));
  }

  // Not logged in -> show the single-form login
  if (!user) return <LoginPage onLogin={handleLogin} />;

  // Route by role — every shell uses the same blue palette + RoleSidebar
  const role = user.role;
  if (role === "ADMIN")      return <AdminShell user={user} onLogout={handleLogout} />;
  if (role === "DOCTOR")     return <DoctorShell user={user} token={token} onLogout={handleLogout} />;
  if (role === "NURSE")      return <NurseShell user={user} token={token} onLogout={handleLogout} />;
  if (role === "PHARMACIST") return <PharmacistShell user={user} token={token} onLogout={handleLogout} />;
  if (role === "MANAGEMENT") return <ManagementShell user={user} token={token} onLogout={handleLogout} />;

  // PATIENT — the full SPA
  return (
    <div className="app-shell">
      <header className="mobile-bar">
        <button className="hamburger" onClick={() => setSidebarOpen(true)}>☰</button>
        <span className="logo-text">MediCore</span>
        <div className="avatar avatar-sm">
          {user.name?.split(" ").map(n => n[0]).join("") || "P"}
        </div>
      </header>
      <PatientSidebar
        activePage={page}
        setPage={setPage}
        user={user}
        onLogout={handleLogout}
        sidebarOpen={sidebarOpen}
        setSidebarOpen={setSidebarOpen}
      />
      <main className="main-content">
        {page === "dashboard"   && <PatientDashboard appointments={appointments} doctors={doctors} setPage={setPage} />}
        {page === "book"        && <BookAppointment doctors={doctors} token={token} onBook={(appt) => { handleBook(appt); setPage("appointments"); }} />}
        {page === "appointments"&& <ViewAppointments appointments={appointments} setPage={setPage} token={token} onCancelled={handleCancelled} />}
      </main>
    </div>
  );
}
