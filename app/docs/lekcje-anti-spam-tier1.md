# Lekcje z sesji Tier 1 anti-spam (2026-05-10)

Sesja zaczela sie od pytania "czy ktos moze spamowac rejestracja?" i analizy
endpointu `/api/register`. Brak jakiejkolwiek ochrony - ani rate limit, ani
captcha, ani walidacji formatu email. Wynikiem sa trzy mechanizmy ochrony
zaimplementowane w jednym commicie + powazna dziura znaleziona przy okazji.

Wnioski podzielone na obszary:

- A) Mechanizmy ochrony rejestracji (3 warstwy)
- B) Flask-Limiter - integracja i kolejnosc hookow
- C) Dziury znalezione przy okazji (do naprawy w Tier 1.5)
- D) Pre-commit hook - false positives
- E) Meta-lekcja: priorytet ataku vs priorytet implementacji

---

## A) Mechanizmy ochrony rejestracji

### A1. Honeypot field - cicho oszukujemy boty

**Commit:** `f1f9f07 feat: Tier 1 anti-spam rejestracji`

**Co zaimplementowane:**

Ukryte pole `<input name="website">` w formularzu rejestracji
([app/website/index.html](../website/index.html)), umieszczone offscreen
przez `position:absolute; left:-9999px; aria-hidden="true"`.

Boty wypelniaja wszystkie pola formularza automatycznie. Ludzie nie widza
tego pola (offscreen + `tabindex="-1"` + `autocomplete="off"`).

Backend ([server.py:165-170](../website/server.py#L165-L170)) sprawdza
czy `data.get("website")` jest niepuste. Jesli tak - **zwraca `ok=true`
z komunikatem sukcesu, ale NIE tworzy usera w bazie**. Loguje `[SECURITY]`
do stderr (Render logs).

#### L-A1. Honeypot fake-success > jawny error

Bot ktory dostal jasny error 403 "honeypot triggered" wie ze jego strategia
nie dziala i probuje innej. Bot ktory dostal `ok=true` myśli ze konto
zostalo zalozone i odchodzi. **Cicho oszukujemy.**

To samo dotyczy enumeracji (`/api/resend-verification` planowany w Tier 2):
nigdy nie potwierdzaj ze adres istnieje/nie istnieje. Zawsze ten sam komunikat.

### A2. Rate limit per IP

**Co zaimplementowane:**

Flask-Limiter ([server.py:64-69](../website/server.py#L64-L69)) z in-memory
storage, dekoratory na endpointach:
- `/api/register`: 5/h, 20/dzien per IP
- `/api/login`: 10/min, 100/h per IP

#### L-A2. In-memory storage wystarcza dla single-worker setup

Z `gunicorn.conf.py` mamy `workers=2, threads=2`. Niby dwa workery, ale na
**Render free tier** w praktyce dzialamy w trybie pojedynczego procesu (limity
RAM 512MB, zwykle jeden worker odpowiada). Storage in-memory oznacza:
- Reset licznikow przy restarcie workera (Render free tier restartuje co kilka godzin)
- Niespojnosc miedzy workerami jesli sa dwa (jeden moze dac przepustke ktora drugi by zablokowal)

Akceptowalne dla MVP. Dla produkcji (>1000 req/s, multi-worker, multi-instance):
przesiadka na Redis (`storage_uri="redis://..."`) gdy bedzie potrzebne.

#### L-A3. `_real_ip()` - X-Forwarded-For przy proxy

[server.py:51-60](../website/server.py#L51-L60). Render jest za proxy,
`request.remote_addr` daje IP proxy a nie usera. Trzeba czytac `X-Forwarded-For`:

```python
def _real_ip():
    xff = request.headers.get("X-Forwarded-For", "")
    if xff:
        return xff.split(",")[0].strip()
    return get_remote_address()
```

XFF moze miec wiele IP (lancuch proxy), pierwszy element to oryginalny klient.

To samo bedzie potrzebne dla **Cloudflare** (Tier 2) - tam header to
`CF-Connecting-IP` i ma priorytet nad XFF.

#### L-A4. Custom 429 handler zwraca JSON, nie HTML

Bez handlera Flask-Limiter zwraca generyczny HTML "Too Many Requests"
(Werkzeug default). GUI/frontend dostawalby HTML zamiast JSON i parsowanie
by padlo. [server.py:72-78](../website/server.py#L72-L78):

```python
@app.errorhandler(429)
def _ratelimit_handler(e):
    return jsonify({
        "ok": False,
        "msg": "Zbyt wiele prob. Sprobuj ponownie za chwile.",
    }), 429
```

Wzorzec dla wszystkich custom error handlerow w API: zachowaj **strukture
odpowiedzi spojna** (zawsze JSON z `ok` + `msg`).

### A3. Walidacja email regex

**Co zaimplementowane:**

Regex `^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$` w trzech miejscach:
- [server.py:48](../website/server.py#L48) - autoryzacja serwerowa
- [script.js:54](../website/script.js#L54) - walidacja klienta WWW
- [gui/db.py:18](../gui/db.py#L18) - walidacja klienta GUI

Plus limit dlugosci 254 znaki (RFC 5321).

#### L-A5. Walidacja po obu stronach (klient + serwer), NIE polegac na frontendzie

Walidacja na kliencie = lepszy UX (instant feedback). Walidacja na serwerze =
bezpieczenstwo (atakujacy moze ominac frontend). **Oba sa potrzebne, nie
zamiennie.**

Regex ten sam w obu miejscach -> kazda zmiana **musi byc zsynchronizowana**.
Jesli zmienimy regex na serwerze a zapomnimy na kliencie - frontend bedzie
odrzucal adresy ktore serwer akceptuje (ok, irytujace) lub akceptowal ktore
serwer odrzuca (zle - user wypelnia formularz, dostaje server error).

Na przyszlosc: rozwazyc wspolna definicje regex w jednym miejscu (np. plik
JSON z konfiguracja zaladowany przez backend i serwowany do frontendu).

---

## B) Flask-Limiter - integracja

### B1. Kolejnosc rejestracji hookow ma znaczenie

**Wazna zaleznosc:** Limiter musi byc utworzony **przed** deklaracja
`@app.before_request def _before_request()`, ktory pobiera connection
z poola.

W [server.py](../website/server.py):
- Linia 64: `Limiter(app=app, ...)` - rejestruje swoj `before_request` hook (rate limit check)
- Linia 99: `@app.before_request def _before_request()` - rejestruje nasz hook (pool getconn)

Flask wykonuje `before_request` hooki **w kolejnosci rejestracji**. Limiter
jest zarejestrowany pierwszy -> jego rate limit check idzie pierwszy.

#### L-B1. Skutek: rate limit chroni connection pool

Jesli atakujacy przekroczy limit (5/h register, 10/min login):
- 6-ty request: Limiter zwraca 429 **bez dotarcia do `_before_request`**
- Connection pool **NIE jest dotykany**
- Baza danych **NIE jest dotykana**

To jest **dokladnie ta wartosc** rate limitu - chroni pool (4 connection)
i baze przed przeciazeniem.

**Gdyby kolejnosc byla odwrotna** (`Limiter` po `_before_request`): kazdy
request zablokowany przez limit i tak by pobieral connection z poola, czyli
atakujacy mogby wyczerpac pool nawet z 429.

### B2. Honeypot liczy sie do limitu

Dekorator `@limiter.limit(...)` jest stosowany **przed** wywolaniem funkcji.
Czyli **kazdy request** liczy sie do limitu, nawet ten ktory potem zostanie
zatrzymany przez honeypot lub walidacje email.

To jest **dobre** - bot ktory spamuje fake polem honeypotem **tez** sie
zlapie na rate limit po 5 prob.

#### L-B2. Smoke test pokazal kumulacje requestow

Smoke test 4 (rate limit) zaczal blokowac juz przy 4-tym requeście w petli,
nie 6-tym. Powod: requesty z testu 2 (honeypot) i testu 3 (walidacja email)
**rowniez sie liczyly do limitu 5/h** (bo dekorator jest stosowany dla calego
endpointu, nie tylko dla "udanych" wywolan).

Lekcja: testujac rate limit, odlicz **wszystkie** wywolania endpointu od
wczesniejszych testow w tej samej godzinie/IP.

---

## C) Dziury znalezione przy okazji

Podczas analizy `server.py` wyplynely problemy ktorych celem nie byl Tier 1,
ale wymagaja uwagi.

### C1. POWAZNE: `/api/round/use` bez autoryzacji

**Status:** NIENAPRAWIONE, do naprawy w Tier 1.5

**Co**: endpoint [/api/round/use:395](../website/server.py#L395) przyjmuje
`user_id` z JSON body **bez weryfikacji ze user jest zalogowany**:

```python
user_id = data.get("user_id")
# ...
cur.execute("SELECT * FROM check_and_increment_rounds(%s)", (user_id,))
```

**Wektor ataku:**

1. Atakujacy zaklada konto (legalnie albo przez bypass), dostaje swoje user_id
2. Wywoluje POST `/api/round/use` z **dowolnym user_id** w body (1, 2, 3, ..., N)
3. Funkcja `check_and_increment_rounds` inkrementuje rundy **dowolnemu userowi**
4. Wszyscy userzy maja **wyczerpany limit 50 rund dziennie** -> bot legalny im nie startuje

Jest to **gorsza** dziura niz spam rejestracji, bo dotyczy aktualnych userow
i nie da sie zalatac samym rate limitem (atakujacy moze rotowac IP).

**Fix wymaga:**
- Sesji/JWT - login zwraca token, kazdy chroniony endpoint sprawdza token
- LUB prostszy: weryfikacja `user_id` z body **vs** cos co serwer wie o
  zalogowanym userze (cookie, basic auth, signed token)

Tier 1.5 = osobna sesja. Plan w `ai-setup/temp/` po zaakceptowaniu zakresu.

### C2. 6 endpointow bez rate limitu

Tylko `/api/register` i `/api/login` maja dekorator. Pozostale:

- `GET /api/health` - lekkie ale zatrzymuje connection
- `GET /api/subscription/<user_id>` - **enumeracja!** atakujacy moze odpytywac id 1, 2, 3...
- `GET /api/payments/<user_id>` - to samo
- `GET /api/usage/<user_id>` - to samo
- `POST /api/round/use` - patrz C1
- `GET /api/plans` - lekkie ale tez bez limitu

#### L-C1. Dodanie Limitera do jednego endpointu = trzeba zrewidowac wszystkie pozostale

Latwo zapomniec ze inne endpointy istnieja i sa narazone tak samo. Smoke test
Tier 1 nie pokazalby tego problemu, bo nie testowalismy tych endpointow.

**Reguła dla Tier 1.5:** kazdy publiczny endpoint ma `@limiter.limit(...)` **albo**
`@require_auth` **albo** oboje. Dla read-only endpointow (subscription, payments,
usage, plans, health) - rate limit per IP. Dla mutate (round/use) - auth.

---

## D) Pre-commit hook - false positives

### D1. Stary regex zbyt szeroki

**Commit:** `03d4886 chore: poprawa pre-commit hook - eliminacja false positives`

Stary regex `password\s*[:=]` lapil **kazde** wystapienie w kodzie:
- `password = self._password_input.text()` - lokalna zmienna z metody UI
- `password = data.get("password")` - przypisanie z dict
- `def func(password: str)` - parametr funkcji
- `var password = document.getElementById(...)` - JS zmienna
- `body: { password: password }` - JSON key z value-zmiennej

Wszystkie to **false positives**. Hook blokowal Tier 1 commit za prawidlowy
kod.

Nowy regex: `password\s*[:=]\s*["'][^"'$]{3,}` - wymaga **literala stringa**
(z cudzyslowem) o dlugosci min 3 znakow po znaku przypisania.

#### L-D1. Pre-commit hook musi rozrozniac literal string vs zmienna

Wzorzec: `(slowo_klucz)\s*[:=]\s*["']\w{N,}` gdzie:
- `\s*` - opcjonalne biale znaki
- `[:=]` - znak przypisania (Python `=`, YAML `:`, JSON `:`)
- `\s*` - opcjonalne biale znaki po
- `["']` - **wymagany** cudzyslow (literal string)
- `\w{N,}` lub `[^"']{N,}` - minimum N znakow w cudzyslowach

Dla password N=3 (haslo nie jest dluzsze niz konfiguracyjny token), dla
token/api_key N=8 (typowe sekrety sa dlugie).

Wyjatki ktore nadal dzialaja jako szerokie matche (bo nie maja false
positives w typowym kodzie):
- `mysql://`, `postgres://`, `mongodb://`, `redis://` (connection strings)
- `BEGIN ... PRIVATE KEY` (klucze prywatne)
- `AKIA[0-9A-Z]{16}` (AWS access keys - specyficzny pattern)
- `sk-...`, `ghp_...` (OpenAI/GitHub tokens - specyficzny prefix)

#### L-D2. Hook w `setup_hooks/` vs aktywny w `.git/hooks/`

`setup_hooks/pre-commit` jest **wersjonowany** w repo. `.git/hooks/pre-commit`
jest **lokalna kopia** ktora git faktycznie uruchamia. Po zmianie zrodlowego
hooka trzeba **rzecznie skopiowac** do `.git/hooks/`:

```bash
cp setup_hooks/pre-commit .git/hooks/pre-commit
```

Latwa pulapka: zmienisz `setup_hooks/pre-commit`, scommitujesz, ale lokalnie
git wciaz uzywa starej kopii. Inni klonujacy repo musza pamietac o instalacji
hooka recznie.

Rozwiazanie: dodac `setup-hooks.sh` ktory robi ten copy + chmod +x. Albo
przeniesc na `pre-commit` framework (uniwersalny) jesli kiedys bedzie wiecej
hookow.

---

## E) Meta-lekcja: priorytet ataku vs priorytet implementacji

### E1. Zaczalem od najmniej krytycznej dziury

User pytal o spam rejestracji. Zatrzymalem sie na tym i zaplanowalem 3-tier
strategy. **Przy okazji** podczas analizy `server.py` zobaczylem dziure
w `/api/round/use` (sabotaz limitu kazdego usera bez auth) - duzo
powazniejszy problem niz spam rejestracji.

Powinienem byl **przerwac plan Tier 1**, pokazac dziure C1 jako priorytet,
i zapytac usera "to jest gorsze, robimy najpierw to?". Zamiast tego
zrealizowalem caly Tier 1, dziurke pokazalem dopiero w jednym z pozniejszych
pytan.

#### L-E1. Gdy znajdziesz powazniejszy problem podczas implementacji - przerwij i pokaz user

Threat model nalezy aktualizowac w czasie rzeczywistym. Jesli atakujacy
moze zrobic gorsza krzywde (sabotaz aktualnych userow) niz to co robimy
w naszym planie (spam rejestracji nowych userow) - **stop, zmiana priorytetu**.

User ma prawo zdecydowac czy:
- Zmieniamy plan i robimy najpierw to gorsze
- Robimy planowane (spam) bo jest szybsze i potem to gorsze
- Robimy oboje rownolegle

**Zle**: kontynuacja planu bez powiedzenia uzytkownikowi. To pozbawia go
informacji do decyzji.

### E2. Smoke test na produkcji = obowiazek przy klasie zmian D5

Klasa zmian 2 (`app/website/server.py`) = push na main = auto-deploy na Render.

Lekcja: **PO** pushu i redeploy zawsze zrob smoke test na produkcji. Z lekcji
v1.2.6 sekcja "L-D5. Push na main != bezpieczna operacja". Tym razem zrobilem
smoke test (4 przypadki: health, honeypot, walidacja, rate limit) i znalazlem
ze kumulacja requestow z testow wczesniej niz spodziewalem - niegrozne, ale
gdyby honeypot nie dzialal albo Limiter nie chronil pool-a, smoke test by
to wykazal.

Bez smoke testu: wszystkie userzy odczuwaja blad zanim my sie dowiemy.

### E3. Test lokalny niepelny != brak testu lokalnego

Lokalnie nie mialem `.env` z `DATABASE_URL_ADMIN`, wiec **petla testow
e2e nie byla mozliwa**. Ale lokalnie zaladowanie serwera (Flask + Flask-Limiter)
**zadzialalo** - syntaksa OK, integracja Limiter z Flask OK. Sam fakt ze
serwer wstaje to ~50% testu.

Lekcja: jesli pelny test lokalny niemozliwy (brak DB, brak credentials), zrob
**czesciowy test ktory weryfikuje co da sie zweryfikowac** (import + boot
serwera + struktura odpowiedzi przy bledzie). Smoke test produkcji uzupelnia
reszte.

---

## Co poszlo dobrze (warto powtarzac)

- **Plan Tier 1/2/3 przed implementacja**: zamiast wszystkiego naraz, podzial
  na warstwy z konkretnym celem kazdej. Pozwolilo zaakceptowac MVP (Tier 1)
  i odlozyc kosztowne rzeczy (domena, SMTP) do Tier 2.

- **Honeypot przed rate limit**: kolejnosc warstw ma znaczenie. Honeypot
  oszukuje boty bezkosztowo, rate limit chroni infra. Razem dzialaja
  multiplikatywnie.

- **Smoke test po deploy**: 4 testy (health, honeypot, walidacja, rate limit)
  wykonane curl-em w 30 sekund. Wczesnie wykryta kumulacja requestow.

- **Memory dla siebie**: zapis lekcji `feedback_retrospective_proactive.md`
  ma na celu nigdy wiecej nie czekac na "czemu nie zaproponowales sam?".

## Co poszlo zle (do poprawy)

- **Brak proaktywnej retrospektywy**: user musial mi przypomniec po smoke
  tescie. Naprawione przez memory feedback - patrz wyzej.

- **Pozno zauwazona dziura `/api/round/use`**: powinienem byl pokazac w fazie
  analizy `server.py`, nie w jednym z pozniejszych pytan o "boty tworzace
  polaczenia". Patrz L-E1.

- **Kumulacja requestow w smoke tescie**: nie liczylem ze testy 2 i 3 zuzyja
  sloty rate limitu. Maly blad obserwacji, niegrozny, ale typu "powinienem
  byl wiedziec".

---

## Linki

- Plan: [ai-setup/temp/plan-anti-spam-rejestracji.md](../../ai-setup/temp/plan-anti-spam-rejestracji.md)
- Tier 2 (kolejne): [ai-setup/temp/plan-anti-spam-tier2.md](../../ai-setup/temp/plan-anti-spam-tier2.md)
- Tier 3 (ostatecznosc): [ai-setup/temp/plan-anti-spam-tier3.md](../../ai-setup/temp/plan-anti-spam-tier3.md)
- Commit Tier 1: `f1f9f07`
- Commit pre-commit hook: `03d4886`
