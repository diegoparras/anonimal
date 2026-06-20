/*!
 * anon-options.js — Componente de opciones de anonimización del ecosistema.
 * Viaja dentro de `anonimal_lite` (fuente única); cada app (Escriba/Extracta/
 * Fisherboy) lo sirve como estático para que las opciones sean IDÉNTICAS.
 *
 * Ejes: escalable (vanilla, sin deps), seguro (sin eval/innerHTML con datos,
 * estilos por CSSOM = CSP-safe), eficiente (un archivo), UX continuista (usa
 * <select>/<input> pelados que heredan el estilo de cada app + var(--accent)).
 *
 * Uso:
 *   const a = AnonOptions.mount(el, { lang:"es", hasService:true, mode:"pseudo",
 *                                     onChange(v){ ... } });
 *   a.getValues(); // { mode, rules:{ always:[], never:[], patterns:[] } }
 */
(function (global) {
  "use strict";

  var MODES = ["off", "pseudo", "mask", "hash", "typed", "anon"];

  var I18N = {
    es: {
      modeLabel: "Anonimizar datos personales (PII)",
      mode_off: "No anonimizar", mode_pseudo: "Seudónimo (reversible)",
      mode_mask: "Máscara parcial", mode_hash: "Hash estable",
      mode_typed: "Etiquetado por tipo", mode_anon: "Anónimo",
      engineFull: "Completo (IA)", engineLite: "Básico (regex)",
      engineHint: "Modo básico: detecta datos estructurados. Conectá Anonimal para nombres y direcciones.",
      rulesTitle: "Reglas propias", alwaysLabel: "Ocultar siempre",
      neverLabel: "No ocultar nunca", patternsLabel: "Patrones avanzados (JSON)",
      patternsHint: 'Lista JSON, p. ej. [{"regex":"LEG-\\\\d{6}","placeholder":"ID"}]',
      listPh: "término1, término2",
    },
    en: {
      modeLabel: "Anonymize personal data (PII)",
      mode_off: "Don't anonymize", mode_pseudo: "Pseudonym (reversible)",
      mode_mask: "Partial mask", mode_hash: "Stable hash",
      mode_typed: "Labeled by type", mode_anon: "Anonymous",
      engineFull: "Full (AI)", engineLite: "Basic (regex)",
      engineHint: "Basic mode: detects structured data. Connect Anonimal for names and addresses.",
      rulesTitle: "Your own rules", alwaysLabel: "Always hide",
      neverLabel: "Never hide", patternsLabel: "Advanced patterns (JSON)",
      patternsHint: 'JSON list, e.g. [{"regex":"LEG-\\\\d{6}","placeholder":"ID"}]',
      listPh: "term1, term2",
    },
    fr: {
      modeLabel: "Anonymiser les données personnelles (PII)",
      mode_off: "Ne pas anonymiser", mode_pseudo: "Pseudonyme (réversible)",
      mode_mask: "Masque partiel", mode_hash: "Hachage stable",
      mode_typed: "Étiqueté par type", mode_anon: "Anonyme",
      engineFull: "Complet (IA)", engineLite: "Basique (regex)",
      engineHint: "Mode basique : détecte les données structurées. Connectez Anonimal pour noms et adresses.",
      rulesTitle: "Vos règles", alwaysLabel: "Toujours masquer",
      neverLabel: "Ne jamais masquer", patternsLabel: "Motifs avancés (JSON)",
      patternsHint: 'Liste JSON, ex. [{"regex":"LEG-\\\\d{6}","placeholder":"ID"}]',
      listPh: "terme1, terme2",
    },
    pt: {
      modeLabel: "Anonimizar dados pessoais (PII)",
      mode_off: "Não anonimizar", mode_pseudo: "Pseudônimo (reversível)",
      mode_mask: "Máscara parcial", mode_hash: "Hash estável",
      mode_typed: "Rotulado por tipo", mode_anon: "Anônimo",
      engineFull: "Completo (IA)", engineLite: "Básico (regex)",
      engineHint: "Modo básico: detecta dados estruturados. Conecte o Anonimal para nomes e endereços.",
      rulesTitle: "Suas regras", alwaysLabel: "Sempre ocultar",
      neverLabel: "Nunca ocultar", patternsLabel: "Padrões avançados (JSON)",
      patternsHint: 'Lista JSON, ex. [{"regex":"LEG-\\\\d{6}","placeholder":"ID"}]',
      listPh: "termo1, termo2",
    },
    it: {
      modeLabel: "Anonimizza dati personali (PII)",
      mode_off: "Non anonimizzare", mode_pseudo: "Pseudonimo (reversibile)",
      mode_mask: "Maschera parziale", mode_hash: "Hash stabile",
      mode_typed: "Etichettato per tipo", mode_anon: "Anonimo",
      engineFull: "Completo (IA)", engineLite: "Base (regex)",
      engineHint: "Modo base: rileva dati strutturati. Collega Anonimal per nomi e indirizzi.",
      rulesTitle: "Le tue regole", alwaysLabel: "Nascondi sempre",
      neverLabel: "Non nascondere mai", patternsLabel: "Pattern avanzati (JSON)",
      patternsHint: 'Lista JSON, es. [{"regex":"LEG-\\\\d{6}","placeholder":"ID"}]',
      listPh: "termine1, termine2",
    },
    zh: {
      modeLabel: "匿名化个人数据（PII）",
      mode_off: "不匿名化", mode_pseudo: "假名（可逆）",
      mode_mask: "部分掩码", mode_hash: "稳定哈希",
      mode_typed: "按类型标签", mode_anon: "匿名",
      engineFull: "完整（AI）", engineLite: "基础（正则）",
      engineHint: "基础模式：检测结构化数据。连接 Anonimal 以识别姓名和地址。",
      rulesTitle: "自定义规则", alwaysLabel: "始终隐藏",
      neverLabel: "从不隐藏", patternsLabel: "高级模式（JSON）",
      patternsHint: 'JSON 列表，例如 [{"regex":"LEG-\\\\d{6}","placeholder":"ID"}]',
      listPh: "词1, 词2",
    },
    ja: {
      modeLabel: "個人データ（PII）を匿名化",
      mode_off: "匿名化しない", mode_pseudo: "仮名（可逆）",
      mode_mask: "部分マスク", mode_hash: "安定ハッシュ",
      mode_typed: "種別ラベル", mode_anon: "匿名",
      engineFull: "完全（AI）", engineLite: "基本（正規表現）",
      engineHint: "基本モード：構造化データを検出。氏名・住所は Anonimal を接続してください。",
      rulesTitle: "独自ルール", alwaysLabel: "常に隠す",
      neverLabel: "隠さない", patternsLabel: "高度なパターン（JSON）",
      patternsHint: 'JSON リスト、例 [{"regex":"LEG-\\\\d{6}","placeholder":"ID"}]',
      listPh: "語1, 語2",
    },
  };

  function t(lang, key) {
    var d = I18N[lang] || I18N.es;
    return d[key] || I18N.es[key] || key;
  }

  function elem(tag, style) {
    var n = document.createElement(tag);
    if (style) { for (var k in style) { n.style[k] = style[k]; } }
    return n;
  }

  function field(labelText) {
    var wrap = elem("div", { display: "flex", flexDirection: "column", gap: "4px", margin: "0 0 12px" });
    var lab = elem("label", { fontSize: "13px", fontWeight: "600", color: "var(--muted-2, var(--text, #333))" });
    lab.textContent = labelText;
    wrap.appendChild(lab);
    return { wrap: wrap, label: lab };
  }

  function parseList(s) {
    return (s || "").split(",").map(function (x) { return x.trim(); }).filter(Boolean);
  }

  function parsePatterns(s) {
    s = (s || "").trim();
    if (!s) return [];
    try {
      var v = JSON.parse(s);
      var arr = Array.isArray(v) ? v : (v && Array.isArray(v.patterns) ? v.patterns : []);
      return arr.filter(function (p) { return p && typeof p.regex === "string"; });
    } catch (e) { return []; }
  }

  function mount(container, opts) {
    opts = opts || {};
    var lang = opts.lang || "es";
    var hasService = !!opts.hasService;
    var onChange = typeof opts.onChange === "function" ? opts.onChange : function () {};

    while (container.firstChild) { container.removeChild(container.firstChild); }

    // --- Modo + indicador de motor ---
    var modeF = field(t(lang, "modeLabel"));
    var row = elem("div", { display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap" });
    var sel = elem("select");
    MODES.forEach(function (m) {
      var o = document.createElement("option");
      o.value = m; o.textContent = t(lang, "mode_" + m);
      sel.appendChild(o);
    });
    sel.value = MODES.indexOf(opts.mode) >= 0 ? opts.mode : "pseudo";
    var badge = elem("span", {
      fontSize: "12px", fontWeight: "600", padding: "3px 10px", borderRadius: "999px",
      whiteSpace: "nowrap",
      border: "1px solid var(--accent, #888)",
      color: hasService ? "var(--on-accent, #fff)" : "var(--accent, #888)",
      background: hasService ? "var(--accent, #888)" : "transparent",
    });
    badge.textContent = hasService ? t(lang, "engineFull") : t(lang, "engineLite");
    row.appendChild(sel); row.appendChild(badge);
    modeF.wrap.appendChild(row);
    if (!hasService) {
      var hint = elem("p", { fontSize: "12px", color: "var(--muted, #777)", margin: "6px 0 0" });
      hint.textContent = t(lang, "engineHint");
      modeF.wrap.appendChild(hint);
    }
    container.appendChild(modeF.wrap);

    // --- Reglas propias (avanzado, plegable) --- opcional (opts.showRules).
    // Apps con su propia UI de reglas (p. ej. Escriba) montan con showRules:false
    // y usan AnonOptions solo para el núcleo (modo + indicador).
    var alwaysIn = null, neverIn = null, patTa = null;
    if (opts.showRules !== false) {
      var det = elem("details", { border: "1px solid var(--border, #ddd)", borderRadius: "var(--radius, 10px)", padding: "0 12px" });
      var sum = elem("summary", { cursor: "pointer", padding: "10px 0", fontSize: "13px", fontWeight: "600", color: "var(--muted-2, var(--text, #333))" });
      sum.textContent = t(lang, "rulesTitle");
      det.appendChild(sum);
      var body = elem("div", { padding: "4px 0 12px", display: "flex", flexDirection: "column", gap: "10px" });

      var alwaysF = field(t(lang, "alwaysLabel"));
      alwaysIn = elem("input"); alwaysIn.type = "text"; alwaysIn.placeholder = t(lang, "listPh");
      alwaysF.wrap.style.margin = "0"; alwaysF.wrap.appendChild(alwaysIn); body.appendChild(alwaysF.wrap);

      var neverF = field(t(lang, "neverLabel"));
      neverIn = elem("input"); neverIn.type = "text"; neverIn.placeholder = t(lang, "listPh");
      neverF.wrap.style.margin = "0"; neverF.wrap.appendChild(neverIn); body.appendChild(neverF.wrap);

      var patF = field(t(lang, "patternsLabel"));
      patTa = elem("textarea", { fontFamily: "ui-monospace, Consolas, monospace", fontSize: "12px", minHeight: "64px", resize: "vertical" });
      patTa.spellcheck = false; patTa.placeholder = t(lang, "patternsHint");
      patF.wrap.style.margin = "0"; patF.wrap.appendChild(patTa); body.appendChild(patF.wrap);

      det.appendChild(body);
      container.appendChild(det);
    }

    function getValues() {
      return {
        mode: sel.value,
        rules: {
          always: alwaysIn ? parseList(alwaysIn.value) : [],
          never: neverIn ? parseList(neverIn.value) : [],
          patterns: patTa ? parsePatterns(patTa.value) : [],
        },
      };
    }
    [sel, alwaysIn, neverIn, patTa].forEach(function (n) {
      if (n) n.addEventListener("change", function () { onChange(getValues()); });
    });

    var api = { getValues: getValues, lang: lang };
    container._anonOptions = api;
    return api;
  }

  global.AnonOptions = {
    mount: mount,
    getValues: function (c) { return c._anonOptions ? c._anonOptions.getValues() : null; },
    MODES: MODES,
  };
})(typeof window !== "undefined" ? window : this);
