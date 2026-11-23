document.addEventListener("DOMContentLoaded", () => {
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content;
  document.querySelectorAll('form[method="post"], form[method="POST"]').forEach(form => {
    if (csrf && !form.querySelector('input[name="_csrf_token"]')) {
      const input = document.createElement("input");
      input.type = "hidden"; input.name = "_csrf_token"; input.value = csrf;
      form.appendChild(input);
    }
  });
  const menu = document.querySelector(".mobile-menu");
  const nav = document.querySelector(".main-nav");
  if (menu && nav) menu.addEventListener("click", () => {
    const open = nav.classList.toggle("nav-open");
    menu.setAttribute("aria-expanded", String(open));
  });
  document.querySelectorAll(".flash-close").forEach(btn => btn.addEventListener("click", () => btn.closest(".flash").remove()));
  document.querySelectorAll("[data-target]").forEach(btn => btn.addEventListener("click", () => {
    const input = document.getElementById(btn.dataset.target);
    if (!input) return;
    input.type = input.type === "password" ? "text" : "password";
    btn.textContent = input.type === "password" ? "Show" : "Hide";
  }));
  document.querySelectorAll("[data-copy-input]").forEach(btn => btn.addEventListener("click", async () => {
    const input = document.getElementById(btn.dataset.copyInput);
    if (!input) return;
    try { await navigator.clipboard.writeText(input.value); btn.textContent = "Copied!"; }
    catch { input.select(); document.execCommand("copy"); btn.textContent = "Copied!"; }
    setTimeout(() => btn.textContent = "Copy", 1600);
  }));
  document.querySelectorAll("form[data-confirm]").forEach(form => form.addEventListener("submit", e => {
    if (!confirm(form.dataset.confirm)) e.preventDefault();
  }));
  const observer = new IntersectionObserver(entries => entries.forEach(entry => {
    if (entry.isIntersecting) { entry.target.classList.add("is-visible"); observer.unobserve(entry.target); }
  }), {threshold: .12});
  document.querySelectorAll(".reveal").forEach(el => observer.observe(el));
  const filter = document.getElementById("calendar-filter");
  if (filter) filter.addEventListener("change", () => {
    document.querySelectorAll("#calendar-table tbody tr[data-date]").forEach(row => {
      row.hidden = !!filter.value && row.dataset.date !== filter.value;
    });
  });
});
