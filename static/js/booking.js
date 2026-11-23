document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("booking-form");
  if (!form) return;
  const dateInput = document.getElementById("appointment-date");
  const slotArea = document.getElementById("slot-area");
  const startInput = document.getElementById("start-time");
  const confirm = document.getElementById("confirm-booking");
  const summaryService = document.getElementById("summary-service");
  const summaryDetail = document.getElementById("summary-detail");
  let selectedService = null;
  let selectedTime = null;
  const updateButton = () => {
    confirm.disabled = !(selectedService && dateInput.value && selectedTime);
    summaryDetail.textContent = selectedTime && dateInput.value ? `${dateInput.value} · ${selectedTime}` : "Your selected date and time will appear here.";
  };
  async function loadSlots() {
    selectedTime = null; startInput.value = ""; updateButton();
    if (!selectedService || !dateInput.value) {
      slotArea.innerHTML = '<p class="slot-placeholder">Choose a service and date to view available times.</p>'; return;
    }
    slotArea.innerHTML = '<p class="slot-placeholder"><span class="spinner"></span> Finding available times…</p>';
    try {
      const url = new URL(window.ILO_BOOKING_URL, window.location.origin);
      url.searchParams.set("date", dateInput.value);
      url.searchParams.set("service_id", selectedService.value);
      const response = await fetch(url);
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Could not load slots.");
      if (!data.slots.length) { slotArea.innerHTML = '<div class="no-slots">No available times on this date. Try another day.</div>'; return; }
      slotArea.innerHTML = '<div class="slot-grid"></div>';
      const grid = slotArea.querySelector(".slot-grid");
      data.slots.forEach(time => {
        const button = document.createElement("button");
        button.type = "button"; button.className = "slot-button"; button.textContent = time;
        button.addEventListener("click", () => {
          slotArea.querySelectorAll(".slot-button").forEach(b => b.classList.remove("selected"));
          button.classList.add("selected"); selectedTime = time; startInput.value = time; updateButton();
        });
        grid.appendChild(button);
      });
    } catch (error) { slotArea.textContent = error.message; }
  }
  document.querySelectorAll('input[name="service_id"]').forEach(input => input.addEventListener("change", () => {
    selectedService = input;
    const label = input.closest(".service-option");
    summaryService.textContent = label.querySelector(".service-info b").textContent;
    loadSlots();
  }));
  dateInput.addEventListener("change", loadSlots);
  form.addEventListener("submit", e => {
    if (!selectedService || !selectedTime) { e.preventDefault(); alert("Please select a service and available time."); }
    else { confirm.disabled = true; confirm.textContent = "Confirming…"; }
  });
});
