import React, { useEffect, useMemo, useState } from "react";

const RANGE_OPTIONS = [7, 14, 30];

function parseDate(value) {
  return new Date(`${value}T12:00:00Z`);
}

function formatDate(value, options = {}) {
  if (!value) return "the latest recorded day";
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    ...options,
    timeZone: "UTC",
  }).format(parseDate(value));
}

function normaliseSeries(data) {
  const series = data?.["daily-visitor-counts"];
  if (Array.isArray(series) && series.length) {
    return series
      .filter((item) => item?.date && Number.isFinite(Number(item.visitors)))
      .map((item) => ({ date: item.date, visitors: Number(item.visitors) }))
      .sort((left, right) => left.date.localeCompare(right.date));
  }

  if (data?.["last-date"]) {
    return [
      {
        date: data["last-date"],
        visitors: Number(data["daily-visits"] ?? 0),
      },
    ];
  }

  return [];
}

function comparisonFor(series) {
  if (series.length < 14) return null;

  const recent = series.slice(-7);
  const previous = series.slice(-14, -7);
  const recentAverage =
    recent.reduce((total, item) => total + item.visitors, 0) / 7;
  const previousAverage =
    previous.reduce((total, item) => total + item.visitors, 0) / 7;

  if (previousAverage === 0) return null;
  return Math.round(
    ((recentAverage - previousAverage) / previousAverage) * 100,
  );
}

export default function TrafficPulse() {
  const [traffic, setTraffic] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [range, setRange] = useState(30);
  const [selectedDate, setSelectedDate] = useState(null);

  useEffect(() => {
    let active = true;

    fetch("/data/log-processor/data.json")
      .then((response) => {
        if (!response.ok) throw new Error("Traffic data request failed");
        return response.json();
      })
      .then((data) => {
        if (!active) return;
        setTraffic(data);
        setSelectedDate(data["last-date"] ?? null);
        setLoading(false);
      })
      .catch(() => {
        if (!active) return;
        setError(true);
        setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  const allSeries = useMemo(() => normaliseSeries(traffic), [traffic]);
  const visibleSeries = useMemo(
    () => allSeries.slice(-range),
    [allSeries, range],
  );
  const selected =
    visibleSeries.find((item) => item.date === selectedDate) ??
    visibleSeries[visibleSeries.length - 1];
  const maximum = Math.max(...visibleSeries.map((item) => item.visitors), 1);
  const periodTotal = visibleSeries.reduce(
    (total, item) => total + item.visitors,
    0,
  );
  const comparison = comparisonFor(allSeries);

  if (loading) {
    return (
      <div className="traffic-pulse traffic-pulse--status" aria-live="polite">
        <p className="dashboard-card__eyebrow">Traffic pulse</p>
        <p>Loading recent traffic…</p>
      </div>
    );
  }

  if (error || !visibleSeries.length) {
    return (
      <div className="traffic-pulse traffic-pulse--status" aria-live="polite">
        <p className="dashboard-card__eyebrow">Traffic pulse</p>
        <p>Recent traffic is temporarily unavailable.</p>
      </div>
    );
  }

  const latest = allSeries[allSeries.length - 1];
  const hasHistory = allSeries.length > 1;

  return (
    <section className="traffic-pulse" aria-labelledby="traffic-pulse-title">
      <div className="traffic-pulse__header">
        <div>
          <p className="dashboard-card__eyebrow">Live system signal</p>
          <h3 id="traffic-pulse-title">Traffic pulse</h3>
        </div>
        {hasHistory && (
          <div className="traffic-pulse__ranges" aria-label="Chart range">
            {RANGE_OPTIONS.map((option) => (
              <button
                type="button"
                key={option}
                className={range === option ? "is-active" : ""}
                aria-pressed={range === option}
                onClick={() => {
                  setRange(option);
                  setSelectedDate(latest.date);
                }}
              >
                {option}d
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="traffic-pulse__body">
        <div className="traffic-pulse__headline">
          <span className="traffic-pulse__number">{selected.visitors}</span>
          <span className="traffic-pulse__headline-copy">
            estimated visitor{selected.visitors === 1 ? "" : "s"}
            <strong>{formatDate(selected.date, { year: "numeric" })}</strong>
          </span>
        </div>

        {hasHistory && (
          <div className="traffic-pulse__chart-wrap">
            <div
              className="traffic-pulse__chart"
              role="group"
              aria-label="Estimated daily visitors"
            >
              {visibleSeries.map((item) => {
                const height = Math.max(
                  (item.visitors / maximum) * 100,
                  item.visitors ? 6 : 2,
                );
                const isSelected = item.date === selected.date;
                return (
                  <button
                    type="button"
                    key={item.date}
                    className={isSelected ? "is-selected" : ""}
                    style={{ "--bar-height": `${height}%` }}
                    aria-label={`${formatDate(item.date, { year: "numeric" })}: ${item.visitors} estimated visitors`}
                    aria-pressed={isSelected}
                    onMouseEnter={() => setSelectedDate(item.date)}
                    onFocus={() => setSelectedDate(item.date)}
                    onClick={() => setSelectedDate(item.date)}
                  >
                    <span className="traffic-pulse__bar" aria-hidden="true" />
                  </button>
                );
              })}
            </div>
            <div className="traffic-pulse__axis" aria-hidden="true">
              <span>{formatDate(visibleSeries[0].date)}</span>
              <span>
                {formatDate(visibleSeries[visibleSeries.length - 1].date)}
              </span>
            </div>
          </div>
        )}

        <div className="traffic-pulse__metrics">
          <div>
            <span>Period total</span>
            <strong>{periodTotal.toLocaleString("en-GB")}</strong>
          </div>
          <div>
            <span>Latest complete day</span>
            <strong>{formatDate(latest.date)}</strong>
          </div>
          <div>
            <span>7-day trend</span>
            <strong>
              {comparison === null
                ? "Building history"
                : comparison === 0
                  ? "Level"
                  : `${comparison > 0 ? "+" : ""}${comparison}%`}
            </strong>
          </div>
        </div>
      </div>
    </section>
  );
}
