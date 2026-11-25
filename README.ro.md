# ZeroTier Web UI

[🇬🇧 English](README.md) · 🇷🇴 Română

Interfață web proprie, într-un singur container, pentru daemonul **ZeroTier instalat nativ** (Ubuntu / Linux).
Afișează Node ID și status, rețelele alăturate, permite join/leave și vizualizarea peers dintr-un browser.
Se construiește local din sursă (fără imagini terțe), cu Basic Auth, protecție CSRF, 12 limbi și mod întunecat implicit.

## Funcții

- Un singur container Docker (Flask + waitress) pe portul **8080**
- Vorbește cu API-ul local ZeroTier (`127.0.0.1:9993`) folosind `authtoken.secret`
- Basic Auth (`.htpasswd`) pe toate rutele, token CSRF la join/leave
- Rețele alăturate cu badge Online/Offline, adrese IPv4/IPv6, join / leave
- Fereastră modală **Peers** (echivalent `zerotier-cli peers`: rol, latență, direct/relay, cale)
- 12 limbi încărcate din `zerotier-web-ui/language/*.json` (română implicită); poți adăuga o limbă fără cod
- Temă întunecată (implicită) / luminoasă, layout responsive, versiunea afișată discret în subsol

## Cerințe

- Docker + Docker Compose
- ZeroTier instalat nativ și funcțional (`zerotier-cli info`)
- `apache2-utils` pentru `.htpasswd`: `sudo apt install -y apache2-utils`

## Instalare

```bash
git clone https://github.com/ms74ro/ZeroTier-Web-UI.git
cd ZeroTier-Web-UI

# fișierul de utilizatori (primul user: -c; fără -c pentru useri suplimentari)
htpasswd -c .htpasswd admin

docker compose config            # validează YAML-ul
docker compose up -d --build
```

Deschide `http://<IP_server>:8080` și autentifică-te. Verifică faptul că fără credențiale accesul e refuzat:

```bash
curl -I http://127.0.0.1:8080/   # 401 Unauthorized
```

### Structura proiectului

```
.
├── docker-compose.yml
├── .htpasswd                 # creat de tine, nu se comite
└── zerotier-web-ui/
    ├── Dockerfile
    ├── requirements.txt
    ├── app.py
    ├── favicon.svg           # poți pune propriul SVG
    └── language/             # câte un fișier JSON pe limbă
```

### Note despre docker-compose.yml

- `network_mode: host` e necesar ca aplicația să ajungă la daemon, la `127.0.0.1:9993`.
- `/var/lib/zerotier-one` e montat read-only (se citește `authtoken.secret`).
- `.htpasswd` e montat read-only.
- `language/` e montat, deci limbile se pot edita **fără rebuild**.
- `TZ` afectează doar ora din `docker compose logs`; setează-l pe fusul tău orar.

## Nginx Proxy Manager (opțional)

Proxy Host: scheme `http`, Forward Hostname/IP = IP-ul LAN al serverului (sau `172.17.0.1` dacă NPM e în rețea bridge
și nu ajunge la IP-ul LAN), port `8080`. **Nu** adăuga Access List în NPM — aplicația cere deja user/parolă.

## Limbi

Incluse: Română (implicită), Български, Deutsch, Ελληνικά, English, Español, Français, Italiano, Nederlands,
Polski, Svenska, Україна. Meniul de limbă se construiește automat din folder.

Adăugarea unei limbi:

1. `cp zerotier-web-ui/language/en.json zerotier-web-ui/language/ja.json`
2. Schimbă `_name` și tradu valorile (cheile rămân). `{id}` din `confirmLeave` este înlocuit cu ID-ul rețelei.
3. `python3 -m json.tool zerotier-web-ui/language/ja.json > /dev/null && echo OK`
4. Reîncarcă pagina.

Cheile lipsă se completează din română (`DEFAULT_LANG` în `app.py`). „Node ID” și „Peers” sunt lăsate intenționat netraduse.

## Peers

Butonul **Peers** (lângă „Rețele alăturate”) deschide o fereastră cu toți peers ai nodului. Lista este a nodului, nu a unei
rețele: API-ul local ZeroTier nu spune ce peer aparține cărei rețele. Se închide cu butonul, **Esc** sau click pe fundal.

## Actualizare

```bash
git pull
docker compose up -d --build
```

Modificările din `language/*.json` cer doar reîncărcarea paginii.

## Versionare

Pe bază de dată: `YYYY.MM.DD.contor` (ex. `2026.11.25.1` = prima versiune din 25 nov. 2026).
Valoarea este constanta `VERSION` din `zerotier-web-ui/app.py`, afișată în subsolul paginii și identică cu tag-ul git
(`v2026.11.25.1`). Vezi [CHANGELOG.md](CHANGELOG.md).

## Securitate — rezumat

- Fără drepturi de admin pe ZeroTier: aplicația doar citește `authtoken.secret` (montat read-only) și apelează API-ul local.
- Basic Auth protejează toate rutele, inclusiv `/join`, `/leave` și `/peers`.
- Token CSRF la join/leave; un POST fără token valid primește `403` (un refresh rezolvă după repornirea containerului).
- Accesibil pe `:8080` din afara LAN-ului? Credențialele se cer oricum, dar poți limita accesul la LAN cu o regulă `ufw`.

## Depanare

- **`path ".../zerotier-web-ui" not found`** — lipsește subfolderul `zerotier-web-ui/`; respectă structura de mai sus.
- **`did not find expected key` (YAML)** — tab-uri/caractere ascunse; recreează fișierul și rulează `docker compose config`.
- **Meniul de limbă e gol** — `zerotier-web-ui/language/` trebuie să existe pe host (altfel Docker montează un folder gol). Un JSON invalid e ignorat în tăcere; verifică cu `python3 -m json.tool`.
- **Build eșuează la `favicon.svg`** — Dockerfile îl copiază explicit; păstrează un SVG cu acest nume.
- **`403` la primul join/leave după restart** — reîncarcă pagina pentru un token CSRF nou.
