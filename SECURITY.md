# Bezpieczenstwo - BeSafeFish

## Zasady bezpieczenstwa projektu

### 1. NIGDY nie commituj wrazliwych danych

Do repo NIE WOLNO dodawac:
- Hasel, tokenow, kluczy API
- Connection stringow do baz danych
- Kluczy prywatnych (SSH, PEM, PFX)
- Danych logowania (login/haslo do czegokolwiek)
- Webhookow, adresow serwerow produkcyjnych

### 2. Jak przechowywac sekrety

- Uzyj pliku `.env` (jest w .gitignore - nie trafi do repo)
- Lub zmiennych srodowiskowych systemu
- Pliki `config.local.*` i `*.secret` sa automatycznie ignorowane

### 3. Pre-commit hook

Repo ma **pre-commit hook** ktory automatycznie:
- Skanuje kazdy commit pod katem hasel, tokenow, kluczy, connection stringow
- **Blokuje commit** jesli wykryje cos podejrzanego
- Pokazuje dokladnie ktory plik i jaka linia jest problemem

Zrodlo hooka: `setup_hooks/pre-commit` (wersjonowane w repo).
Zainstalowany hook: `.git/hooks/pre-commit` (lokalna kopia).

Instalacja po sklonowaniu repo:
```
cp setup_hooks/pre-commit .git/hooks/pre-commit
```

Obejscie (tylko po weryfikacji ze to false positive):
```
git commit --no-verify
```

### 4. .gitignore

Plik `.gitignore` chroni przed przypadkowym dodaniem:
- `.env`, `.env.*` - pliki srodowiskowe
- `*.pem`, `*.key`, `*.p12`, `*.pfx` - klucze i certyfikaty
- `config.local.*`, `credentials.*`, `*.secret` - lokalna konfiguracja
- `id_rsa*` - klucze SSH
- `.vscode/settings.json` - lokalne ustawienia edytora

### 5. Copilot Agent / Claude Agent

Plik `.github/copilot-instructions.md` ogranicza GitHub Copilot Agent:
- Operuje WYLACZNIE w obrebie workspace BeSafeFish
- NIGDY nie czyta plikow poza projektem (klucze SSH, tokeny, .env systemowe)
- NIGDY nie wyswietla zmiennych srodowiskowych z sekretami
- Przed kazdym commitem audytuje pliki pod katem wrazliwych danych

### 6. Co robic gdy wyciekna dane

Jesli przypadkowo scommitowales wrazliwe dane:

1. **NATYCHMIAST** zmien haslo/token/klucz ktory wyciekl
2. Usun dane z kodu i scommituj poprawke
3. Jesli dane trafily do historii Git - uzyj `git filter-branch` lub `BFG Repo Cleaner`
4. Sam commit z usunieciem NIE wystarczy - Git pamieta cala historie

## Ochrona endpointow API

### Rate limit (Flask-Limiter)

Endpointy chronione dekoratorem `@limiter.limit(...)`:
- `/api/register`: 5/h, 20/dzien per IP
- `/api/login`: 10/min, 100/h per IP

Endpointy **bez** rate limitu (do dodania w Tier 1.5):
- `/api/health`, `/api/subscription/<id>`, `/api/payments/<id>`,
  `/api/usage/<id>`, `/api/round/use`, `/api/plans`

Konfiguracja: `Limiter(key_func=_real_ip, storage_uri="memory://")` -
identyfikacja klienta z `X-Forwarded-For` (Render za proxy), in-memory
storage dla single-worker.

### Honeypot na rejestracji

Formularz rejestracji ma ukryte pole `<input name="website">` (CSS off-screen).
Bot wypelnia, czlowiek nie. Backend cicho udaje sukces (`ok=true`) bez
tworzenia usera w bazie + log `[SECURITY]` do stderr (Render logs).

### Walidacja inputu

- email: regex `^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$` + max 254 znaki (RFC 5321)
- username: min 3 znaki
- password: 8-64 znaki

Walidacja zarowno na kliencie (UX, instant feedback) jak i serwerze (security).

### Znane dziury (do naprawy w Tier 1.5)

- `/api/round/use` przyjmuje `user_id` z body bez weryfikacji autoryzacji.
  Atakujacy moze inkrementowac dzienne rundy dowolnemu userowi (sabotaz limitu).
  Wymaga sesji/JWT.

Pelne lekcje i analiza: [app/docs/lekcje-anti-spam-tier1.md](app/docs/lekcje-anti-spam-tier1.md).
