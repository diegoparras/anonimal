// Anonimal — UI. Vanilla JS, sin dependencias.
(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var lang = localStorage.getItem("anonimal-lang") || "es";
  if (!window.I18N[lang]) lang = "es";

  function t(key) { return (window.I18N[lang] && window.I18N[lang][key]) || window.I18N.es[key] || key; }

  function applyI18n() {
    document.documentElement.lang = lang;
    document.querySelectorAll("[data-i18n]").forEach(function (el) {
      el.textContent = t(el.getAttribute("data-i18n"));
    });
    document.querySelectorAll("[data-i18n-ph]").forEach(function (el) {
      el.setAttribute("placeholder", t(el.getAttribute("data-i18n-ph")));
    });
  }

  function escapeHtml(s) {
    return s.replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  // Resalta el texto original marcando los spans (ya vienen ordenados y sin solapar).
  function renderHighlight(text, spans) {
    var out = "", pos = 0;
    spans.forEach(function (s) {
      if (s.start < pos) return;
      out += escapeHtml(text.slice(pos, s.start));
      out += '<mark class="pii" title="' + escapeHtml(s.label) + '">' +
             escapeHtml(text.slice(s.start, s.end)) + "</mark>";
      pos = s.end;
    });
    out += escapeHtml(text.slice(pos));
    return out || "&nbsp;";
  }

  function api(path, body) {
    return fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(function (r) {
      return r.json().then(function (j) {
        if (!r.ok) throw new Error(j.detail || ("HTTP " + r.status));
        return j;
      });
    });
  }

  function parseList(s) {
    return s.split(",").map(function (x) { return x.trim(); }).filter(Boolean);
  }
  function currentRules() {
    var always = parseList($("ruleAlways").value);
    var never = parseList($("ruleNever").value);
    if (!always.length && !never.length) return null;
    return { always: always, never: never };
  }

  function download(name, text, type) {
    var blob = new Blob([text], { type: type || "text/plain;charset=utf-8" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url; a.download = name; a.click();
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  }

  function flash(btn, key) {
    var prev = btn.textContent;
    btn.textContent = t(key);
    setTimeout(function () { btn.textContent = prev; }, 1400);
  }

  // ---- estado del último resultado de texto ----
  var last = { output: "", map: null };

  function anonymize() {
    var text = $("input").value;
    var err = $("anonErr");
    err.classList.add("hidden");
    if (!text.trim()) { $("input").focus(); return; }
    var btn = $("anonBtn"); var label = btn.textContent;
    btn.disabled = true; btn.textContent = t("processing");

    api("/anonymize", {
      text: text, mode: $("mode").value, engine: $("engine").value, rules: currentRules(),
    }).then(function (j) {
      $("engineBadge").textContent = j.engine;
      $("highlight").innerHTML = renderHighlight(text, j.spans || []);
      $("output").textContent = j.output;
      last.output = j.output; last.map = j.map && Object.keys(j.map).length ? j.map : null;

      // resumen por categoría
      var chips = $("summary"); chips.innerHTML = "";
      var labels = Object.keys(j.summary || {});
      if (!labels.length) {
        var c = document.createElement("span"); c.className = "chip"; c.textContent = t("noPii");
        chips.appendChild(c);
      } else {
        labels.forEach(function (k) {
          var c = document.createElement("span"); c.className = "chip";
          c.textContent = k + " · " + j.summary[k]; chips.appendChild(c);
        });
      }
      $("dlMapBtn").classList.toggle("hidden", !last.map);
      $("reversibleNote").classList.toggle("hidden", !j.reversible);
      $("result").classList.remove("hidden");
    }).catch(function (e) {
      err.textContent = e.message || t("errGeneric"); err.classList.remove("hidden");
    }).finally(function () {
      btn.disabled = false; btn.textContent = label;
    });
  }

  function sendToEscriba() {
    if (!last.output) return;
    var payload = {
      from: "anonimal", version: 1, title: "Texto anonimizado",
      source: "anonimal", mime: "text/markdown", content: last.output,
      ts: Date.now(),
    };
    try {
      sessionStorage.setItem("escriba.handoff", JSON.stringify(payload));
      localStorage.setItem("escriba.handoff", JSON.stringify(payload));
    } catch (e) {}
    var url = localStorage.getItem("anonimal-escriba-url");
    if (url) window.open(url, "_blank");
    flash($("sendBtn"), "sent");
  }

  // ---- archivos ----
  function handleFiles(fileList) {
    var out = $("filesOut");
    Array.prototype.forEach.call(fileList, function (file) {
      var fd = new FormData();
      fd.append("file", file);
      fd.append("mode", $("mode").value);
      fd.append("engine", $("engine").value);
      var rules = currentRules();
      if (rules) fd.append("rules_json", JSON.stringify(rules));

      var card = document.createElement("div");
      card.className = "file-card";
      card.innerHTML = '<span class="nm"></span><span class="meta">' + t("processing") + "</span>";
      card.querySelector(".nm").textContent = file.name;
      out.appendChild(card);

      fetch("/anonymize_file", { method: "POST", body: fd })
        .then(function (r) { return r.json().then(function (j) { if (!r.ok) throw new Error(j.detail); return j; }); })
        .then(function (j) {
          var n = Object.keys(j.summary || {}).reduce(function (a, k) { return a + j.summary[k]; }, 0);
          card.querySelector(".meta").textContent = j.format + " · " + n + " PII";
          var dl = document.createElement("button"); dl.className = "btn ghost"; dl.textContent = t("download");
          dl.addEventListener("click", function () { download("anon_" + file.name, j.content); });
          card.appendChild(dl);
          if (j.map && Object.keys(j.map).length) {
            var dm = document.createElement("button"); dm.className = "btn ghost"; dm.textContent = t("downloadMap");
            dm.addEventListener("click", function () { download(file.name + ".map.json", JSON.stringify(j.map, null, 2), "application/json"); });
            card.appendChild(dm);
          }
        })
        .catch(function (e) { card.querySelector(".meta").textContent = e.message || t("errGeneric"); });
    });
  }

  // ---- redacción de PDF ----
  function handlePdf(file) {
    if (!file) return;
    var fd = new FormData();
    fd.append("file", file);
    fd.append("engine", $("engine").value);
    var rules = currentRules();
    if (rules) fd.append("rules_json", JSON.stringify(rules));

    var card = document.createElement("div");
    card.className = "file-card";
    card.innerHTML = '<span class="nm"></span><span class="meta"></span>';
    card.querySelector(".nm").textContent = file.name;
    card.querySelector(".meta").textContent = t("processing");
    $("pdfOut").appendChild(card);

    fetch("/redact_pdf", { method: "POST", body: fd })
      .then(function (r) {
        if (!r.ok) return r.json().then(function (j) { throw new Error(j.detail || ("HTTP " + r.status)); });
        var n = r.headers.get("X-Redactions") || "?";
        return r.blob().then(function (b) { return { blob: b, n: n }; });
      })
      .then(function (res) {
        card.querySelector(".meta").textContent = t("pdfDone").replace("{n}", res.n);
        var dl = document.createElement("button");
        dl.className = "btn ghost"; dl.textContent = t("download");
        dl.addEventListener("click", function () {
          var url = URL.createObjectURL(res.blob);
          var a = document.createElement("a");
          a.href = url; a.download = "redactado_" + file.name; a.click();
          setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
        });
        card.appendChild(dl);
      })
      .catch(function (e) { card.querySelector(".meta").textContent = e.message || t("errGeneric"); });
  }

  // ---- re-identificar ----
  function reidentify() {
    var err = $("reidErr"); err.classList.add("hidden");
    var text = $("reidInput").value, mapRaw = $("reidMap").value.trim();
    if (!text.trim() || !mapRaw) { err.textContent = t("reidErrEmpty"); err.classList.remove("hidden"); return; }
    var map;
    try { map = JSON.parse(mapRaw); } catch (e) { err.textContent = t("reidErrMap"); err.classList.remove("hidden"); return; }
    api("/deanonymize", { text: text, map: map }).then(function (j) {
      $("reidOutput").textContent = j.output;
      $("reidResult").classList.remove("hidden");
    }).catch(function (e) { err.textContent = e.message || t("errGeneric"); err.classList.remove("hidden"); });
  }

  // ---- wiring ----
  function setTab(which) {
    var anon = which === "anon";
    $("tabAnon").classList.toggle("active", anon);
    $("tabReid").classList.toggle("active", !anon);
    $("panelAnon").classList.toggle("hidden", !anon);
    $("panelReid").classList.toggle("hidden", anon);
  }

  function init() {
    $("lang").value = lang;
    applyI18n();

    $("themeBtn").addEventListener("click", function () {
      var dark = document.documentElement.getAttribute("data-theme") === "dark";
      document.documentElement.setAttribute("data-theme", dark ? "light" : "dark");
      localStorage.setItem("anonimal-theme", dark ? "light" : "dark");
    });
    $("lang").addEventListener("change", function () {
      lang = $("lang").value; localStorage.setItem("anonimal-lang", lang); applyI18n();
    });
    $("tabAnon").addEventListener("click", function () { setTab("anon"); });
    $("tabReid").addEventListener("click", function () { setTab("reid"); });

    $("anonBtn").addEventListener("click", anonymize);
    $("copyBtn").addEventListener("click", function () {
      navigator.clipboard.writeText(last.output); flash($("copyBtn"), "copied");
    });
    $("dlBtn").addEventListener("click", function () { download("anonimizado.txt", last.output); });
    $("dlMapBtn").addEventListener("click", function () {
      if (last.map) download("mapa.json", JSON.stringify(last.map, null, 2), "application/json");
    });
    $("sendBtn").addEventListener("click", sendToEscriba);
    $("files").addEventListener("change", function (e) { handleFiles(e.target.files); e.target.value = ""; });
    $("pdf").addEventListener("change", function (e) { handlePdf(e.target.files[0]); e.target.value = ""; });

    $("reidBtn").addEventListener("click", reidentify);
    $("reidCopyBtn").addEventListener("click", function () {
      navigator.clipboard.writeText($("reidOutput").textContent); flash($("reidCopyBtn"), "copied");
    });
    $("reidMapFile").addEventListener("change", function (e) {
      var f = e.target.files[0]; if (!f) return;
      var rd = new FileReader();
      rd.onload = function () { $("reidMap").value = rd.result; };
      rd.readAsText(f);
    });

    // estado del motor por defecto
    fetch("/health").then(function (r) { return r.json(); }).then(function (h) {
      $("engineBadge").textContent = h.ml && h.ml.ready ? "ml" : "lite";
    }).catch(function () {});
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
