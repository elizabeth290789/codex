const modal = document.querySelector("[data-modal]");
const modalOpenButtons = document.querySelectorAll("[data-modal-open]");
const modalCloseButton = document.querySelector("[data-modal-close]");

modalOpenButtons.forEach((button) =>
  button.addEventListener("click", () => {
    modal.classList.add("open");
  })
);

modalCloseButton.addEventListener("click", () => {
  modal.classList.remove("open");
});

modal.addEventListener("click", (event) => {
  if (event.target === modal) {
    modal.classList.remove("open");
  }
});

const tabGroups = document.querySelectorAll(".tabs");

tabGroups.forEach((group) => {
  const buttons = group.querySelectorAll(".tab-button");
  const panels = group.querySelectorAll(".tab-panel");
  buttons.forEach((button) => {
    button.addEventListener("click", () => {
      const target = button.dataset.tab;
      buttons.forEach((btn) => btn.classList.remove("active"));
      button.classList.add("active");
      panels.forEach((panel) => {
        panel.classList.toggle("active", panel.dataset.panel === target);
      });
    });
  });
});

const accordionItems = document.querySelectorAll(".accordion-item");

accordionItems.forEach((item) => {
  item.addEventListener("click", () => {
    const isActive = item.classList.contains("active");
    accordionItems.forEach((btn) => btn.classList.remove("active"));
    if (!isActive) {
      item.classList.add("active");
    }
  });
});

const counters = document.querySelectorAll("[data-counter]");
const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      const el = entry.target;
      const target = Number(el.dataset.counter);
      let current = 0;
      const increment = Math.max(1, Math.floor(target / 40));
      const interval = setInterval(() => {
        current += increment;
        if (current >= target) {
          current = target;
          clearInterval(interval);
        }
        el.textContent = current;
      }, 30);
      observer.unobserve(el);
    });
  },
  { threshold: 0.5 }
);

counters.forEach((counter) => observer.observe(counter));

const scrollButtons = document.querySelectorAll("[data-scroll]");
scrollButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const targetId = button.dataset.scroll;
    const target = document.getElementById(targetId);
    if (target) {
      target.scrollIntoView({ behavior: "smooth" });
    }
  });
});
