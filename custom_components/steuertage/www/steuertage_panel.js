class SteuertagePanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._tab = "calendar";
    this._month = new Date(new Date().getFullYear(), new Date().getMonth(), 1);
    this._selected = null;
    this._calendarEntityId = null;
    this._activeUserId = null;
    this._calendarInitialized = false;
    this._calendarSignature = "";
    this._hasReceivedHass = false;
    this._haThemeVariables = new Set();
    this._events = [];
    this._loadedMonth = "";
    this._busy = false;
    this._message = "";
    this._messageTimer = undefined;
    this._unsubscribe = undefined;
    this._exportEvents = null;
    this._exportKey = "";
    this._exportUnsubscribe = undefined;
    this._exportYear = new Date().getFullYear();
  }

  set hass(hass) {
    this._hass = hass;
    this._applyHomeAssistantTheme();
    const activeUserId = hass?.user?.id || null;
    const userChanged = activeUserId !== this._activeUserId;
    this._activeUserId = activeUserId;
    const calendars = this._calendarEntities();
    const signature = calendars.map((item) => [
      item.entity_id,
      item.attributes.worklog_person_entity,
      item.attributes.worklog_person_name,
      item.attributes.worklog_user_id,
    ].join(":")).join("|");
    const initial = !this._hasReceivedHass;
    const listChanged = signature !== this._calendarSignature;
    let selectionChanged = false;

    if (userChanged && this._hasReceivedHass) {
      const calendar = this._preferredCalendarEntity(calendars);
      this._calendarEntityId = calendar?.entity_id || null;
      this._calendarInitialized = true;
      this._loadedMonth = "";
      this._events = [];
      this._exportEvents = null;
      this._exportKey = "";
      this._selected = null;
      selectionChanged = true;
    } else if (!this._calendarInitialized && calendars.length) {
      const calendar = this._calendarEntity();
      this._calendarEntityId = calendar?.entity_id || null;
      this._calendarInitialized = true;
      this._loadedMonth = "";
      this._events = [];
      selectionChanged = true;
    } else if (
      this._calendarEntityId &&
      !calendars.some((item) => item.entity_id === this._calendarEntityId)
    ) {
      this._calendarEntityId = null;
      this._loadedMonth = "";
      this._events = [];
      selectionChanged = true;
    }

    this._calendarSignature = signature;
    this._hasReceivedHass = true;
    if (initial || listChanged || selectionChanged || this._tab === "config") {
      this._render();
    }
    if (this._tab === "calendar" && (initial || listChanged || selectionChanged)) {
      this._loadEvents();
    }
  }

  _applyHomeAssistantTheme() {
    const applied = new Map();
    const readVariables = (element) => {
      if (!element) return;
      const computed = getComputedStyle(element);
      for (let i = 0; i < computed.length; i++) {
        const name = computed[i];
        if (name.startsWith('--')) {
          const value = computed.getPropertyValue(name).trim();
          if (value) applied.set(name, value);
        }
      }
    };
    readVariables(document.documentElement);
    readVariables(document.body);
    readVariables(this.parentElement);
    const themes = this._hass?.themes;
    const themeName = themes?.theme;
    const isDark = Boolean(themes?.darkMode);
    const themeDefinition = themes?.themes?.[themeName] || {};
    const { modes, ...common } = themeDefinition;
    for (const [name, value] of Object.entries(common)) {
      if (typeof value === 'string') applied.set('--' + name, value);
    }
    const modeValues = modes?.[isDark ? 'dark' : 'light'] || {};
    for (const [name, value] of Object.entries(modeValues)) {
      if (typeof value === 'string') applied.set('--' + name, value);
    }
    if (themeName === 'default') {
      const selected = this._hass?.selectedTheme || {};
      if (selected.primaryColor) applied.set('--primary-color', selected.primaryColor);
      if (selected.accentColor) applied.set('--accent-color', selected.accentColor);
    }
    for (const name of this._haThemeVariables) {
      if (!applied.has(name)) this.style.removeProperty(name);
    }
    for (const [name, value] of applied) this.style.setProperty(name, value);
    this._haThemeVariables = new Set(applied.keys());
    this.style.colorScheme = isDark ? 'dark' : 'light';
  }
  set narrow(value) {
    this._narrow = value;
    this._render();
  }

  set panel(value) {
    this._panel = value;
  }

  _isoDate(date) {
    return [date.getFullYear(), String(date.getMonth() + 1).padStart(2, "0"), String(date.getDate()).padStart(2, "0")].join("-");
  }

  _calendarEntities() {
    return Object.values(this._hass?.states || {})
      .filter((item) => item.entity_id.startsWith("calendar.") &&
        item.attributes.worklog_person_entity)
      .sort((a, b) =>
        (a.attributes.worklog_person_name || a.entity_id).localeCompare(
          b.attributes.worklog_person_name || b.entity_id,
          this._hass?.locale?.language || "de-DE"
        )
      );
  }

  _preferredCalendarEntity(calendars = this._calendarEntities()) {
    return calendars.find((item) => item.attributes.worklog_user_id &&
      item.attributes.worklog_user_id === this._activeUserId) ||
      calendars.find((item) => this._calendarLabel(item).trim().toLocaleLowerCase() ===
        (this._hass?.user?.name || "").trim().toLocaleLowerCase()) ||
      (calendars.length === 1 ? calendars[0] : undefined);
  }

  _calendarEntity() {
    const calendars = this._calendarEntities();
    return calendars.find((item) => item.entity_id === this._calendarEntityId) ||
      this._preferredCalendarEntity(calendars);
  }

  _calendarLabel(calendar) {
    return calendar.attributes.worklog_person_name ||
      calendar.attributes.friendly_name ||
      calendar.entity_id;
  }

  async _loadEvents() {
    const calendar = this._calendarEntity();
    const entityId = calendar?.entity_id;
    const monthKey = entityId + ":" + this._isoDate(this._month);
    if (!entityId) {
      if (this._unsubscribe) {
        const unsubscribe = this._unsubscribe;
        this._unsubscribe = undefined;
        await unsubscribe();
      }
      this._loadedMonth = "";
      this._events = [];
      this._render();
      return;
    }
    if (this._loadedMonth === monthKey || !this._hass?.connection) return;
    this._loadedMonth = monthKey;
    if (this._unsubscribe) {
      const unsubscribe = this._unsubscribe;
      this._unsubscribe = undefined;
      await unsubscribe();
    }
    this._events = [];
    this._render();
    const start = new Date(this._month.getFullYear(), this._month.getMonth(), 1);
    const end = new Date(this._month.getFullYear(), this._month.getMonth() + 1, 1);
    try {
      this._unsubscribe = await this._hass.connection.subscribeMessage(
        (message) => {
          if (this._calendarEntityId !== entityId) return;
          this._events = Array.isArray(message?.events)
            ? message.events
            : Array.isArray(message?.event?.events)
              ? message.event.events
              : [];
          this._render();
        },
        {
          type: "calendar/event/subscribe",
          entity_id: entityId,
          start: start.toISOString(),
          end: end.toISOString(),
        }
      );
    } catch (error) {
      this._loadedMonth = "";
      this._message = "Der Kalender konnte nicht geladen werden.";
      this._render();
    }
  }

  _type(event) {
    const summary = (event?.summary || "").toLowerCase();
    if (summary.includes("büro- und")) return "office_and_home_office";
    if (summary.includes("homeoffice")) return "home_office";
    if (summary.includes("bürotag")) return "office";
    if (summary.includes("urlaub")) return "vacation";
    if (summary.includes("krankheit")) return "sick_leave";
    if (summary.includes("prüfen")) return "needs_review";
    if (summary.includes("erkennung läuft")) return "tracking";
    if (summary.includes("arbeitstag")) return "no_work";
    return "";
  }

  _label(type) {
    return ({
      no_work: "Kein Arbeitstag",
      tracking: "Erkennung läuft",
      home_office: "Homeoffice-Tag",
      office: "Bürotag",
      office_and_home_office: "Büro- und Homeoffice-Signale",
      needs_review: "Bitte prüfen",
      vacation: "Urlaub",
      sick_leave: "Krankheit",
    })[type] || "Noch kein Eintrag";
  }

  _eventForDay(day) {
    if (!day) return undefined;
    return this._events.find((event) => (event.start || "").slice(0, 10) === day);
  }

  _changeHistory(event) {
    const marker = "STEUERTAGE_HISTORY:";
    const description = event?.description || "";
    const index = description.indexOf(marker);
    if (index < 0) return [];
    try {
      const history = JSON.parse(description.slice(index + marker.length));
      return Array.isArray(history) ? history : [];
    } catch (error) {
      return [];
    }
  }

  _monthStats() {
    const prefix = this._isoDate(this._month).slice(0, 7);
    const days = new Map();
    this._events.forEach((event) => {
      const date = (event.start || "").slice(0, 10);
      if (!date.startsWith(prefix)) return;
      const type = this._type(event);
      if (!type) return;
      if (!days.has(date)) days.set(date, new Set());
      days.get(date).add(type);
    });
    const entries = [...days.values()];
    const workTypes = new Set(["office", "home_office", "office_and_home_office"]);
    return {
      workdays: entries.filter((types) => [...types].some((type) => workTypes.has(type))).length,
      office: entries.filter((types) => types.has("office") || types.has("office_and_home_office")).length,
      homeOffice: entries.filter((types) => types.has("home_office") || types.has("office_and_home_office")).length,
      vacation: entries.filter((types) => types.has("vacation")).length,
      sick: entries.filter((types) => types.has("sick_leave")).length,
    };
  }

  _showMessage(message) {
    if (this._messageTimer) clearTimeout(this._messageTimer);
    this._message = message;
    this._render();
    this._messageTimer = setTimeout(() => {
      this._message = "";
      this._messageTimer = undefined;
      this._render();
    }, 3000);
  }

  _escape(value) {
    return String(value).replace(/[&<>"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[char]);
  }

  _configMarkup(calendars) {
    const cards = calendars.map((calendar) => {
      const a = calendar.attributes || {};
      const rows = [["Person", a.worklog_person_entity], ["Home-Zone", a.worklog_home_zone_entity],
        ["Büro-Zone", a.worklog_office_zone_entity || "Nicht eingerichtet"],
        ["Homeoffice-Tracker", a.worklog_device_tracker || a.worklog_legacy_signal || "Nicht eingerichtet"],
        ["HA-Benutzer", a.worklog_user_name || "Automatische Zuordnung"]];
      return "<section class='config-card'><div class='config-title'><h3>" + this._escape(this._calendarLabel(calendar)) +
        "</h3><a href='/config/integrations/integration/steuertage#config_entry=" + encodeURIComponent(a.worklog_entry_id || "") +
        "'>Einstellungen öffnen</a></div><dl>" + rows.map(([k,v]) => "<div><dt>" + k + "</dt><dd>" +
        this._escape(v || "Nicht eingerichtet") + "</dd></div>").join("") + "</dl></section>";
    }).join("");
    return "<ha-card><h2>Konfigurator</h2><p>Hier siehst du die aktuellen Werte je Person. Über „Einstellungen öffnen“ kannst du sie in Home Assistant ändern.</p>" +
      (cards || "<p>Richte zuerst eine Person über Einstellungen → Geräte &amp; Dienste → Integration hinzufügen → Steuertage ein.</p>") +
      "<section class='info-card'><h3>So funktioniert die automatische Erkennung</h3><p>Steuertage sammelt Bürozeit und Homeoffice-Zeit getrennt im Hintergrund. Im Kalender werden keine Stunden angezeigt.</p><ul>" +
      "<li><b>Büro:</b> Die Person befindet sich in der ausgewählten Büro-Zone.</li><li><b>Homeoffice:</b> Die Person und der ausgewählte Tracker sind beide in der Home-Zone.</li>" +
      "<li>In dieser Beta zählt das jeweilige Signal ab <b>30 Minuten</b>. Büro und Homeoffice können am selben Tag beide erkannt werden.</li>" +
      "<li>Bis dahin erscheint „Erkennung läuft“. Bei fehlenden oder nicht verfügbaren Quellen erscheint „Bitte prüfen“.</li>" +
      "<li>Urlaub, Krankheit und abweichende Erkennung kannst du im Kalender manuell setzen. Der Änderungsverlauf dokumentiert Änderungen.</li></ul><p>Der Schwellwert ist in der Beta fest auf 30 Minuten eingestellt.</p></section></ha-card>";
  }

  _exportRows() {
    const byDate = new Map();
    (this._exportEvents || []).forEach((event) => {
      const date = (event.start || "").slice(0, 10);
      if (date.startsWith(String(this._exportYear) + "-") && !byDate.has(date)) byDate.set(date, event);
    });
    return [...byDate.entries()].sort((a,b) => a[0].localeCompare(b[0])).map(([date,event]) => ({
      date, type: this._type(event), label: this._label(this._type(event)),
      manual: (event.description || "").includes("Manuell geändert"),
    }));
  }

  _exportMarkup(calendars) {
    const rows = this._exportEvents;
    const counts = { office: 0, home_office: 0, office_and_home_office: 0, sick_leave: 0, vacation: 0, needs_review: 0, tracking: 0 };
    (rows || []).forEach((event) => { const t = this._type(event); if (t in counts) counts[t]++; });
    const stat = (label,value) => "<div class='stat'><span>" + label + "</span><strong>" + value + "</strong></div>";
    const person = calendars.length > 1 ? "<label>Person <select data-export-calendar>" + calendars.map((item) =>
      "<option value='" + item.entity_id + "' " + (item.entity_id === this._calendarEntityId ? "selected" : "") + ">" +
      this._escape(this._calendarLabel(item)) + "</option>").join("") + "</select></label>" : "";
    let table = "<p>Lade gespeicherte Tage …</p>";
    if (rows !== null) {
      const list = this._exportRows();
      table = list.length ? "<div class='table-wrap'><table><thead><tr><th>Datum</th><th>Erkannter Typ</th><th>Hinweis</th></tr></thead><tbody>" +
        list.map((r) => "<tr class='" + (r.type === "needs_review" ? "needs-review" : r.type === "tracking" ? "tracking-row" : "") +
        "'><td>" + r.date + "</td><td>" + this._escape(r.label) + (r.manual ? " <span class='manual-tag'>Manuell geändert</span>" : "") +
        "</td><td>" + (r.type === "needs_review" ? "<button class='text-button' data-review-date='" + r.date + "'>Bitte im Kalender prüfen</button>" :
        r.type === "tracking" ? "Erkennung noch nicht abgeschlossen" : "—") + "</td></tr>").join("") + "</tbody></table></div>" :
        "<p>Für dieses Jahr sind noch keine gespeicherten Tage vorhanden.</p>";
    }
    return "<ha-card><h2>Export</h2><div class='export-controls'>" + person +
      "<label>Jahr <input data-export-year type='number' min='2000' max='2100' value='" + this._exportYear + "'></label>" +
      "<button class='export-button' data-download='csv' " + (rows === null ? "disabled" : "") + ">CSV herunterladen</button>" +
      "<button class='export-button' data-download='txt' " + (rows === null ? "disabled" : "") + ">TXT herunterladen</button>" +
      "<button class='export-button' data-download='html' " + (rows === null ? "disabled" : "") + ">HTML herunterladen</button></div>" +
      "<p class='disclaimer'>Steuertage unterstützt lediglich die automatische Erfassung relevanter Daten auf Grundlage der in Home Assistant vorhandenen Erkennung. Für Richtigkeit und Vollständigkeit Ihrer Steuererklärung tragen Sie die volle Verantwortung. Alle Angaben ohne Gewähr.</p><p class='muted'>„Büro + Homeoffice“ zählt als eigene Kategorie und als ein Arbeitstag. Nur durch diese App erfasste Tage können in der Auswertung berücksichtigt werden.</p>" +
      (rows === null ? table : "<div class='stats export-stats'>" + stat("Bürotage",counts.office) + stat("Homeoffice-Tage",counts.home_office) +
      stat("Büro + Homeoffice",counts.office_and_home_office) + stat("Krankheitstage",counts.sick_leave) + stat("Urlaubstage",counts.vacation) +
      stat("Arbeitstage gesamt",counts.office+counts.home_office+counts.office_and_home_office) + stat("Bitte prüfen",counts.needs_review) +
      stat("Erkennung läuft",counts.tracking) + "</div>" + table) + "</ha-card>";
  }

  async _loadExportEvents() {
    const entity = this._calendarEntity(), entityId = entity?.entity_id;
    const key = entityId + ":" + this._exportYear;
    if (!entityId || !this._hass?.connection) { this._exportEvents = []; this._render(); return; }
    if (key === this._exportKey && this._exportEvents !== null) return;
    this._exportKey = key; this._exportEvents = null; this._render();
    if (this._exportUnsubscribe) { const stop = this._exportUnsubscribe; this._exportUnsubscribe = undefined; await stop(); }
    const start = new Date(this._exportYear, 0, 1), end = new Date(this._exportYear + 1, 0, 1);
    try {
      this._exportUnsubscribe = await this._hass.connection.subscribeMessage((message) => {
        if (this._calendarEntityId !== entityId || this._exportYear !== start.getFullYear()) return;
        this._exportEvents = Array.isArray(message?.events) ? message.events :
          Array.isArray(message?.event?.events) ? message.event.events : [];
        this._render();
      }, { type: "calendar/event/subscribe", entity_id: entityId, start: start.toISOString(), end: end.toISOString() });
    } catch (error) { this._exportEvents = []; this._render(); }
  }

  _downloadExport(format) {
    const person = this._calendarLabel(this._calendarEntity() || {attributes:{},entity_id:""});
    const rows = this._exportRows();
    const c = {office:0,home_office:0,office_and_home_office:0,sick_leave:0,vacation:0,needs_review:0,tracking:0};
    rows.forEach((r) => { if (r.type in c) c[r.type]++; });
    const total = c.office+c.home_office+c.office_and_home_office;
    const headers = ["Datum","Tagestyp","Manuell geändert","Hinweis"];
    const values = rows.map((r) => [r.date,r.label,r.manual?"Ja":"Nein",r.type==="needs_review"?"Bitte im Kalender prüfen":r.type==="tracking"?"Erkennung noch nicht abgeschlossen":""]);
    const esc = (v) => String(v ?? "").replace(/[&<>"]/g, (x) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[x]));
    let content, mime = "text/plain;charset=utf-8";
    const summary = [["Bürotage",c.office],["Homeoffice-Tage",c.home_office],["Büro + Homeoffice",c.office_and_home_office],["Krankheitstage",c.sick_leave],["Urlaubstage",c.vacation],["Arbeitstage gesamt",total],["Bitte prüfen",c.needs_review],["Erkennung läuft",c.tracking]];
    if (format === "csv") {
      content = "\ufeff" + [["Steuertage",this._exportYear,person],["Hinweis","Nur durch diese App erfasste Tage können in der Auswertung berücksichtigt werden."],["Verantwortung","Steuertage unterstützt lediglich die automatische Erfassung relevanter Daten auf Grundlage der in Home Assistant vorhandenen Erkennung. Für Richtigkeit und Vollständigkeit Ihrer Steuererklärung tragen Sie die volle Verantwortung. Alle Angaben ohne Gewähr."],[],...summary,[],headers,...values].map((line) => line.map((v) => '"' + String(v ?? "").replace(/"/g,'""') + '"').join(";")).join("\r\n");
      mime = "text/csv;charset=utf-8";
    } else if (format === "html") {
      content = "<!doctype html><html lang='de'><meta charset='utf-8'><title>Steuertage " + this._exportYear + "</title><style>body{font:16px system-ui,sans-serif;max-width:1000px;margin:2rem auto;padding:0 1rem;color:#222}table{border-collapse:collapse;width:100%}th,td{text-align:left;border-bottom:1px solid #ddd;padding:.55rem}.notice{background:#fff4d5}li{margin:.3rem 0}</style><h1>Steuertage " + this._exportYear + " – " + esc(person) + "</h1><h2>Übersicht</h2><ul>" +
        summary.map((x) => "<li>" + esc(x[0]) + ": " + x[1] + "</li>").join("") + "</ul><h2>Tage</h2><table><thead><tr>" +
        headers.map((x) => "<th>" + esc(x) + "</th>").join("") + "</tr></thead><tbody>" + rows.map((r) => "<tr class='" +
        (r.type === "needs_review" || r.type === "tracking" ? "notice" : "") + "'><td>" + esc(r.date) + "</td><td>" + esc(r.label) +
        "</td><td>" + (r.manual?"Ja":"Nein") + "</td><td>" + esc(r.type === "needs_review"?"Bitte im Kalender prüfen":r.type === "tracking"?"Erkennung noch nicht abgeschlossen":"") +
        "</td></tr>").join("") + "</tbody></table><p>Nur durch diese App erfasste Tage können in der Auswertung berücksichtigt werden.</p><p>Steuertage unterstützt lediglich die automatische Erfassung relevanter Daten auf Grundlage der in Home Assistant vorhandenen Erkennung. Für Richtigkeit und Vollständigkeit Ihrer Steuererklärung tragen Sie die volle Verantwortung. Alle Angaben ohne Gewähr.</p></html>";
      mime = "text/html;charset=utf-8";
    } else {
      content = "Steuertage " + this._exportYear + " – " + person + "\n\n" + summary.map((x) => x[0] + ": " + x[1]).join("\n") +
        "\n\n" + headers.join(" | ") + "\n" + values.map((r) => r.join(" | ")).join("\n") +
        "\n\nNur durch diese App erfasste Tage können in der Auswertung berücksichtigt werden.\n\nSteuertage unterstützt lediglich die automatische Erfassung relevanter Daten auf Grundlage der in Home Assistant vorhandenen Erkennung. Für Richtigkeit und Vollständigkeit Ihrer Steuererklärung tragen Sie die volle Verantwortung. Alle Angaben ohne Gewähr.";
    }
    const url = URL.createObjectURL(new Blob([content], {type:mime}));
    const link = document.createElement("a"); link.href=url; link.download="steuertage-"+this._exportYear+"."+format; link.click();
    setTimeout(() => URL.revokeObjectURL(url),1000);
  }

  _render() {
    if (!this._hass) return;
    const locale = this._hass.locale?.language || "de-DE";
    const title = new Intl.DateTimeFormat(locale, { month: "long", year: "numeric" }).format(this._month);
    const selectedEvent = this._eventForDay(this._selected);
    const monthStats = this._monthStats();
    const selectedType = this._type(selectedEvent);
    const monthStart = new Date(this._month.getFullYear(), this._month.getMonth(), 1);
    const offset = (monthStart.getDay() + 6) % 7;
    const gridStart = new Date(monthStart.getFullYear(), monthStart.getMonth(), 1 - offset);
    const dayNames = new Intl.DateTimeFormat(locale, { weekday: "short" });
    let headers = "";
    for (let i = 0; i < 7; i++) {
      const weekday = new Date(2024, 0, 1 + i);
      const weekendLabel = i >= 5 ? " weekend-label" : "";
      headers += "<div class='weekday" + weekendLabel + "'>" + dayNames.format(weekday) + "</div>";
    }
    let cells = "";
    for (let i = 0; i < 42; i++) {
      const d = new Date(gridStart.getFullYear(), gridStart.getMonth(), gridStart.getDate() + i);
      const iso = this._isoDate(d);
      const event = this._eventForDay(iso);
      const type = this._type(event);
      const isWeekend = d.getDay() === 0 || d.getDay() === 6;
      const manuallyChanged = (event?.description || "").includes("Manuell geändert");
      const cls = ["day", isWeekend ? "weekend" : "", type ? "type-" + type : "", manuallyChanged ? "manual" : "", d.getMonth() !== this._month.getMonth() ? "outside" : "", iso === this._selected ? "selected" : ""].filter(Boolean).join(" ");
      cells += "<button class='" + cls + "' data-date='" + iso + "' aria-label='" + iso + (event ? ": " + this._label(type) : "") + (manuallyChanged ? ", manuell geändert" : "") + "'>" + d.getDate() + "</button>";
    }
    const states = Object.values(this._hass.states || {});
    const sensorLines = states.filter((item) => item.entity_id.startsWith("sensor.") &&
      /tagestyp|erkennungszeit/i.test((item.attributes.friendly_name || "") + " " + item.entity_id))
      .map((item) => "<li>" + this._escape(item.attributes.friendly_name || item.entity_id) + ": " + this._escape(item.state) + "</li>").join("");
    const calendars = this._calendarEntities();
    const calendarTabs = calendars.length > 1
      ? "<div class='person-tabs' role='group' aria-label='Kalender auswählen'>" + calendars.map((item) =>
          "<button type='button' class='person-tab' data-calendar='" + item.entity_id + "' aria-pressed='" +
          (item.entity_id === this._calendarEntityId ? "true" : "false") + "'>" +
          this._escape(this._calendarLabel(item)) + "</button>"
        ).join("") + "</div>"
      : "";
    const selectedHistory = this._changeHistory(selectedEvent);
    const selectedHistoryMarkup = selectedHistory.length
      ? "<details class='change-history'><summary>Änderungsverlauf (" + selectedHistory.length + ")</summary><ul>" + selectedHistory.map((change) => {
          const displayTime = change.timestamp ? new Intl.DateTimeFormat(locale, { dateStyle: "short", timeStyle: "short" }).format(new Date(change.timestamp)) : "";
          const who = this._escape(change.changed_by_name || change.changed_by || "Home Assistant");
          const from = this._escape(this._label(change.old_value));
          const to = this._escape(this._label(change.new_value));
          return "<li><time>" + this._escape(displayTime) + "</time> · " + who + ": " + from + " → " + to + "</li>";
        }).join("") + "</ul></details>"
      : "";
    const tab = this._tab;
    const content = tab === "calendar"
      ? (this._calendarEntity() ? "<ha-card>" + calendarTabs + "<div class='calendar-head'><button class='month-nav' data-action='prev' aria-label='Vorheriger Monat'>‹</button><h2>" + title + "</h2><button class='today-nav' data-action='today' aria-label='Zum heutigen Datum springen'>Heute</button><button class='month-nav' data-action='next' aria-label='Nächster Monat'>›</button></div><div class='stats'>" + [{ label: "Arbeitstage", value: monthStats.workdays }, { label: "Büro", value: monthStats.office }, { label: "Homeoffice", value: monthStats.homeOffice }, { label: "Urlaub", value: monthStats.vacation }, { label: "Krankheit", value: monthStats.sick }].map((item) => "<div class='stat'><span>" + item.label + "</span><strong>" + item.value + "</strong></div>").join("") + "</div><div class='grid'>" + headers + cells + "</div><div class='legend'><span><i class='legend-dot office-dot'></i>Büro</span><span><i class='legend-dot home-dot'></i>Homeoffice</span><span><i class='legend-dot vacation-dot'></i>Urlaub</span><span><i class='legend-dot sick-dot'></i>Krankheit</span><span><i class='legend-dot tracking-dot'></i>Erkennung läuft</span><span><i class='legend-dot no-work-dot'></i>Kein Arbeitstag</span><span><i class='legend-dot manual-dot'></i>Manuell geändert</span></div>" + (this._selected ? "<div class='selection'><h3>" + this._selected + "</h3><p>" + this._label(selectedType) + (selectedEvent?.description?.includes('Manuell geändert') ? " · manuell geändert" : "") + "</p><div class='actions'><button data-type='office'>Bürotag</button><button data-type='home_office'>Homeoffice</button><button data-type='no_work'>Kein Arbeitstag</button><button data-type='vacation'>Urlaub</button><button data-type='sick_leave'>Krankheit</button><button data-type='automatic'>Automatisch</button></div>" + selectedHistoryMarkup + "<p class='message'>" + this._message + "</p></div>" : "") + "</ha-card>" : calendars.length > 1 ? "<ha-card>" + calendarTabs + "<p>Bitte wähle eine Person aus, um den Kalender zu öffnen.</p></ha-card>" : "<ha-card><p>Es ist noch keine Person für Steuertage eingerichtet.</p></ha-card>")
      : tab === "config" ? this._configMarkup(calendars) : this._exportMarkup(calendars);
    this.shadowRoot.innerHTML = "<style>:host{display:block;color:var(--primary-text-color,CanvasText);background:var(--primary-background-color,Canvas);min-height:100vh;font-family:var(--paper-font-body1_-_font-family,Roboto,Noto,sans-serif)}.page{max-width:1050px;margin:auto;padding:24px}.top{display:flex;align-items:center;gap:12px;margin-bottom:16px}.brand{display:grid;gap:2px}.top h1{font-size:24px;font-weight:500;margin:0}.brand p{margin:0;color:var(--secondary-text-color);font-size:14px}.tabs{display:flex;gap:8px;border-bottom:1px solid var(--divider-color);margin-bottom:20px}.tabs button,.actions button,.month-nav,.today-nav{font:inherit;color:var(--primary-text-color);background:var(--ha-card-background,var(--card-background-color,Canvas));border:1px solid var(--divider-color);border-radius:8px;padding:9px 14px;cursor:pointer}.tabs button.active{color:var(--primary-color);border-color:var(--primary-color)}ha-card{display:block;background:var(--card-background-color);color:var(--primary-text-color);border-radius:12px;padding:20px;box-shadow:var(--ha-card-box-shadow,0 2px 8px rgba(0,0,0,.12))}.calendar-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}.calendar-head h2{font-size:20px;font-weight:500;margin:0;text-transform:capitalize}.grid{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:6px}.weekday{text-align:center;color:var(--secondary-text-color);font-size:13px;padding:8px 0}.legend{display:flex;flex-wrap:wrap;gap:8px 16px;margin-top:14px;color:var(--secondary-text-color);font-size:13px}.legend span{display:inline-flex;align-items:center;gap:6px}.legend-dot{width:11px;height:11px;border-radius:50%;display:inline-block}.office-dot{background:var(--info-color,#039be5)}.home-dot{background:var(--success-color,#43a047)}.vacation-dot{background:var(--warning-color,#fbc02d)}.sick-dot{background:var(--error-color,#db4437)}.tracking-dot{background:var(--state-icon-color,#9e9e9e)}.no-work-dot{background:var(--divider-color,#9e9e9e)}.weekday.weekend-label{color:var(--warning-color,var(--primary-color));font-weight:600}.day{position:relative;min-height:44px;border:1px solid var(--divider-color);border-radius:8px;background:var(--card-background-color);color:var(--primary-text-color);font:inherit;cursor:pointer}.day.weekend{background:var(--secondary-background-color,var(--card-background-color));border-bottom:3px solid var(--warning-color,var(--primary-color))}.day.outside{opacity:.45}.day.selected{outline:2px solid var(--primary-color)}.day.manual::after{content:'';position:absolute;top:4px;right:4px;width:6px;height:6px;border-radius:50%;background:var(--primary-text-color);opacity:.8;box-shadow:0 0 0 1px var(--card-background-color)}.manual-dot{background:var(--primary-text-color);opacity:.7}.person-tabs{display:flex;gap:8px;margin:0 0 16px;border-bottom:1px solid var(--divider-color)}.person-tab{font:inherit;color:var(--secondary-text-color);background:transparent;border:0;border-bottom:2px solid transparent;padding:10px 14px;cursor:pointer}.person-tab[aria-pressed='true']{color:var(--primary-color);border-bottom-color:var(--primary-color);font-weight:600}.config-card,.info-card{border:1px solid var(--divider-color);border-radius:10px;padding:16px;margin:14px 0}.config-title{display:flex;justify-content:space-between;align-items:center;gap:12px}.config-title h3,.info-card h3{margin:0 0 8px;font-size:17px;font-weight:500}.config-title a{color:var(--primary-color)}dl{margin:10px 0 0}.config-card dl>div{display:grid;grid-template-columns:minmax(130px,1fr) 2fr;gap:10px;padding:7px 0;border-top:1px solid var(--divider-color)}dt{color:var(--secondary-text-color)}dd{margin:0;overflow-wrap:anywhere}.info-card li{margin:8px 0}.export-controls{display:flex;align-items:end;flex-wrap:wrap;gap:10px;margin:16px 0}.export-controls label{display:grid;gap:5px;color:var(--secondary-text-color)}.export-controls input,.export-controls select,.export-button{font:inherit;color:var(--primary-text-color);background:var(--card-background-color);border:1px solid var(--divider-color);border-radius:7px;padding:9px 12px}.export-button{cursor:pointer}.export-button:disabled{opacity:.5;cursor:wait}.export-stats{grid-template-columns:repeat(4,minmax(0,1fr));margin-top:16px}.muted{color:var(--secondary-text-color);font-size:13px}.disclaimer{margin-top:16px;padding:12px 14px;border-inline-start:3px solid var(--warning-color,var(--primary-color));background:var(--secondary-background-color,var(--card-background-color,Canvas));color:var(--secondary-text-color);font-size:13px;line-height:1.5}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;margin-top:12px}th,td{text-align:left;padding:10px;border-bottom:1px solid var(--divider-color)}th{color:var(--secondary-text-color);font-weight:500}.needs-review{background:var(--secondary-background-color)}.tracking-row{background:var(--secondary-background-color)}.manual-tag{display:inline-block;border-radius:10px;background:var(--secondary-background-color);padding:2px 7px;font-size:12px;color:var(--secondary-text-color)}.text-button{border:0;background:transparent;color:var(--primary-color);font:inherit;cursor:pointer;padding:0}.change-history{margin-top:12px;color:var(--secondary-text-color)}.change-history ul{padding-left:20px}.change-history time{font-variant-numeric:tabular-nums}.day.type-office,.day.type-office_and_home_office{background:var(--info-color,#039be5);color:var(--text-primary-color,#fff)}.day.type-home_office{background:var(--success-color,#43a047);color:var(--text-primary-color,#fff)}.day.type-vacation{background:var(--warning-color,#fbc02d);color:var(--primary-text-color)}.day.type-sick_leave,.day.type-needs_review{background:var(--error-color,#db4437);color:var(--text-primary-color,#fff)}.day.type-tracking{background:var(--state-icon-color,#9e9e9e)}.stats{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px;margin:0 0 16px}.stat{display:flex;flex-direction:column;gap:4px;background:var(--secondary-background-color,var(--card-background-color));border-radius:8px;padding:10px 12px}.stat span{color:var(--secondary-text-color);font-size:12px}.stat strong{font-size:20px;font-weight:500}.selection{border-top:1px solid var(--divider-color);margin-top:20px;padding-top:12px}.selection h3{font-size:17px;margin:0 0 6px}.selection p{color:var(--secondary-text-color)}.actions{display:flex;flex-wrap:wrap;gap:8px}.actions button{padding:8px 10px}.message:empty{display:none}.message{min-height:1em}ha-card>h2{font-weight:500}.page li{margin:8px 0}@media(max-width:600px){.page{padding:12px}.day{min-height:38px}.stats{grid-template-columns:repeat(2,minmax(0,1fr))}.export-stats{grid-template-columns:repeat(2,minmax(0,1fr))}.config-title{align-items:flex-start;flex-direction:column}.grid{gap:3px}.tabs{overflow-x:auto}.tabs button{white-space:nowrap;padding:8px 10px}}</style><div class='page'><div class='top'><ha-menu-button></ha-menu-button><div class='brand'><h1>Steuertage</h1><p>Büro- und Homeoffice-Tage für die Steuererklärung</p></div></div><div class='tabs'><button data-tab='calendar' class='" + (tab === "calendar" ? "active" : "") + "'>Kalender</button><button data-tab='config' class='" + (tab === "config" ? "active" : "") + "'>Konfigurator</button><button data-tab='export' class='" + (tab === "export" ? "active" : "") + "'>Export</button></div>" + content + "</div>";
    const menu = this.shadowRoot.querySelector("ha-menu-button");
    if (menu) menu.hass = this._hass;
    this.shadowRoot.querySelectorAll("[data-tab]").forEach((button) => button.addEventListener("click", () => {
      this._tab = button.dataset.tab;
      this._render();
      if (this._tab === "calendar") this._loadEvents();
      if (this._tab === "export") this._loadExportEvents();
    }));
    this.shadowRoot.querySelectorAll("[data-date]").forEach((button) => button.addEventListener("click", () => {
      this._selected = button.dataset.date;
      this._render();
    }));
    this.shadowRoot.querySelector("[data-action='prev']")?.addEventListener("click", () => {
      this._month = new Date(this._month.getFullYear(), this._month.getMonth() - 1, 1);
      this._selected = null;
      this._loadedMonth = "";
      this._render();
      this._loadEvents();
    });
    this.shadowRoot.querySelector("[data-action='today']")?.addEventListener("click", () => {
      const today = new Date();
      const currentMonth = new Date(today.getFullYear(), today.getMonth(), 1);
      if (this._isoDate(currentMonth) !== this._isoDate(this._month)) this._loadedMonth = "";
      this._month = currentMonth;
      this._selected = this._isoDate(today);
      this._render();
      this._loadEvents();
    });
    this.shadowRoot.querySelector("[data-action='next']")?.addEventListener("click", () => {
      this._month = new Date(this._month.getFullYear(), this._month.getMonth() + 1, 1);
      this._selected = null;
      this._loadedMonth = "";
      this._render();
      this._loadEvents();
    });
    this.shadowRoot.querySelectorAll("[data-calendar]").forEach((button) => button.addEventListener("click", async () => {
      const nextCalendar = button.dataset.calendar;
      if (nextCalendar === this._calendarEntityId) return;
      this._calendarEntityId = nextCalendar;
      this._calendarInitialized = true;
      this._loadedMonth = "";
      this._events = [];
      this._selected = null;
      this._render();
      await this._loadEvents();
    }));
    this.shadowRoot.querySelector("[data-export-year]")?.addEventListener("change", () => {
      const value = Number(this.shadowRoot.querySelector("[data-export-year]").value);
      if (!Number.isInteger(value) || value < 2000 || value > 2100) return;
      this._exportYear = value; this._exportKey = ""; this._exportEvents = null; this._loadExportEvents();
    });
    this.shadowRoot.querySelector("[data-export-calendar]")?.addEventListener("change", (event) => {
      this._calendarEntityId = event.target.value; this._calendarInitialized = true;
      this._loadedMonth = ""; this._events = []; this._exportKey = ""; this._exportEvents = null;
      this._selected = null; this._render();
      if (this._tab === "calendar") this._loadEvents();
      if (this._tab === "export") this._loadExportEvents();
    });
    this.shadowRoot.querySelectorAll("[data-download]").forEach((button) => button.addEventListener("click", () => this._downloadExport(button.dataset.download)));
    this.shadowRoot.querySelectorAll("[data-review-date]").forEach((button) => button.addEventListener("click", () => {
      const parts = button.dataset.reviewDate.split("-").map(Number);
      this._month = new Date(parts[0], parts[1] - 1, 1); this._selected = button.dataset.reviewDate;
      this._tab = "calendar"; this._loadedMonth = ""; this._render(); this._loadEvents();
    }));
    this.shadowRoot.querySelectorAll("[data-type]").forEach((button) => button.addEventListener("click", async () => {
      if (this._busy) return;
      const selectedCalendar = this._calendarEntity();
      const personEntity = selectedCalendar?.attributes.worklog_person_entity;
      this._busy = true;
      this._message = "Speichere Änderung …";
      this._render();
      try {
        await this._hass.callService("steuertage", "set_day_override", {
          person_entity: personEntity,
          date: this._selected,
          day_type: button.dataset.type,
        });
        this._loadedMonth = "";
        await this._loadEvents();
        this._showMessage("Änderung gespeichert.");
      } catch (error) {
        this._showMessage("Änderung konnte nicht gespeichert werden.");
      } finally {
        this._busy = false;
        this._render();
      }
    }));
  }
}

customElements.define("steuertage-panel", SteuertagePanel);
