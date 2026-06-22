import React, { useEffect, useState } from "react";

function formatUsd(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value ?? 0);
}

export default function Costs() {
  const [costs, setCosts] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch("data/cost-explorer/data.json")
      .then((res) => {
        if (!res.ok) throw new Error("Network response was not ok");
        return res.json();
      })
      .then((data) => {
        setCosts(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  if (loading)
    return (
      <div className="dashboard-card">
        <p>Loading cost data...</p>
      </div>
    );
  if (error)
    return (
      <div className="dashboard-card">
        <p>Error loading data: {error}</p>
      </div>
    );
  if (!costs)
    return (
      <div className="dashboard-card">
        <p>No cost data available.</p>
      </div>
    );

  return (
    <a
      href="/data/cost-explorer/data.json"
      target="_blank"
      rel="noopener noreferrer"
      className="dashboard-card dashboard-card--data"
    >
      <p className="dashboard-card__eyebrow">Cost</p>
      <ul>
        <li>
          <strong>{costs["billing-month"]}</strong>
          <span className="metric-value">
            {formatUsd(costs["last-month-total"])}
          </span>
        </li>
      </ul>
    </a>
  );
}
