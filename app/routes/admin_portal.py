from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app import db
from app.models import Student, FeeDemand, Payment
from app.routes import role_required

admin_bp = Blueprint("admin_p", __name__)


@admin_bp.route("/admin/fees", methods=["GET", "POST"])
@role_required("admin")
def manage_fees():
    if request.method == "POST":
        sem = int(request.form.get("semester", 1))
        fee_type = request.form.get("fee_type", "Semester Fee")
        title = request.form.get("title", "").strip()
        amount = float(request.form.get("amount", 0))
        due_date = datetime.strptime(request.form["due_date"], "%Y-%m-%d").date()

        students = Student.query.filter_by(semester=sem).all()
        created = 0
        for st in students:
            exists = FeeDemand.query.filter_by(student_id=st.id, title=title).first()
            if not exists:
                db.session.add(
                    FeeDemand(
                        student_id=st.id,
                        fee_type=fee_type,
                        title=title,
                        semester=sem,
                        amount=amount,
                        due_date=due_date,
                    )
                )
                created += 1
        db.session.commit()
        flash(f"Generated '{title}' for {created} students in Semester {sem}.", "success")
        return redirect(url_for("admin_p.manage_fees"))

    demands = FeeDemand.query.order_by(FeeDemand.id.desc()).limit(30).all()
    payments = Payment.query.order_by(Payment.paid_at.desc()).limit(20).all()
    return render_template("admin/manage_fees.html", demands=demands, payments=payments)
