// Demo de AnonOptions (script externo: CSP-safe, sin inline).
(function () {
  "use strict";
  var host = document.getElementById("host");
  var out = document.getElementById("out");
  var langSel = document.getElementById("lang");
  var svc = document.getElementById("svc");
  var dark = document.getElementById("dark");

  function render() {
    AnonOptions.mount(host, {
      lang: langSel.value,
      hasService: svc.checked,
      mode: "pseudo",
      onChange: function (v) { out.textContent = JSON.stringify(v, null, 2); },
    });
    out.textContent = JSON.stringify(AnonOptions.getValues(host), null, 2);
  }

  langSel.addEventListener("change", render);
  svc.addEventListener("change", render);
  dark.addEventListener("change", function () {
    document.documentElement.setAttribute("data-theme", dark.checked ? "dark" : "light");
  });
  render();
})();
