# KisanMandi — Smart Queue & Slot Management System

A production-ready web application built using **Flask**, **SQLAlchemy**, and **PostgreSQL** for managing state-wise agricultural mandi slot bookings, live queue tracking, payment states, and admin operations. Optimized for continuous deployment on **Vercel**.

---

## 🏗 System Architecture & Database Structure

### Database Schema

1. **User Table (`User`)**
   - `id`: Primary Key
   - `name`: Full Name
   - `mobile`: Unique Phone Number (Login identifier)
   - `password_hash`: Werkzeug Secure Hashed Password
   - `is_admin`: Boolean flag distinguishing normal farmers from Mandi Managers.

2. **Mandi Table (`Mandi`)**
   - `id`: Primary Key
   - `state`: State Name (28 States supported)
   - `name`: Regional APMC Mandi Title
   - `center`: Assigned Center / Gate Allocation

3. **Booking Table (`Booking`)**
   - `id`: Primary Key
   - `user_id`: Foreign Key (`User.id`)
   - `mandi_id`: Foreign Key (`Mandi.id`)
   - `crop`, `quantity`, `date`, `slot`: Operational Parameters
   - `token`: Sequential Token assigned per Mandi per Day
   - `status`: Booking Lifecycle (`WAITING` -> `IN_PROGRESS` -> `COMPLETED` / `ABSENT`)
   - `payment_status`: Ledger Tracker (`PENDING` -> `PAID`)

---

## 🌟 Core Features

- **2-Slot Daily Booking Limit**: Restricts any farmer account to booking a maximum of 2 slots per calendar date.
- **Dynamic Slot Availability Visuals**: Time slots update dynamically with color codes based on remaining capacity:
  - 🟢 **Green**: > 10 slots available
  - 🟡 **Yellow**: 5 - 10 slots available
  - 🟠 **Orange**: 1 - 4 slots available
  - 🔴 **Red**: 0 slots available
- **State Coverage**: Contains at least 1 verified APMC Mandi for every Indian state. Distance parameters removed.
- **Real-Time Polling & Notifications**: Polling mechanism auto-refreshes current active queue status every 4 seconds without reloads and issues Chrome/Web Notification Alerts on token progression.
- **Admin Operations Dashboard**:
  - Secure login access for administrators.
  - Manual queue advance ("Call Next").
  - Skip absent farmers without clearing record ("Mark Absent").
  - Mark completion and settlement ("Mark Done", "Mark Paid").
- **Responsive Interface**: Mobile-first grid and auto-scaling resolution across desktop, tablet, and mobile browsers.

---

## 🚀 Local Setup Instructions

1. **Clone & Setup Virtual Environment**:
   ```bash
   git clone <repo-url>
   cd kisan-mandi
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
