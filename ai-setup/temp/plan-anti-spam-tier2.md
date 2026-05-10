# Plan Tier 2: Email weryfikacja + Cloudflare przed Render

Tier 2 = realizujemy **po** Tier 1 i po potwierdzeniu ze Tier 1 dziala na produkcji
(min. tydzien obserwacji logow Render pod katem `[SECURITY]` i HTTP 429).

## Cel Tier 2

Dwa mechanizmy ktore razem lapia >99% spamu z minimalnym kosztem:
1. **Email weryfikacja** - link aktywacyjny. Konto utworzone ale `is_active=false`
   az do klikniecia w link z maila. Wymusza posiadanie prawdziwego maila.
2. **Cloudflare przed Render** - darmowy plan, dodaje rate limit globalny,
   anty-bot, ochrone DDoS. Tylko trzeba ustawic CNAME.

---

## KROK A - Email weryfikacja (link aktywacyjny)

### A.0. Decyzja: dostawca SMTP

Trzy realne opcje (wszystkie z darmowym tierem):

| Dostawca | Free tier | Plusy | Minusy |
|----------|-----------|-------|--------|
| **Resend** | 3000 mail/mc, 100/dzien | nowoczesne API, dobry dev experience, polski jezyk OK | nowy gracz (od 2023), free tier maly |
| **Mailgun** | 5000 mail/mc przez 3 mies, potem $35/mc | duzy, sprawdzony | po 3 mies platne |
| **Postmark** | 100/mc free, $15/mc 10k | najlepsza dostarczalnosc | najmniejszy free tier |
| **Brevo (Sendinblue)** | 300/dzien free na zawsze | duzo na free tier, panel PL | wolniejsze API, gorszy DX |

**Rekomendacja: Resend** - dla MVP 100 mail/dzien wystarczy z duzym zapasem
(spodziewam sie ~5-20 rejestracji dziennie max). Jesli wzrost - przesiadka na Brevo.

**Alternatywa: Gmail SMTP** - 500 mail/dzien, bezplatne ale wymaga aplikacyjnego
hasla i jest wolniejsze. Tylko jako backup jesli Resend nie zadziala.

### A.1. Setup Resend

1. Rejestracja na resend.com (darmowo)
2. Weryfikacja domeny lub uzycie `onboarding@resend.dev` (testowe, max 100/dzien
   tylko na adres rejestracyjny - nie nadaje sie na produkcje)
3. **Dla produkcji potrzebna wlasna domena** - mamy `kosa-h283.onrender.com` ale
   to subdomena Render (nie mozemy weryfikowac SPF/DKIM). Trzeba kupic domene
   (np. `besafefish.pl` ~50 zl/rok na nazwa.pl).
4. Po weryfikacji domeny - klucz API w `.env`

**Decyzja do podjecia:** czy kupujemy domene czy uzywamy testowej resend.dev?

Bez wlasnej domeny - emaile beda ladowac w SPAM (brak SPF/DKIM/DMARC), wiec
weryfikacja praktycznie nie zadziala. **Wlasna domena jest must-have dla Tier 2.**

### A.2. Schema bazy - migracja

**Plik: `app/SQL/migrations/2026_05_XX_email_verification.sql`**

```sql
-- Dodanie kolumn do weryfikacji emaila w tabeli users
ALTER TABLE public.users
    ADD COLUMN email_verified_at timestamptz,
    ADD COLUMN email_verification_token varchar(64),
    ADD COLUMN email_verification_sent_at timestamptz;

-- Index na token (uzywany w GET /api/verify-email/<token>)
CREATE INDEX idx_users_email_verification_token
    ON public.users(email_verification_token)
    WHERE email_verification_token IS NOT NULL;

-- Comment
COMMENT ON COLUMN public.users.email_verified_at IS 'Kiedy user kliknal link aktywacyjny. NULL = niepotwierdzony';
COMMENT ON COLUMN public.users.email_verification_token IS 'Token w URL aktywacyjnym (64 znaki hex). NULL po weryfikacji';
COMMENT ON COLUMN public.users.email_verification_sent_at IS 'Kiedy ostatnio wyslalismy mail (do rate limit ponownego wyslania)';

-- Migracja istniejacych userow - traktujemy jako zweryfikowanych
-- (zeby nie wybic im logowania po deploymencie)
UPDATE public.users
SET email_verified_at = created_at
WHERE email_verified_at IS NULL;
```

**Update [app/SQL/tables/users.sql](../../app/SQL/tables/users.sql)** - dodac te
kolumny do kanonicznej definicji.

**Update [app/SQL/supabase_migration.sql](../../app/SQL/supabase_migration.sql)** -
dodac do skryptu zbiorczego.

### A.3. Funkcja SQL - generowanie tokena

```sql
-- Plik: app/SQL/functions/generate_email_token.sql
CREATE OR REPLACE FUNCTION public.generate_email_token()
RETURNS varchar(64)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, extensions
AS $$
DECLARE
    token varchar(64);
BEGIN
    -- 32 bajty losowe -> 64 znaki hex
    token := encode(gen_random_bytes(32), 'hex');
    RETURN token;
END;
$$;
```

Wymaga rozszerzenia `pgcrypto` (juz jest w Supabase).

### A.4. Update funkcji `create_user_short`

Dodac generowanie tokena przy rejestracji:

```sql
CREATE OR REPLACE FUNCTION public.create_user_short(
    p_login varchar,
    p_email varchar,
    p_password varchar,
    p_role varchar DEFAULT 'user'
)
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, extensions
AS $$
DECLARE
    new_user_id integer;
    verification_token varchar(64);
BEGIN
    verification_token := generate_email_token();

    INSERT INTO users (
        login, email, password_hash, role,
        is_active, email_verification_token, email_verification_sent_at
    ) VALUES (
        p_login, p_email,
        extensions.crypt(p_password, extensions.gen_salt('bf', 12)),
        p_role,
        false,  -- !!! is_active=false do czasu weryfikacji
        verification_token,
        NOW()
    )
    RETURNING id INTO new_user_id;

    -- ... istniejaca logika auto-przypisania subskrypcji probnej

    RETURN new_user_id;
END;
$$;
```

**WAZNE**: `is_active=false` przy rejestracji **zlamie obecny login**! Trzeba zmienic
SQL w `/api/login`:

```sql
-- Stare (login.sql w server.py linia 191-200)
WHERE login = %s
  AND password_hash = extensions.crypt(%s, password_hash)
  AND is_active = true
  AND deleted_at IS NULL

-- Nowe - dwa scenariusze
SELECT id, is_active, email_verified_at FROM users
WHERE login = %s
  AND password_hash = extensions.crypt(%s, password_hash)
  AND deleted_at IS NULL
```

Logika w Pythonie:
```python
if not row:
    # zle haslo
    return jsonify({"ok": False, "msg": "Nieprawidlowa nazwa..."})

user_id, is_active, email_verified_at = row
if not email_verified_at:
    return jsonify({"ok": False, "msg": "Konto niepotwierdzone. Sprawdz maila i kliknij link aktywacyjny."}), 403
if not is_active:
    return jsonify({"ok": False, "msg": "Konto zablokowane."}), 403
```

### A.5. Endpoint `/api/verify-email/<token>`

**Plik: [app/website/server.py](../../app/website/server.py)**

```python
@app.route("/api/verify-email/<token>", methods=["GET"])
@limiter.limit("20 per hour")  # zeby nie brute-forcowali tokenow
def verify_email(token):
    """Aktywuje konto po klikneciu w link z maila."""
    if not token or len(token) != 64:
        return jsonify({"ok": False, "msg": "Nieprawidlowy token."}), 400

    try:
        cur = g.db_conn.cursor()
        cur.execute(
            """
            UPDATE users
            SET email_verified_at = NOW(),
                is_active = true,
                email_verification_token = NULL
            WHERE email_verification_token = %s
              AND email_verified_at IS NULL
            RETURNING id, login, email
            """,
            (token,),
        )
        row = cur.fetchone()
        g.db_conn.commit()
        cur.close()

        if not row:
            return jsonify({"ok": False, "msg": "Token nieprawidlowy lub juz uzyty."}), 404

        return jsonify({"ok": True, "msg": "Konto aktywowane! Mozesz sie zalogowac."})
    except Exception as e:
        g.db_conn.rollback()
        return jsonify({"ok": False, "msg": f"Blad weryfikacji: {e}"}), 500
```

### A.6. Funkcja wysylania maila (Resend)

**Nowy plik: `app/website/email_sender.py`**

```python
"""Wysylka mailow przez Resend API."""
import os
import sys
import json
import urllib.request
import urllib.error

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "noreply@besafefish.pl")
APP_URL = os.getenv("APP_URL", "https://kosa-h283.onrender.com")


def send_verification_email(to_email: str, username: str, token: str) -> bool:
    """Wysyla mail aktywacyjny. Zwraca True przy sukcesie. Fail-open."""
    if not RESEND_API_KEY:
        print("[WARN] RESEND_API_KEY brak - mail nie wyslany", file=sys.stderr, flush=True)
        return False

    verify_url = f"{APP_URL}/api/verify-email/{token}"
    html_body = f"""
    <h2>Witaj {username}!</h2>
    <p>Dziekujemy za rejestracje w BeSafeFish.</p>
    <p>Aby aktywowac konto, kliknij ponizszy link:</p>
    <p><a href="{verify_url}">Aktywuj konto</a></p>
    <p>Link wygasa po 24 godzinach.</p>
    <p>Jesli to nie Ty zarejestrowales konto - zignoruj ta wiadomosc.</p>
    """

    payload = {
        "from": RESEND_FROM_EMAIL,
        "to": [to_email],
        "subject": "Aktywuj konto BeSafeFish",
        "html": html_body,
    }

    try:
        req = urllib.request.Request(
            "https://api.resend.com/emails",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"[WARN] Resend send failed for {to_email}: {e}", file=sys.stderr, flush=True)
        return False
```

### A.7. Update `register()` w server.py

Po `create_user_short()` - pobranie tokena i wyslanie maila:

```python
cur.execute(
    "SELECT id, email_verification_token FROM users WHERE login = %s",
    (username,),
)
new_user_id, token = cur.fetchone()
conn.commit()
cur.close()

# Wyslanie maila aktywacyjnego (fail-open - jesli mail nie pojdzie, user moze
# poprosic o resend przez /api/resend-verification)
from email_sender import send_verification_email
sent = send_verification_email(email, username, token)

msg = "Konto utworzone! Sprawdz maila aby aktywowac konto."
if not sent:
    msg += " (Mail nie zostal wyslany - skontaktuj sie z adminem)"

return jsonify({"ok": True, "msg": msg})
```

### A.8. Endpoint `/api/resend-verification`

```python
@app.route("/api/resend-verification", methods=["POST"])
@limiter.limit("3 per hour; 5 per day")
def resend_verification():
    """Ponowne wyslanie linku aktywacyjnego (gdy poprzedni nie dotarl)."""
    data = request.get_json()
    email = (data.get("email") or "").strip()

    if not email:
        return jsonify({"ok": False, "msg": "Podaj adres email."}), 400

    try:
        cur = g.db_conn.cursor()
        # Tylko niezweryfikowani userzy z istniejacym tokenem
        cur.execute(
            """
            SELECT login, email_verification_token, email_verification_sent_at
            FROM users
            WHERE email = %s AND email_verified_at IS NULL AND deleted_at IS NULL
            """,
            (email,),
        )
        row = cur.fetchone()

        if not row:
            # Cicho udajemy sukces (zeby nie pomagac w enumeracji adresow)
            return jsonify({"ok": True, "msg": "Jesli podany adres istnieje, link zostal wyslany."})

        username, token, sent_at = row

        # Cooldown - max 1 mail co 5 minut na ten sam email
        if sent_at and (datetime.now(timezone.utc) - sent_at).total_seconds() < 300:
            return jsonify({"ok": False, "msg": "Poczekaj 5 minut przed kolejnym wyslaniem."}), 429

        # Update sent_at
        cur.execute(
            "UPDATE users SET email_verification_sent_at = NOW() WHERE email = %s",
            (email,),
        )
        g.db_conn.commit()
        cur.close()

        send_verification_email(email, username, token)
        return jsonify({"ok": True, "msg": "Link aktywacyjny wyslany ponownie."})

    except Exception as e:
        g.db_conn.rollback()
        return jsonify({"ok": False, "msg": f"Blad: {e}"}), 500
```

### A.9. Czyszczenie starych tokenow (lazy)

Token nie powinien zyc wiecznie. Lazy expiration (zgodnie z zasada techniczna #14):

W `verify_email()` dodac sprawdzenie:
```sql
UPDATE users
SET email_verified_at = NOW(), is_active = true, email_verification_token = NULL
WHERE email_verification_token = %s
  AND email_verified_at IS NULL
  AND email_verification_sent_at > NOW() - INTERVAL '24 hours'  -- token wazny 24h
RETURNING id, login, email
```

Jesli token starszy niz 24h - response "Token wygasl, poproś o nowy link".

### A.10. Update GUI ([app/gui/db.py](../../app/gui/db.py))

Po rejestracji w GUI - pokazac komunikat "Sprawdz maila".
Przy logowaniu - obsluzyc nowy error 403 "Konto niepotwierdzone" - dodac
przycisk "Wyslij ponownie link".

### A.11. Update strony ([app/website/index.html](../../app/website/index.html))

Po rejestracji - komunikat "Sprawdz maila aby aktywowac konto".
Dodac strone `/verify-success` i `/verify-failed` z odpowiednimi komunikatami.

### A.12. Render env vars do dodania

W Dashboard Render -> Environment:
```
RESEND_API_KEY=re_xxx (z resend.com)
RESEND_FROM_EMAIL=noreply@besafefish.pl
APP_URL=https://besafefish.pl  (po podpieciu domeny)
```

### A.13. Test calego flow

1. Rejestracja -> sprawdz maila -> kliknij link -> probuj sie zalogowac (powinno dzialac)
2. Rejestracja -> NIE klikaj linka -> probuj sie zalogowac -> "Konto niepotwierdzone"
3. Resend verification -> sprawdz drugi mail
4. Token > 24h -> probuj kliknac -> "Token wygasl"
5. Bot rejestruje 1000x z fake mailami -> nikt sie nie aktywuje, baza ma userow
   ale nieaktywnych - moze warto dodac cron do czyszczenia po 7 dniach?

### Ryzyka Tier 2 / Krok A

- **Mail w spamie** bez SPF/DKIM/DMARC. Wymaga wlasnej domeny i konfiguracji
  rekordow DNS w Resend. Bez tego cala feature praktycznie martwa.
- **Resend daily limit 100** - jesli atakujacy zarejestruje 100 fake kont w 1 dzien,
  zuzyje cala kwote i prawdziwi userzy nie dostana mailow. Mitigation: rate limit
  z Tier 1 (5 register/h/IP) + monitoring zuzycia w dashboard Resend.
- **Migration istniejacych userow** - musimy ustawic `email_verified_at = created_at`
  dla wszystkich obecnych userow, inaczej po deploycie nikt sie nie zaloguje.
- **Cooldown rejestracji** - jesli user nie dostanie maila w 5 min i bedzie
  klikac "Resend" co 30s -> dostanie 429. Trzeba pokazac countdown w UI.
- **Username/email enumeration** - `/api/resend-verification` musi cicho udawac sukces
  dla nieistniejacych adresow (zeby atakujacy nie sprawdzal jakie adresy juz sa
  w bazie). Juz zaplanowane.

---

## KROK B - Cloudflare przed Render

### B.0. Wymaganie wstepne

**Wlasna domena** (np. `besafefish.pl`). Cloudflare nie obsluguje subdomen
hostingowych typu `*.onrender.com` - musimy miec wlasna.

Jesli kupimy domene w Kroku A.1 - tu juz tylko podpinamy.

### B.1. Setup Cloudflare

1. Konto na cloudflare.com (darmowe)
2. Dodaj domene `besafefish.pl` -> Cloudflare skanuje istniejace DNS
3. Zmien nameservery domeny na CF (w panelu rejestratora, np. nazwa.pl):
   - `xxx.ns.cloudflare.com`
   - `yyy.ns.cloudflare.com`
4. Czekamy na propagacje (5min - 24h)
5. W Cloudflare DNS settings:
   - `CNAME` `besafefish.pl` -> `kosa-h283.onrender.com` (proxied: ON, oranzowa chmura)
   - `CNAME` `www` -> `kosa-h283.onrender.com` (proxied: ON)

### B.2. SSL/TLS w Cloudflare

W Cloudflare -> SSL/TLS -> Overview:
- Mode: **Full (strict)** - CF do origin po HTTPS, sprawdza certyfikat Render
- Render daje darmowy SSL automatycznie, wiec to dziala out-of-the-box

### B.3. Page Rules / WAF

W Cloudflare -> Security -> WAF:
- **Rate limit reguly** (free tier: 1 reguta gratis):
  - URL `*/api/register*` -> 10 requestow / 1 min / IP -> Block
  - To dziala **przed** dotrze do serwera, oszczedzajac connection pool
- **Bot Fight Mode** (free): wlaczyc - lapie znane boty (curl, wget, Python requests)
- **Security Level**: Medium (default)

### B.4. Caching - WAZNE

Cloudflare domyslnie cachuje statyczne pliki. Trzeba upewnic sie ze NIE cachuje
endpointow API:

Page Rules -> dodac:
- `besafefish.pl/api/*` -> Cache Level: Bypass

### B.5. Update Render konfiguracji

W Render Dashboard:
- Custom Domain -> dodaj `besafefish.pl`, `www.besafefish.pl`
- Render daje instrukcje weryfikacji (TXT record albo CNAME)

### B.6. Update kodu

**[app/website/server.py](../../app/website/server.py):**

Cloudflare wysyla prawdziwy IP usera w `CF-Connecting-IP` header. Musimy go uzywac
zamiast `X-Forwarded-For`:

```python
def _real_ip():
    """IP klienta - priorytet: CF, potem XFF, potem remote_addr."""
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip
    xff = request.headers.get("X-Forwarded-For", "")
    if xff:
        return xff.split(",")[0].strip()
    return get_remote_address()
```

**[app/gui/db.py](../../app/gui/db.py):**

Update API_URL:
```python
API_URL = "https://besafefish.pl"
```

**[app/website/index.html](../../app/website/index.html):**

Wszystkie linki do `kosa-h283.onrender.com` -> `besafefish.pl`.

**[README.md](../../README.md):**

Update linkow.

### B.7. Test po deploymencie

```bash
# Sprawdz czy Cloudflare jest aktywny (header CF-Ray)
curl -I https://besafefish.pl/

# Powinno: cf-ray: xxx, server: cloudflare

# Test rate limit Cloudflare (powinno blokowac przed 11-tym requestem)
for i in $(seq 1 15); do
    curl -X POST https://besafefish.pl/api/register \
      -H "Content-Type: application/json" \
      -d '{"username":"test","email":"t@t.pl","password":"12345678"}'
    echo ""
done
# 11+ powinno dostac 1015 (Cloudflare rate limit) lub 429
```

### Ryzyka Tier 2 / Krok B

- **Bledna konfiguracja DNS = strona offline** dla wszystkich userow do czasu
  fixu. Najlepiej robic w nocy / weekend gdy ruch maly.
- **Mismatched SSL** - jesli ustawimy Full zamiast Full(strict) - mozliwe
  ataki MITM. Full(strict) wymaga aktualnego cert na origin (Render auto-renewuje).
- **CF Bot Fight Mode false positives** - moze blokowac legalnych userow
  z agresywnymi extensionami przegladarki. Monitoring potrzebny.
- **Domena platna co rok** - musimy pamietac o przedluzeniu (50 zl/rok). Jesli
  domena wygasnie - aplikacja offline. Ustawic auto-renewal.

---

## Co po Tier 2

Po skutecznej implementacji powinnismy miec:

- Spam zatrzymany na 3 poziomach: Cloudflare (przed serwerem) -> Flask-Limiter
  (na serwerze) -> Honeypot (na endpoincie) -> Email weryfikacja (post-rejestracja)
- Wlasna domena z mailami branded (`@besafefish.pl`)
- Render free tier nie powinien sie juz zatykac przy spamie

**Co dalej:** Tier 3 (CAPTCHA + blacklist disposable email) - tylko jesli
mimo Tier 1+2 widzimy spam w logach.

---

## Akceptacja

Plan zatwierdzony do realizacji: **TAK / NIE** (do uzupelnienia po Tier 1)

Wymagane decyzje przed startem Tier 2:
- [ ] Kupujemy wlasna domene? Jaka? (besafefish.pl ~50zl/rok)
- [ ] Wybor SMTP: Resend / Brevo / inny?
- [ ] Cloudflare: tak/nie? (zalezne od domeny)
- [ ] Czy migrujemy istniejacych userow jako "zweryfikowani" (rekomendowane)?
