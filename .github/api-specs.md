# Coderr API-Spezifikation

Diese Spezifikation wurde aus [api-doku.html](../api-doku.html) abgeleitet und um die abgestimmten Implementierungsregeln ergänzt. Sie beschreibt alle Endpunkte, Antwortformate, Berechtigungen und Validierungsregeln.

## Allgemeines

- **API-Präfix:** `/api/`
- **Datenformat:** JSON, sofern für Datei-Uploads nicht ausdrücklich `multipart/form-data` angegeben ist.
- **Authentifizierung:** DRF-Tokenauthentifizierung über `Authorization: Token <token>`. Registrierung, Login, öffentliche Angebotsliste und Basisinformationen sind nicht authentifizierungspflichtig; für andere Endpunkte gelten die jeweiligen Angaben.
- **Ratenbegrenzung:** Für die dokumentierten Endpunkte ist kein Limit angegeben.
- Pfadparameter in geschweiften Klammern, z. B. `{id}`, müssen durch den jeweiligen Wert ersetzt werden.
- Datumswerte werden als ISO-8601-Strings zurückgegeben.
- Benutzerrollen sind `customer` und `business`. Usernames werden nach äußerem Whitespace-Trim case-sensitiv eindeutig behandelt und behalten ihre Schreibweise. E-Mail-Adressen werden außen getrimmt, kleingeschrieben und case-insensitiv eindeutig behandelt.
- Fehler bei ungültigen Eingaben verwenden DRF-Feldfehler. Authentifizierungs-, Berechtigungs- und Nichtgefunden-Fehler verwenden ein JSON-Objekt mit `detail`. Interne Fehlerdetails werden nicht zurückgegeben.
- Datei-Uploads akzeptieren JPEG und PNG bis maximal 5 MB. Responses enthalten nur den Dateinamen, keine URL. Bei PATCH bedeutet ein ausgelassenes Bildfeld „unverändert“; der Multipart-Textwert `null` löscht das Bild.

## Authentifizierung

### `POST /api/registration/`
Erstellt atomar Benutzerkonto, gemeinsames Profil und Authentifizierungstoken für `customer` oder `business`. Keine Authentifizierung erforderlich. Username und E-Mail werden außen getrimmt. Der Username bleibt case-sensitiv und muss exakt eindeutig sein; die E-Mail wird kleingeschrieben und case-insensitiv eindeutig behandelt. Das Passwort muss mindestens 4 Zeichen lang sein; zusätzliche Django-Passwortregeln werden nicht angewendet. `password` und `repeated_password` müssen übereinstimmen.

**Request Body**

```json
{
  "username": "exampleUsername",
  "email": "example@mail.de",
  "password": "pass",
  "repeated_password": "pass",
  "type": "customer"
}
```

**Erfolgreiche Antwort – `201 Created`**

```json
{
  "token": "83bf098723b08f7b23429u0fv8274",
  "username": "exampleUsername",
  "email": "example@mail.de",
  "user_id": 123
}
```

Weitere Statuscodes: `400` ungültige Anfragedaten (einschließlich doppeltem Username/E-Mail oder abweichender Passwörter), `500` interner Serverfehler. Ein Fehler während der Anlage darf weder Teilkonto noch ungebundenes Token hinterlassen.

### `POST /api/login/`
Authentifiziert einen Benutzer und liefert ein Token. Der Username-Login ist case-sensitiv; die beim Login angegebene Schreibweise muss mit dem gespeicherten Username übereinstimmen. Keine Authentifizierung erforderlich.

**Request Body**

```json
{
  "username": "exampleUsername",
  "password": "examplePassword"
}
```

**Erfolgreiche Antwort – `200 OK`**

```json
{
  "token": "83bf098723b08f7b23429u0fv8274",
  "username": "exampleUsername",
  "email": "example@mail.de",
  "user_id": 123
}
```

Weitere Statuscodes: `400` fehlende oder ungültige Anmeldedaten, `500` interner Serverfehler. Die Fehlerantwort darf nicht offenlegen, ob Username oder Passwort falsch war.

## Profile

### `GET /api/profile/{pk}/`
Liefert das vollständige Profil des Benutzers `{pk}`. Authentifizierung erforderlich. Nicht vorhandene optionale Textfelder werden als `""` statt `null` ausgegeben. `file` ist der gespeicherte Basis-Dateiname oder `null`, falls kein Bild vorhanden ist.

**Erfolgreiche Antwort – `200 OK`**

```json
{
  "user": 1,
  "username": "max_mustermann",
  "first_name": "Max",
  "last_name": "Mustermann",
  "file": "profile_picture.jpg",
  "location": "Berlin",
  "tel": "123456789",
  "description": "Business description",
  "working_hours": "9-17",
  "type": "business",
  "email": "max@business.de",
  "created_at": "2023-01-01T12:00:00Z"
}
```

Die Felder `first_name`, `last_name`, `location`, `tel`, `description` und `working_hours` sollen nicht `null` sein; bei fehlenden Werten werden leere Strings verwendet. Weitere Statuscodes: `401` nicht authentifiziert, `404` Profil nicht gefunden, `500` interner Serverfehler.

### `PATCH /api/profile/{pk}/`
Aktualisiert ausgewählte Profildaten des eigenen Kontos; fremde Profile dürfen nicht bearbeitet werden. `username` und `type` sind nicht änderbar. Gemeinsame editierbare Felder sind `first_name`, `last_name`, `location`, `tel` und `email`. `description` und `working_hours` sind nur für Business-Profile editierbar. Nicht übermittelte Felder bleiben unverändert. E-Mail-Eindeutigkeit ist case-insensitiv.

Für Bilddateien wird `multipart/form-data` verwendet. `file` enthält JPEG/PNG bis 5 MB. Bei ausgelassenem Feld bleibt das aktuelle Bild bestehen; der Multipart-Textwert `null` entfernt es. JSON-Feldwerte werden bei Multipart als Textfelder übertragen. Ungültige Dateiformate oder zu große Dateien ergeben `400`.

**Request Body** (JSON ohne Bilddatei; mit Bilddatei als `multipart/form-data`)

```json
{
  "first_name": "Max",
  "last_name": "Mustermann",
  "location": "Berlin",
  "tel": "987654321",
  "description": "Updated business description",
  "working_hours": "10-18",
  "email": "new_email@business.de"
}
```

**Erfolgreiche Antwort – `200 OK`**: aktualisiertes Profil im selben Format wie bei `GET /api/profile/{pk}/`. `file` enthält nur den Basis-Dateinamen oder `null`, wenn kein Bild vorhanden ist.

Weitere Statuscodes: `401` nicht authentifiziert, `403` nicht Eigentümer des Profils, `404` Profil nicht gefunden, `500` interner Serverfehler.

### `GET /api/profiles/business/`
Liefert eine Liste der Geschäftsnutzer. Authentifizierung erforderlich.

**Erfolgreiche Antwort – `200 OK`**

```json
[
  {
    "user": 1,
    "username": "max_business",
    "first_name": "Max",
    "last_name": "Mustermann",
    "file": "profile_picture.jpg",
    "location": "Berlin",
    "tel": "123456789",
    "description": "Business description",
    "working_hours": "9-17",
    "type": "business"
  }
]
```

Weitere Statuscodes: `401` nicht authentifiziert, `500` interner Serverfehler.

### `GET /api/profiles/customer/`
Liefert eine Liste der Kundenprofile. Authentifizierung erforderlich. `uploaded_at` bezeichnet den letzten Profilbild-Upload, bleibt nur in diesem Kundenlisten-Response enthalten und ist `null`, wenn noch kein Profilbild hochgeladen wurde.

**Erfolgreiche Antwort – `200 OK`**

```json
[
  {
    "user": 2,
    "username": "customer_jane",
    "first_name": "Jane",
    "last_name": "Doe",
    "file": "profile_picture_customer.jpg",
    "uploaded_at": "2023-09-15T09:00:00",
    "type": "customer"
  }
]
```

Weitere Statuscodes: `401` nicht authentifiziert, `500` interner Serverfehler.

## Angebote

### `GET /api/offers/`
Liefert Angebote mit Angebotsdetails, Mindestpreis und kürzester Lieferzeit. Keine Authentifizierung erforderlich. Die Antwort ist paginiert (PageNumberPagination); Standardgröße ist 3, maximal 100 Ergebnisse. Größere `page_size`-Werte werden auf 100 begrenzt. `ordering` akzeptiert `updated_at`, `-updated_at`, `min_price` oder `-min_price`; Standard ist `-updated_at`. `min_price` ist ein inklusiver Mindestpreisfilter; `max_delivery_time` ist inklusiv. `search` sucht case-insensitiv in `title` und `description`. Ungültige oder unbekannte Parameter ergeben `400`.

**Query-Parameter**

| Parameter | Typ | Beschreibung |
| --- | --- | --- |
| `creator_id` | integer | Filtert nach dem Ersteller des Angebots. |
| `min_price` | decimal | Inklusiver Mindestpreisfilter. Preiswerte haben höchstens zwei Dezimalstellen. |
| `max_delivery_time` | integer | Filtert nach Lieferzeit kleiner oder gleich dem Wert. |
| `ordering` | string | Sortierung nach `updated_at`, `-updated_at`, `min_price` oder `-min_price`. Standard: `-updated_at`. |
| `search` | string | Durchsucht `title` und `description`. |
| `page_size` | integer | Ergebnisse pro Seite; Standard 3, Maximum 100 (größere Werte werden auf 100 begrenzt). |

**Erfolgreiche Antwort – `200 OK`**

```json
{
  "count": 1,
  "next": "http://127.0.0.1:8000/api/offers/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "user": 1,
      "title": "Website Design",
      "image": null,
      "description": "Professionelles Website-Design...",
      "created_at": "2024-09-25T10:00:00Z",
      "updated_at": "2024-09-28T12:00:00Z",
      "details": [
        { "id": 1, "url": "/offerdetails/1/" },
        { "id": 2, "url": "/offerdetails/2/" },
        { "id": 3, "url": "/offerdetails/3/" }
      ],
      "min_price": 100,
      "min_delivery_time": 7,
      "user_details": {
        "first_name": "John",
        "last_name": "Doe",
        "username": "jdoe"
      }
    }
  ]
}
```

Weitere Statuscodes: `400` ungültige Anfrageparameter, `500` interner Serverfehler.

### `POST /api/offers/`
Erstellt ein Angebot. Erfordert Authentifizierung; nur Benutzer vom Typ `business` dürfen Angebote erstellen. Ein Angebot muss genau drei Angebotsdetails enthalten: jeweils eines mit `offer_type` `basic`, `standard` und `premium`. `title` ist erforderlich, nicht leer und maximal 150 Zeichen. `description` ist maximal 500 Zeichen. Der Preis jedes Details muss größer als 0 und höchstens 100000 sein, mit maximal zwei Dezimalstellen. `delivery_time_in_days` liegt zwischen 1 und 365; `revisions` zwischen 0 und 100. `features` ist eine Liste frei formulierter Texte und darf leer sein; es gibt keine vorgegebenen Textbausteine.

Der Request verwendet `multipart/form-data`, wenn ein Bild hochgeladen wird. Die Angebotsdetails werden als JSON-kodierter Textwert im Feld `details` übertragen. `image` akzeptiert JPEG/PNG bis 5 MB. Ohne Bild ist `image` `null`; Responses enthalten bei vorhandenem Bild nur den Dateinamen.

**Request Body** (`application/json`, wenn kein Bild hochgeladen wird; andernfalls `multipart/form-data` mit JSON-kodiertem Feld `details`)

```json
{
  "title": "Grafikdesign-Paket",
  "image": null,
  "description": "Ein umfassendes Grafikdesign-Paket für Unternehmen.",
  "details": [
    {
      "title": "Basic Design",
      "revisions": 2,
      "delivery_time_in_days": 5,
      "price": 100,
      "features": ["Logo Design", "Visitenkarte"],
      "offer_type": "basic"
    },
    {
      "title": "Standard Design",
      "revisions": 5,
      "delivery_time_in_days": 7,
      "price": 200,
      "features": ["Logo Design", "Visitenkarte", "Briefpapier"],
      "offer_type": "standard"
    },
    {
      "title": "Premium Design",
      "revisions": 10,
      "delivery_time_in_days": 10,
      "price": 500,
      "features": ["Logo Design", "Visitenkarte", "Briefpapier", "Flyer"],
      "offer_type": "premium"
    }
  ]
}
```

**Erfolgreiche Antwort – `201 Created`**: erstelltes Angebot mit `id`, `title`, `image`, `description` und den Angebotsdetails einschließlich ihrer IDs und Detailfelder.

Weitere Statuscodes: `400` ungültige oder unvollständige Anfragedaten, `401` nicht authentifiziert, `403` kein Business-Profil, `500` interner Serverfehler. Ein unerwarteter Serverfehler wird mit `{"detail":"Internal server error."}` beantwortet; interne Fehlerdetails werden nicht offengelegt.

### `GET /api/offers/{id}/`
Liefert ein einzelnes Angebot und dessen Detail-URLs. Authentifizierung erforderlich. Bildantworten enthalten den Dateinamen, nicht die URL. Die drei Detail-URLs referenzieren `GET /api/offerdetails/{id}/`.

**Erfolgreiche Antwort – `200 OK`**

```json
{
  "id": 66,
  "user": 114,
  "title": "Grafikdesign-Paket",
  "image": null,
  "description": "Ein umfassendes Grafikdesign-Paket für Unternehmen.",
  "created_at": "2025-01-23T07:44:15.365773Z",
  "updated_at": "2025-01-23T07:44:15.365773Z",
  "details": [
    { "id": 199, "url": "http://127.0.0.1:8000/api/offerdetails/199/" },
    { "id": 200, "url": "http://127.0.0.1:8000/api/offerdetails/200/" },
    { "id": 201, "url": "http://127.0.0.1:8000/api/offerdetails/201/" }
  ],
  "min_price": 50,
  "min_delivery_time": 5
}
```

Weitere Statuscodes: `401` nicht authentifiziert, `404` Angebot nicht gefunden, `500` interner Serverfehler. Ein unerwarteter Serverfehler wird mit `{"detail":"Internal server error."}` beantwortet.

### `PATCH /api/offers/{id}/`
Aktualisiert nur die übermittelten Angebotsfelder. Nur der Ersteller darf das Angebot bearbeiten. Bei Detailänderungen identifiziert `offer_type` (`basic`, `standard`, `premium`) die bestehende Stufe. IDs bleiben erhalten; ausgelassene Felder und Stufen bleiben unverändert. Pflichtfelder dürfen nicht `null` sein. Ein mitgesendetes `features`-Array ersetzt die bisherige Liste. Stufen können nicht entfernt werden. Für Bild-Uploads wird Multipart verwendet: `details` ist ein JSON-kodierter Textwert; ausgelassenes `image` lässt das Bild unverändert, `image: null` löscht es. Zulässige Bildformate und Größen entsprechen dem POST-Endpunkt.

**Request Body** (`application/json`, wenn kein Bild hochgeladen oder gelöscht wird; andernfalls `multipart/form-data` mit JSON-kodiertem Feld `details`)

```json
{
  "title": "Updated Grafikdesign-Paket",
  "details": [
    {
      "title": "Basic Design Updated",
      "revisions": 3,
      "delivery_time_in_days": 6,
      "price": 120,
      "features": ["Logo Design", "Flyer"],
      "offer_type": "basic"
    }
  ]
}
```

**Erfolgreiche Antwort – `200 OK`**: `id`, `title`, `image`, `description` und alle Angebotsdetails einschließlich ihrer IDs und Detailfelder.

Weitere Statuscodes: `400` ungültige oder unvollständige Anfragedaten, `401` nicht authentifiziert, `403` nicht Ersteller, `404` Angebot nicht gefunden, `500` interner Serverfehler. Ein unerwarteter Serverfehler wird mit `{"detail":"Internal server error."}` beantwortet.

### `DELETE /api/offers/{id}/`
Löscht ein Angebot. Nur der Ersteller darf es löschen; Authentifizierung erforderlich. Bereits angelegte Bestellungen enthalten einen Snapshot der gekauften Angebotsdetails und bleiben durch eine Angebotslöschung unverändert.

**Erfolgreiche Antwort – `204 No Content`** (ohne Response-Body).

Weitere Statuscodes: `401` nicht authentifiziert, `403` nicht Ersteller, `404` Angebot nicht gefunden, `500` interner Serverfehler. Ein unerwarteter Serverfehler wird mit `{"detail":"Internal server error."}` beantwortet.

### `GET /api/offerdetails/{id}/`
Liefert ein einzelnes Angebotsdetail. Authentifizierung erforderlich.

**Erfolgreiche Antwort – `200 OK`**

```json
{
  "id": 1,
  "title": "Basic Design",
  "revisions": 2,
  "delivery_time_in_days": 5,
  "price": 100,
  "features": ["Logo Design", "Visitenkarte"],
  "offer_type": "basic"
}
```

Weitere Statuscodes: `401` nicht authentifiziert, `404` Angebotsdetail nicht gefunden, `500` interner Serverfehler. Ein unerwarteter Serverfehler wird mit `{"detail":"Internal server error."}` beantwortet.

## Bestellungen

### `GET /api/orders/`
Liefert Bestellungen, bei denen der angemeldete Benutzer Kunde oder Geschäftspartner ist, neueste zuerst. Authentifizierung erforderlich. Bestellungen anderer Benutzer werden nicht zurückgegeben.

**Erfolgreiche Antwort – `200 OK`**: Liste mit Bestellungen im folgenden Format.

```json
[
  {
    "id": 1,
    "customer_user": 1,
    "business_user": 2,
    "title": "Logo Design",
    "revisions": 3,
    "delivery_time_in_days": 5,
    "price": 150,
    "features": ["Logo Design", "Visitenkarten"],
    "offer_type": "basic",
    "status": "in_progress",
    "created_at": "2024-09-29T10:00:00Z",
    "updated_at": "2024-09-30T12:00:00Z"
  }
]
```

Weitere Statuscodes: `401` nicht authentifiziert, `500` interner Serverfehler.

### `POST /api/orders/`
Erstellt eine Bestellung auf Grundlage eines Angebotsdetails. Nur authentifizierte Benutzer vom Typ `customer` dürfen Bestellungen erstellen. Selbstbestellungen (Kauf eines eigenen Angebots) sind nicht zulässig. Bestellfelder wie Titel, Preis, Features, Typ, Revisionen und Lieferzeit werden als Snapshot gespeichert; spätere Änderungen oder Löschungen des Angebots ändern die Bestellung nicht. Der Status startet als `in_progress`.

**Request Body**

```json
{
  "offer_detail_id": 1
}
```

**Erfolgreiche Antwort – `201 Created`**: erstellte Bestellung im Format der Bestellliste. Der Status beginnt beispielhaft mit `in_progress`.

Weitere Statuscodes: `400` fehlende oder ungültige Angebotsdetail-ID, `401` nicht authentifiziert, `403` keine Kundenrolle, `404` Angebotsdetail nicht gefunden, `500` interner Serverfehler.

### `PATCH /api/orders/{id}/`
Aktualisiert den Status einer Bestellung. Nur der zugeordnete Business-Benutzer darf aktualisieren. Zulässig sind ausschließlich Übergänge von `in_progress` nach `completed` oder `cancelled`; beide Zielstatus sind endgültig. Andere Statusübergänge sowie Änderungen an anderen Feldern sind unzulässig.

**Request Body**

```json
{
  "status": "completed"
}
```

**Erfolgreiche Antwort – `200 OK`**: aktualisierte Bestellung im Format der Bestellliste.

Weitere Statuscodes: `400` ungültiger Status oder unzulässige Felder, `401` nicht authentifiziert, `403` keine Berechtigung, `404` Bestellung nicht gefunden, `500` interner Serverfehler.

### `DELETE /api/orders/{id}/`
Löscht eine Bestellung. Nur Admin-Benutzer (Staff) dürfen diese Aktion ausführen; Authentifizierung erforderlich.

**Erfolgreiche Antwort – `204 No Content`** (ohne Response-Body).

Weitere Statuscodes: `401` nicht authentifiziert, `403` keine Berechtigung, `404` Bestellung nicht gefunden, `500` interner Serverfehler.

### `GET /api/order-count/{business_user_id}/`
Liefert die Anzahl der Bestellungen des Geschäftsnutzers mit Status `in_progress`. Jeder authentifizierte Benutzer darf den Endpunkt aufrufen.

**Erfolgreiche Antwort – `200 OK`**

```json
{
  "order_count": 5
}
```

Weitere Statuscodes: `401` nicht authentifiziert, `404` Geschäftsnutzer nicht gefunden, `500` interner Serverfehler.

### `GET /api/completed-order-count/{business_user_id}/`
Liefert die Anzahl der abgeschlossenen Bestellungen des Geschäftsnutzers. Jeder authentifizierte Benutzer darf den Endpunkt aufrufen.

**Erfolgreiche Antwort – `200 OK`**

```json
{
  "completed_order_count": 10
}
```

Weitere Statuscodes: `401` nicht authentifiziert, `404` Geschäftsnutzer nicht gefunden, `500` interner Serverfehler.

## Bewertungen

### `GET /api/reviews/`
Liefert Bewertungen; alle authentifizierten Benutzer dürfen lesen. Filterung und Sortierung sind möglich. `ordering` akzeptiert `updated_at`, `-updated_at`, `rating` und `-rating`. Ungültige Filter- oder Sortierparameter ergeben `400`.

**Query-Parameter**

| Parameter | Typ | Beschreibung |
| --- | --- | --- |
| `business_user_id` | integer | Filtert nach dem bewerteten Geschäftsnutzer. |
| `reviewer_id` | integer | Filtert nach dem Benutzer, der die Bewertung erstellt hat. |
| `ordering` | string | Sortierung nach `updated_at`, `-updated_at`, `rating` oder `-rating`. |

**Erfolgreiche Antwort – `200 OK`**

```json
[
  {
    "id": 1,
    "business_user": 2,
    "reviewer": 3,
    "rating": 4,
    "description": "Sehr professioneller Service.",
    "created_at": "2023-10-30T10:00:00Z",
    "updated_at": "2023-10-31T10:00:00Z"
  }
]
```

Weitere Statuscodes: `400` ungültige Filter- oder Sortierparameter, `401` nicht authentifiziert, `500` interner Serverfehler.

### `POST /api/reviews/`
Erstellt eine Bewertung für einen Geschäftsnutzer. Nur authentifizierte Kunden dürfen bewerten; der Kunde muss mindestens eine abgeschlossene Bestellung beim angegebenen Geschäftsnutzer haben. Pro Kunden-/Business-Paar darf höchstens eine aktive Bewertung existieren. Gelöschte Bewertungen blockieren keine neue Bewertung. `rating` ist eine ganze Zahl von 1 bis 5; `description` ist nicht leer und maximal 500 Zeichen. Wird die qualifizierende Bestellung später gelöscht, bleibt die Bewertung erhalten.

**Request Body**

```json
{
  "business_user": 2,
  "rating": 4,
  "description": "Alles war toll!"
}
```

**Erfolgreiche Antwort – `201 Created`**: neu erstellte Bewertung einschließlich `id`, `reviewer` und Zeitstempeln.

Weitere Statuscodes: `400` fehlerhafte Anfrage oder bereits vorhandene Bewertung, `401` nicht authentifiziert/kein Kundenprofil, `403` keine Berechtigung, `500` interner Serverfehler.

### `PATCH /api/reviews/{id}/`
Aktualisiert eine Bewertung. Nur der Ersteller darf sie bearbeiten; editierbar sind ausschließlich `rating` (ganze Zahl von 1 bis 5) und `description` (1 bis 500 Zeichen).

**Request Body**

```json
{
  "rating": 5,
  "description": "Noch besser als erwartet!"
}
```

**Erfolgreiche Antwort – `200 OK`**: aktualisierte Bewertung einschließlich unveränderlicher Identifikations- und Zeitstempelfelder.

Weitere Statuscodes: `400` ungültige Daten, `401` nicht authentifiziert, `403` keine Berechtigung, `404` Bewertung nicht gefunden.

### `DELETE /api/reviews/{id}/`
Löscht eine Bewertung. Nur der Ersteller darf sie löschen.

**Erfolgreiche Antwort – `204 No Content`** (ohne Response-Body).

Weitere Statuscodes: `401` nicht authentifiziert, `403` keine Berechtigung, `404` Bewertung nicht gefunden.

## Übergreifende Informationen

### `GET /api/base-info/`
Liefert öffentliche aggregierte Basisinformationen zur Plattform. Keine Authentifizierung erforderlich. `average_rating` wird über alle Bewertungen berechnet und auf eine Dezimalstelle gerundet; wenn noch keine Bewertungen vorhanden sind, ist der Wert `0.0`.

**Erfolgreiche Antwort – `200 OK`**

```json
{
  "review_count": 10,
  "average_rating": 4.6,
  "business_profile_count": 45,
  "offer_count": 150
}
```

Weitere Statuscodes: `500` interner Serverfehler.
