# API

Pełna lista adresów HTTP z kolumną „Dostęp" (otwarty / sesja / zablokowane w demo) i przypisaniem
do procesu: [04-integracje — Adresy aplikacji](../04-integracje.md#adresy-aplikacji-interfejs-http).
Zmienne środowiskowe: [04-integracje — Środowisko](../04-integracje.md#zmienne-środowiskowe).

Zasada dla nowych endpointów (SEC): każdy `/admin/api/*` ma `is_admin()` jako pierwszą linię i test
„brak sesji → 401"; endpointy zmieniające słowniki, konta lub konfigurację trafiają do `DEMO_BLOCKED`.
