import uuid
try:
    import razorpay
except ImportError:
    razorpay = None

from datetime import date, datetime, timedelta
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, current_app, abort
)
from flask_login import current_user
from app import db
from app.models import (
    Course, Attendance, Mark, StudyMaterial, ExamEnrollment,
    FeeDemand, Payment, LibraryBook, BookIssue
)
from app.routes import role_required
from app.routes.academic import grade

stud_bp = Blueprint("stud", __name__)


def _rzp_client():
    if razorpay is None:
        return None
    kid = current_app.config.get("RAZORPAY_KEY_ID")
    sec = current_app.config.get("RAZORPAY_KEY_SECRET")
    if kid and sec and not kid.startswith("rzp_test_xxxx"):
        return razorpay.Client(auth=(kid, sec))
    return None


@stud_bp.route("/my/attendance")
@role_required("student")
def my_attendance():
    s = current_user.student
    courses = Course.query.filter_by(department_id=s.department_id, semester=s.semester).all()
    rows = []
    overall_tot = 0
    overall_att = 0
    for c in courses:
        recs = (
            Attendance.query.filter_by(student_id=s.id, course_id=c.id)
            .order_by(Attendance.date.desc())
            .all()
        )
        total = len(recs)
        att = sum(1 for r in recs if r.present)
        overall_tot += total
        overall_att += att
        pct = round(att * 100 / total, 1) if total else 0.0
        needed = 0
        if total > 0 and pct < 75:
            needed = max(0, int((0.75 * total - att) / 0.25 + 0.999))
        rows.append({
            "course": c,
            "total": total,
            "attended": att,
            "absent": total - att,
            "pct": pct,
            "needed": needed,
            "history": recs[:12],
        })
    overall_pct = round(overall_att * 100 / overall_tot, 1) if overall_tot else 0.0
    return render_template(
        "student/my_attendance.html",
        s=s,
        rows=rows,
        overall_tot=overall_tot,
        overall_att=overall_att,
        overall_pct=overall_pct,
    )


@stud_bp.route("/my/materials")
@role_required("student")
def my_materials():
    s = current_user.student
    courses = Course.query.filter_by(department_id=s.department_id, semester=s.semester).all()
    cids = [c.id for c in courses]
    materials = (
        StudyMaterial.query.filter(StudyMaterial.course_id.in_(cids))
        .order_by(StudyMaterial.created_at.desc())
        .all()
        if cids else []
    )
    return render_template("student/materials.html", courses=courses, materials=materials)


@stud_bp.route("/my/marksheet")
@role_required("student")
def marksheet():
    s = current_user.student
    courses = Course.query.filter_by(department_id=s.department_id, semester=s.semester).all()
    rows, got, mx = [], 0.0, 0.0
    total_credits = 0
    weighted_points = 0.0
    gp_map = {"O": 10, "A+": 9, "A": 8, "B+": 7, "B": 6, "C": 5, "F": 0}

    for c in courses:
        ms = Mark.query.filter_by(student_id=s.id, course_id=c.id).all()
        if not ms:
            continue
        g = sum(m.marks for m in ms)
        t = sum(m.max_marks for m in ms)
        got += g
        mx += t
        cpct = round(g * 100 / t, 2) if t else 0
        cg = grade(cpct)
        total_credits += c.credits
        weighted_points += gp_map.get(cg, 0) * c.credits
        rows.append({
            "course": c,
            "marks": ms,
            "total": round(g, 1),
            "max": round(t, 1),
            "pct": cpct,
            "grade": cg,
        })

    pct = round(got * 100 / mx, 2) if mx else 0.0
    sgpa = round(weighted_points / total_credits, 2) if total_credits else 0.0
    return render_template(
        "docs/marksheet.html",
        s=s,
        rows=rows,
        got=round(got, 1),
        mx=round(mx, 1),
        pct=pct,
        g=grade(pct),
        sgpa=sgpa,
        auto_print=request.args.get("print") == "1",
    )


@stud_bp.route("/my/registration")
@role_required("student")
def registration_card():
    s = current_user.student
    courses = Course.query.filter_by(department_id=s.department_id, semester=s.semester).all()
    return render_template(
        "docs/registration_card.html",
        s=s,
        courses=courses,
        auto_print=request.args.get("print") == "1",
    )


@stud_bp.route("/my/admit-card")
@role_required("student")
def admit_card():
    s = current_user.student
    enr = ExamEnrollment.query.filter_by(student_id=s.id, semester=s.semester).first()
    if not enr or enr.status != "Enrolled":
        flash("Complete your Exam Enrollment & Fee payment to unlock your Admit Card.", "warning")
        return redirect(url_for("stud.exam_enrollment"))
    courses = Course.query.filter_by(department_id=s.department_id, semester=s.semester).all()
    return render_template(
        "docs/admit_card.html",
        s=s,
        enr=enr,
        courses=courses,
        auto_print=request.args.get("print") == "1",
    )


@stud_bp.route("/my/exam-enrollment", methods=["GET", "POST"])
@role_required("student")
def exam_enrollment():
    s = current_user.student
    enr = ExamEnrollment.query.filter_by(student_id=s.id, semester=s.semester).first()
    if not enr:
        enr = ExamEnrollment(
            student_id=s.id,
            semester=s.semester,
            exam_session=f"Semester {s.semester} University Examinations 2026",
            fee_amount=1200.0,
            status="Pending",
        )
        db.session.add(enr)
        db.session.commit()

    demand = FeeDemand.query.filter_by(
        student_id=s.id, fee_type="Exam Fee", semester=s.semester
    ).first()
    if not demand:
        demand = FeeDemand(
            student_id=s.id,
            fee_type="Exam Fee",
            title=f"Semester {s.semester} Exam Enrollment Fee",
            semester=s.semester,
            amount=enr.fee_amount,
            due_date=date.today() + timedelta(days=15),
            status="Paid" if enr.status == "Enrolled" else "Unpaid",
            reference_id=enr.id,
        )
        db.session.add(demand)
        db.session.commit()

    courses = Course.query.filter_by(department_id=s.department_id, semester=s.semester).all()
    return render_template(
        "student/exam_enrollment.html",
        s=s,
        enr=enr,
        demand=demand,
        courses=courses,
    )


@stud_bp.route("/my/fees")
@role_required("student")
def fees_portal():
    s = current_user.student
    demands = FeeDemand.query.filter_by(student_id=s.id).order_by(FeeDemand.status.asc(), FeeDemand.due_date.asc()).all()
    payments = Payment.query.filter_by(student_id=s.id).order_by(Payment.paid_at.desc()).all()
    total_unpaid = sum(d.amount for d in demands if d.status == "Unpaid")
    total_paid = sum(p.amount for p in payments if p.status == "Success")
    return render_template(
        "student/fees.html",
        s=s,
        demands=demands,
        payments=payments,
        total_unpaid=total_unpaid,
        total_paid=total_paid,
    )


@stud_bp.route("/my/fees/<int:did>/checkout")
@role_required("student")
def fee_checkout(did):
    s = current_user.student
    demand = db.get_or_404(FeeDemand, did)
    if demand.student_id != s.id:
        abort(403)
    if demand.status == "Paid":
        flash("This fee has already been paid.", "info")
        return redirect(url_for("stud.fees_portal"))

    rzp = _rzp_client()
    order_id = f"order_sim_{uuid.uuid4().hex[:12]}"
    rzp_key = ""
    live_mode = False

    if rzp:
        try:
            order = rzp.order.create({
                "amount": int(demand.amount * 100),
                "currency": "INR",
                "receipt": f"demand_{demand.id}_{uuid.uuid4().hex[:6]}",
                "payment_capture": 1,
            })
            order_id = order["id"]
            rzp_key = current_app.config["RAZORPAY_KEY_ID"]
            live_mode = True
        except Exception as e:
            flash(f"Razorpay API fallback to Sandbox Checkout ({e})", "warning")

    return render_template(
        "student/checkout.html",
        s=s,
        demand=demand,
        order_id=order_id,
        rzp_key=rzp_key,
        live_mode=live_mode,
    )


@stud_bp.route("/my/fees/<int:did>/confirm", methods=["POST"])
@role_required("student")
def fee_confirm(did):
    s = current_user.student
    demand = db.get_or_404(FeeDemand, did)
    if demand.student_id != s.id:
        abort(403)
    if demand.status == "Paid":
        return redirect(url_for("stud.fees_portal"))

    order_id = request.form.get("razorpay_order_id", f"order_{uuid.uuid4().hex[:10]}")
    payment_id = request.form.get("razorpay_payment_id", f"pay_{uuid.uuid4().hex[:12]}")
    signature = request.form.get("razorpay_signature", "")
    method_label = request.form.get("method_label", "Razorpay Online")

    rzp = _rzp_client()
    if rzp and signature:
        try:
            rzp.utility.verify_payment_signature({
                "razorpay_order_id": order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": signature,
            })
        except Exception:
            flash("Payment signature verification failed.", "danger")
            return redirect(url_for("stud.fees_portal"))

    demand.status = "Paid"

    if demand.fee_type == "Exam Fee":
        enr = ExamEnrollment.query.filter_by(student_id=s.id, semester=demand.semester).first()
        if enr:
            enr.status = "Enrolled"
            enr.enrolled_at = datetime.utcnow()
            if not enr.admit_no:
                enr.admit_no = f"ADM{date.today().year}{s.semester}{s.id:04d}"

    if demand.fee_type == "Library Fine" and demand.reference_id:
        issue = db.session.get(BookIssue, demand.reference_id)
        if issue:
            issue.fine_amount = demand.amount
            issue.fine_paid = True

    receipt_no = f"RCPT-{date.today().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    pay = Payment(
        receipt_no=receipt_no,
        student_id=s.id,
        fee_demand_id=demand.id,
        fee_type=demand.fee_type,
        title=demand.title,
        amount=demand.amount,
        gateway=method_label,
        razorpay_order_id=order_id,
        razorpay_payment_id=payment_id,
        status="Success",
    )
    db.session.add(pay)
    db.session.commit()

    flash(f"Payment of ₹{demand.amount:,.2f} successful! Receipt {receipt_no} generated.", "success")
    return redirect(url_for("stud.payment_receipt", pid=pay.id))


@stud_bp.route("/my/receipt/<int:pid>")
@role_required("student", "admin")
def payment_receipt(pid):
    pay = db.get_or_404(Payment, pid)
    if current_user.role == "student" and pay.student_id != current_user.student.id:
        abort(403)
    return render_template(
        "docs/payment_receipt.html",
        pay=pay,
        s=pay.student,
        auto_print=request.args.get("print") == "1",
    )


# ---------- Student: Library Access (Request Issue / Request Return / Pay Fine) ----------
@stud_bp.route("/my/library")
@role_required("student")
def library():
    s = current_user.student
    q = request.args.get("q", "").strip()
    cat = request.args.get("cat", "").strip()
    query = LibraryBook.query
    if q:
        query = query.filter(
            LibraryBook.title.ilike(f"%{q}%")
            | LibraryBook.author.ilike(f"%{q}%")
            | LibraryBook.isbn.ilike(f"%{q}%")
        )
    if cat:
        query = query.filter_by(category=cat)

    books = query.order_by(LibraryBook.title).all()
    categories = [r[0] for r in db.session.query(LibraryBook.category).distinct().all()]
    my_issues = BookIssue.query.filter_by(student_id=s.id).order_by(BookIssue.requested_on.desc()).all()
    active_count = sum(1 for i in my_issues if i.status in ("Issue Requested", "Issued", "Return Requested"))
    unpaid_fine_total = sum(i.computed_fine for i in my_issues if not i.fine_paid and i.computed_fine > 0)

    return render_template(
        "student/library.html",
        s=s,
        books=books,
        categories=categories,
        my_issues=my_issues,
        active_count=active_count,
        unpaid_fine_total=unpaid_fine_total,
        q=q,
        cat=cat,
    )


@stud_bp.route("/my/library/request-issue/<int:bid>", methods=["POST"])
@role_required("student")
def request_issue_book(bid):
    s = current_user.student
    book = db.get_or_404(LibraryBook, bid)
    ongoing = BookIssue.query.filter(
        BookIssue.student_id == s.id,
        BookIssue.status.in_(["Issue Requested", "Issued", "Return Requested"]),
    ).all()
    if len(ongoing) >= 3:
        flash("Maximum limit reached: You can have up to 3 active/requested books at a time.", "warning")
        return redirect(url_for("stud.library"))
    if any(i.book_id == book.id for i in ongoing):
        flash("You already have an active request or issued copy of this book.", "info")
        return redirect(url_for("stud.library"))
    if book.available_copies < 1:
        flash("No copies currently available for request.", "danger")
        return redirect(url_for("stud.library"))

    req_issue = BookIssue(
        student_id=s.id,
        book_id=book.id,
        status="Issue Requested",
        remarks="Awaiting Librarian approval",
    )
    db.session.add(req_issue)
    db.session.commit()
    flash(f"Issue request submitted for '{book.title}'. Visit the Library desk or wait for Librarian approval.", "success")
    return redirect(url_for("stud.library"))


@stud_bp.route("/my/library/request-return/<int:iid>", methods=["POST"])
@role_required("student")
def request_return_book(iid):
    s = current_user.student
    issue = db.get_or_404(BookIssue, iid)
    if issue.student_id != s.id or issue.status != "Issued":
        abort(403)

    fine = issue.computed_fine
    if fine > 0 and not issue.fine_paid:
        flash(f"Please settle the overdue fine of ₹{fine:.2f} before requesting book return.", "warning")
        return redirect(url_for("stud.pay_library_fine", iid=issue.id))

    issue.status = "Return Requested"
    issue.remarks = "Return requested by student · Awaiting Librarian verification"
    db.session.commit()
    flash(f"Return request sent for '{issue.book.title}'. Please hand over the book to the Librarian for approval.", "info")
    return redirect(url_for("stud.library"))


@stud_bp.route("/my/library/fine/<int:iid>/pay")
@role_required("student")
def pay_library_fine(iid):
    s = current_user.student
    issue = db.get_or_404(BookIssue, iid)
    if issue.student_id != s.id:
        abort(403)
    fine = issue.computed_fine
    if fine <= 0 or issue.fine_paid:
        flash("No pending fine on this book.", "info")
        return redirect(url_for("stud.library"))

    demand = FeeDemand.query.filter_by(
        student_id=s.id, fee_type="Library Fine", reference_id=issue.id, status="Unpaid"
    ).first()
    if not demand:
        demand = FeeDemand(
            student_id=s.id,
            fee_type="Library Fine",
            title=f"Library Overdue Fine: {issue.book.title} ({issue.overdue_days} days)",
            semester=s.semester,
            amount=fine,
            due_date=date.today(),
            status="Unpaid",
            reference_id=issue.id,
        )
        db.session.add(demand)
        db.session.commit()
    else:
        demand.amount = fine
        db.session.commit()

    return redirect(url_for("stud.fee_checkout", did=demand.id))
