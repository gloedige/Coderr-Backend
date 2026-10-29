# Coderr – Backend

[![Python](https://img.shields.io/badge/Python-3.14-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-6.1-092E20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Django REST Framework](https://img.shields.io/badge/DRF-3.18-red)](https://www.django-rest-framework.org/)
[![Database](https://img.shields.io/badge/Database-SQLite-lightgrey?logo=sqlite&logoColor=blue)](https://www.sqlite.org/)
[![Frontend](https://img.shields.io/badge/Frontend-Vanilla%20JavaScript-yellow?logo=javascript)](https://github.com/Developer-Akademie-Backendkurs/project.Coderr)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Coderr ist eine Plattform zur Vermittlung von Freelancer-Dienstleistungen – ähnlich wie Fiverr. Dieses Repository enthält die Django-REST-API des Projekts. Das dazugehörige Frontend wird in einem separaten Repository gepflegt.

- **Frontend:** [Developer-Akademie-Backendkurs/project.Coderr](https://github.com/Developer-Akademie-Backendkurs/project.Coderr)
- **API-Dokumentation:** [api-doku.html](api-doku.html)
- **Lizenz:** MIT (siehe [LICENSE](LICENSE))

## Inhaltsverzeichnis

- [Projektüberblick](#projektüberblick)
- [Projektstruktur](#projektstruktur)
- [Frontend-Konfiguration](#frontend-konfiguration)
- [Funktionen und Seitenübersicht](#funktionen-und-seitenübersicht)
- [Gast-Zugänge](#gast-zugänge)
- [Lokale Installation](#lokale-installation)
- [Tests und API ausprobieren](#tests-und-api-ausprobieren)

## Projektüberblick

Coderr verbindet Kunden, die digitale Dienstleistungen suchen, mit Freelancern, die ihre Angebote auf der Plattform präsentieren. Die Anwendung ist fachlich in Backend und Frontend aufgeteilt. Das Backend stellt die REST-API und die Geschäftslogik bereit; das Frontend ist ein eigenständiges Vanilla-JavaScript-Projekt.

| Bereich | Technologie / Status |
| --- | --- |
| Backend | Python 3.14, Django 6.1, Django REST Framework 3.18 |
| Datenbank | SQLite als lokale Standardkonfiguration; PostgreSQL kann für eine entsprechende Deployment-Konfiguration eingesetzt werden |
| Tests | Django-Test-Runner und `unittest`-basierte Django-Tests; Pytest ist derzeit nicht in `requirements.txt` eingerichtet |
| Frontend | Vanilla JavaScript, HTML und CSS; siehe [Frontend-Repository](https://github.com/Developer-Akademie-Backendkurs/project.Coderr) |

## Projektstruktur

Das Backend ist in diesem Repository direkt im Stammverzeichnis abgelegt. Das Frontend liegt im oben verlinkten, separaten Repository; `frontend/` ist daher kein Verzeichnis dieses Checkouts.

```text
Coderr-Backend/
├── accounts_app/       # Benutzer, Profile, Login und Registrierung
│   ├── api/             # API-Views, Serializer und Account-Tests
│   └── migrations/      # Datenbankschema und vorbereitete Gastkonten
├── core/                # Django-Konfiguration und gemeinsame API-Funktionen
│   └── api/             # Basisinformationen, Utilities und Tests
├── marketplace_app/     # Angebote, Bestellungen und Bewertungen
│   ├── api/             # Featurebezogene API-Module und Tests
│   └── migrations/
├── api-doku.html        # API-Dokumentation
├── manage.py
├── requirements.txt
└── db.sqlite3           # lokale Entwicklungsdatenbank (wird bei Bedarf erstellt)
```

## Frontend-Konfiguration

Das Frontend verwendet eine zentrale Konfigurationsdatei für API-Endpunkte und weitere Voreinstellungen. Je nach Frontend-Version befindet sie sich beispielsweise unter `frontend/src/assets/config.js` oder heißt `config.js`. Im verlinkten Vanilla-JavaScript-Frontend liegt sie unter `shared/scripts/config.js`.

Beim Verbinden mit dem Backend müssen die API-Basis-URL und der Gast-Login in dieser Datei mit den Backend-Einstellungen übereinstimmen. Für die Angebots-Paginierung muss folgende Seitengröße übernommen werden:

```js
PAGE_SIZE = 3
```

Das Backend paginiert Angebote standardmäßig mit drei Einträgen pro Seite und erlaubt bis zu 100 Einträge über den Parameter `page_size`.

## Funktionen und Seitenübersicht

Die folgenden Bezeichnungen beschreiben die sichtbaren Anwendungsbereiche. Im aktuellen Frontend ist der HTML-Dokumenttitel auf den Seiten allgemein `Coderr/`; die Tabelle nennt deshalb die jeweilige Seite und ihren Zweck.

| Anwendungsbereich / Seite | Frontend-Seite | Funktionen |
| --- | --- | --- |
| Landing / Home | `index.html` | Dienstleistungen entdecken, Angebote suchen, Plattformkennzahlen ansehen |
| Offers / Services | `offer_list.html` | Angebotsübersicht durchsuchen und nach Lieferzeit oder Preis sortieren/filtern |
| Offer-Details | `offer.html` | Angebotsdetails und Bewertungen ansehen; Basic-, Standard- und Premium-Pakete auswählen; Bestellung aufgeben |
| Orders / Profil | `own_profile.html` | Eigene Bestellungen und das eigene Profil ansehen und verwalten; Funktionen unterscheiden sich nach Kunden- und Anbieterrolle |
| Login | `login.html` | Mit Benutzername und Passwort anmelden oder einen Kunden-/Anbieter-Gastzugang auswählen |
| Registrierung | `registration.html` | Ein Kunden- oder Anbieterkonto erstellen |

Wichtige API-Routen sind unter anderem `/api/login/`, `/api/registration/`, `/api/offers/`, `/api/orders/`, `/api/reviews/` und `/api/base-info/`. Vollständige Details stehen in der [API-Dokumentation](api-doku.html).

## Gast-Zugänge

Die Migration legt beim Ausführen von `migrate` zwei Konten inklusive Profil und API-Token an. Sie sind für lokale Vorschauen und Entwicklung vorgesehen.

| Rolle | Benutzername | E-Mail | Passwort |
| --- | --- | --- | --- |
| Kunde (`customer`) | `guest_customer` | `guest_customer@example.com` | `guest1234` |
| Anbieter (`business`) | `guest_business` | `guest_business@example.com` | `guest1234` |

> **Sicherheitshinweis:** Diese Zugangsdaten sind öffentlich und ausschließlich für lokale Entwicklung und Demos gedacht. Vor einem öffentlichen oder produktiven Einsatz müssen sie ersetzt beziehungsweise deaktiviert werden.

## Lokale Installation

Voraussetzung ist eine installierte Python-Version, die mit den Versionen in `requirements.txt` kompatibel ist.

1. Repository klonen und in das Backend-Verzeichnis wechseln.
2. Virtuelle Umgebung erstellen und aktivieren:

   **Windows (PowerShell):**

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   **macOS / Linux:**

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. Abhängigkeiten installieren:

   ```bash
   pip install -r requirements.txt
   ```

4. Datenbankmigrationen ausführen. Dabei werden auch die vorbereiteten Gastkonten angelegt:

   ```bash
   python manage.py migrate
   ```

5. Entwicklungsserver starten:

   ```bash
   python manage.py runserver
   ```

Die API ist anschließend standardmäßig unter <http://127.0.0.1:8000/api/> erreichbar. SQLite wird anhand der Django-Konfiguration automatisch als lokale Datenbank verwendet.

## Tests und API ausprobieren

Führe die Tests mit dem integrierten Django-Test-Runner aus:

```bash
python manage.py test
```

Die API kann beispielsweise mit Postman getestet werden. Starte zuerst den lokalen Server, verwende anschließend die Routen aus der [API-Dokumentation](api-doku.html) und sende bei geschützten Endpunkten das Token als `Authorization: Token <token>`.
