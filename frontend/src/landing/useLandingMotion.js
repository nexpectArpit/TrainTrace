import { useEffect } from "react";

const cardSelector = [
  ".tt-chapter",
  ".tt-problem-grid article",
  ".tt-capability-grid article",
  ".tt-feature-content article",
  ".tt-feature-menu button",
  ".tt-stage-tabs button",
].join(", ");

export default function useLandingMotion() {
  useEffect(() => {
    if (
      !window.IntersectionObserver ||
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ) {
      document
        .querySelectorAll(".tt-landing .tt-reveal, .tt-landing .tt-card-enter")
        .forEach((node) =>
          node.classList.add("tt-revealed", "tt-card-visible"),
        );
      return;
    }

    const root = document.querySelector(".tt-landing");
    if (!root) return;
    const cards = new Set();
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.classList.add("tt-card-visible");
            observer.unobserve(entry.target);
          }
        }
      },
      { threshold: 0.08, rootMargin: "0px 0px -24px 0px" },
    );

    const registerCards = () => {
      root.querySelectorAll(cardSelector).forEach((card, index) => {
        if (cards.has(card)) return;
        cards.add(card);
        card.classList.add("tt-card-enter");
        card.style.setProperty("--tt-card-delay", `${(index % 3) * 65}ms`);
        observer.observe(card);
      });
    };
    registerCards();
    const fallbackTimer = setTimeout(() => {
      root
        .querySelectorAll(".tt-card-enter")
        .forEach((c) => c.classList.add("tt-card-visible"));
    }, 450);
    const mutations = new MutationObserver(registerCards);
    mutations.observe(root, { childList: true, subtree: true });

    return () => {
      clearTimeout(fallbackTimer);
      mutations.disconnect();
      observer.disconnect();
      cards.forEach((card) => {
        card.classList.remove("tt-card-enter", "tt-card-visible");
        card.style.removeProperty("--tt-card-delay");
      });
    };
  }, []);
}
