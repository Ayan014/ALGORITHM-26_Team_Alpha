document.addEventListener("DOMContentLoaded", () => {
  // 1. Mobile Sidebar Drawer Controls
  const sidebar = document.getElementById("chSidebar");
  const backdrop = document.getElementById("chBackdrop");
  const toggleBtn = document.getElementById("sidebarToggle");
  const closeBtn = document.getElementById("sidebarClose");

  function openSidebar() {
    if (sidebar) sidebar.classList.add("open");
    if (backdrop) backdrop.classList.add("show");
  }

  function closeSidebar() {
    if (sidebar) sidebar.classList.remove("open");
    if (backdrop) backdrop.classList.remove("show");
  }

  if (toggleBtn) toggleBtn.addEventListener("click", openSidebar);
  if (closeBtn) closeBtn.addEventListener("click", closeSidebar);
  if (backdrop) backdrop.addEventListener("click", closeSidebar);

  // 2. Highlight active sidebar link automatically
  const currentPath = window.location.pathname;
  document.querySelectorAll(".ch-nav-link").forEach((link) => {
    const href = link.getAttribute("href");
    if (href && (currentPath === href || (href !== "/dashboard" && href !== "/" && currentPath.startsWith(href)))) {
      link.classList.add("active");
    }
  });

  // 3. Smooth Animated Number Counters for KPI Metrics
  document.querySelectorAll(".count-up").forEach((el) => {
    const raw = el.dataset.target || el.textContent.trim();
    const match = raw.match(/^([^0-9.-]*)([0-9,.]+)(.*)$/);
    if (!match) return;
    const prefix = match[1];
    const numStr = match[2].replace(/,/g, "");
    const suffix = match[3];
    const target = parseFloat(numStr);
    if (isNaN(target) || target === 0) return;

    const isFloat = numStr.includes(".");
    const decimals = isFloat ? (numStr.split(".")[1] || "").length : 0;
    const hasComma = match[2].includes(",");
    const duration = 750;
    const startTime = performance.now();

    function tick(now) {
      const progress = Math.min((now - startTime) / duration, 1);
      const ease = 1 - Math.pow(1 - progress, 3);
      const current = target * ease;
      let formatted = isFloat ? current.toFixed(decimals) : Math.round(current).toString();
      if (hasComma) {
        const parts = formatted.split(".");
        parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ",");
        formatted = parts.join(".");
      }
      el.textContent = prefix + formatted + suffix;
      if (progress < 1) {
        requestAnimationFrame(tick);
      } else {
        el.textContent = raw;
      }
    }
    requestAnimationFrame(tick);
  });

  // 4. Live Topbar Date/Time Badge
  const clockEl = document.getElementById("liveClock");
  if (clockEl) {
    const updateClock = () => {
      const now = new Date();
      clockEl.textContent = now.toLocaleDateString("en-IN", {
        weekday: "short",
        day: "2-digit",
        month: "short",
        year: "numeric"
      });
    };
    updateClock();
  }
});

// Global Document Share Helper (Preserved from original app)
function shareDocument(title, text) {
  const url = window.location.href;
  if (navigator.share) {
    navigator.share({ title: title, text: text, url: url }).catch(() => {});
  } else {
    navigator.clipboard.writeText(title + "\n" + text + "\n" + url);
    alert("Link & details copied to clipboard! You can paste and share anywhere.");
  }
}
