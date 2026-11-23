# ILO (Interactive Local Organizer)

**ILO** Emphasizes local businesses and customer discovery is a smart, multi-business appointment booking platform that simplifies how local businesses manage appointments and how customers book services.

It provides every registered business with its own public booking link, allowing customers to select services, choose available time slots and confirm appointments without repetitive phone calls or WhatsApp messages.

---

## About the Project

Salons, clinics, tutors and consultants often manage appointments manually through phone calls and messaging applications. This can result in double bookings, forgotten appointments, missed customers and unnecessary communication.

SCHEDLY aims to solve these problems through a centralized booking platform where multiple businesses can independently manage their services, schedules and customer appointments.

## Key Features

### 1. Multi-Business Support
- Multiple businesses can register on the platform.
- Each business gets its own profile and public booking link.
- Business information and appointments remain separate.

### 2. Business Management
- Create and manage business profiles.
- Add, edit and delete services.
- Set service names, prices and durations.
- Configure weekly working hours.
- Set holidays and days off.

### 3. Public Booking System
- Unique booking page for every business.
- Customers can select available services.
- Date and time selection.
- Customer name and phone number collection.
- Simple appointment confirmation.

### 4. Smart Slot Generation
- Automatically calculates available appointment slots.
- Considers working hours and service duration.
- Accounts for existing bookings and buffer time.
- Prevents overlapping appointments.

### 5. Owner Dashboard
- View daily appointments.
- Manage customer details.
- View upcoming bookings.
- Access daily and weekly calendar views.
- Track completed and missed appointments.

### 6. Booking Management
- Unique booking management links.
- Appointment cancellation.
- Appointment rescheduling.
- Automatically releases cancelled time slots.

### 7. No-Show Tracking
- Business owners can mark missed appointments.
- View simple no-show reports.

### 8. Booking Confirmation
- Displays booking details after successful reservation.
- Provides a unique link to manage the appointment.
- Supports email confirmation or a WhatsApp click-to-chat link.

---

## Technology Stack

| Technology | Purpose |
|---|---|
| HTML5 | Website structure |
| CSS3 | Styling and responsive layouts |
| JavaScript | Frontend interactions |
| Python | Backend programming |
| Flask | Web framework |
| SQLite | Database management |
| Git | Version control |
| GitHub | Source code hosting |

---

## Application Pages

| Page | Description |
|---|---|
| Home | Platform introduction and features |
| Login & Registration | Business owner authentication |
| Business Setup | Business profile and service configuration |
| Public Booking | Customer appointment booking |
| Booking Confirmation | Successful booking details |
| Owner Dashboard | Appointment overview and calendar |
| Business Management | Manage services and schedules |
| Manage Booking | Cancel or reschedule appointments |

---

## How ILO Works

**For Business Owners**

1. Register on ILO.
2. Create a business profile.
3. Add services with prices and durations.
4. Configure working hours and days off.
5. Receive a unique public booking link.
6. Share the link with customers.
7. Manage appointments through the dashboard.

**For Customers**

1. Open the business's booking link.
2. Select a service.
3. Choose an available date.
4. Select a time slot.
5. Enter personal contact details.
6. Confirm the appointment.
7. Receive booking confirmation.

---

## Project Structure

```text
ILO/
│
├── app.py
├── database.db
├── requirements.txt
│
├── templates/
│   ├── index.html
│   ├── login.html
│   ├── setup.html
│   ├── booking.html
│   ├── confirmation.html
│   ├── dashboard.html
│   ├── management.html
│   └── manage_booking.html
│
├── static/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── script.js
│   └── images/
│
└── README.md
```

---

## Installation and Setup

### Prerequisites

- Python 3.10 or above
- Visual Studio Code
- Git

### Step 1: Clone the Repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
```

### Step 2: Navigate to the Project

```bash
cd SCHEDLY
```

### Step 3: Create a Virtual Environment

```bash
python -m venv venv
```

### Step 4: Activate the Virtual Environment

**Windows:**

```bash
venv\Scripts\activate
```

### Step 5: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 6: Run the Application

```bash
python app.py
```

### Step 7: Open in Browser

```text
http://127.0.0.1:5000
```

---

## Expected Demonstration

The final demonstration showcases two browser windows:

**Customer Window**
- A customer opens a business booking link.
- Selects a service and available time slot.
- Confirms an appointment.

**Business Owner Window**
- The owner's dashboard updates with the appointment.
- An attempt to book the same slot is rejected.
- Cancelling an appointment makes the slot available again.

---

## Future Enhancements

- Online payment integration.
- Email and SMS notifications.
- Advanced booking analytics.
- Customer booking history.
- Business performance reports.
- Enhanced calendar management.
- Progressive Web App (PWA) support.

---

## Project Objective

To provide a simple, reliable and efficient appointment scheduling solution for local businesses while making service booking easier and faster for customers.

**ILO — Your Business. Your Schedule. Your Bookings.**

---

ILO

Connect. Discover. Book.
