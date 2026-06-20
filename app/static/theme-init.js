// Anti-FOUC: aplica el tema guardado antes de pintar (script externo por CSP).
(function () {
  try {
    var t = localStorage.getItem("anonimal-theme");
    if (t === "dark" || (!t && matchMedia("(prefers-color-scheme: dark)").matches)) {
      document.documentElement.setAttribute("data-theme", "dark");
    }
  } catch (e) {}
})();
