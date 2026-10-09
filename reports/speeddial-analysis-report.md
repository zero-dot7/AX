# Analiza "Speed Dial" — zadanie AX speeddial-analysis

- Model: qwen/qwen3.8-flash (reasoning OFF)
- Źródło: zero-dot7/projects-and-more @ speed-dial (commit cf297d5)
- Status: ok | długość raportu: 14538 znaków

---

# Raport Analizy Rozszerzenia "Speed Dial" (Manifest V3)

Poniżej znajduje się szczegółowa analiza kodu źródłowego rozszerzenia. Kod jest generalnie dobrze napisany, czytelny i zgodny z duchem Manifest V3, jednak zawiera kilka krytycznych błędów logicznych oraz luk bezpieczeństwa wynikających z nieprawidłowego użycia API Chrome i braku odpowiedniej walidacji danych wejściowych w specyficznych scenariuszach.

## Bledy (BUGS)

### 1. Krytyczny błąd: `chrome.tabs.captureVisibleTab` wymaga aktywnego okna
*   **Lokalizacja:** `app.js`, funkcja `makeThumb` (linia ~145).
*   **Opis:** W komentarzu do pkt 36/49 autor słusznie zauważa, że `captureVisibleTab` działa tylko na *widoczne* okna. Jednakże, nawet jeśli okno popup jest utworzone z `focused: false`, metoda `captureVisibleTab(windowId)` w Chrome MV3 często zwraca pusty obraz lub błąd, jeśli to konkretne okno nie jest aktualnie na wierzchu (active/focused) w momencie wywołania, albo jeśli system operacyjny minimalizuje je natychmiast po utracie fokusu.
*   **Wpływ:** Generowanie miniatur może być niestabilne lub całkowicie nieskuteczne na niektórych konfiguracjach systemowych (szczególnie Linux/Wayland lub przy agresywnym zarządzaniu energią), mimo że kod obsługuje błąd (`catch`). Użytkownik zobaczy komunikat o błędzie lub brak miniatury.
*   **Sugerowany fix:** Zamiast `focused: false`, należy użyć `focused: true` dla tworzonego okna, a następnie natychmiastowo przywrócić fokus do karty nowej (newtab) za pomocą `chrome.windows.update(currentWindowId, { focused: true })` przed wykonaniem `captureVisibleTab`. Alternatywnie, można spróbować wymusić renderowanie przez `chrome.debugger` (wymaga dodatkowych uprawnień), ale podejście z `focused: true` + szybkie przełączenie jest standardowym obejściem dla "screenshotów w tle".

### 2. Błąd logiki: `dbxMaybeAutoBackup` nie sprawdza stanu połączenia poprawnie
*   **Lokalizacja:** `app.js`, funkcja `dbxMaybeAutoBackup` (linia ~480).
*   **Opis:** Funkcja sprawdza `if (!dbxState.auto || !dbxState.accessToken) return;`. Problem polega na tym, że `dbxState.accessToken` może być przeterminowany (wygasły), ale nadal istnieć w pamięci. Jeśli token wygasł, `dbxPush` zadzwoni do `dbxValidToken()`, która spróbuje odświeżyć token. Jeśli odświeżenie powiedzie się – OK. Ale jeśli `dbxState.refreshToken` też jest nieważny (np. użytkownik cofnął dostęp w Dropbox), `dbxValidToken` zwróci `null`, a `dbxPush` wyświetli błąd. To jest zachowanie oczekiwane.
    *   *Jednakże:* Brak mechanizmu ponownego uwierzytelnienia (re-auth flow) przy automatycznym backupie. Jeśli token wygaśnie i refresh failnie, auto-backup przestaje działać cicho (lub z ostrzeżeniem w konsoli), dopóki użytkownik ręcznie nie wejdzie w ustawienia.
*   **Wpływ:** Ciche zaprzestanie synchronizacji po dłuższym okresie nieużywania lub zmianie haseł w Dropbox.
*   **Sugerowany fix:** W przypadku błędu `dbxValidToken` w trybie `silent=true`, warto ustawić flagę wymagającą interwencji użytkownika lub wyświetlić toast z sugestią ponownego połączenia.

### 3. Błąd importu: `convertGsd` nie obsługuje braku pola `url` w dialach
*   **Lokalizacja:** `app.js`, funkcja `convertGsd` (linia ~560).
*   **Opis:** Linia `.filter(t => t && typeof t.url === 'string' && t.url.startsWith('http'))` jest bezpieczna. Jednakże, jeśli stary plik GSD ma dials bez pola `name`, `hostOf(t.url)` zostanie wywołane. `hostOf` łapie wyjątek, więc to OK.
    *   *Realny bug:* W `sanitizeGroups` (linia ~590) sprawdzamy `okUrl(t.url)`. `okUrl` wymaga prefiksu `https?://`. Jeśli użytkownik zaimportuje plik, gdzie URL to np. `www.google.com` (bez protokołu), kafelki zostaną odrzucone jako niepoprawne, mimo że `normalizeUrl` w edycji dodaje protokół. Import powinien być bardziej tolerancyjny lub normalizować dane przed sanitizacją.
*   **Wpływ:** Niektóre stare backupy mogą stracić kafelki podczas importu, jeśli nie miały pełnego protokołu w URL-u.
*   **Sugerowany fix:** Przed `sanitizeGroups` zastosować mapowanie, które próbuje dodać `https://` do adresów bez protokołu, tak jak robi to `normalizeUrl`.

### 4. Błąd UI: `render()` nadpisuje `innerHTML` boarda, niszcząc stan scrolla
*   **Lokalizacja:** `app.js`, funkcja `render` (linia ~200).
*   **Opis:** `board.innerHTML = ''` powoduje całkowite usunięcie DOM i jego odbudowę. Jeśli użytkownik przewinął stronę w dół, aby zobaczyć dolne grupy, a zmieni układ (layout) lub filtr, pozycja scrolla resetuje się do góry.
*   **Wpływ:** Frustrujące UX przy częstych zmianach widoku.
*   **Sugerowany fix:** Zachować `window.scrollY` przed renderem i przywrócić je po appendChild, lub stosować diffing DOM (choć przy tej skali danych `innerHTML` jest prostszy, wystarczy zapisanie offsetu).

## Optymalizacje

### 1. Wydajność Renderowania: Nadmiarowe `render()` w `save()`
*   **Lokalizacja:** `app.js`, funkcja `save` (linia ~75) oraz wszystkie miejsca jej wywołania.
*   **Opis:** Funkcja `save()` zapisuje dane do storage, a następnie wiele akcji (np. `moveTile`, `removeGroup`) wywołuje `save(); render();`. Jest to poprawne, ale `save()` jest asynchroniczne. Jeśli użytkownik szybko kliknie dwa razy, mogą wystąpić race conditions w renderowaniu (choć JS jest single-threaded, `await` w `save` może opóźnić `render`).
*   **Optymalizacja:** Warto oddzielić zapis od renderu. `save()` powinien tylko zapisywać. Render powinien być wywoływany jawnie. Obecna struktura jest OK, ale `dbxMaybeAutoBackup` w `save()` uruchamia fetch sieciowy przy każdym zapisie lokalnym (nawet jeśli auto-backup jest wyłączony, sprawdzenie jest tanie, ale samo wywołanie funkcji asynchronicznej generuje overhead).
*   **Konkretna sugestia:** Opóźnij `dbxMaybeAutoBackup` o debounce (np. 500ms), aby uniknąć wysyłania wielu żądań HTTP przy szybkich edycjach (np. przeciąganie wielu kafelków).

### 2. Storage: Przechowywanie Miniatur w `chrome.storage.local`
*   **Lokalizacja:** `app.js`, `makeThumb` -> `tile.thumb = dataUrl`.
*   **Opis:** Miniatury JPEG (quality 75) mogą ważyć 50-100KB każda. Przy 100 kafelkach to 5-10MB. `chrome.storage.local` ma limit (zwykle 10MB bez `unlimitedStorage`, tutaj mamy `unlimitedStorage`, więc jest OK). Jednakże serializacja/deserializacja dużych obiektów JSON z base64 stringami jest kosztowna CPU.
*   **Optymalizacja:** Rozważ przechowywanie miniatur w IndexedDB zamiast w `storage.local`. Pozwoli to na asynchroniczne pobieranie blobów bez blokowania głównego wątku przy ładowaniu strony (`load()` musi parsować cały JSON z miniaturami).

### 3. Sieć: OAuth Token Refresh Race Condition
*   **Lokalizacja:** `app.js`, `dbxValidToken`.
*   **Opis:** Jeśli dwie operacje (np. auto-backup i ręczny restore) wywołają `dbxValidToken` jednocześnie, gdy token wygasł, obie spróbują odświeżyć token. Dropbox może unieważnić poprzedni refresh token przy pierwszym odświeżeniu (rotacja tokenów), co spowoduje błąd drugiej operacji.
*   **Optymalizacja:** Dodaj mutex/promise lock dla `dbxRefreshAccessToken`, aby upewnić się, że tylko jedna próba odświeżenia jest wykonywana w danym czasie.

## Bezpieczeństwo

### 1. XSS w `contentEditable` (Niskie ryzyko, ale istotne)
*   **Lokalizacja:** `app.js`, `renderGroup` -> `h2.onblur`.
*   **Opis:** Użytkownik edytuje nazwę grupy przez `contentEditable`. Wartość jest pobierana przez `h2.textContent.trim()`. `textContent` jest bezpieczne pod kątem XSS (ignoruje tagi HTML). Jednakże, jeśli w przyszłości ktoś zmieni to na `innerHTML`, będzie dziura. Obecnie jest OK.
*   **Uwaga:** `title` i `url` są renderowane przez `textContent` w `renderTile`, więc są bezpieczne.

### 2. OAuth/PKCE Implementacja
*   **Lokalizacja:** `app.js`, `dbxAuthorize`.
*   **Analiza:**
    *   Użycie PKCE (`code_verifier`, `code_challenge` SHA-256) jest **poprawne** i bezpieczne dla aplikacji publicznych (public client).
    *   `redirect_uri` jest dynamiczny (`chrome.runtime.id`), co jest dobrą praktyką.
    *   **Ryzyko:** App Key jest przechowywany w `chrome.storage.sync`. Sync jest zaszyfrowany przez Google, ale jeśli użytkownik ma złośliwe rozszerzenie z uprawnieniami `storage`, może odczytać klucz. Klucz app jest publiczny (jak w dokumentacji Dropbox), więc to nie jest sekretem. Sekretem są tokeny.
    *   **Tokeny:** Przechowywane w `chrome.storage.local`. To jest bezpieczne miejsce (lokalne, nie synchronizowane między urządzeniami, chyba że user sam eksportuje).
    *   **Brak CSRF protection w state:** W standardowym OAuth często używa się parametru `state` w URL autoryzacyjnym, aby zweryfikować, że callback pochodzi z tej samej sesji. Tutaj `chrome.identity.launchWebAuthFlow` abstrahuje ten proces i bezpiecznie przekazuje redirect URL. Jest to bezpieczne dzięki izolacji kontekstu rozszerzenia.

### 3. Permissions w Manifest
*   **Lokalizacja:** `manifest.json`.
*   **Analiza:**
    *   `<all_urls>` w `host_permissions`: Jest to **bardzo szerokie** uprawnienie. Jest wymagane do `chrome.tabs.captureVisibleTab` (aby zrobić screenshot dowolnej strony) oraz potencjalnie do faviconów (choć `_favicon` API nie wymaga host permissions).
    *   **Ryzyko:** Użytkownicy mogą obawiać się tego uprawnienia ("rozszerzenie widzi wszystko").
    *   **Sugestia:** Czy `captureVisibleTab` naprawdę wymaga `<all_urls>`? Tak, aby złapać zawartość dowolnej otwartej karty. Można rozważyć ograniczenie do konkretnych domen, jeśli miniatury mają być robione tylko dla znanych serwisów, ale dla uniwersalnego speed diala jest to konieczne kompromis. Należy to wyraźnie wyjaśnić w opisie rozszerzenia.

### 4. Walidacja Importu JSON
*   **Lokalizacja:** `app.js`, `importJson`.
*   **Opis:** `JSON.parse` jest owinięty w `try/catch`. `sanitizeGroups` sprawdza typy.
*   **Ryzyko:** DoS (Denial of Service) poprzez bardzo głęboki zagnieżdżony JSON lub ogromny plik. Limit 50MB jest dobry. `structuredClone` w `load()` może rzucić wyjątek przy cyklicznych referencjach (mało prawdopodobne w JSON, ale możliwe w manipulowanym pliku).
*   **Sugestia:** Upewnij się, że `sanitizeGroups` nie rekuruje zbyt głęboko (obecnie iteruje płasko po grupach/tiles, więc jest OK).

## Jakosc kodu

### 1. Duplikacja Logiki Error Handling w Dropbox
*   **Lokalizacja:** `app.js`, `dbxPush` i `dbxRestore`.
*   **Opis:** Bloki `try/catch` obsługujące błędy HTTP z Dropbox są niemal identyczne (parsowanie `error_summary`, fallback na tekst).
*   **Sugestia:** Wyodrębnić funkcję pomocniczą `handleDropboxError(res)`, która zwraca sformatowany string błędu.

### 2. Martwy Kod / Niepotrzebne Zmienne
*   **Lokalizacja:** `app.js`, `state.view.pages`.
*   **Opis:** Stan stron jest trzymany w `state.view.pages[g.id]`. Jest to poprawne. Jednakże w `renderGroup` linia `const page = clampInt(...)` modyfikuje `state.view.pages[g.id] = page`. Modyfikacja stanu globalnego w funkcji renderującej jest antywzorcem (side-effect w renderze). Powinno to być zrobione przed renderem lub w handlerze zmiany strony.
*   **Wpływ:** Może prowadzić do niespodziewanych zachowań przy debugowaniu lub hot-reloadzie.

### 3. Brak Obsługi Błędu `crypto.randomUUID`
*   **Lokalizacja:** `app.js`, `uid`.
*   **Opis:** Fallback na `Math.random` jest dobry, ale `Math.random().toString(36).slice(2, 10)` nie gwarantuje unikalności tak dobrze jak UUID. Dla lokalnego narzędzia jest to akceptowalne, ale warto dodać timestamp do ID, aby zminimalizować kolizje przy imporcie wielu plików naraz.

### 4. Styl CSS: Magiczne Liczby
*   **Lokalizacja:** `style.css`.
*   **Opis:** Dużo hardkodowanych wartości (np. `top: -20px`, `padding-top: 22px`). Trudne do utrzymania przy zmianach layoutu.
*   **Sugestia:** Użyć zmiennych CSS (`--tile-host-offset: 20px;`) dla lepszej spójności.

## Architektura

### 1. Monolit `app.js`
*   **Problem:** Cała logika (UI, Storage, Network/OAuth, Thumbnail Generation) jest w jednym pliku (~600 linii).
*   **Refaktoryzacja:** Podział na moduły ES6 (jeśli manifest pozwala na `type: module` w scriptie, co MV3 wspiera):
    *   `storage.js`: Abstrakcja nad `chrome.storage`.
    *   `dropbox.js`: Cała logika OAuth i API.
    *   `thumbnails.js`: Kolejka i generowanie miniatur.
    *   `ui.js`: Rendering i eventy.
*   **Dlaczego:** Łatwiejsze testowanie jednostkowe (testy obecne są integracyjne i kruche), lepsza czytelność.

### 2. Brak Warstwy Abstrakcji dla Storage
*   **Problem:** Bezpośrednie wywołania `chrome.storage.local.get/set` rozrzucone po kodzie.
*   **Refaktoryzacja:** Stworzenie klasy `StoreManager`, która enkapsuluje dostęp do danych, walidację schematu i migracje wersji. Obecnie `load()` robi dużo pracy walidacyjnej inline.

### 3. Synchronizacja Stanu
*   **Problem:** `state` jest mutowalny globalnie.
*   **Refaktoryzacja:** Rozważ przejście na wzorzec Redux-like (actions/reducers) lub przynajmniej immutability dla kluczowych struktur danych, aby ułatwić debugowanie i undo/redo (opcjonalnie).

## Top 10 - Lista Priorytetowa Najważniejszych Znalezisk

1.  **[BUG] Niestabilne generowanie miniatur (`captureVisibleTab`)**: Ryzyko, że funkcja kluczowa (miniatury) nie będzie działać na wszystkich platformach/systemach ze względu na focus window. *Priorytet: Wysoki.*
2.  **[SECURITY] Uprawnienie `<all_urls>`**: Choć uzasadnione technicznie, stanowi barierę adopcji i potencjalne ryzyko prywatności. Należy rozważyć alternatywę lub jasną komunikację. *Priorytet: Średni (UX/Trust).*
3.  **[BUG] Brak Mutexa przy odświeżaniu Tokena OAuth**: Możliwość uszkodzenia tokenu refresh przy równoległych operacjach sieciowych. *Priorytet: Średni.*
4.  **[CODE] Side-effect w `renderGroup` (mutacja `state.view.pages`)**: Naruszenie czystości funkcji renderujących. *Priorytet: Niski (Stabilność).*
5.  **[OPT] Debounce dla Auto-Backup**: Obecnie każdy zapis lokalny triggeruje check backupu. Przy masowych edycjach może to generować zbędne obciążenie. *Priorytet: Niski.*
6.  **[BUG] Import bez protokołu URL**: Kafelki z `www.example.com` mogą zostać odrzucone przy imporcie, mimo że działają w edycji. *Priorytet: Średni (UX).*
7.  **[ARCH] Monolityczna struktura kodu**: Trudność w utrzymaniu i testowaniu. *Priorytet: Długoterminowy.*
8.  **[SEC] Przechowywanie App Key w `storage.sync`**: Choć key jest publiczny, lepiej trzymać go w `local` razem z tokenami, aby nie synchronizować konfiguracji między urządzeniami, jeśli nie jest to potrzebne. *Priorytet: Niski.*
9.  **[CODE] Duplikacja obsługi błędów Dropbox**: Zwiększa ryzyko rozbieżności w raportowaniu błędów. *Priorytet: Niski.*
10. **[OPT] Przeniesienie miniatur do IndexedDB**: Poprawa wydajności ładowania strony przy dużej liczbie kafelków. *Priorytet: Średni (Wydajność).*
