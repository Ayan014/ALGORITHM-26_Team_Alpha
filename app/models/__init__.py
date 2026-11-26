from datetime import datetime, date
from flask import url_for
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum("student", "faculty", "admin", "librarian"), nullable=False)
    profile_photo = db.Column(db.String(255), nullable=True)  # filename in static/uploads/avatars OR external URL
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

    @property
    def avatar_url(self):
        if self.profile_photo:
            if self.profile_photo.startswith(("http://", "https://", "data:")):
                return self.profile_photo
            return url_for("static", filename=f"uploads/avatars/{self.profile_photo}")
        # Clean SVG monogram fallback embedded as data URI so it works offline too
        initials = "".join([part[0].upper() for part in self.name.split()[:2]]) or "U"
        palette = {
            "student": "#2563eb",
            "faculty": "#059669",
            "librarian": "#7c3aed",
            "admin": "#0f172a",
        }
        bg = palette.get(self.role, "#2563eb")
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128">'
            f'<rect width="128" height="128" rx="64" fill="{bg}"/>'
            f'<text x="50%" y="54%" dominant-baseline="middle" text-anchor="middle" '
            f'fill="#ffffff" font-family="Segoe UI, Arial, sans-serif" font-size="48" font-weight="bold">{initials}</text>'
            f'</svg>'
        )
        from urllib.parse import quote
        return f"data:image/svg+xml;utf8,{quote(svg)}"


class Department(db.Model):
    __tablename__ = "departments"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(15), unique=True, nullable=False)
    name = db.Column(db.String(100), unique=True, nullable=False)


class Student(db.Model):
    __tablename__ = "students"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True)
    roll_no = db.Column(db.String(30), unique=True, nullable=False, index=True)
    reg_no = db.Column(db.String(40), unique=True, nullable=False)
    admission_year = db.Column(db.Integer, default=2026)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"))
    semester = db.Column(db.Integer, default=1)
    section = db.Column(db.String(5), default="A")
    phone = db.Column(db.String(20))
    dob = db.Column(db.String(20), default="2004-05-14")
    guardian_name = db.Column(db.String(100), default="Parent / Guardian")
    address = db.Column(db.String(255), default="Campus Hostel, Block B")

    user = db.relationship("User", backref=db.backref("student", uselist=False))
    department = db.relationship("Department")


class Faculty(db.Model):
    __tablename__ = "faculty"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True)
    employee_id = db.Column(db.String(30), unique=True, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"))
    designation = db.Column(db.String(60), default="Assistant Professor")
    phone = db.Column(db.String(20))

    user = db.relationship("User", backref=db.backref("faculty", uselist=False))
    department = db.relationship("Department")


class Librarian(db.Model):
    __tablename__ = "librarians"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True)
    staff_id = db.Column(db.String(30), unique=True, nullable=False)
    designation = db.Column(db.String(60), default="Chief Librarian")
    phone = db.Column(db.String(20))

    user = db.relationship("User", backref=db.backref("librarian", uselist=False))


class Course(db.Model):
    __tablename__ = "courses"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    title = db.Column(db.String(120), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    credits = db.Column(db.Integer, default=4)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"))
    faculty_id = db.Column(db.Integer, db.ForeignKey("faculty.id"))

    department = db.relationship("Department")
    faculty = db.relationship("Faculty")


class Notice(db.Model):
    __tablename__ = "notices"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    category = db.Column(
        db.Enum("General", "Exam", "Fees", "Event", "Holiday", "Library"),
        default="General",
    )
    pinned = db.Column(db.Boolean, default=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    author = db.relationship("User")


class Attendance(db.Model):
    __tablename__ = "attendance"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), index=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), index=True)
    date = db.Column(db.Date, nullable=False)
    present = db.Column(db.Boolean, default=True)
    remarks = db.Column(db.String(120), default="")

    student = db.relationship("Student")
    course = db.relationship("Course")
    __table_args__ = (db.UniqueConstraint("student_id", "course_id", "date"),)


class Mark(db.Model):
    __tablename__ = "marks"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), index=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), index=True)
    exam_type = db.Column(db.Enum("Internal", "Midterm", "Final"), nullable=False)
    marks = db.Column(db.Float, nullable=False)
    max_marks = db.Column(db.Float, default=100)

    student = db.relationship("Student")
    course = db.relationship("Course")
    __table_args__ = (db.UniqueConstraint("student_id", "course_id", "exam_type"),)


class StudyMaterial(db.Model):
    __tablename__ = "study_materials"
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), index=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey("faculty.id"))
    title = db.Column(db.String(160), nullable=False)
    material_type = db.Column(
        db.Enum("Lecture Notes", "Assignment", "Question Bank", "Lab Manual", "Reference Link"),
        default="Lecture Notes",
    )
    content = db.Column(db.Text, nullable=False)
    due_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    course = db.relationship("Course")
    faculty = db.relationship("Faculty")


class TimetableSlot(db.Model):
    __tablename__ = "timetable_slots"
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"))
    day_of_week = db.Column(
        db.Enum("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"),
        nullable=False,
    )
    start_time = db.Column(db.String(20), nullable=False)
    end_time = db.Column(db.String(20), nullable=False)
    room = db.Column(db.String(40), nullable=False)

    course = db.relationship("Course")


class ExamEnrollment(db.Model):
    __tablename__ = "exam_enrollments"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), index=True)
    semester = db.Column(db.Integer, nullable=False)
    exam_session = db.Column(db.String(60), default="End-Semester Examinations 2026")
    fee_amount = db.Column(db.Float, default=1200.0)
    status = db.Column(db.Enum("Pending", "Enrolled"), default="Pending")
    admit_no = db.Column(db.String(40), unique=True, nullable=True)
    enrolled_at = db.Column(db.DateTime, nullable=True)

    student = db.relationship("Student")
    __table_args__ = (db.UniqueConstraint("student_id", "semester"),)


class FeeDemand(db.Model):
    __tablename__ = "fee_demands"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), index=True)
    fee_type = db.Column(
        db.Enum("Semester Fee", "Exam Fee", "Library Fine", "Hostel / Lab Fee"),
        nullable=False,
    )
    title = db.Column(db.String(150), nullable=False)
    semester = db.Column(db.Integer, default=1)
    amount = db.Column(db.Float, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.Enum("Unpaid", "Paid"), default="Unpaid")
    reference_id = db.Column(db.Integer, nullable=True)

    student = db.relationship("Student")


class Payment(db.Model):
    __tablename__ = "payments"
    id = db.Column(db.Integer, primary_key=True)
    receipt_no = db.Column(db.String(40), unique=True, nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), index=True)
    fee_demand_id = db.Column(db.Integer, db.ForeignKey("fee_demands.id"), nullable=True)
    fee_type = db.Column(db.String(60), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    gateway = db.Column(db.String(40), default="Razorpay")
    razorpay_order_id = db.Column(db.String(80))
    razorpay_payment_id = db.Column(db.String(80))
    status = db.Column(db.Enum("Success", "Failed"), default="Success")
    paid_at = db.Column(db.DateTime, default=datetime.utcnow)

    student = db.relationship("Student")
    fee_demand = db.relationship("FeeDemand")


class LibraryBook(db.Model):
    __tablename__ = "library_books"
    id = db.Column(db.Integer, primary_key=True)
    isbn = db.Column(db.String(30), unique=True, nullable=False)
    title = db.Column(db.String(180), nullable=False)
    author = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(60), default="Computer Science")
    total_copies = db.Column(db.Integer, default=5)
    available_copies = db.Column(db.Integer, default=5)
    shelf_location = db.Column(db.String(40), default="Rack A-1")


class BookIssue(db.Model):
    __tablename__ = "book_issues"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), index=True)
    book_id = db.Column(db.Integer, db.ForeignKey("library_books.id"), index=True)
    # Workflow states:
    # Issue Requested -> Issued (or Rejected) -> Return Requested -> Returned
    status = db.Column(
        db.Enum("Issue Requested", "Issued", "Return Requested", "Returned", "Rejected"),
        default="Issue Requested",
        nullable=False,
    )
    requested_on = db.Column(db.DateTime, default=datetime.utcnow)
    issued_on = db.Column(db.Date, nullable=True)
    due_date = db.Column(db.Date, nullable=True)
    returned_on = db.Column(db.Date, nullable=True)
    approved_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    remarks = db.Column(db.String(160), default="")
    fine_amount = db.Column(db.Float, default=0.0)
    fine_paid = db.Column(db.Boolean, default=False)

    student = db.relationship("Student")
    book = db.relationship("LibraryBook")
    approved_by = db.relationship("User")

    @property
    def computed_fine(self):
        if self.status in ("Issue Requested", "Rejected") or not self.due_date:
            return 0.0
        end_day = self.returned_on or date.today()
        overdue = (end_day - self.due_date).days
        if overdue > 0:
            return round(overdue * 10.0, 2)  # Rs 10/day
        return round(self.fine_amount or 0.0, 2)

    @property
    def overdue_days(self):
        if self.status in ("Issue Requested", "Rejected") or not self.due_date:
            return 0
        end_day = self.returned_on or date.today()
        return max(0, (end_day - self.due_date).days)
