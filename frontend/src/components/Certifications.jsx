import React, { useEffect, useRef, useState } from "react";

export default function Certifications() {
  const [certs, setCerts] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeIndex, setActiveIndex] = useState(0);
  const carouselRef = useRef(null);

  useEffect(() => {
    fetch("/static/certifications.json", { cache: "no-store" })
      .then((res) => {
        if (!res.ok) throw new Error("Failed to fetch certifications.");
        return res.json();
      })
      .then((data) => {
        setCerts(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    if (!certs?.some((cert) => cert.shareBadgeId)) return;

    const existingScript = document.querySelector(
      "script[data-credly-embed-script='true']",
    );
    if (existingScript) return;

    const script = document.createElement("script");
    script.src = "https://cdn.credly.com/assets/utilities/embed.js";
    script.async = true;
    script.type = "text/javascript";
    script.dataset.credlyEmbedScript = "true";
    document.body.appendChild(script);
  }, [certs]);

  useEffect(() => {
    const carousel = carouselRef.current;
    if (!carousel) return;

    let dragPointerId = null;
    let dragStartX = 0;
    let dragStartScrollLeft = 0;
    let suppressClick = false;

    const updateActiveIndex = () => {
      const items = Array.from(carousel.children);
      if (items.length === 0) return;

      const currentIndex = items.findIndex((item) => {
        const itemLeft = item.offsetLeft;
        const itemRight = itemLeft + item.clientWidth;
        const scrollCenter = carousel.scrollLeft + carousel.clientWidth / 2;
        return scrollCenter >= itemLeft && scrollCenter <= itemRight;
      });

      setActiveIndex(currentIndex >= 0 ? currentIndex : 0);
    };

    const preventNativeDrag = (event) => event.preventDefault();
    const startDrag = (event) => {
      if (event.pointerType !== "mouse" || event.button !== 0) return;

      dragPointerId = event.pointerId;
      dragStartX = event.clientX;
      dragStartScrollLeft = carousel.scrollLeft;
      suppressClick = false;
      carousel.setPointerCapture(event.pointerId);
    };
    const moveDrag = (event) => {
      if (dragPointerId !== event.pointerId) return;

      const distance = event.clientX - dragStartX;
      if (Math.abs(distance) > 5) {
        suppressClick = true;
        carousel.classList.add("cert-grid--dragging");
      }

      if (!suppressClick) return;
      event.preventDefault();
      carousel.scrollLeft = dragStartScrollLeft - distance;
    };
    const finishDrag = (event) => {
      if (dragPointerId !== event.pointerId) return;
      if (carousel.hasPointerCapture(event.pointerId)) {
        carousel.releasePointerCapture(event.pointerId);
      }
      dragPointerId = null;
      carousel.classList.remove("cert-grid--dragging");
    };
    const preventDraggedClick = (event) => {
      if (!suppressClick) return;
      event.preventDefault();
      event.stopPropagation();
      suppressClick = false;
    };

    updateActiveIndex();
    carousel.addEventListener("scroll", updateActiveIndex, { passive: true });
    carousel.addEventListener("dragstart", preventNativeDrag);
    carousel.addEventListener("pointerdown", startDrag);
    carousel.addEventListener("pointermove", moveDrag);
    carousel.addEventListener("pointerup", finishDrag);
    carousel.addEventListener("pointercancel", finishDrag);
    carousel.addEventListener("click", preventDraggedClick, true);
    window.addEventListener("resize", updateActiveIndex);

    return () => {
      carousel.removeEventListener("scroll", updateActiveIndex);
      carousel.removeEventListener("dragstart", preventNativeDrag);
      carousel.removeEventListener("pointerdown", startDrag);
      carousel.removeEventListener("pointermove", moveDrag);
      carousel.removeEventListener("pointerup", finishDrag);
      carousel.removeEventListener("pointercancel", finishDrag);
      carousel.removeEventListener("click", preventDraggedClick, true);
      window.removeEventListener("resize", updateActiveIndex);
    };
  }, [certs]);

  function scrollToIndex(index) {
    const carousel = carouselRef.current;
    if (!carousel) return;

    const items = Array.from(carousel.children);
    const nextItem = items[index];
    if (!nextItem) return;

    carousel.scrollTo({
      left: nextItem.offsetLeft,
      behavior: "smooth",
    });
  }

  if (loading)
    return (
      <div className="dashboard-card">
        <p>Loading certifications...</p>
      </div>
    );

  if (error)
    return (
      <div className="dashboard-card">
        <p>Error loading certifications: {error}</p>
      </div>
    );

  if (!certs || certs.length === 0)
    return (
      <div className="dashboard-card">
        <p>No certifications found.</p>
      </div>
    );

  return (
    <div className="cert-carousel">
      <div className="cert-grid" ref={carouselRef}>
        {certs.map((cert, index) => {
          const shareBadgeHost =
            cert.shareBadgeHost || "https://www.credly.com";
          const href =
            cert.href ||
            (cert.shareBadgeId
              ? `${shareBadgeHost}/badges/${cert.shareBadgeId}/public_url`
              : undefined);

          return (
            <a
              key={index}
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className={
                cert.shareBadgeId ? "cert-card cert-card--embed" : "cert-card"
              }
              aria-label={cert.alt}
              title={cert.alt}
            >
              {cert.shareBadgeId ? (
                <div className="cert-embed-wrapper" aria-label={cert.alt}>
                  <div
                    data-iframe-width={cert.iframeWidth || 200}
                    data-iframe-height={cert.iframeHeight || 260}
                    data-share-badge-id={cert.shareBadgeId}
                    data-share-badge-host={shareBadgeHost}
                  ></div>
                </div>
              ) : (
                <div className="cert-img-wrapper">
                  <img src={cert.src} alt={cert.alt} />
                </div>
              )}
            </a>
          );
        })}
      </div>
      <div
        className="cert-carousel__pagination"
        aria-label="Certification pages"
      >
        {certs.map((cert, index) => (
          <button
            key={cert.shareBadgeId || cert.href || cert.alt || index}
            type="button"
            className={
              index === activeIndex
                ? "cert-carousel__dot cert-carousel__dot--active"
                : "cert-carousel__dot"
            }
            aria-label={`Show certification ${index + 1}`}
            aria-pressed={index === activeIndex}
            onClick={() => scrollToIndex(index)}
          />
        ))}
      </div>
    </div>
  );
}
