import os
import uuid
from datetime import date
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import current_user, login_required
from app import db
from app.models import (
    Student, Faculty, Librarian, Course, User, Notice, Attendance,
    FeeDemand, Payment, ExamEnrollment, BookIssue, TimetableSlot, LibraryBook
)
from app.routes import role_required

dash_bp = Blueprint("dash", __name__)

ALLOWED_EXTS = {"png", "jpg", "jpeg", "gif", "webp"}


def _allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTS


@dash_bp.route("/dashboard")
@login_required
def home():
    # Librarian goes straight to dedicated Library Workspace
    if current_user.role == "librarian":
        return redirect(url_for("lib.workspace"))

    notices = Notice.query.order_by(Notice.pinned.desc(), Notice.created_at.desc()).limit(4).all()

    if current_user.role == "admin":
        stats = {
            "Students": Student.query.count(),
            "Faculty": Faculty.query.count(),
            "Courses": Course.query.count(),
            "Fee Collected": f"₹{sum(p.amount for p in Payment.query.filter_by(status='Success').all()):,.0f}",
        }
        recent_payments = Payment.query.order_by(Payment.paid_at.desc()).limit(6).all()
        pending_dues = FeeDemand.query.filter_by(status="Unpaid").count()
        return render_template(
            "dashboard/admin.html",
            stats=stats,
            notices=notices,
            recent_payments=recent_payments,
            pending_dues=pending_dues,
        )

    if current_user.role == "faculty":
        fac = current_user.faculty
        courses = Course.query.filter_by(faculty_id=fac.id).all()
        course_stats = []
        for c in courses:
            total_students = Student.query.filter_by(department_id=c.department_id, semester=c.semester).count()
            classes_taken = db.session.query(Attendance.date).filter_by(course_id=c.id).distinct().count()
            low_att = 0
            for st in Student.query.filter_by(department_id=c.department_id, semester=c.semester).all():
                tot = Attendance.query.filter_by(student_id=st.id, course_id=c.id).count()
                att = Attendance.query.filter_by(student_id=st.id, course_id=c.id, present=True).count()
                if tot > 0 and (att * 100 / tot) < 75:
                    low_att += 1
            course_stats.append({
                "course": c,
                "total_students": total_students,
                "classes_taken": classes_taken,
                "low_att": low_att,
            })
        today_name = date.today().strftime("%A")
        my_slots = (
            TimetableSlot.query.join(Course)
            .filter(Course.faculty_id == fac.id, TimetableSlot.day_of_week == today_name)
            .all()
        )
        return render_template(
            "dashboard/faculty.html",
            fac=fac,
            course_stats=course_stats,
            notices=notices,
            my_slots=my_slots,
            today_name=today_name,
        )

    # Student Dashboard
    s = current_user.student
    courses = Course.query.filter_by(department_id=s.department_id, semester=s.semester).all()
    att_summary = []
    tot_classes = 0
    tot_present = 0
    for c in courses:
        t = Attendance.query.filter_by(student_id=s.id, course_id=c.id).count()
        a = Attendance.query.filter_by(student_id=s.id, course_id=c.id, present=True).count()
        tot_classes += t
        tot_present += a
        att_summary.append({
            "course": c,
            "total": t,
            "attended": a,
            "pct": round(a * 100 / t, 1) if t else 0.0,
        })
    overall_att = round(tot_present * 100 / tot_classes, 1) if tot_classes else 0.0
    unpaid_fees = FeeDemand.query.filter_by(student_id=s.id, status="Unpaid").all()
    total_due = sum(f.amount for f in unpaid_fees)

    active_books = BookIssue.query.filter(
        BookIssue.student_id == s.id,
        BookIssue.status.in_(["Issued", "Return Requested"]),
    ).all()
    pending_book_reqs = BookIssue.query.filter_by(student_id=s.id, status="Issue Requested").count()
    lib_fine = sum(b.computed_fine for b in active_books if not b.fine_paid)

    exam_enr = ExamEnrollment.query.filter_by(student_id=s.id, semester=s.semester).first()
    today_name = date.today().strftime("%A")
    today_slots = (
        TimetableSlot.query.join(Course)
        .filter(
            Course.department_id == s.department_id,
            Course.semester == s.semester,
            TimetableSlot.day_of_week == today_name,
        )
        .all()
    )
    return render_template(
        "dashboard/student.html",
        s=s,
        courses=courses,
        att_summary=att_summary,
        overall_att=overall_att,
        total_due=total_due,
        unpaid_count=len(unpaid_fees),
        active_books=active_books,
        pending_book_reqs=pending_book_reqs,
        lib_fine=lib_fine,
        exam_enr=exam_enr,
        notices=notices,
        today_slots=today_slots,
        today_name=today_name,
    )


@dash_bp.route("/students")
@role_required("admin", "faculty", "librarian")
def students():
    q = request.args.get("q", "").strip()
    sem = request.args.get("sem", "").strip()
    query = Student.query.join(User)
    if q:
        query = query.filter(
            (User.name.ilike(f"%{q}%"))
            | (Student.roll_no.ilike(f"%{q}%"))
            | (Student.reg_no.ilike(f"%{q}%"))
        )
    if sem.isdigit():
        query = query.filter(Student.semester == int(sem))
    return render_template(
        "dashboard/students.html",
        students=query.order_by(Student.roll_no).all(),
        q=q,
        sem=sem,
    )


@dash_bp.route("/student/<int:sid>/profile")
@role_required("admin", "faculty", "librarian")
def student_profile(sid):
    s = db.get_or_404(Student, sid)
    courses = Course.query.filter_by(department_id=s.department_id, semester=s.semester).all()
    att_rows = []
    for c in courses:
        t = Attendance.query.filter_by(student_id=s.id, course_id=c.id).count()
        a = Attendance.query.filter_by(student_id=s.id, course_id=c.id, present=True).count()
        att_rows.append({"course": c, "total": t, "attended": a, "pct": round(a * 100 / t, 1) if t else 0})
    payments = Payment.query.filter_by(student_id=s.id).order_by(Payment.paid_at.desc()).all()
    issues = BookIssue.query.filter_by(student_id=s.id).order_by(BookIssue.requested_on.desc()).all()
    return render_template(
        "dashboard/student_profile.html",
        s=s,
        att_rows=att_rows,
        payments=payments,
        issues=issues,
    )


@dash_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "upload_photo":
            file = request.files.get("photo")
            photo_url = request.form.get("photo_url", "").strip()
            if file and file.filename:
                if not _allowed_file(file.filename):
                    flash("Please upload a valid image (PNG, JPG, JPEG, WEBP, GIF).", "danger")
                    return redirect(url_for("dash.profile"))
                ext = file.filename.rsplit(".", 1)[1].lower()
                fname = f"user_{current_user.id}_{uuid.uuid4().hex[:8]}.{ext}"
                save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], fname)
                file.save(save_path)
                current_user.profile_photo = fname
                db.session.commit()
                flash("Profile photo updated!", "success")
            elif photo_url:
                current_user.profile_photo = photo_url
                db.session.commit()
                flash("Profile photo URL updated!", "success")
            else:
                flash("Choose an image file or paste an image URL.", "warning")

        elif action == "update_info":
            current_user.name = request.form.get("name", current_user.name).strip()
            if current_user.role == "student" and current_user.student:
                current_user.student.phone = request.form.get("phone", "").strip()
                current_user.student.address = request.form.get("address", "").strip()
                current_user.student.guardian_name = request.form.get("guardian_name", "").strip()
            elif current_user.role == "faculty" and current_user.faculty:
                current_user.faculty.phone = request.form.get("phone", "").strip()
            elif current_user.role == "librarian" and current_user.librarian:
                current_user.librarian.phone = request.form.get("phone", "").strip()
            db.session.commit()
            flash("Profile details updated successfully.", "success")

        elif action == "change_password":
            old_pw = request.form.get("old_password", "")
            new_pw = request.form.get("new_password", "")
            if not current_user.check_password(old_pw):
                flash("Current password is incorrect.", "danger")
            elif len(new_pw) < 6:
                flash("New password must be at least 6 characters.", "warning")
            else:
                current_user.set_password(new_pw)
                db.session.commit()
                flash("Password changed successfully.", "success")
        return redirect(url_for("dash.profile"))
    return render_template("dashboard/profile.html")
