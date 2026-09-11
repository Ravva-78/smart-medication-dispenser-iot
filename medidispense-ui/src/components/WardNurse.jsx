export default function WardNurse() {
  return (
    <div className="ward-nurse-card">

      <div className="card-header">
        <span className="card-header-title">Ward Nurse</span>
      </div>

      <div className="nurse-row">
        <span className="nurse-label">Nurse</span>
        <span className="nurse-value">Maria Gomez</span>
      </div>

      <div className="nurse-row">
        <span className="nurse-label">Ward</span>
        <span className="nurse-value">3B</span>
      </div>

      <div className="nurse-row">
        <span className="nurse-label">Patients</span>
        <span className="nurse-value">12</span>
      </div>

      <div className="nurse-row">
        <span className="nurse-label">Shift</span>
        <span className="nurse-value">08:00 – 16:00</span>
      </div>

      <div className="nurse-row">
        <span className="nurse-label">Beds</span>
        <span className="nurse-value">18 / 24</span>
      </div>

    </div>
  );
}