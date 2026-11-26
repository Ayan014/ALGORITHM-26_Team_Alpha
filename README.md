# CampusHub – Complete College Management System (Flask + MySQL + Razorpay)

## Roles & Credentials (after `python seed.py`)
- **Student**: `student1@college.edu` / `password123`
- **Faculty**: `faculty1@college.edu` / `password123`
- **Librarian**: `librarian@college.edu` / `password123`
- **Admin**: `admin@college.edu` / `admin123`

## Setup
```bash
pip install -r requirements.txt
cp .env.example .env
python seed.py
python run.py
```

## Project Structure

```text
ALGORITHM-26_Team_Alpha/
├── app/
│   ├── models/
│   │   └── __init__.py            # SQLAlchemy database models
│   ├── routes/
│   │   ├── __init__.py            # Route/blueprint registration
│   │   ├── academic.py            # Courses, attendance, marks, materials, timetable
│   │   ├── admin_portal.py        # Admin fee management and portal routes
│   │   ├── auth.py                # Authentication and login/logout routes
│   │   ├── dashboard.py           # Role dashboards, notices, profiles, student directory
│   │   ├── library_portal.py      # Library catalog, issue/return requests, approvals
│   │   └── student_portal.py      # Fees, exam enrollment, checkout/payments, library view
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css          # Application stylesheets
│   │   ├── js/
│   │   │   └── app.js             # Client-side scripts
│   │   └── uploads/
│   │       └── avatars/           # Uploaded user profile avatars
│   │           └── .gitkeep
│   ├── templates/
│   │   ├── admin/
│   │   │   └── manage_fees.html
│   │   ├── auth/
│   │   │   └── login.html
│   │   ├── dashboard/
│   │   │   ├── admin.html
│   │   │   ├── faculty.html
│   │   │   ├── notice_form.html
│   │   │   ├── notices.html
│   │   │   ├── profile.html
│   │   │   ├── student.html
│   │   │   ├── student_profile.html
│   │   │   ├── students.html
│   │   │   └── timetable.html
│   │   ├── docs/
│   │   │   ├── admit_card.html
│   │   │   ├── marksheet.html
│   │   │   ├── notice_print.html
│   │   │   ├── payment_receipt.html
│   │   │   └── registration_card.html
│   │   ├── faculty/
│   │   │   ├── attendance_report.html
│   │   │   ├── enter_marks.html
│   │   │   ├── materials.html
│   │   │   └── take_attendance.html
│   │   ├── librarian/
│   │   │   └── workspace.html
│   │   ├── student/
│   │   │   ├── checkout.html
│   │   │   ├── exam_enrollment.html
│   │   │   ├── fees.html
│   │   │   ├── library.html
│   │   │   ├── materials.html
│   │   │   └── my_attendance.html
│   │   └── base.html              # Base layout template
│   └── __init__.py                # Flask app factory and extension initialization
├── certs/
│   └── README.txt                 # Certificate/TLS notes
├── .env.example                   # Sample environment variable configuration
├── .gitignore                     # Git ignore rules
├── config.py                      # Application configuration settings
├── pyproject.toml                 # Project build/tooling configuration
├── README.md                      # Project documentation
├── requirements.txt               # Python dependencies
├── run.py                         # Application entry point
└── seed.py                        # Database seeder with sample data and demo accounts
```
