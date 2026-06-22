import React, { useEffect, useState } from "react";

function formatUsd(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value ?? 0);
}

export default function RuntimeSummary() {
  const [visits, setVisits] = useState(null);
  const [costs, setCosts] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;

    Promise.all([
      fetch("/data/log-processor/data.json").then((res) => {
        if (!res.ok) throw new Error("Visit data request failed");
        return res.json();
      }),
      fetch("/data/cost-explorer/data.json").then((res) => {
        if (!res.ok) throw new Error("Cost data request failed");
        return res.json();
      }),
    ])
      .then(([visitData, costData]) => {
        if (!active) return;
        setVisits(visitData);
        setCosts(costData);
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

  if (!visits || !costs) {
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
        <a
          href="/data/cost-explorer/data.json"
          target="_blank"
          rel="noopener noreferrer"
          className="runtime-summary__item"
        >
          <span className="runtime-summary__label">Cost</span>
          <strong className="runtime-summary__value">
            {formatUsd(costs["last-month-total"])}
          </strong>
          <span className="runtime-summary__meta">{costs["billing-month"]}</span>
        </a>
      </div>
    </div>
  );
}
