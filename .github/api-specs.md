# Coderr API-Spezifikation

Diese Spezifikation wurde aus [api-doku.html](api-doku.html) abgeleitet. Sie beschreibt die dort dokumentierten Endpunkte und Beispielantworten.

## Allgemeines

- **API-Präfix:** `/api/`
- **Datenformat:** JSON
- **Authentifizierung:** Geschützte Endpunkte setzen ein Authentifizierungs-Token voraus. Die HTML-Dokumentation legt das genaue Header-Format nicht fest.
- **Ratenbegrenzung:** Für die dokumentierten Endpunkte ist kein Limit angegeben.
- Pfadparameter in geschweiften Klammern, z. B. `{id}`, müssen durch den jeweiligen Wert ersetzt werden.
- Datumswerte werden als ISO-8601-Strings zurückgegeben.

## Authentifizierung

### `POST /api/registration/`
Erstellt ein Benutzerkonto vom Typ `customer` oder `business`. Keine Authentifizierung erforderlich.

**Request Body**

```json
{
  "username": "exampleUsername",
  "email": "example@mail.de",
  "password": "examplePassword",
  "repeated_password": "examplePassword",
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

Weitere Statuscodes: `400` ungültige Anfragedaten, `500` interner Serverfehler.

### `POST /api/login/`
Authentifiziert einen Benutzer und liefert ein Token. Keine Authentifizierung erforderlich.

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

Weitere Statuscodes: `400` ungültige Anfragedaten, `500` interner Serverfehler.

## Profile

### `GET /api/profile/{pk}/`
Liefert das vollständige Profil des Benutzers `{pk}`. Authentifizierung erforderlich.

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
Aktualisiert ausgewählte Profildaten. Benutzer dürfen ausschließlich ihr eigenes Profil bearbeiten; Authentifizierung erforderlich.

**Request Body** (alle gezeigten Felder sind Beispiele für änderbare Felder)

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

**Erfolgreiche Antwort – `200 OK`**: aktualisiertes Profil im selben Format wie bei `GET /api/profile/{pk}/`.

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
Liefert eine Liste der Kundenprofile. Authentifizierung erforderlich.

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
Liefert Angebote mit Angebotsdetails, Mindestpreis und kürzester Lieferzeit. Keine Authentifizierung erforderlich. Die Antwort ist paginiert (PageNumberPagination).

**Query-Parameter**

| Parameter | Typ | Beschreibung |
| --- | --- | --- |
| `creator_id` | integer | Filtert nach dem Ersteller des Angebots. |
| `min_price` | float | Filtert nach einem Mindestpreis. |
| `max_delivery_time` | integer | Filtert nach Lieferzeit kleiner oder gleich dem Wert. |
| `ordering` | string | Sortierung nach `updated_at` oder `min_price`. |
| `search` | string | Durchsucht `title` und `description`. |
| `page_size` | integer | Anzahl der Ergebnisse pro Seite. |

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
Erstellt ein Angebot. Erfordert Authentifizierung; nur Benutzer vom Typ `business` dürfen Angebote erstellen. Ein Angebot muss drei Angebotsdetails enthalten.

**Request Body**

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

**Erfolgreiche Antwort – `201 Created`**: erstelltes Angebot mit `id` sowie den Angebotsdetails einschließlich ihrer IDs.

Weitere Statuscodes: `400` ungültige oder unvollständige Anfragedaten, `401` nicht authentifiziert, `403` kein Business-Profil, `500` interner Serverfehler.

### `GET /api/offers/{id}/`
Liefert ein einzelnes Angebot und dessen Detail-URLs. Authentifizierung erforderlich.

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

Weitere Statuscodes: `401` nicht authentifiziert, `404` Angebot nicht gefunden, `500` interner Serverfehler.

### `PATCH /api/offers/{id}/`
Aktualisiert nur die übermittelten Angebotsfelder. Nur der Ersteller darf das Angebot bearbeiten. Bei Detailänderungen sollen die bestehenden IDs erhalten bleiben und `offer_type` mitgesendet werden.

**Request Body**

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

**Erfolgreiche Antwort – `200 OK`**: das vollständige aktualisierte Angebot einschließlich aller Angebotsdetails.

Weitere Statuscodes: `400` ungültige oder unvollständige Anfragedaten, `401` nicht authentifiziert, `403` nicht Ersteller, `404` Angebot nicht gefunden, `500` interner Serverfehler.

### `DELETE /api/offers/{id}/`
Löscht ein Angebot. Nur der Ersteller darf es löschen; Authentifizierung erforderlich.

**Erfolgreiche Antwort – `204 No Content`** (ohne Response-Body).

Weitere Statuscodes: `401` nicht authentifiziert, `403` nicht Ersteller, `404` Angebot nicht gefunden, `500` interner Serverfehler.

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

Weitere Statuscodes: `401` nicht authentifiziert, `404` Angebotsdetail nicht gefunden, `500` interner Serverfehler.

## Bestellungen

### `GET /api/orders/`
Liefert Bestellungen, bei denen der angemeldete Benutzer Kunde oder Geschäftspartner ist. Authentifizierung erforderlich.

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
Erstellt eine Bestellung auf Grundlage eines Angebotsdetails. Nur authentifizierte Benutzer vom Typ `customer` dürfen Bestellungen erstellen.

**Request Body**

```json
{
  "offer_detail_id": 1
}
```

**Erfolgreiche Antwort – `201 Created`**: erstellte Bestellung im Format der Bestellliste. Der Status beginnt beispielhaft mit `in_progress`.

Weitere Statuscodes: `400` fehlende oder ungültige Angebotsdetail-ID, `401` nicht authentifiziert, `403` keine Kundenrolle, `404` Angebotsdetail nicht gefunden, `500` interner Serverfehler.

### `PATCH /api/orders/{id}/`
Aktualisiert den Status einer Bestellung. Laut Dokumentation kann ein Business-Benutzer den Status aktualisieren. Als mögliche Werte werden `in_progress`, `completed` und `cancelled` genannt.

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
Liefert die Anzahl der Bestellungen des Geschäftsnutzers mit Status `in_progress`. Authentifizierung erforderlich.

**Erfolgreiche Antwort – `200 OK`**

```json
{
  "order_count": 5
}
```

Weitere Statuscodes: `401` nicht authentifiziert, `404` Geschäftsnutzer nicht gefunden, `500` interner Serverfehler.

### `GET /api/completed-order-count/{business_user_id}/`
Liefert die Anzahl der abgeschlossenen Bestellungen des Geschäftsnutzers. Authentifizierung erforderlich.

**Erfolgreiche Antwort – `200 OK`**

```json
{
  "completed_order_count": 10
}
```

Weitere Statuscodes: `401` nicht authentifiziert, `404` Geschäftsnutzer nicht gefunden, `500` interner Serverfehler.

## Bewertungen

### `GET /api/reviews/`
Liefert Bewertungen; Filterung und Sortierung sind möglich. Authentifizierung erforderlich.

**Query-Parameter**

| Parameter | Typ | Beschreibung |
| --- | --- | --- |
| `business_user_id` | integer | Filtert nach dem bewerteten Geschäftsnutzer. |
| `reviewer_id` | integer | Filtert nach dem Benutzer, der die Bewertung erstellt hat. |
| `ordering` | string | Sortierung nach `updated_at` oder `rating`. |

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

Weitere Statuscodes: `401` nicht authentifiziert, `500` interner Serverfehler.

### `POST /api/reviews/`
Erstellt eine Bewertung für einen Geschäftsnutzer. Nur authentifizierte Benutzer mit Kundenprofil dürfen Bewertungen erstellen; pro Geschäftsnutzer ist eine Bewertung je Benutzer möglich.

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
Aktualisiert eine Bewertung. Nur der Ersteller darf sie bearbeiten; editierbar sind `rating` und `description`.

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
Liefert öffentliche aggregierte Basisinformationen zur Plattform. Keine Authentifizierung erforderlich. `average_rating` wird über alle Bewertungen berechnet und auf eine Dezimalstelle gerundet.

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
