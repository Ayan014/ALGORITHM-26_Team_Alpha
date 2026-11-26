import csv
import io
from datetime import date, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response, abort
from flask_login import current_user, login_required
from app import db
from app.models import (
    Student, Course, Attendance, Mark, Notice, User, StudyMaterial, TimetableSlot
)
from app.routes import role_required

acad_bp = Blueprint("acad", __name__)


def _course_for_faculty(cid):
    c = db.get_or_404(Course, cid)
    if current_user.role == "faculty" and c.faculty_id != current_user.faculty.id:
        abort(403)
    return c


def _students_of(c):
    return (
        Student.query.filter_by(department_id=c.department_id, semester=c.semester)
        .join(User)
        .order_by(Student.roll_no)
        .all()
    )


def grade(p):
    return (
        "O" if p >= 90
        else "A+" if p >= 80
        else "A" if p >= 70
        else "B+" if p >= 60
        else "B" if p >= 50
        else "C" if p >= 40
        else "F"
    )


@acad_bp.route("/faculty/attendance/<int:cid>", methods=["GET", "POST"])
@role_required("faculty", "admin")
def take_attendance(cid):
    c = _course_for_faculty(cid)
    day_str = request.values.get("date", date.today().isoformat())
    day = datetime.strptime(day_str, "%Y-%m-%d").date()
    studs = _students_of(c)

    if request.method == "POST":
        present_ids = set(map(int, request.form.getlist("present")))
        for s in studs:
            rec = Attendance.query.filter_by(student_id=s.id, course_id=c.id, date=day).first()
            if not rec:
                rec = Attendance(student_id=s.id, course_id=c.id, date=day)
                db.session.add(rec)
            rec.present = s.id in present_ids
            rec.remarks = request.form.get(f"rem_{s.id}", "").strip()
        db.session.commit()
        flash(f"Attendance saved for {c.code} on {day:%d %b %Y} ({len(present_ids)}/{len(studs)} present).", "success")
        return redirect(url_for("acad.take_attendance", cid=cid, date=day.isoformat()))

    existing_recs = Attendance.query.filter_by(course_id=c.id, date=day).all()
    existing = {a.student_id: a.present for a in existing_recs}
    remarks_map = {a.student_id: a.remarks for a in existing_recs}
    recent_dates = [
        r[0]
        for r in db.session.query(Attendance.date)
        .filter_by(course_id=c.id)
        .distinct()
        .order_by(Attendance.date.desc())
        .limit(8)
        .all()
    ]
    return render_template(
        "faculty/take_attendance.html",
        c=c,
        studs=studs,
        day=day,
        today=date.today(),
        existing=existing,
        remarks_map=remarks_map,
        recent_dates=recent_dates,
    )


@acad_bp.route("/faculty/attendance/<int:cid>/report")
@role_required("faculty", "admin")
def attendance_report(cid):
    c = _course_for_faculty(cid)
    studs = _students_of(c)
    total_classes = db.session.query(Attendance.date).filter_by(course_id=c.id).distinct().count()
    report = []
    for s in studs:
        tot = Attendance.query.filter_by(student_id=s.id, course_id=c.id).count()
        att = Attendance.query.filter_by(student_id=s.id, course_id=c.id, present=True).count()
        pct = round(att * 100 / tot, 1) if tot else 0.0
        report.append({"student": s, "total": tot, "attended": att, "absent": tot - att, "pct": pct})

    if request.args.get("export") == "csv":
        si = io.StringIO()
        writer = csv.writer(si)
        writer.writerow(["Roll No", "Registration No", "Student Name", "Classes Held", "Attended", "Absent", "Percentage", "Status"])
        for r in report:
            status = "Eligible" if r["pct"] >= 75 else "Shortage (<75%)"
            writer.writerow([r["student"].roll_no, r["student"].reg_no, r["student"].user.name, r["total"], r["attended"], r["absent"], f"{r['pct']}%", status])
        return Response(
            si.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={c.code}_attendance_report.csv"},
        )

    return render_template("faculty/attendance_report.html", c=c, report=report, total_classes=total_classes)


@acad_bp.route("/faculty/marks/<int:cid>", methods=["GET", "POST"])
@role_required("faculty", "admin")
def enter_marks(cid):
    c = _course_for_faculty(cid)
    exam = request.values.get("exam", "Internal")
    studs = _students_of(c)

    if request.method == "POST":
        mx = float(request.form.get("max_marks", 100))
        saved = 0
        for s in studs:
            v = request.form.get(f"m_{s.id}", "").strip()
            if v == "":
                continue
            val = max(0.0, min(float(v), mx))
            rec = Mark.query.filter_by(student_id=s.id, course_id=c.id, exam_type=exam).first()
            if not rec:
                rec = Mark(student_id=s.id, course_id=c.id, exam_type=exam)
                db.session.add(rec)
            rec.marks = val
            rec.max_marks = mx
            saved += 1
        db.session.commit()
        flash(f"{exam} marks saved for {saved} students in {c.code}.", "success")
        return redirect(url_for("acad.enter_marks", cid=cid, exam=exam))

    existing = {m.student_id: m for m in Mark.query.filter_by(course_id=c.id, exam_type=exam)}
    default_max = next(iter(existing.values())).max_marks if existing else (50 if exam == "Internal" else 100)

    if request.args.get("export") == "csv":
        si = io.StringIO()
        writer = csv.writer(si)
        writer.writerow(["Roll No", "Name", "Exam Type", "Marks Obtained", "Max Marks", "Percentage", "Grade"])
        for s in studs:
            m = existing.get(s.id)
            if m:
                pct = round(m.marks * 100 / m.max_marks, 1)
                writer.writerow([s.roll_no, s.user.name, exam, m.marks, m.max_marks, f"{pct}%", grade(pct)])
        return Response(
            si.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={c.code}_{exam}_marks.csv"},
        )

    return render_template(
        "faculty/enter_marks.html",
        c=c,
        studs=studs,
        exam=exam,
        existing=existing,
        default_max=int(default_max),
    )


@acad_bp.route("/faculty/materials/<int:cid>", methods=["GET", "POST"])
@role_required("faculty", "admin")
def manage_materials(cid):
    c = _course_for_faculty(cid)
    if request.method == "POST":
        due_str = request.form.get("due_date", "").strip()
        due_dt = datetime.strptime(due_str, "%Y-%m-%d").date() if due_str else None
        mat = StudyMaterial(
            course_id=c.id,
            faculty_id=current_user.faculty.id if current_user.faculty else c.faculty_id,
            title=request.form["title"].strip(),
            material_type=request.form["material_type"],
            content=request.form["content"].strip(),
            due_date=due_dt,
        )
        db.session.add(mat)
        db.session.commit()
        flash("Study material / assignment posted to course.", "success")
        return redirect(url_for("acad.manage_materials", cid=cid))

    materials = StudyMaterial.query.filter_by(course_id=c.id).order_by(StudyMaterial.created_at.desc()).all()
    return render_template("faculty/materials.html", c=c, materials=materials)


@acad_bp.route("/faculty/materials/<int:mid>/delete", methods=["POST"])
@role_required("faculty", "admin")
def delete_material(mid):
    mat = db.get_or_404(StudyMaterial, mid)
    cid = mat.course_id
    _course_for_faculty(cid)
    db.session.delete(mat)
    db.session.commit()
    flash("Resource removed.", "info")
    return redirect(url_for("acad.manage_materials", cid=cid))


@acad_bp.route("/timetable")
@login_required
def timetable():
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    if current_user.role == "faculty":
        slots = (
            TimetableSlot.query.join(Course)
            .filter(Course.faculty_id == current_user.faculty.id)
            .order_by(TimetableSlot.start_time)
            .all()
        )
    elif current_user.role == "student":
        s = current_user.student
        slots = (
            TimetableSlot.query.join(Course)
            .filter(Course.department_id == s.department_id, Course.semester == s.semester)
            .order_by(TimetableSlot.start_time)
            .all()
        )
    else:
        slots = TimetableSlot.query.order_by(TimetableSlot.start_time).all()

    by_day = {d: [sl for sl in slots if sl.day_of_week == d] for d in days}
    return render_template("dashboard/timetable.html", days=days, by_day=by_day)


@acad_bp.route("/notices")
@login_required
def notices():
    q = request.args.get("q", "").strip()
    cat = request.args.get("cat", "").strip()
    query = Notice.query
    if q:
        query = query.filter(Notice.title.ilike(f"%{q}%") | Notice.body.ilike(f"%{q}%"))
    if cat:
        query = query.filter_by(category=cat)
    items = query.order_by(Notice.pinned.desc(), Notice.created_at.desc()).all()
    return render_template("dashboard/notices.html", items=items, q=q, cat=cat)


@acad_bp.route("/notices/new", methods=["GET", "POST"])
@role_required("admin", "faculty", "librarian")
def new_notice():
    if request.method == "POST":
        db.session.add(
            Notice(
                title=request.form["title"].strip(),
                body=request.form["body"].strip(),
                category=request.form["category"],
                pinned=bool(request.form.get("pinned")),
                author_id=current_user.id,
            )
        )
        db.session.commit()
        flash("Notice published to CampusHub.", "success")
        return redirect(url_for("acad.notices"))
    return render_template("dashboard/notice_form.html")


@acad_bp.route("/notices/<int:nid>/view")
@login_required
def view_notice(nid):
    n = db.get_or_404(Notice, nid)
    return render_template("docs/notice_print.html", n=n, auto_print=request.args.get("print") == "1")


@acad_bp.route("/notices/<int:nid>/download")
@login_required
def download_notice(nid):
    n = db.get_or_404(Notice, nid)
    text=(
        f"====================================================\n"
        f"CAMPUSHUB OFFICIAL NOTICE #{n.id}\n"
        f"Category : {n.category}\n"
        f"Published: {n.created_at:%d %b %Y, %I:%M %p}\n"
        f"Issued By: {n.author.name if n.author else 'Administration'}\n"
        f"====================================================\n\n"
        f"{n.title.upper()}\n\n"
        f"{n.body}\n"
    )
    return Response(
        text,
        mimetype="text/plain",
        headers={"Content-Disposition": f"attachment; filename=CampusHub_Notice_{n.id}.txt"},
    )
