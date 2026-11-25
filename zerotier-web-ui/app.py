import json
import os
import secrets
import requests
from flask import (
    Flask, request, redirect, url_for, render_template_string,
    send_from_directory, session, abort, Response, jsonify,
)
from markupsafe import Markup, escape
from passlib.apache import HtpasswdFile

VERSION = "2026.11.25.1"  # YYYY.MM.DD.counter - same value as git tag / Docker tag

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)  # generat la pornirea containerului

HTPASSWD_PATH = "/app/.htpasswd"


@app.template_filter("softwrap")
def softwrap(value, chars=":_"):
    """Escapeaza textul si pune <wbr> dupa caracterele date: locuri unde browserul poate rupe
    randul pe ecrane inguste, fara sa modifice textul care se copiaza (spre deosebire de U+200B)."""
    out = escape(str(value))
    for ch in chars:
        out = out.replace(ch, Markup(ch + "<wbr>"))
    return out

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LANG_DIR = os.path.join(BASE_DIR, "language")
DEFAULT_LANG = "ro"


def load_translations():
    """Citeste toate fisierele language/<cod>.json. Cheia "_name" = numele afisat in meniu."""
    translations = {}
    try:
        filenames = sorted(os.listdir(LANG_DIR))
    except OSError:
        return translations
    for filename in filenames:
        if not filename.endswith(".json") or filename.startswith("."):
            continue
        try:
            with open(os.path.join(LANG_DIR, filename), encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            continue  # fisier invalid: il sarim, restul limbilor merg mai departe
        if isinstance(data, dict):
            translations[filename[:-5]] = data
    return translations


def pick_default_lang(translations):
    """Limba implicita (DEFAULT_LANG); daca fisierul ei lipseste, prima limba disponibila."""
    if DEFAULT_LANG in translations:
        return DEFAULT_LANG
    return next(iter(sorted(translations)), DEFAULT_LANG)


def build_language_list(translations):
    """Lista pentru meniu: limba implicita prima, restul in ordine alfabetica dupa nume."""
    items = [{"code": c, "name": d.get("_name", c)} for c, d in translations.items()]
    items.sort(key=lambda l: (l["code"] != DEFAULT_LANG, l["name"]))
    return items



def check_auth():
    auth = request.authorization
    if not auth:
        return False
    try:
        ht = HtpasswdFile(HTPASSWD_PATH)
    except (FileNotFoundError, OSError):
        return False
    return ht.check_password(auth.username, auth.password) is True


@app.before_request
def require_auth():
    if not check_auth():
        translations = load_translations()
        message = translations.get(pick_default_lang(translations), {}).get(
            "authRequired", "Authentication required."
        )
        return Response(
            message, 401,
            {"WWW-Authenticate": 'Basic realm="ZeroTier"'},
        )

ZT_API = "http://127.0.0.1:9993"
TOKEN_PATH = "/var/lib/zerotier-one/authtoken.secret"


def get_csrf_token():
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_hex(16)
        session["csrf_token"] = token
    return token


def check_csrf():
    submitted = request.form.get("csrf_token", "")
    if not submitted or submitted != session.get("csrf_token"):
        abort(403)


def get_token():
    with open(TOKEN_PATH) as f:
        return f.read().strip()


def zt_get(path):
    r = requests.get(f"{ZT_API}{path}", headers={"X-ZT1-Auth": get_token()}, timeout=5)
    r.raise_for_status()
    return r.json()


def zt_post(path):
    r = requests.post(f"{ZT_API}{path}", headers={"X-ZT1-Auth": get_token()}, json={}, timeout=5)
    r.raise_for_status()


def zt_delete(path):
    r = requests.delete(f"{ZT_API}{path}", headers={"X-ZT1-Auth": get_token()}, timeout=5)
    r.raise_for_status()


TEMPLATE = """
<!doctype html>
<html lang="{{ default_lang }}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ZeroTier Web UI</title>
<script>
  // aplica tema INAINTE ca pagina sa se randeze, ca sa nu clipeasca alb (FOUC)
  (function () {
    try {
      var t = localStorage.getItem("zt_theme") || "dark";
      if (t === "dark") document.documentElement.classList.add("dark");
    } catch (e) {}
  })();
</script>
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<style>
  * { box-sizing: border-box; }

  :root {
    --bg: #ffffff;
    --text: #1a1a1a;
    --text-muted: #6b7280;
    --card-bg: #f6f7f8;
    --card-border: #e5e7eb;
    --input-border: #d1d5db;
    --input-bg: #ffffff;
    --row-border: #e5e7eb;
    --badge-online-bg: #d1fae5;
    --badge-online-fg: #059669;
    --badge-offline-bg: #fee2e2;
    --badge-offline-fg: #dc2626;
    --link: #2563eb;
    --btn-border: #d1d5db;
    --btn-text: #374151;
    --btn-hover-bg: #f3f4f6;
    --err-bg: #fdecea;
    --err-fg: #b00020;
  }

  html.dark {
    --bg: #0f1115;
    --text: #e5e7eb;
    --text-muted: #9ca3af;
    --card-bg: #1a1d23;
    --card-border: #2a2e37;
    --input-border: #3a3f4b;
    --input-bg: #12151a;
    --row-border: #2a2e37;
    --badge-online-bg: #064e3b;
    --badge-online-fg: #34d399;
    --badge-offline-bg: #7f1d1d;
    --badge-offline-fg: #f87171;
    --link: #60a5fa;
    --btn-border: #3a3f4b;
    --btn-text: #d1d5db;
    --btn-hover-bg: #23272f;
    --err-bg: #451a1a;
    --err-fg: #f87171;
  }

  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    max-width: 1024px;
    margin: 48px auto;
    padding: 0 16px;
    color: var(--text);
    background: var(--bg);
    transition: background .15s ease, color .15s ease;
  }

  .top-row { display: flex; justify-content: space-between; align-items: flex-start; }
  h1 { font-size: 28px; font-weight: 700; margin: 0 0 2px 0; }
  .subtitle { color: var(--text-muted); font-size: 14px; margin: 0 0 24px 0; }

  .toggles { display: flex; gap: 8px; }
  .app-footer { margin-top: 28px; text-align: center; font-size: 11px; opacity: .45; }
  .toggle-btn {
    background: var(--card-bg); border: 1px solid var(--btn-border); border-radius: 6px;
    padding: 6px 14px; font-size: 13px; font-weight: 600; color: var(--btn-text);
    cursor: pointer;
  }
  .toggle-btn:hover { background: var(--btn-hover-bg); }

  .card {
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 8px;
    padding: 18px 22px;
    margin-bottom: 16px;
  }
  .card-title {
    font-size: 12px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--text);
    margin: 0 0 12px 0;
  }

  .node-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; font-size: 14px; }
  .node-row code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 13px; }
  .sep { color: var(--text-muted); }

  .badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
  }
  .badge.online { background: var(--badge-online-bg); color: var(--badge-online-fg); }
  .badge.offline { background: var(--badge-offline-bg); color: var(--badge-offline-fg); }

  .empty { color: var(--text-muted); font-size: 14px; margin: 0; }

  table { border-collapse: collapse; width: 100%; }
  td, th {
    padding: 10px 10px;
    text-align: left;
    font-size: 14px;
    border-bottom: 1px solid var(--row-border);
    vertical-align: middle;
    white-space: nowrap;
  }
  th {
    color: var(--text-muted); font-weight: 600; font-size: 11px; text-transform: uppercase;
    letter-spacing: 0.03em;
  }
  tr:last-child td { border-bottom: none; }
  td code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 13px; }
  .ip-line {
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 12.5px;
    white-space: nowrap;
    word-break: keep-all;
    overflow-wrap: normal;
  }
  .ip-line:not(:last-child) { margin-bottom: 4px; }
  /* Rezerva invizibila: coloana IP pastreaza latimea unei adrese IPv6 (ex. fd80:...:d68f/88 = 42 caractere),
     chiar daca IPv6 e dezactivat, ca restul coloanelor sa nu se deplaseze. Aceleasi font si marime ca .ip-line. */
  .ip-reserve {
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 12.5px;
    width: 42ch; height: 0; visibility: hidden; pointer-events: none;
  }
  /* pe desktop adresa ramane pe un singur rand: <wbr> se activeaza doar in layout-ul pentru ecrane inguste */
  .ip-line wbr { display: none; }
  .col-status { text-align: center; }
  /* numele retelei si starea (ex. REQUESTING_CONFIGURATION) se pot rupe pe mai multe randuri daca nu e loc */
  /* Numele primeste tot spatiul ramas (poate fi lung) si se rupe la nevoie; ID-ul, IP-ul si butonul se strang pe continut */
  td.col-name { white-space: normal; overflow-wrap: anywhere; min-width: 110px; }
  td.col-status { white-space: normal; overflow-wrap: break-word; font-size: 13px; }
  .table-scroll { overflow-x: auto; }
  .col-actions { text-align: right; }
  /* IP-ul si butonul ocupa strict cat au nevoie; spatiul in plus se imparte intre primele coloane */
  .col-id, .col-ip, .col-actions, .col-status { width: 1%; }
  td.col-ip, th.col-ip { padding-right: 26px; }
  .mobile-label { display: none; }

  @media (max-width: 940px) {
    .networks-table .table-header-row { display: none; }
    .networks-table, .networks-table tbody, .networks-table tr, .networks-table td { display: block; width: 100% !important; }
    .networks-table td {
      border-bottom: none;
      padding: 3px 0;
      white-space: normal;
    }
    .networks-table tr {
      border-bottom: 1px solid var(--row-border);
      padding-bottom: 10px;
      margin-bottom: 10px;
    }
    .networks-table tr:last-child { border-bottom: none; margin-bottom: 0; }
    .col-status, .col-actions { text-align: left; }
    .col-actions { padding-top: 6px; }
    .networks-table td.col-ip { padding: 3px 0; }
    .ip-reserve { display: none; }
    .card-head { margin-right: 0; }
    .mobile-label {
      display: inline-block;
      min-width: 100px;
      font-size: 10px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.03em;
      color: var(--text-muted);
    }
    .ip-line { white-space: normal; overflow-wrap: anywhere; word-break: break-word; }
    .ip-line wbr { display: inline; }
  }

  .leave-btn, .peers-btn {
    background: var(--card-bg); border: 1px solid var(--btn-border); border-radius: 6px;
    padding: 6px 12px; font-size: 12px; cursor: pointer; color: var(--btn-text);
    white-space: nowrap;
  }
  .leave-btn:hover { background: var(--badge-offline-bg); border-color: var(--badge-offline-fg); color: var(--badge-offline-fg); }

  /* antetul cardului: titlul la stanga, butonul Peers la dreapta, deasupra coloanei "Paraseste" */
  .card-head {
    display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between;
    gap: 8px; margin: 0 10px 12px 0;
  }
  .card-head .card-title { margin: 0; }
  .peers-btn:hover { background: var(--btn-hover-bg); border-color: var(--link); color: var(--link); }

  .mono { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 13px; }
  .badge.relay { background: var(--btn-hover-bg); color: var(--text-muted); }

  dialog.modal {
    border: 1px solid var(--card-border); border-radius: 10px;
    background: var(--card-bg); color: var(--text);
    width: min(780px, 94vw); max-height: 86vh; padding: 0; overflow: hidden;
  }
  dialog.modal::backdrop { background: rgba(0, 0, 0, 0.6); }
  .modal-inner {
    padding: 18px 22px; display: flex; flex-direction: column; gap: 12px;
    max-height: 86vh;
  }
  .modal-title { margin: 0; font-size: 16px; font-weight: 700; }
  .modal-note { margin: 0; font-size: 12.5px; color: var(--text-muted); line-height: 1.5; }
  #peersBody { overflow: auto; min-height: 0; }
  .peers-table th { position: sticky; top: 0; background: var(--card-bg); }
  .modal-actions { display: flex; justify-content: flex-end; }

  .join-layout { display: flex; flex-wrap: wrap; align-items: center; gap: 14px 20px; }
  .join-row { display: flex; flex-wrap: wrap; gap: 10px; flex: 0 1 auto; max-width: 100%; }
  input[type=text] {
    flex: 0 0 auto;  /* latimea exacta e calculata in JS (fitIdInput) dupa cel mai lung placeholder */
    max-width: 100%;
    min-width: 0;
    text-overflow: ellipsis;
    padding: 10px 14px;
    border: 1px solid var(--input-border);
    border-radius: 6px;
    background: var(--input-bg);
    color: var(--text);
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 14px;
  }
  .join-btn {
    background: #f5a623;
    color: #1a1a1a;
    border: none;
    border-radius: 6px;
    padding: 10px 22px;
    font-weight: 600;
    font-size: 14px;
    cursor: pointer;
    white-space: nowrap;
  }
  .join-btn:hover { background: #e0961a; }

  .help-text { flex: 1 1 300px; min-width: 0; overflow-wrap: anywhere; font-size: 13px; color: var(--text-muted); margin: 0; line-height: 1.6; text-align: center; }
  .help-text p { margin: 0 0 4px 0; }
  .help-text p:last-child { margin-bottom: 0; }
  .help-text a { color: var(--link); text-decoration: none; }
  .help-text a:hover { text-decoration: underline; }

  .err { color: var(--err-fg); background: var(--err-bg); padding: 12px 16px; border-radius: 8px; margin-bottom: 16px; }

  /* ecrane foarte mici: margini mai mici, ca sa incapa caseta de ID cu tot placeholderul */
  @media (max-width: 480px) {
    body { padding: 0 12px; }
    .card { padding: 16px; }
    input[type=text] { padding: 10px 12px; }
  }
</style>
</head>
<body>

<div class="top-row">
  <div>
    <h1>ZeroTier Web UI</h1>
    <p class="subtitle" data-i18n="subtitle">{{ T.subtitle }}</p>
  </div>
  <div class="toggles">
    <button id="themeToggle" type="button" class="toggle-btn">🌙</button>
    <select id="langSelect" class="toggle-btn">
      {% for l in languages %}
      <option value="{{ l.code }}"{% if l.code == default_lang %} selected{% endif %}>{{ l.name }}</option>
      {% endfor %}
    </select>
  </div>
</div>

{% if error %}
  <p class="err"><span data-i18n="errorPrefix">{{ T.errorPrefix }}</span> {{ error }}</p>
{% else %}

  <div class="card">
    <div class="node-row">
      <span><b><span data-i18n="nodeId">{{ T.nodeId }}</span>:</b> <code>{{ status.get('address', '-') }}</code></span>
      {% if status.get('online') %}
        <span class="badge online" data-i18n="online">{{ T.online }}</span>
      {% else %}
        <span class="badge offline" data-i18n="offline">{{ T.offline }}</span>
      {% endif %}
      <span class="sep">·</span>
      <span><span data-i18n="version">{{ T.version }}</span> {{ status.get('version', '-') }}</span>
    </div>
  </div>

  <div class="card">
    <div class="card-head">
      <p class="card-title" data-i18n="sectionNetworks">{{ T.sectionNetworks }}</p>
      <button type="button" class="peers-btn" data-i18n="peersBtn">{{ T.peersBtn }}</button>
    </div>
    {% if networks %}
    <div class="table-scroll">
    <table class="networks-table">
      <tr class="table-header-row">
        <th class="col-name" data-i18n="thName">{{ T.thName }}</th>
        <th class="col-id" data-i18n="thId">{{ T.thId }}</th>
        <th class="col-status" data-i18n="thStatus">{{ T.thStatus }}</th>
        <th class="col-ip" data-i18n="thIp">{{ T.thIp }}</th>
        <th class="col-actions"></th>
      </tr>
      {% for n in networks %}
      <tr>
        <td class="col-name"><span class="mobile-label" data-i18n="thName">{{ T.thName }}</span>{{ n.get('name') or '-' }}</td>
        <td class="col-id"><span class="mobile-label" data-i18n="thId">{{ T.thId }}</span><code>{{ n.get('id') }}</code></td>
        <td class="col-status"><span class="mobile-label" data-i18n="thStatus">{{ T.thStatus }}</span>{{ (n.get('status') or '')|softwrap('_') }}</td>
        <td class="col-ip">
          <span class="mobile-label" data-i18n="thIp">{{ T.thIp }}</span>
          {% for ip in n.get('assignedAddresses', []) %}
            <div class="ip-line">{{ ip|softwrap(':') }}</div>
          {% endfor %}
          <div class="ip-reserve" aria-hidden="true"></div>
        </td>
        <td class="col-actions">
          <form class="leave-form" method="post" action="{{ url_for('leave') }}">
            <input type="hidden" name="nwid" value="{{ n.get('id') }}">
            <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
            <button type="submit" class="leave-btn" data-i18n="leaveBtn">{{ T.leaveBtn }}</button>
          </form>
        </td>
      </tr>
      {% endfor %}
    </table>
    </div>
    {% else %}
    <p class="empty" data-i18n="emptyNetworks">{{ T.emptyNetworks }}</p>
    {% endif %}
  </div>

  <div class="card">
    <p class="card-title" data-i18n="sectionJoin">{{ T.sectionJoin }}</p>
    <div class="join-layout">
      <form method="post" action="{{ url_for('join') }}" class="join-row">
        <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
        <input type="text" name="nwid" data-i18n-placeholder="placeholder"
               placeholder="{{ T.placeholder }}"
               pattern="[0-9a-fA-F]{16}" maxlength="16" required>
        <button type="submit" class="join-btn" data-i18n="joinBtn">{{ T.joinBtn }}</button>
      </form>
      <div class="help-text" data-i18n-html="helpText">{{ T.helpText|safe }}</div>
    </div>
  </div>

{% endif %}

<dialog id="peersDialog" class="modal">
  <div class="modal-inner">
    <h3 class="modal-title" data-i18n="peersTitle">{{ T.peersTitle }}</h3>
    <p class="modal-note" data-i18n="peersNote">{{ T.peersNote }}</p>
    <div id="peersBody"></div>
    <div class="modal-actions">
      <button type="button" id="peersClose" class="toggle-btn" data-i18n="close">{{ T.close }}</button>
    </div>
  </div>
</dialog>

<script>
  const dict = {{ translations|tojson }};
  const DEFAULT_LANG = {{ default_lang|tojson }};

  function t(lang, key) {
    const cur = dict[lang] || {};
    if (cur[key] !== undefined) return cur[key];
    return (dict[DEFAULT_LANG] || {})[key];
  }

  function applyLang(lang) {
    if (!dict[lang]) lang = DEFAULT_LANG;
    document.documentElement.lang = lang;
    document.querySelectorAll('[data-i18n]').forEach(function (el) {
      const v = t(lang, el.getAttribute('data-i18n'));
      if (v !== undefined) el.textContent = v;
    });
    document.querySelectorAll('[data-i18n-html]').forEach(function (el) {
      const v = t(lang, el.getAttribute('data-i18n-html'));
      if (v !== undefined) el.innerHTML = v;
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(function (el) {
      const v = t(lang, el.getAttribute('data-i18n-placeholder'));
      if (v !== undefined) el.placeholder = v;
    });
    document.getElementById('langSelect').value = lang;
    window.currentLang = lang;
    localStorage.setItem('zt_lang', lang);
  }

  const peersDialog = document.getElementById('peersDialog');
  const peersBody = document.getElementById('peersBody');
  const PEERS_URL = {{ url_for('peers')|tojson }};

  function peersMessage(key, detail) {
    peersBody.textContent = '';
    const p = document.createElement('p');
    p.className = 'empty';
    const span = document.createElement('span');
    span.setAttribute('data-i18n', key);
    span.textContent = t(window.currentLang, key) || '';
    p.appendChild(span);
    if (detail) p.appendChild(document.createTextNode(' ' + detail));
    peersBody.appendChild(p);
  }

  function peerCell(row, text, cls) {
    const td = row.insertCell();
    td.textContent = text;
    if (cls) td.className = cls;
    return td;
  }

  function renderPeers(peers) {
    if (!peers.length) { peersMessage('peersEmpty'); return; }
    peersBody.textContent = '';
    const table = document.createElement('table');
    table.className = 'peers-table';
    const head = table.insertRow();
    ['peerAddress', 'peerRole', 'version', 'peerLatency', 'peerLink', 'peerPath'].forEach(function (key) {
      const th = document.createElement('th');
      th.setAttribute('data-i18n', key);
      th.textContent = t(window.currentLang, key) || '';
      head.appendChild(th);
    });
    peers.forEach(function (p) {
      const row = table.insertRow();
      peerCell(row, p.address || '-', 'mono');
      peerCell(row, p.role || '-');
      peerCell(row, p.version || '-');
      peerCell(row, p.latency === null || p.latency === undefined ? '-' : p.latency + ' ms');
      const linkCell = row.insertCell();
      const badge = document.createElement('span');
      badge.className = 'badge ' + (p.link === 'DIRECT' ? 'online' : 'relay');
      badge.textContent = p.link;
      linkCell.appendChild(badge);
      peerCell(row, p.path || '-', 'mono');
    });
    peersBody.appendChild(table);
  }

  function openPeers() {
    peersMessage('peersLoading');
    if (!peersDialog.open) peersDialog.showModal();
    fetch(PEERS_URL, { headers: { 'Accept': 'application/json' }, credentials: 'same-origin', cache: 'no-store' })
      .then(function (r) {
        return r.json().then(function (data) { return { ok: r.ok, data: data }; });
      })
      .then(function (res) {
        if (!res.ok) throw new Error((res.data && res.data.error) || 'HTTP error');
        renderPeers(res.data.peers || []);
      })
      .catch(function (err) { peersMessage('peersError', err.message); });
  }

  document.querySelectorAll('.peers-btn').forEach(function (btn) {
    btn.addEventListener('click', openPeers);
  });
  document.getElementById('peersClose').addEventListener('click', function () { peersDialog.close(); });
  peersDialog.addEventListener('click', function (e) { if (e.target === peersDialog) peersDialog.close(); });

  // Latimea casetei de ID = cel mai lung placeholder dintre toate limbile din folderul language/.
  // Masurat chiar in caseta reala (scriu textul in ea, fara padding, latime 1px, si citesc scrollWidth),
  // IN LIMBA FIECARUI TEXT: browserul alege fonturile de rezerva pentru greaca/chirilica dupa limba,
  // iar acestea pot fi mai late decat fontul principal. Peste valoarea masurata adaug o marja de siguranta.
  function fitIdInput() {
    const input = document.querySelector('.join-row input[type=text]');
    if (!input) return;
    const cs = getComputedStyle(input);
    const extra = parseFloat(cs.paddingLeft) + parseFloat(cs.paddingRight) +
                  parseFloat(cs.borderLeftWidth) + parseFloat(cs.borderRightWidth);
    const savedStyle = input.getAttribute('style');
    const savedLang = input.getAttribute('lang');
    const savedValue = input.value;
    input.style.cssText = 'box-sizing:content-box;padding:0;border:0;width:1px;';
    let widest = 0;
    function measure(text, lang) {
      if (lang) input.setAttribute('lang', lang); else input.removeAttribute('lang');
      input.value = text;
      widest = Math.max(widest, input.scrollWidth);
    }
    measure('0000000000000000');                                  // un ID de 16 caractere trebuie sa incapa
    Object.keys(dict).forEach(function (lang) {
      if (dict[lang].placeholder) measure(dict[lang].placeholder, lang);
    });
    input.value = savedValue;
    if (savedLang === null) input.removeAttribute('lang'); else input.setAttribute('lang', savedLang);
    if (savedStyle === null) input.removeAttribute('style'); else input.setAttribute('style', savedStyle);
    input.style.width = Math.ceil(widest * 1.10 + extra + 10) + 'px';
  }

  function applyTheme(theme) {
    document.documentElement.classList.toggle('dark', theme === 'dark');
    document.getElementById('themeToggle').textContent = theme === 'dark' ? '☀️' : '🌙';
    window.currentTheme = theme;
    localStorage.setItem('zt_theme', theme);
  }

  document.getElementById('langSelect').addEventListener('change', function () {
    applyLang(this.value);
  });

  document.getElementById('themeToggle').addEventListener('click', function () {
    applyTheme(window.currentTheme === 'dark' ? 'light' : 'dark');
  });

  document.querySelectorAll('.leave-form').forEach(function (form) {
    form.addEventListener('submit', function (e) {
      const nwid = form.querySelector('input[name=nwid]').value;
      if (!confirm((t(window.currentLang, 'confirmLeave') || '').replace('{id}', nwid))) e.preventDefault();
    });
  });

  applyLang(localStorage.getItem('zt_lang') || DEFAULT_LANG);
  fitIdInput();
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(fitIdInput);
  window.addEventListener('load', fitIdInput);
  applyTheme(localStorage.getItem('zt_theme') || 'dark');
</script>

<footer class="app-footer">v{{ version }}</footer>

</body>
</html>
"""


@app.route("/")
def index():
    error = None
    status, networks = {}, []
    try:
        status = zt_get("/status")
        networks = zt_get("/network")
        for n in networks:
            # IPv4 (fara ':') afisat deasupra, apoi IPv6 dedesubt
            n["assignedAddresses"] = sorted(
                n.get("assignedAddresses", []),
                key=lambda a: (":" in a, a),
            )
    except Exception as e:
        error = str(e)
    translations = load_translations()
    languages = build_language_list(translations)
    default_lang = pick_default_lang(translations)
    return render_template_string(
        TEMPLATE, status=status, networks=networks, error=error,
        csrf_token=get_csrf_token(), version=VERSION,
        translations=translations, languages=languages, default_lang=default_lang,
        T=translations.get(default_lang, {}),
    )


PEER_ROLE_ORDER = {"LEAF": 0, "MOON": 1, "PLANET": 2}


@app.route("/peers")
def peers():
    """Lista de peers a nodului (GET /peer din API-ul local ZeroTier), normalizata pentru UI."""
    try:
        raw = zt_get("/peer")
    except Exception as e:
        return jsonify(error=str(e)), 502
    result = []
    for peer in raw:
        paths = [x for x in peer.get("paths", []) if x.get("active") and not x.get("expired")]
        best = next((x for x in paths if x.get("preferred")), paths[0] if paths else None)
        version = str(peer.get("version", ""))
        latency = peer.get("latency")
        result.append({
            "address": peer.get("address", ""),
            "role": peer.get("role", ""),
            "version": "" if version.startswith("-1") else version,
            "latency": latency if isinstance(latency, (int, float)) and latency >= 0 else None,
            "link": "DIRECT" if paths else "RELAY",
            "path": best.get("address", "") if best else "",
        })
    result.sort(key=lambda x: (PEER_ROLE_ORDER.get(x["role"], 3), x["address"]))
    return jsonify(peers=result)


@app.route("/favicon.svg")
def favicon():
    return send_from_directory(app.root_path, "favicon.svg", mimetype="image/svg+xml")


@app.route("/join", methods=["POST"])
def join():
    check_csrf()
    nwid = request.form.get("nwid", "").strip()
    if nwid:
        zt_post(f"/network/{nwid}")
    return redirect(url_for("index"))


@app.route("/leave", methods=["POST"])
def leave():
    check_csrf()
    nwid = request.form.get("nwid", "").strip()
    if nwid:
        zt_delete(f"/network/{nwid}")
    return redirect(url_for("index"))


if __name__ == "__main__":
    from waitress import serve
    # 0.0.0.0: necesar ca NPM (retea docker bridge separata) sa poata ajunge la aplicatie.
    # Protectia e acum asigurata de Basic Auth (vezi require_auth), nu de nginx.
    serve(app, host="0.0.0.0", port=8080)
