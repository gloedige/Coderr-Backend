Du bist ein erfahrener Senior Software Engineer. Erstelle eine professionelle, übersichtliche und gut strukturierte `README.md` im Markdown-Format für das Monorepo-Projekt **Coderr**.

### Inhaltsverzeichnis der Readme ###

#### 1. Projekt-Kontext & Übersicht
* **Projektname:** Coderr
* **Beschreibung:** Eine Plattform zur Vermittlung von Freelancer-Dienstleistungen (ähnlich wie Fiverr). Das Repository ist als Monorepo aufgebaut (`backend/`).
* **Backend-Tech-Stack:** Python, Django, Django REST Framework (DRF), SQLite/PostgreSQL, Pytest.
*
 **Frontend Repo:** <https://github.com/Developer-Akademie-Backendkurs/project.Coderr>

---

#### 2. Spezifische Anforderungen an die README

Bitte integriere folgende Abschnitte und Details präzise:

##### A. Projektstruktur (Monorepo)
* Kurze Übersicht der Ordnerstruktur 
* Hinweis zur Frontend-Konfiguration: Erwähne, dass das Frontend eine zentrale Konfigurationsdatei (`frontend/src/assets/config.js` bzw. `config.js`) nutzt, in der API-Endpunkte und Voreinstellungen hinterlegt sind. Hier muss der Gast-Login dem Backend angepasst werden.
Zudem muss hier die PAGE_SIZE aufgelistet werden, die in der config.js zu übernehmen ist: Wert=3

##### B. Gast-Zugänge (Guest Logins)
* Führe die vordefinierten Test- bzw. Gast-Zugänge übersichtlich auf, die für eine schnelle Vorschau/Entwicklung genutzt werden können:

GUEST_USERS = (
    ('guest_customer', 'guest_customer@example.com', 'customer'),
    ('guest_business', 'guest_business@example.com', 'business'),
)
GUEST_PASSWORD = 'guest1234'

##### C. Features & Page Titles (Seiten-Übersicht)
* Erstelle eine Tabelle oder Liste aller Hauptseiten/Anwendungsfälle inklusive ihrer **Page Titles** (Frontend) und der dazugehörigen Funktionen:
  * **Landing / Home:** Dienstleistungen durchsuchen, Filter nutzen.
  * **Offers / Services:** Detaillierte Angebotsansicht (Basic, Standard, Premium Tiers).
  * **Orders / Profil:** Übersicht eigener Bestellungen und Profileinstellungen.
  * **Auth (Login / Register):** Authentifizierung inkl. Klick-Option für Guest-Login.

##### D. Setup & Lokale Installation
* **Backend einrichten:**
  1. Virtuelle Umgebung erstellen und aktivieren (`python -m venv .venv`).
  2. Abhängigkeiten installieren (`pip install -r requirements.txt`).
  3. Datenbank-Migrationen ausführen (`python manage.py migrate`), um auch die vorbereiteten Guest-User automatisch in der DB anzulegen.
  4. Server starten (`python manage.py runserver`).
 
Test des Backends z.b. mit Postman.
---

#### 3. Formatierungsregeln
* Nutze klare Markdown-Überschriften (`#`, `##`, `###`).
* Verwende Badges (z. B. für Python, Django, Angular, License), Tabellen für Quick Links/Seitenübersichten und Code-Blöcke für Terminal-Befehle.
* Der Ton soll professionell, sachlich und leicht verständlich sein.