# ILO — Interactive Local Organizer
### Your Business. Your Schedule. Your Bookings.

ILO is a multi-business appointment booking and management platform. Local businesses can create a public booking page, manage services and working hours, and receive appointments. Customers can book available time slots without creating an account.

## Features
- Multi-business owner accounts and isolated business data
- Unique public booking link for each business
- Service management with price, duration and buffer time
- Weekly working hours, breaks and unavailable dates
- Automatic availability calculation
- Server-side booking revalidation and SQLite write transaction
- Customer booking confirmation and secure management link
- Booking cancellation and rescheduling
- Owner dashboard, calendar and appointment status management
- No-show tracking and simple reports
- Responsive interface with custom illustrations and animations

## Technology
- HTML5, CSS3, Vanilla JavaScript
- Python, Flask, Jinja templates
- SQLite
- Werkzeug password hashing
- Session-bound CSRF tokens on form submissions

## Setup (Windows)
1. Install Python 3.10 or newer.
2. Open this folder in VS Code.
3. Create and activate a virtual environment:
```powershell
   python -m venv .venv
   .venv\\Scripts\\activate
   ```

4. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

5. Copy `.env.example` to `.env` and set a unique `SECRET_KEY`.
6. Start the application:

   ```powershell
   python app.py
   ```

7. Visit `http://127.0.0.1:5000`.

The SQLite database is initialized automatically in `instance/ilo.db`.

## Main routes
| Route | Purpose |
|---|---|
| `/` | Landing page |
| `/register` | Owner registration |
| `/login` | Owner login |
| `/setup` | Business onboarding |
| `/dashboard` | Owner dashboard |
| `/management` | Services, schedule and booking settings |
| `/book/<slug>` | Public booking page |
| `/manage/<token>` | Customer booking management |
| `/calendar` | Appointment list/calendar |
| `/profile` | Business profile editor |

## Tests
Run:

```powershell
pytest -q
```

## Important notes
- The first version supports one business profile per owner account.
- Email sending is not configured by default; on-screen confirmation and a secure management link work without an email provider.
- WhatsApp contact can be handled using the business phone number shown on the public booking page.
- Configure a strong secret key before deployment.
- For production deployment, use HTTPS, secure cookie settings, a production WSGI server, backups and operational monitoring.
- Booking times use the server's local timezone in this starter implementation. Configure the deployment timezone consistently with the businesses being served.

## Hackathon demonstration
Open the customer booking page in one browser window and the owner dashboard in another. Create a booking, verify it appears in the dashboard, then cancel it through the secure management link and confirm the time becomes available again.

---

