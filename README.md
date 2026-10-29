# Coderr – Backend

[![Python](https://img.shields.io/badge/Python-3.14-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-6.1-092E20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Django REST Framework](https://img.shields.io/badge/DRF-3.18-red)](https://www.django-rest-framework.org/)
[![Database](https://img.shields.io/badge/Database-SQLite-lightgrey?logo=sqlite&logoColor=blue)](https://www.sqlite.org/)
[![Frontend](https://img.shields.io/badge/Frontend-Vanilla%20JavaScript-yellow?logo=javascript)](https://github.com/Developer-Akademie-Backendkurs/project.Coderr)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Coderr is a platform that connects customers with freelancers offering digital services, similar to Fiverr. This repository contains the project's Django REST API. The frontend is maintained in a separate repository.

- **Frontend:** [Developer-Akademie-Backendkurs/project.Coderr](https://github.com/Developer-Akademie-Backendkurs/project.Coderr)
- **API documentation:** [api-specs.md](.github/api-specs.md)
- **License:** MIT (see [LICENSE](LICENSE))

## Table of Contents

- [Project Overview](#project-overview)
- [Project Structure](#project-structure)
- [Frontend Configuration](#frontend-configuration)
- [Features and Pages](#features-and-pages)
- [Guest Logins](#guest-logins)
- [Local Setup](#local-setup)
- [Testing and API Usage](#testing-and-api-usage)

## Project Overview

Coderr connects customers looking for digital services with freelancers showcasing their offers on the platform. The application is split into a backend and a frontend. The backend provides the REST API and business logic; the frontend is a standalone Vanilla JavaScript project.

| Area | Technology / Status |
| --- | --- |
| Backend | Python 3.14, Django 6.1, Django REST Framework 3.18 |
| Database | SQLite is configured by default for local development; PostgreSQL can be used with a suitable deployment configuration |
| Tests | Django test runner and `unittest`-based Django tests; Pytest is not currently configured in `requirements.txt` |
| Frontend | Vanilla JavaScript, HTML, and CSS; see the [frontend repository](https://github.com/Developer-Akademie-Backendkurs/project.Coderr) |

## Project Structure

The backend lives in the root of this repository. The frontend is maintained in the separate repository linked above, so `frontend/` is not part of this checkout.

```text
Coderr-Backend/
├── accounts_app/       # Users, profiles, login, and registration
│   ├── api/             # API views, serializers, and account tests
│   └── migrations/      # Database schema and seeded guest accounts
├── core/                # Django configuration and shared API functionality
│   └── api/             # Base information, utilities, and tests
├── marketplace_app/     # Offers, orders, and reviews
│   ├── api/             # Feature-specific API modules and tests
│   └── migrations/
├── manage.py
├── requirements.txt
└── db.sqlite3           # Local development database (created as needed)
```

## Frontend Configuration

The frontend uses a central configuration file for API endpoints and other defaults. Depending on the frontend version, it may be located at `frontend/src/assets/config.js` or simply named `config.js`. In the linked Vanilla JavaScript frontend, it is located at `shared/scripts/config.js`.

When connecting the frontend to this backend, make sure the API base URL and guest login credentials in this file match the backend configuration. Set the following page size for offer pagination:

```js
PAGE_SIZE = 3
```

The backend returns three offers per page by default and allows up to 100 items through the `page_size` query parameter.

## Features and Pages

The following table summarizes the main frontend pages and their functionality. The current frontend uses the generic HTML document title `Coderr/` across pages, so the page name below refers to each application's area.

| Page / Area | Frontend page | Features |
| --- | --- | --- |
| Landing / Home | `index.html` | Discover and search services; view platform statistics |
| Offers / Services | `offer_list.html` | Browse offers and filter or sort by delivery time and price |
| Offer details | `offer.html` | View offer details and reviews; select Basic, Standard, or Premium tiers; place an order |
| Orders / Profile | `own_profile.html` | View and manage personal orders and profile; available functions depend on the customer or freelancer role |
| Login | `login.html` | Sign in with a username and password or choose a customer/freelancer guest login |
| Registration | `registration.html` | Create a customer or freelancer account |

Key API routes include `/api/login/`, `/api/registration/`, `/api/offers/`, `/api/orders/`, `/api/reviews/`, and `/api/base-info/`.

## Guest Logins

Running `migrate` creates two guest accounts, each with a profile and API token. They are intended for local previews and development.

| Role | Username | Email | Password |
| --- | --- | --- | --- |
| Customer (`customer`) | `guest_customer` | `guest_customer@example.com` | `guest1234` |
| Freelancer (`business`) | `guest_business` | `guest_business@example.com` | `guest1234` |

> **Security notice:** These credentials are public and intended only for local development and demos. Replace or disable them before any public or production deployment.

## Local Setup

Make sure you have a Python version compatible with the packages listed in `requirements.txt`.

1. Clone this repository and open the backend directory.
2. Create and activate a virtual environment:

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

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Apply database migrations. This also creates the guest accounts:

   ```bash
   python manage.py migrate
   ```

5. Start the development server:

   ```bash
   python manage.py runserver
   ```

The API is then available at <http://127.0.0.1:8000/api/> by default. SQLite is used as the local database according to the Django configuration.

## Testing and API Usage

Run the test suite with Django's built-in test runner:

```bash
python manage.py test
```

You can test the API with a client such as Postman. Start the local server, use the routes described in the API documentation, and send a token with protected endpoints using the `Authorization: Token <token>` header.
