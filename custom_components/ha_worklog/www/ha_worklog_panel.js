class HAWorklogPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._tab = "calendar";
    this._month = new Date(new Date().getFullYear(), new Date().getMonth(), 1);
    this._selected = null;
    this._calendarEntityId = null;
    this._calendarInitialized = false;
    this._haThemeVariables = new Set();
    this._events = [];
    this._loadedMonth = "";
    this._busy = false;
    this._message = "";
    this._messageTimer = undefined;
    this._unsubscribe = undefined;
  }

  set hass(hass) {
    this._hass = hass;
    this._applyTheme(hass);
    const calendars = this._calendarEntities();
    if (!this._calendarInitialized && calendars.length) {
      const calendar = this._calendarEntity();
      this._calendarEntityId = calendar?.entity_id || null;
      this._calendarInitialized = true;
      this._loadedMonth = "";
      this._events = [];
    } else if (
      this._calendarEntityId &&
      !calendars.some((item) => item.entity_id === this._calendarEntityId)
    ) {
      this._calendarEntityId = null;
      this._loadedMonth = "";
      this._events = [];
    }
    this._render();
    if (this._tab === "calendar") this._loadEvents();
  }

  _applyTheme(hass) {
    const root = this;
    const themes = hass?.themes;
    if (!root || !themes) return;
    const themeName = themes.theme || themes.default_theme;
    const theme = themes.themes?.[themeName] || {};
    const mode = themes.darkMode ? "dark" : "light";
    const variables = { ...theme, ...(theme.modes?.[mode] || {}) };
    this._haThemeVariables.forEach((name) => root.style.removeProperty(name));
    this._haThemeVariables.clear();
    Object.entries(variables).forEach(([key, value]) => {
      if (key === "modes" || value === undefined || value === null) return;
      const name = key.startsWith("--") ? key : "--" + key;
      root.style.setProperty(name, String(value));
      this._haThemeVariables.add(name);
    });
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

  _calendarEntity() {
    const calendars = this._calendarEntities();
    return calendars.find((item) => item.entity_id === this._calendarEntityId) ||
      calendars.find((item) => item.attributes.worklog_user_id &&
        item.attributes.worklog_user_id === this._hass?.user?.id) ||
      (calendars.length === 1 ? calendars[0] : undefined);
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
    const marker = "HA_WORKLOG_HISTORY:";
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
    const calendarSelector = calendars.length > 1
      ? "<div class='person-switch'><label for='worklog-person'>Person</label><select id='worklog-person' data-calendar>" + (this._calendarEntityId ? "" : "<option value='' selected>Person auswählen …</option>") + calendars.map((item) => "<option value='" + item.entity_id + "'" + (item.entity_id === this._calendarEntityId ? " selected" : "") + ">" + this._escape(this._calendarLabel(item)) + "</option>").join("") + "</select></div>"
      : "";
    const selectedHistory = this._changeHistory(selectedEvent);
    const selectedHistoryMarkup = selectedHistory.length
      ? "<details class='change-history'><summary>Änderungsverlauf (" + selectedHistory.length + ")</summary><ul>" + selectedHistory.map((change) => {
          const displayTime = change.timestamp ? new Intl.DateTimeFormat(locale, { dateStyle: "short", timeStyle: "short" }).format(new Date(change.timestamp)) : "";
          const who = this._escape(change.changed_by_name || change.changed_by || "Home Assistant");
          const from = this._escape(this._label(change.old_value));
          const to = this._escape(this._label(change.new_value));
          const reason = change.reason ? " · " + this._escape(change.reason) : "";
          return "<li><time>" + this._escape(displayTime) + "</time> · " + who + ": " + from + " → " + to + reason + "</li>";
        }).join("") + "</ul></details>"
      : "";
    const tab = this._tab;
    const content = tab === "calendar"
      ? (this._calendarEntity() ? "<ha-card>" + calendarSelector + "<div class='calendar-head'><button class='month-nav' data-action='prev' aria-label='Vorheriger Monat'>‹</button><h2>" + title + "</h2><button class='today-nav' data-action='today' aria-label='Zum heutigen Datum springen'>Heute</button><button class='month-nav' data-action='next' aria-label='Nächster Monat'>›</button></div><div class='stats'>" + [{ label: "Arbeitstage", value: monthStats.workdays }, { label: "Büro", value: monthStats.office }, { label: "Homeoffice", value: monthStats.homeOffice }, { label: "Urlaub", value: monthStats.vacation }, { label: "Krankheit", value: monthStats.sick }].map((item) => "<div class='stat'><span>" + item.label + "</span><strong>" + item.value + "</strong></div>").join("") + "</div><div class='grid'>" + headers + cells + "</div><div class='legend'><span><i class='legend-dot office-dot'></i>Büro</span><span><i class='legend-dot home-dot'></i>Homeoffice</span><span><i class='legend-dot vacation-dot'></i>Urlaub</span><span><i class='legend-dot sick-dot'></i>Krankheit</span><span><i class='legend-dot tracking-dot'></i>Erkennung läuft</span><span><i class='legend-dot no-work-dot'></i>Kein Arbeitstag</span><span><i class='legend-dot manual-dot'></i>Manuell geändert</span></div>" + (this._selected ? "<div class='selection'><h3>" + this._selected + "</h3><p>" + this._label(selectedType) + (selectedEvent?.description?.includes('Manuell geändert') ? " · manuell geändert" : "") + "</p><label class='reason'>Änderungsgrund (optional)<input data-reason type='text' maxlength='500' /></label><div class='actions'><button data-type='office'>Bürotag</button><button data-type='home_office'>Homeoffice</button><button data-type='no_work'>Kein Arbeitstag</button><button data-type='vacation'>Urlaub</button><button data-type='sick_leave'>Krankheit</button><button data-type='automatic'>Automatisch</button></div>" + selectedHistoryMarkup + "<p class='message'>" + this._message + "</p></div>" : "") + "</ha-card>" : calendars.length > 1 ? "<ha-card>" + calendarSelector + "<p>Bitte wähle eine Person aus, um den Kalender zu öffnen.</p></ha-card>" : "<ha-card><p>Es ist noch keine Person für HA Work-Log eingerichtet.</p></ha-card>")
      : tab === "config"
        ? "<ha-card><h2>Konfigurator</h2><p>Die Beta erkennt einen Tag ab 30 Minuten in der Arbeitszone oder mit aktivem Homeoffice-Sensor.</p><p>Sensoren und Arbeitszone werden über die Einstellungen der Integration gewählt.</p><ul>" + (sensorLines || "<li>Die Entitäten erscheinen nach dem ersten Erkennungslauf.</li>") + "</ul></ha-card>"
        : "<ha-card><h2>Export</h2><p>Der Export ist für eine spätere Version vorgesehen.</p></ha-card>";
    this.shadowRoot.innerHTML = "<style>:host{display:block;color:var(--primary-text-color,inherit);background:var(--primary-background-color,transparent);min-height:100vh;font-family:var(--paper-font-body1_-_font-family,Roboto,Noto,sans-serif)}.page{max-width:1050px;margin:auto;padding:24px}.top{display:flex;align-items:center;gap:12px;margin-bottom:16px}.top h1{font-size:24px;font-weight:500;margin:0}.tabs{display:flex;gap:8px;border-bottom:1px solid var(--divider-color);margin-bottom:20px}.tabs button,.actions button,.month-nav,.today-nav{font:inherit;color:var(--primary-text-color);background:var(--card-background-color);border:1px solid var(--divider-color);border-radius:8px;padding:9px 14px;cursor:pointer}.tabs button.active{color:var(--primary-color);border-color:var(--primary-color)}ha-card{display:block;background:var(--card-background-color);color:var(--primary-text-color);border-radius:12px;padding:20px;box-shadow:var(--ha-card-box-shadow,0 2px 8px rgba(0,0,0,.12))}.calendar-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}.calendar-head h2{font-size:20px;font-weight:500;margin:0;text-transform:capitalize}.grid{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:6px}.weekday{text-align:center;color:var(--secondary-text-color);font-size:13px;padding:8px 0}.legend{display:flex;flex-wrap:wrap;gap:8px 16px;margin-top:14px;color:var(--secondary-text-color);font-size:13px}.legend span{display:inline-flex;align-items:center;gap:6px}.legend-dot{width:11px;height:11px;border-radius:50%;display:inline-block}.office-dot{background:var(--info-color,#039be5)}.home-dot{background:var(--success-color,#43a047)}.vacation-dot{background:var(--warning-color,#fbc02d)}.sick-dot{background:var(--error-color,#db4437)}.tracking-dot{background:var(--state-icon-color,#9e9e9e)}.no-work-dot{background:var(--divider-color,#9e9e9e)}.weekday.weekend-label{color:var(--warning-color,var(--primary-color));font-weight:600}.day{position:relative;min-height:44px;border:1px solid var(--divider-color);border-radius:8px;background:var(--card-background-color);color:var(--primary-text-color);font:inherit;cursor:pointer}.day.weekend{background:var(--secondary-background-color,var(--card-background-color));border-bottom:3px solid var(--warning-color,var(--primary-color))}.day.outside{opacity:.45}.day.selected{outline:2px solid var(--primary-color)}.day.manual::after{content:'';position:absolute;top:4px;right:4px;width:6px;height:6px;border-radius:50%;background:var(--primary-text-color);opacity:.8;box-shadow:0 0 0 1px var(--card-background-color)}.manual-dot{background:var(--primary-text-color);opacity:.7}.person-switch{display:flex;align-items:center;gap:10px;margin:0 0 12px}.person-switch select,.reason input{font:inherit;color:var(--primary-text-color);background:var(--card-background-color);border:1px solid var(--divider-color);border-radius:6px;padding:8px}.reason{display:grid;gap:6px;max-width:420px}.change-history{margin-top:12px;color:var(--secondary-text-color)}.change-history ul{padding-left:20px}.change-history time{font-variant-numeric:tabular-nums}.day.type-office,.day.type-office_and_home_office{background:var(--info-color,#039be5);color:var(--text-primary-color,#fff)}.day.type-home_office{background:var(--success-color,#43a047);color:var(--text-primary-color,#fff)}.day.type-vacation{background:var(--warning-color,#fbc02d);color:var(--primary-text-color)}.day.type-sick_leave,.day.type-needs_review{background:var(--error-color,#db4437);color:var(--text-primary-color,#fff)}.day.type-tracking{background:var(--state-icon-color,#9e9e9e)}.stats{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px;margin:0 0 16px}.stat{display:flex;flex-direction:column;gap:4px;background:var(--secondary-background-color,var(--card-background-color));border-radius:8px;padding:10px 12px}.stat span{color:var(--secondary-text-color);font-size:12px}.stat strong{font-size:20px;font-weight:500}.selection{border-top:1px solid var(--divider-color);margin-top:20px;padding-top:12px}.selection h3{font-size:17px;margin:0 0 6px}.selection p{color:var(--secondary-text-color)}.actions{display:flex;flex-wrap:wrap;gap:8px}.actions button{padding:8px 10px}.message:empty{display:none}.message{min-height:1em}ha-card>h2{font-weight:500}.page li{margin:8px 0}@media(max-width:600px){.page{padding:12px}.day{min-height:38px}.stats{grid-template-columns:repeat(2,minmax(0,1fr))}.grid{gap:3px}.tabs{overflow-x:auto}.tabs button{white-space:nowrap;padding:8px 10px}}</style><div class='page'><div class='top'><ha-menu-button></ha-menu-button><h1>HA Work-Log</h1></div><div class='tabs'><button data-tab='calendar' class='" + (tab === "calendar" ? "active" : "") + "'>Kalender</button><button data-tab='config' class='" + (tab === "config" ? "active" : "") + "'>Konfigurator</button><button data-tab='export' class='" + (tab === "export" ? "active" : "") + "'>Export</button></div>" + content + "</div>";
    const menu = this.shadowRoot.querySelector("ha-menu-button");
    if (menu) menu.hass = this._hass;
    this.shadowRoot.querySelectorAll("[data-tab]").forEach((button) => button.addEventListener("click", () => {
      this._tab = button.dataset.tab;
      this._render();
      if (this._tab === "calendar") this._loadEvents();
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
    this.shadowRoot.querySelector("[data-calendar]")?.addEventListener("change", async (event) => {
      this._calendarEntityId = event.target.value || null;
      this._calendarInitialized = true;
      this._loadedMonth = "";
      this._events = [];
      this._selected = null;
      this._render();
      await this._loadEvents();
    });
    this.shadowRoot.querySelectorAll("[data-type]").forEach((button) => button.addEventListener("click", async () => {
      if (this._busy) return;
      const selectedCalendar = this._calendarEntity();
      const personEntity = selectedCalendar?.attributes.worklog_person_entity;
      const reason = this.shadowRoot.querySelector("[data-reason]")?.value?.trim() || "";
      this._busy = true;
      this._message = "Speichere Änderung …";
      this._render();
      try {
        await this._hass.callService("ha_worklog", "set_day_override", {
          person_entity: personEntity,
          date: this._selected,
          day_type: button.dataset.type,
          reason,
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

customElements.define("ha-worklog-panel", HAWorklogPanel);
