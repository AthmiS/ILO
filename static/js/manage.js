document.addEventListener("DOMContentLoaded", () => {
  const dateInput = document.getElementById("reschedule-date");
  if (!dateInput) return;
  const area = document.getElementById("reschedule-slots");
  const timeInput = document.getElementById("reschedule-time");
  const submit = document.getElementById("reschedule-submit");
  let selected = null;
  dateInput.addEventListener("change", async () => {
    selected = null; timeInput.value = ""; submit.disabled = true;
    area.innerHTML = '<p class="slot-placeholder"><span class="spinner"></span> Checking times…</p>';
    try {
      const url = new URL(window.ILO_MANAGE_URL, window.location.origin);
      url.searchParams.set("date", dateInput.value);
      const response = await fetch(url); const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Unable to load times.");
      if (!data.slots.length) { area.innerHTML = '<p class="no-slots">No available times on this date.</p>'; return; }
      area.innerHTML = '<div class="slot-grid"></div>';
      const grid = area.querySelector(".slot-grid");
      data.slots.forEach(time => {
        const button = document.createElement("button");
        button.type = "button"; button.className = "slot-button"; button.textContent = time;
        button.addEventListener("click", () => {
          grid.querySelectorAll("button").forEach(b => b.classList.remove("selected"));
          button.classList.add("selected"); selected = time; timeInput.value = time; submit.disabled = false;
        });
        grid.appendChild(button);
      });
    } catch (error) { area.textContent = error.message; }
  });
});
