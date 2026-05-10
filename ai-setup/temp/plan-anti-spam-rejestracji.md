# Plan: Ochrona rejestracji przed spamem (Tier 1)

Roboczy plan implementacji - usunac po zakonczeniu i wpisaniu lekcji do `app/docs/`.

## Stan obecny (bug)

Endpoint `/api/register` w [app/website/server.py:118-158](../../app/website/server.py#L118-L158)
nie ma zadnej ochrony:
- brak rate limit per IP
- brak walidacji formatu email (przejdzie "x@x")
- brak honeypot
- brak CAPTCHA
- brak weryfikacji email po rejestracji

Atakujacy moze zrobic 10 000 kont w 30 sekund jednym `curl` w petli, wypelniajac
baze Supabase free tier (500 MB) i wyczerpujac connection pool (`maxconn=4`).

## Cel Tier 1

Trzy mechanizmy ktore razem lapia >95% prymitywnego spamu:
1. **Honeypot field** - lapie boty z `curl`/`requests`/proste skrypty
2. **Rate limit per IP** - lapie spam nawet jak ominie honeypot
3. **Walidacja formatu email** - odrzuca smieciowe adresy

Email weryfikacja (link aktywacyjny) - osobny temat (Tier 2), wymaga SMTP.

---

## Krok 1 - Honeypot field

### Cel

Ukryte pole `website` w formularzu. Boty wypelniaja, ludzie nie. Backend
udaje sukces gdy wypelnione (bot myśli ze sie udalo i odchodzi).

### Pliki do zmiany

**1.1. [app/website/index.html](../../app/website/index.html)**

Znalezc `<form id="registerForm">` i tuz przed `<button type="submit">`
dodac ukryte pole:

```html
<!-- Honeypot - niewidoczny dla ludzi, lapie boty -->
<div style="position:absolute; left:-9999px;" aria-hidden="true">
    <label for="reg-website">Strona WWW (nie wypelniaj)</label>
    <input type="text" id="reg-website" name="website" tabindex="-1" autocomplete="off" />
</div>
```

Uwagi:
- `position:absolute; left:-9999px` zamiast `display:none` (boty pomijaja `display:none`)
- `tabindex="-1"` - czlowiek z klawiatury nie wpadnie przez Tab
- `autocomplete="off"` - blokuje password manager od wypelnienia
- `aria-hidden="true"` - czytniki ekranu pomijaja (dostepnosc)

**1.2. [app/website/script.js](../../app/website/script.js)**

W handlerze `registerForm` (linia 28+) odczytac wartosc i dolaczyc do payloadu:

```javascript
var honeypot = document.getElementById('reg-website').value;

fetch('/api/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        username: username,
        email: email,
        password: password,
        website: honeypot   // <-- nowe
    })
})
```

**1.3. [app/website/server.py](../../app/website/server.py)**

Na poczatku funkcji `register()` (linia 119) dodac sprawdzenie:

```python
# Honeypot - jesli wypelnione, to bot. Cicho udajemy sukces.
if data.get("website"):
    print(
        f"[SECURITY] Honeypot triggered from IP={request.remote_addr}",
        file=sys.stderr, flush=True,
    )
    return jsonify({"ok": True, "msg": "Konto utworzone! Mozesz pobrac aplikacje i sie zalogowac."})
```

**WAZNE**: udajemy sukces (`ok: True`) - bot nie probuje innej metody, nie analizuje
czy honeypot dziala. Logujemy do stderr (Render logs) zeby widziec ile spamu lapiemy.

### Test

- Otworz strone w przegladarce - pole `website` nie jest widoczne
- Wypelnij normalnie -> rejestracja dziala
- `curl` z `"website": "spam"` -> dostaje `ok: true` ale **nie ma usera w bazie**
- Sprawdz logi Render: `[SECURITY] Honeypot triggered`

---

## Krok 2 - Rate limit per IP (Flask-Limiter)

### Cel

Maksymalnie 5 rejestracji / godzine / IP, 20 / dzien / IP.
Logowania: 10 / minute / IP (zeby nie blokowac normalnego uzytku ale lapiac brute force).

### Pliki do zmiany

**2.1. [app/website/requirements.txt](../../app/website/requirements.txt)**

Dodac:
```
Flask-Limiter==3.13
```

Backend in-memory (default) wystarczy - Render free tier ma jeden worker
gunicorn, w dodatku z `preload`. Nie potrzeba Redis.

**2.2. [app/website/server.py](../../app/website/server.py)**

Na poczatku (po imporcie Flask):

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
```

Po `app = Flask(...)` (linia 42):

```python
def _real_ip():
    """Pobiera IP klienta z X-Forwarded-For (Render jest za proxy)."""
    xff = request.headers.get("X-Forwarded-For", "")
    if xff:
        return xff.split(",")[0].strip()
    return get_remote_address()


limiter = Limiter(
    app=app,
    key_func=_real_ip,
    default_limits=[],   # nie limituj domyslnie - explicit per endpoint
    storage_uri="memory://",
)
```

Uwaga: na Render za proxy, `request.remote_addr` daje IP proxy, nie usera. Trzeba
brac z `X-Forwarded-For` (juz tak robimy w `/api/login`).

**2.3. Dekoratory na endpointach:**

```python
@app.route("/api/register", methods=["POST"])
@limiter.limit("5 per hour; 20 per day")
def register():
    ...

@app.route("/api/login", methods=["POST"])
@limiter.limit("10 per minute; 100 per hour")
def login():
    ...
```

**2.4. Custom error handler dla 429 (Too Many Requests):**

```python
@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({
        "ok": False,
        "msg": "Zbyt wiele prob. Sprobuj ponownie za chwile.",
    }), 429
```

### Test

```bash
# 6x z tego samego IP w ciagu godziny
for i in 1 2 3 4 5 6 7; do
  curl -X POST https://kosa-h283.onrender.com/api/register \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"test$i\",\"email\":\"t$i@t.pl\",\"password\":\"12345678\"}"
  echo ""
done
# 6-ty i 7-my powinny dostac HTTP 429
```

### Ryzyko

- **Wspolne IP (NAT, korpo, akademiki, mobile carrier)** - 5/h moze byc za malo
  jesli kilku userow rejestruje sie z tej samej sieci. Dla MVP ok, dla produkcji
  trzeba zwiekszyc lub dodac inne sygnaly (cookie, fingerprint).
- **In-memory storage** - po restarcie workera licznik sie zeruje. Render free tier
  restartuje co kilka godzin. Atakujacy moze wykorzystac restart, ale to wymaga
  wykrycia okna - w praktyce nie problem.
- **Pierwszy request po cold starcie** - `_real_ip()` musi dzialac od pierwszego
  requestu. Sprawdzic czy nie pada przy braku XFF na lokalnym tescie.

---

## Krok 3 - Walidacja formatu email

### Cel

Odrzucic adresy ktore nie spelniaja formatu `name@domain.tld`. Bez weryfikacji
SMTP - tylko regex/biblioteka.

### Wybor narzedzia

Dwie opcje:
1. **Regex** - zero zaleznosci, prosty pattern. Lapie 99% przypadkow ale nie
   przestrzega RFC 5322 w 100%.
2. **`email-validator` lib** - dokladniejsza walidacja, sprawdza tez DNS MX
   (opcjonalnie). +1 zaleznosc.

**Rekomendacja: regex** - dla MVP wystarczy, mniej zaleznosci, szybciej dziala.
Jesli pozniej chcemy weryfikacje DNS - przesiadka na `email-validator`.

### Pliki do zmiany

**3.1. [app/website/server.py](../../app/website/server.py)**

Na gorze pliku (po importach):

```python
import re

EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
)
```

W `register()` po walidacji długości email dodac:

```python
if not EMAIL_REGEX.match(email):
    return jsonify({"ok": False, "msg": "Nieprawidlowy format adresu email."})

if len(email) > 254:   # RFC 5321 max
    return jsonify({"ok": False, "msg": "Adres email zbyt dlugi."})
```

**3.2. [app/website/script.js](../../app/website/script.js)**

Pre-walidacja po stronie klienta (lepszy UX, nie czekamy na request):

```javascript
var emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
if (!emailRegex.test(email)) {
    msg.textContent = 'Nieprawidlowy format adresu email.';
    msg.classList.add('error');
    return;
}
```

**3.3. [app/gui/db.py](../../app/gui/db.py)**

W `register_user()` (linia 55) tez dodac walidacje:

```python
import re
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

# w funkcji:
if not EMAIL_REGEX.match(email):
    return False, "Nieprawidlowy format adresu email."
```

### Test

Powinny przejsc:
- `user@gmail.com`
- `user.name+tag@sub.domain.co.uk`

Powinny zostac odrzucone:
- `x@x` (brak TLD)
- `@gmail.com` (brak local-part)
- `user@` (brak domeny)
- `user gmail.com` (spacja)
- `user@@gmail.com` (dwa @)

---

## Krok 4 - Test calego flow

### 4.1. Lokalny test (przed pushem)

```powershell
# Terminal 1
cd app/website
py server.py

# Terminal 2 - test honeypot
curl -X POST http://localhost:5000/api/register `
  -H "Content-Type: application/json" `
  -d '{"username":"bot1","email":"bot1@test.pl","password":"12345678","website":"http://spam.com"}'
# Spodziewane: ok=true ale w bazie NIE MA usera "bot1"

# Test rate limit (6 razy)
for ($i=1; $i -le 7; $i++) {
    curl -X POST http://localhost:5000/api/register `
      -H "Content-Type: application/json" `
      -d "{\"username\":\"test$i\",\"email\":\"t$i@t.pl\",\"password\":\"12345678\"}"
}
# Spodziewane: 6 i 7 dostaja 429

# Test email validation
curl -X POST http://localhost:5000/api/register `
  -H "Content-Type: application/json" `
  -d '{"username":"valid","email":"x@x","password":"12345678"}'
# Spodziewane: ok=false, msg "Nieprawidlowy format..."
```

### 4.2. Test w bazie

```sql
-- Po tescie sprawdz czy honeypot user trafil do bazy (nie powinien)
SELECT id, login, email, created_at FROM users
WHERE login LIKE 'bot%' OR login LIKE 'test%'
ORDER BY created_at DESC LIMIT 20;

-- Cleanup test userow
DELETE FROM users WHERE login LIKE 'bot%' OR login LIKE 'test%';
```

### 4.3. Test po deploymencie

Po pushcie -> Render auto-deploy -> czekamy ~2 min -> powtorzyc 4.1
juz na `https://kosa-h283.onrender.com`.

---

## Krok 5 - Commity (osobne, klasa 2 = push = deploy na produkcje)

Workflow zgodnie z **L-D5** (klasy zmian):

```
feat: honeypot field na rejestracji (anti-spam)
feat: rate limit Flask-Limiter (5/h register, 10/min login)
feat: walidacja formatu email (regex RFC-friendly)
```

Kazdy commit testowany lokalnie (Krok 4.1) PRZED pushem. Wszystkie naraz na main
= 1 redeploy Render.

### Zalecane przed pushem

```powershell
# Lokalny test Flaska (wszystkie endpointy)
py app/website/server.py
# w drugim terminalu - smoke test
curl http://localhost:5000/api/health
# powinno: {"ok":true}
```

---

## Krok 6 - Dokumentacja po skonczeniu

### 6.1. Update [app/docs/deployment-i-architektura.md](../../app/docs/deployment-i-architektura.md)

Dodac sekcje "Ochrona rejestracji" z opisem trzech mechanizmow.

### 6.2. Update [SECURITY.md](../../SECURITY.md)

Dopisac do listy: rate limit, honeypot, walidacja email.

### 6.3. Nowy plik `app/docs/lekcje-anti-spam.md`

Lekcje:
- Honeypot vs CAPTCHA - kompromisy
- Flask-Limiter z X-Forwarded-For (proxy Render)
- Dlaczego in-memory storage wystarcza dla 1-worker setup
- Co przegapilismy w MVP (email weryfikacja, Cloudflare)

### 6.4. Memory (jak user potwierdzi ze dziala)

Zapisac wnioski w `~/.claude/projects/.../memory/`:
- `feedback_anti_spam_register.md` - zasada "kazdy publiczny endpoint = honeypot + rate limit + walidacja"

---

## Co jest **poza** Tier 1 (do zrobienia pozniej)

| Tier | Mechanizm | Czemu nie teraz |
|------|-----------|-----------------|
| 2 | Email weryfikacja (link aktywacyjny) | Wymaga SMTP setup (Resend/Mailgun), kolumny `is_email_verified` w bazie, endpoint `/api/verify-email/<token>`, modyfikacji loginu |
| 2 | Cloudflare przed Render (free) | Wymaga DNS CNAME, testow ze SSL, mozliwych problemow z origin |
| 3 | Cloudflare Turnstile / hCaptcha | Wymaga frontend + backend integration, klucze API, mniej irytujace niz reCAPTCHA ale jednak UI change |
| 3 | Blacklist disposable email domains | Lista 5000+ domen, trzeba aktualizowac, false positives |

---

## Akceptacja

Plan zatwierdzony do realizacji: **TAK / NIE** (do uzupelnienia po review)

Kolejnosc realizacji: 1 -> 2 -> 3 -> 4 -> 5 -> 6
