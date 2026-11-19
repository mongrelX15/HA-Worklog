class HAWorklogPanel extends HTMLElement {
  constructor() {
    super();
    this._tab = "calendar";
    this._month = new Date(new Date().getFullYear(), new Date().getMonth(), 1);
    this._selected = this._isoDate(new Date());
    this._events = [];
    this._loadedMonth = "";
    this._busy = false;
    this._message = "";
    this._unsubscribe = undefined;
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
    if (this._tab === "calendar") this._loadEvents();
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

  _calendarEntity() {
    const states = Object.values(this._hass?.states || {});
    const match = states.find((item) => item.entity_id.startsWith("calendar.") &&
      ((item.attributes.friendly_name || "").toLowerCase().includes("arbeitskalender") ||
       item.entity_id.toLowerCase().includes("arbeitskalender")));
    return match?.entity_id;
  }

  async _loadEvents() {
    const monthKey = this._isoDate(this._month);
    const entityId = this._calendarEntity();
    if (!entityId || this._loadedMonth === monthKey || !this._hass?.connection) return;
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
    return this._events.find((event) => (event.start || "").slice(0, 10) === day);
  }

  _escape(value) {
    return String(value).replace(/[&<>"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[char]);
  }

  _render() {
    if (!this._hass) return;
    const locale = this._hass.locale?.language || "de-DE";
    const title = new Intl.DateTimeFormat(locale, { month: "long", year: "numeric" }).format(this._month);
    const selectedEvent = this._eventForDay(this._selected);
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
      const cls = ["day", isWeekend ? "weekend" : "", type ? "type-" + type : "", d.getMonth() !== this._month.getMonth() ? "outside" : "", iso === this._selected ? "selected" : ""].filter(Boolean).join(" ");
      cells += "<button class='" + cls + "' data-date='" + iso + "' aria-label='" + iso + (event ? ": " + this._label(type) : "") + "'>" + d.getDate() + "</button>";
    }
    const states = Object.values(this._hass.states || {});
    const sensorLines = states.filter((item) => item.entity_id.startsWith("sensor.") &&
      /tagestyp|erkennungszeit/i.test((item.attributes.friendly_name || "") + " " + item.entity_id))
      .map((item) => "<li>" + this._escape(item.attributes.friendly_name || item.entity_id) + ": " + this._escape(item.state) + "</li>").join("");
    const tab = this._tab;
    const content = tab === "calendar"
      ? "<ha-card><div class='calendar-head'><button class='month-nav' data-action='prev' aria-label='Vorheriger Monat'>‹</button><h2>" + title + "</h2><button class='today-nav' data-action='today' aria-label='Zum heutigen Datum springen'>Heute</button><button class='month-nav' data-action='next' aria-label='Nächster Monat'>›</button></div><div class='grid'>" + headers + cells + "</div><div class='selection'><h3>" + this._selected + "</h3><p>" + this._label(selectedType) + (selectedEvent?.description?.includes("Manuell geändert") ? " · manuell geändert" : "") + "</p><div class='actions'><button data-type='office'>Bürotag</button><button data-type='home_office'>Homeoffice</button><button data-type='no_work'>Kein Arbeitstag</button><button data-type='vacation'>Urlaub</button><button data-type='sick_leave'>Krankheit</button><button data-type='automatic'>Automatisch</button></div><p class='message'>" + this._message + "</p></div></ha-card>"
      : tab === "config"
        ? "<ha-card><h2>Konfigurator</h2><p>Die Beta erkennt einen Tag ab 30 Minuten in der Arbeitszone oder mit aktivem Homeoffice-Sensor.</p><p>Sensoren und Arbeitszone werden über die Einstellungen der Integration gewählt.</p><ul>" + (sensorLines || "<li>Die Entitäten erscheinen nach dem ersten Erkennungslauf.</li>") + "</ul></ha-card>"
        : "<ha-card><h2>Export</h2><p>Der Export ist für eine spätere Version vorgesehen.</p></ha-card>";
    this.innerHTML = "<style>ha-worklog-panel{display:block;color:var(--primary-text-color,inherit);background:var(--primary-background-color,transparent);min-height:100vh;font-family:var(--paper-font-body1_-_font-family,Roboto,Noto,sans-serif)}.page{max-width:1050px;margin:auto;padding:24px}.top{display:flex;align-items:center;gap:12px;margin-bottom:16px}.top h1{font-size:24px;font-weight:500;margin:0}.tabs{display:flex;gap:8px;border-bottom:1px solid var(--divider-color);margin-bottom:20px}.tabs button,.actions button,.month-nav,.today-nav{font:inherit;color:var(--primary-text-color);background:var(--card-background-color);border:1px solid var(--divider-color);border-radius:8px;padding:9px 14px;cursor:pointer}.tabs button.active{color:var(--primary-color);border-color:var(--primary-color)}ha-card{display:block;background:var(--card-background-color);color:var(--primary-text-color);border-radius:12px;padding:20px;box-shadow:var(--ha-card-box-shadow,0 2px 8px rgba(0,0,0,.12))}.calendar-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}.calendar-head h2{font-size:20px;font-weight:500;margin:0;text-transform:capitalize}.grid{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:6px}.weekday{text-align:center;color:var(--secondary-text-color);font-size:13px;padding:8px 0}.weekday.weekend-label{color:var(--warning-color,var(--primary-color));font-weight:600}.day{min-height:44px;border:1px solid var(--divider-color);border-radius:8px;background:var(--card-background-color);color:var(--primary-text-color);font:inherit;cursor:pointer}.day.weekend{background:var(--secondary-background-color,var(--card-background-color));border-bottom:3px solid var(--warning-color,var(--primary-color))}.day.outside{opacity:.45}.day.selected{outline:2px solid var(--primary-color)}.day.type-office,.day.type-office_and_home_office{background:var(--info-color,#039be5);color:var(--text-primary-color,#fff)}.day.type-home_office{background:var(--success-color,#43a047);color:var(--text-primary-color,#fff)}.day.type-vacation{background:var(--warning-color,#fbc02d);color:var(--primary-text-color)}.day.type-sick_leave,.day.type-needs_review{background:var(--error-color,#db4437);color:var(--text-primary-color,#fff)}.day.type-tracking{background:var(--state-icon-color,#9e9e9e)}.selection{border-top:1px solid var(--divider-color);margin-top:20px;padding-top:12px}.selection h3{font-size:17px;margin:0 0 6px}.selection p{color:var(--secondary-text-color)}.actions{display:flex;flex-wrap:wrap;gap:8px}.actions button{padding:8px 10px}.message{min-height:1em}ha-card>h2{font-weight:500}.page li{margin:8px 0}@media(max-width:600px){.page{padding:12px}.day{min-height:38px}.grid{gap:3px}.tabs{overflow-x:auto}.tabs button{white-space:nowrap;padding:8px 10px}}</style><div class='page'><div class='top'><ha-menu-button></ha-menu-button><h1>HA Work-Log</h1></div><div class='tabs'><button data-tab='calendar' class='" + (tab === "calendar" ? "active" : "") + "'>Kalender</button><button data-tab='config' class='" + (tab === "config" ? "active" : "") + "'>Konfigurator</button><button data-tab='export' class='" + (tab === "export" ? "active" : "") + "'>Export</button></div>" + content + "</div>";
    const menu = this.querySelector("ha-menu-button");
    if (menu) menu.hass = this._hass;
    this.querySelectorAll("[data-tab]").forEach((button) => button.addEventListener("click", () => {
      this._tab = button.dataset.tab;
      this._render();
      if (this._tab === "calendar") this._loadEvents();
    }));
    this.querySelectorAll("[data-date]").forEach((button) => button.addEventListener("click", () => {
      this._selected = button.dataset.date;
      this._render();
    }));
    this.querySelector("[data-action='prev']")?.addEventListener("click", () => {
      this._month = new Date(this._month.getFullYear(), this._month.getMonth() - 1, 1);
      this._selected = this._isoDate(this._month);
      this._loadedMonth = "";
      this._loadEvents();
    });
    this.querySelector("[data-action='today']")?.addEventListener("click", () => {
      const today = new Date();
      const currentMonth = new Date(today.getFullYear(), today.getMonth(), 1);
      if (this._isoDate(currentMonth) !== this._isoDate(this._month)) this._loadedMonth = "";
      this._month = currentMonth;
      this._selected = this._isoDate(today);
      this._render();
      this._loadEvents();
    });
    this.querySelector("[data-action='next']")?.addEventListener("click", () => {
      this._month = new Date(this._month.getFullYear(), this._month.getMonth() + 1, 1);
      this._selected = this._isoDate(this._month);
      this._loadedMonth = "";
      this._loadEvents();
    });
    this.querySelectorAll("[data-type]").forEach((button) => button.addEventListener("click", async () => {
      if (this._busy) return;
      this._busy = true;
      this._message = "Speichere Änderung …";
      this._render();
      try {
        await this._hass.callService("ha_worklog", "set_day_override", {
          date: this._selected,
          day_type: button.dataset.type,
        });
        this._message = "Änderung gespeichert.";
        this._loadedMonth = "";
        await this._loadEvents();
      } catch (error) {
        this._message = "Änderung konnte nicht gespeichert werden.";
      } finally {
        this._busy = false;
        this._render();
      }
    }));
  }
}

customElements.define("ha-worklog-panel", HAWorklogPanel);
