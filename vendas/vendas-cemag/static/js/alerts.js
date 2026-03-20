// Utilitário de toast reaproveitável
// Uso: window.showToast("Mensagem", "success" | "danger" | "info" | "warning");
(function () {
  const colorMap = {
    success: "success",
    danger: "danger",
    error: "danger",
    warning: "warning",
    info: "info",
  };

  window.showToast = function showToast(message, type = "info", options = {}) {
    const color = colorMap[type] || "secondary";
    const delay = options.delay ?? 3000;
    const positionClass = options.positionClass || "top-0 end-0";

    const toast = document.createElement("div");
    toast.className = `toast align-items-center text-bg-${color} border-0 show position-fixed ${positionClass} m-3`;
    toast.style.zIndex = 9999;
    toast.innerHTML = `
      <div class="d-flex">
        <div class="toast-body">${message}</div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
      </div>
    `;

    document.body.appendChild(toast);
    const bsToast = new bootstrap.Toast(toast, { delay });
    bsToast.show();
    toast.addEventListener("hidden.bs.toast", () => toast.remove());
    return bsToast;
  };
})();
