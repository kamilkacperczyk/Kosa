-- Migracja: 2026-04-27 - login_history.user_id NULLABLE
-- Powod: server.py przy nieudanym logowaniu z nieznanym loginem probuje
-- zapisac wpis do login_history z user_id=NULL (audit prob ataku/literowek).
-- Schemat blokowal to przez NOT NULL -> kazda nieudana proba logowania
-- konczyla sie HTTP 500 zamiast czystego "Nieprawidlowa nazwa lub haslo".
--
-- FK do users.id zostaje (NULL nie lamie FK constraint).

ALTER TABLE public.login_history
    ALTER COLUMN user_id DROP NOT NULL;

COMMENT ON COLUMN public.login_history.user_id IS
    'ID uzytkownika (FK -> users.id). NULL gdy proba logowania na nieistniejacy login.';
