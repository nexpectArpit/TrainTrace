import React, { useEffect, useRef } from "react";

export default function Reveal({
  children,
  className = "",
  id,
  as: Element = "div",
}) {
  const ref = useRef(null);
  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    if (
      !window.IntersectionObserver ||
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ) {
      node.classList.add("tt-revealed");
      return;
    }
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          node.classList.add("tt-revealed");
          observer.disconnect();
        }
      },
      { threshold: 0.01 },
    );
    node.classList.add("tt-reveal");
    observer.observe(node);
    // Graceful fallback to guarantee content visibility after initial paint
    const fallbackTimer = setTimeout(() => {
      node.classList.add("tt-revealed");
    }, 350);
    return () => {
      observer.disconnect();
      clearTimeout(fallbackTimer);
    };
  }, []);
  return (
    <Element ref={ref} className={className} id={id}>
      {children}
    </Element>
  );
}
