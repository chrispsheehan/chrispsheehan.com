import React, { useEffect, useState } from "react";

export default function RuntimeSummary() {
  const [visits, setVisits] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;

    fetch("/data/log-processor/data.json")
      .then((res) => {
        if (!res.ok) throw new Error("Visit data request failed");
        return res.json();
      })
      .then((visitData) => {
        if (!active) return;
        setVisits(visitData);
      })
      .catch(() => {
        if (!active) return;
        setError(true);
      });

    return () => {
      active = false;
    };
  }, []);

  if (error) {
    return (
      <div className="runtime-summary" aria-live="polite">
        <p className="dashboard-card__eyebrow">Runtime</p>
        <p className="runtime-summary__status">Runtime data unavailable.</p>
      </div>
    );
  }

  if (!visits) {
    return (
      <div className="runtime-summary" aria-live="polite">
        <p className="dashboard-card__eyebrow">Runtime</p>
        <p className="runtime-summary__status">Loading runtime data...</p>
      </div>
    );
  }

  return (
    <div className="runtime-summary">
      <p className="dashboard-card__eyebrow">Runtime</p>
      <div className="runtime-summary__grid">
        <a
          href="/data/log-processor/data.json"
          target="_blank"
          rel="noopener noreferrer"
          className="runtime-summary__item"
        >
          <span className="runtime-summary__label">Traffic</span>
          <strong className="runtime-summary__value">
            {visits["daily-visits"]}
          </strong>
          <span className="runtime-summary__meta">
            {visits["range"]}-day total {visits["total-visits"]}
          </span>
        </a>
      </div>
    </div>
  );
}
