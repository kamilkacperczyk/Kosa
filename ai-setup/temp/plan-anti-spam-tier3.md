# Plan Tier 3: CAPTCHA + Blacklist disposable email

Tier 3 = realizujemy **tylko jesli** Tier 1+2 nie wystarczyly. Sprawdzamy logi
Render i Cloudflare przez 2-4 tygodnie po Tier 2 - jesli spam trafia do
bazy mimo wszystkiego, dopiero wtedy Tier 3.

## Cel Tier 3

Dwa mechanizmy ostatniej instancji:
1. **CAPTCHA (Cloudflare Turnstile)** - dla podejrzanego ruchu, niewidoczna
   gdy CF uznaje usera za bezpiecznego
2. **Blacklist disposable email domains** - odrzucanie tymczasowych adresow
   (mailinator.com, 10minutemail.com itp.)

---

## KROK A - Cloudflare Turnstile (CAPTCHA)

### A.0. Dlaczego Turnstile a nie reCAPTCHA?

| Cecha | reCAPTCHA v3 | hCaptcha | **Turnstile** |
|-------|--------------|----------|---------------|
| Free tier | 1M req/mc | Free | **Free, bez limitu** |
| Tracking userow | TAK (Google) | Mniej | **Brak** |
| Niewidoczny domyslnie | Tak ale slabo | Nie | **Tak, dobrze** |
| Polski jezyk | Tak | Tak | Tak |
| Setup | sredni | sredni | **prosty** |
| Integracja z CF | brak | brak | **natywna** (mamy CF z Tier 2) |

**Rekomendacja: Turnstile** - skoro mamy juz Cloudflare z Tier 2, integracja
trywialna. Plus brak trackingu Google to wartosc dla userow.

### A.1. Setup Turnstile

1. Cloudflare Dashboard -> Turnstile -> Add Site
2. Domain: `besafefish.pl`
3. Widget Mode: **Managed** (CF sam decyduje czy pokazac challenge czy nie -
   dla 95% userow niewidoczny, dla podejrzanych - challenge)
4. Skopiowac **Site Key** (publiczny) i **Secret Key** (do .env serwera)

### A.2. Frontend - dodanie widgeta

**[app/website/index.html](../../app/website/index.html)**

W `<head>` dodac script Turnstile:
```html
<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
```

W `<form id="registerForm">` przed buttonem submit:
```html
<div class="cf-turnstile"
     data-sitekey="0x4AAAAAAAxxxxxxxxxxxxx"
     data-callback="onTurnstileSuccess"
     data-theme="dark">
</div>
```

**[app/website/script.js](../../app/website/script.js)**

```javascript
var turnstileToken = null;

window.onTurnstileSuccess = function(token) {
    turnstileToken = token;
};

// W handlerze registerForm submit - przed fetch:
if (!turnstileToken) {
    msg.textContent = 'Potwierdz ze nie jestes botem.';
    msg.classList.add('error');
    return;
}

fetch('/api/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        username: username,
        email: email,
        password: password,
        website: honeypot,
        turnstile_token: turnstileToken
    })
});

// Po response - reset tokena (jednorazowy)
turnstileToken = null;
window.turnstile.reset();
```

### A.3. Backend - weryfikacja tokenu

**[app/website/server.py](../../app/website/server.py)**

Na poczatku pliku:
```python
TURNSTILE_SECRET_KEY = os.getenv("TURNSTILE_SECRET_KEY")


def _verify_turnstile(token: str, ip: str) -> bool:
    """Weryfikuje token Turnstile po stronie serwera. Fail-closed - bez tokena nie wpuszczamy."""
    if not TURNSTILE_SECRET_KEY or not token:
        return False
    try:
        payload = {
            "secret": TURNSTILE_SECRET_KEY,
            "response": token,
            "remoteip": ip,
        }
        req = urllib.request.Request(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data=urllib.parse.urlencode(payload).encode("utf-8"),
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("success", False)
    except Exception as e:
        print(f"[WARN] Turnstile verify failed: {e}", file=sys.stderr, flush=True)
        return False  # fail-closed - jesli CF nie odpowiada, blokujemy
```

W `register()`:
```python
turnstile_token = data.get("turnstile_token", "")
if not _verify_turnstile(turnstile_token, _real_ip()):
    return jsonify({"ok": False, "msg": "Weryfikacja anty-bot nie powiodla sie."}), 403
```

### A.4. Czy Turnstile w GUI desktop?

**Problem**: Turnstile to widget HTML, nie dziala w PySide6 natywnie.

Opcje:
1. **Embed QWebEngineView** w GUI - wstrzykuje widget HTML, otrzymuje token,
   wysyla do API. Skomplikowane, wymaga PySide6-WebEngine (~50 MB extra).
2. **Pomijac Turnstile dla GUI** - rejestracja w GUI ma `source: "gui"` -
   serwer rozroznia i nie wymaga tokena dla GUI. **Ryzyko**: atakujacy wysyla
   `source: "gui"` z webu omijajac Turnstile.
3. **Wymusic rejestracje przez WWW** - GUI nie ma juz formularza rejestracji,
   tylko logowanie. Link "Zarejestruj sie" otwiera przegladarke. **Najlepsze rozwiazanie**.

**Rekomendacja: opcja 3**. GUI desktopowe i tak jest "trusted" w pewnym sensie -
user juz pobral .exe. Rejestracja w przegladarce = jeden flow do utrzymania
+ Turnstile dziala dla wszystkich.

**Zmiany w GUI:**
- `register_screen.py` -> tylko link "Zarejestruj sie na stronie" otwierajacy
  przegladarke (`QDesktopServices.openUrl(QUrl("https://besafefish.pl/#register"))`)
- `register_user()` w [app/gui/db.py](../../app/gui/db.py) -> usuniete
- Po rejestracji w przegladarce -> user dostaje mail aktywacyjny -> klika link ->
  wraca do GUI i loguje sie

To dodatkowo upraszcza Tier 2 (jeden flow rejestracji = jedna sciezka emailowa).

### A.5. Test

1. Open `besafefish.pl` w przegladarce -> formularz rejestracji ma widget Turnstile
   (zwykle niewidoczny, czasem checkbox)
2. Wypelnij i submit -> dostajesz token, request idzie z tokenem
3. Sprobuj submit bez tokena (zhackowany frontend) -> 403 "Weryfikacja anty-bot"
4. Sprobuj curl bez tokena -> 403
5. Sprawdz logi - ile spam-prob zatrzymanych

### Ryzyka Tier 3 / Krok A

- **False positives** - Turnstile czasem blokuje legalnych userow (Tor, VPN,
  agresywne extensiony). User musi mieć opcje retry. Monitoring zuzycia w CF.
- **Zlezenie od Cloudflare** - jesli CF ma awarie, Turnstile nie weryfikuje.
  Decyzja: fail-closed (nikt sie nie rejestruje przez kilka minut) czy fail-open
  (przepuszczamy ale logujemy)? **Rekomendacja: fail-closed** dla MVP, lepiej
  brak rejestracji niz spam.
- **Zmiana flow GUI** - rezygnacja z rejestracji w GUI to widoczna zmiana UX.
  Trzeba to wyjasnic w UI ("Rejestracja w przegladarce dla bezpieczeństwa").
- **Akcesibilnosc** - userzy z czytnikami ekranu / niewidomi - Turnstile ma
  alternatywne challenges (audio), ale to slabsze niz wizualne.

---

## KROK B - Blacklist disposable email domains

### B.0. Co to "disposable email"?

Domeny ktore daja tymczasowe maile:
- `mailinator.com`, `tempmail.com`, `10minutemail.com`, `guerrillamail.com`,
  `throwaway.email`, `yopmail.com` - lista tysiecy domen
- Atakujacy moze zarejestrowac konto, kliknac w link aktywacyjny (mail dostepny
  na publicznej stronie), uzyc konta i porzucic

### B.1. Zrodlo listy

Github maintainowane listy (~10k domen):
- https://github.com/disposable-email-domains/disposable-email-domains
- https://github.com/martenson/disposable-email-domains

Format: jeden domain per linia, plain text.

**Strategia**: pobieranie listy podczas builda + cache w pamieci serwera. Refresh
co miesiac (manualny commit) - lista zmienia sie wolno.

### B.2. Plik z lista

**Nowy plik: `app/website/disposable_domains.txt`**

```
mailinator.com
10minutemail.com
guerrillamail.com
yopmail.com
... (~10k linii)
```

Sciagniecie:
```bash
curl -o app/website/disposable_domains.txt \
  https://raw.githubusercontent.com/disposable-email-domains/disposable-email-domains/master/disposable_email_blocklist.conf
```

Commit do repo (~150 KB), update co miesiac.

### B.3. Loading w server.py

**[app/website/server.py](../../app/website/server.py)**

```python
import pathlib

DISPOSABLE_DOMAINS = set()

def _load_disposable_domains():
    """Laduje liste z pliku do seta (fast lookup)."""
    global DISPOSABLE_DOMAINS
    try:
        path = pathlib.Path(__file__).parent / "disposable_domains.txt"
        with open(path, "r", encoding="utf-8") as f:
            DISPOSABLE_DOMAINS = {line.strip().lower() for line in f if line.strip()}
        print(f"[INFO] Loaded {len(DISPOSABLE_DOMAINS)} disposable domains", file=sys.stderr, flush=True)
    except Exception as e:
        print(f"[WARN] Failed to load disposable domains: {e}", file=sys.stderr, flush=True)

# Wywolanie raz na starcie workera
_load_disposable_domains()


def _is_disposable_email(email: str) -> bool:
    """Sprawdza czy domena emaila jest na blackliscie."""
    domain = email.split("@")[-1].lower()
    return domain in DISPOSABLE_DOMAINS
```

W `register()`:
```python
if _is_disposable_email(email):
    return jsonify({"ok": False, "msg": "Adresy email tymczasowe nie sa akceptowane. Uzyj prawdziwego adresu."}), 400
```

### B.4. Test

```bash
curl -X POST https://besafefish.pl/api/register \
  -d '{"username":"spammer","email":"x@mailinator.com","password":"12345678"}'
# Spodziewane: 400 "Adresy email tymczasowe nie sa akceptowane"

curl -X POST https://besafefish.pl/api/register \
  -d '{"username":"normal","email":"x@gmail.com","password":"12345678"}'
# Spodziewane: ok=true (jesli Tier 1+2 OK)
```

### B.5. Update raz na miesiac

Manualny workflow (commit w repo):
1. Pobranie nowej wersji z github raz na miesiac
2. Diff vs poprzednia wersja - widac ktore domeny doszly
3. Commit `chore: update disposable email blacklist (X new domains)`
4. Push -> Render redeploy automatycznie laduje nowa liste

Mozna zautomatyzowac przez GitHub Action (osobny scheduled workflow) - ale dla MVP
manualny update wystarczy.

### Ryzyka Tier 3 / Krok B

- **False positives** - czasem legalne firmy maja maila na "podejrzanej" domenie
  (np. wlasciciele domen typu `simpemail.com` ktorzy sami siebie nie blokuja).
  Jesli user zglasza problem - dodajemy whitelist.
- **Lista nieaktualna** - nowe disposable domains powstaja codziennie. Update
  raz na miesiac to kompromis - 100% nigdy nie zlapiesz, ale 95% wystarczy.
- **Wielkosc listy** - 150 KB w repo + 150 KB w pamieci servera. Akceptowalne.
- **Atakujacy uzywa wlasnej domeny** - kupuje `xyzspam.com` za 20zl/rok i ma
  unique-domain. Wtedy lista nic nie da. Ale to podnosi koszt ataku - filtruje
  amatorow.

---

## Plan rollout Tier 3

**WAZNE**: Tier 3 to ostatecznosc. Najpierw Tier 1+2 i obserwacja przez 2-4 tygodnie.

Sygnaly ze Tier 3 jest potrzebny:
- Logi pokazuja >10 udanych rejestracji dziennie z fake mailami (mimo Tier 2 -
  np. user podaje `mailinator` i Resend rzeczywiscie wysyla mail, atakujacy
  klika link i konto jest aktywne)
- Cloudflare WAF lapie >100 prob/h ale spam i tak przechodzi
- Wzrost zuzycia Resend daily limit przez fake rejestracje

Jesli zadnego z tych sygnalow - Tier 3 niepotrzebny. **Premature optimization.**

---

## Co po Tier 3

Po Tier 1+2+3 powinnismy miec system odporny na 99.9% spamu:

| Warstwa | Co lapie |
|---------|----------|
| Cloudflare WAF + Bot Fight Mode | Boty z prostymi user-agentami, znane skrypty atakow |
| Cloudflare Turnstile | Boty udajace przegladarki (Puppeteer/Playwright bez modyfikacji) |
| Flask-Limiter | Spam z jednego IP nawet po obejsciu CF |
| Honeypot field | Boty wypelniajace wszystkie pola formularza |
| Email validation regex | Smieciowe formaty |
| Disposable email blacklist | Tymczasowe maile typu mailinator |
| Email weryfikacja (link) | Wszystko co przesle bez prawdziwej skrzynki |

**Co poza Tier 3 (jesli mimo wszystko spam):**
- Phone verification (SMS) - drogie ($0.01-0.05/SMS), poprawia user friction
- IP reputation API (np. abuseipdb) - dodatkowy lookup, koszt
- Manual approval - admin akceptuje kazdego nowego usera. Skaluje sie zle ale
  100% pewne.
- Behavioral analytics - czas wypelniania formularza, ruchy myszki. Skomplikowane.

Te poza zakresem normalnego MVP.

---

## Akceptacja

Plan zatwierdzony do realizacji: **TAK / NIE / NIEPOTRZEBNE** (do uzupelnienia
po obserwacji Tier 1+2 przez 2-4 tygodnie)

Decyzje przed startem Tier 3:
- [ ] Czy logi pokazuja realny problem ze spamem mimo Tier 1+2?
- [ ] Turnstile: tak/nie? (zalezne od Cloudflare z Tier 2)
- [ ] Disposable blacklist: tak/nie? (zawsze warto, niewielki koszt)
- [ ] Czy rezygnujemy z rejestracji w GUI desktop? (rekomendowane przy Turnstile)
