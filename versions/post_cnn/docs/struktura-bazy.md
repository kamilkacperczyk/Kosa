# Struktura bazy danych - BeSafeFish

## Diagram zaleznosci

```
users (1) ──────< login_history (N)
  │
  │ (1)
  ├──────< user_subscriptions (N) >──────── subscription_plans (1)
  │                │
  │                │ (1)
  │                └──────< payments (N)
  │
  └── self-reference (created_by)

audit_log ← triggery z: users, user_subscriptions, payments
```

## Tabele

| Tabela | Opis | Triggery |
|--------|------|----------|
| users | Uzytkownicy systemu | set_updated_at, audit_users |
| subscription_plans | Plany subskrypcyjne (Darmowy, Premium) | set_updated_at |
| user_subscriptions | Subskrypcje uzytkownikow | set_updated_at, audit_subscriptions |
| payments | Historia platnosci | set_updated_at, audit_payments |
| login_history | Historia logowan | brak |
| audit_log | Log audytowy (auto) | brak (cel triggerow) |

## Funkcje

| Funkcja | Opis | Sec. Definer |
|---------|------|:------------:|
| create_user_short | Szybkie tworzenie usera (login, email, haslo, rola) | tak |
| create_user_long | Pelne tworzenie usera (+ imie, nazwisko, telefon, opis) | tak |
| change_password | Zmiana hasla (admin = kazdemu, user = sobie) | tak |
| check_user_subscription | Sprawdzenie aktywnej subskrypcji | nie |
| update_updated_at | Trigger: auto updated_at | nie |
| audit_trigger_func | Trigger: logowanie zmian do audit_log | tak |

## Kolejnosc tworzenia

1. Rozszerzenia (`pgcrypto`, `btree_gist`)
2. Enumy (`payment_status`, `subscription_status`)
3. Funkcje triggerowe (`update_updated_at`, `audit_trigger_func`)
4. Tabele (w kolejnosci zaleznosci):
   - `users`
   - `subscription_plans`
   - `user_subscriptions`
   - `payments`
   - `login_history`
   - `audit_log`
5. Funkcje biznesowe (`create_user_*`, `change_password`, `check_user_subscription`)

## Rozszerzenia

| Rozszerzenie | Cel |
|--------------|-----|
| pgcrypto | Hashowanie hasel (bcrypt) |
| btree_gist | Exclusion constraint na subskrypcjach |
