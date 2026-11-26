from datetime import date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import current_user
from app import db
from app.models import LibraryBook, BookIssue, Student, User, FeeDemand
from app.routes import role_required

lib_bp = Blueprint("lib", __name__)


@lib_bp.route("/library")
@role_required("librarian")
def workspace():
    q = request.args.get("q", "").strip()
    cat = request.args.get("cat", "").strip()

    # Pending issue and return requests awaiting librarian approval
    issue_requests = (
        BookIssue.query.filter_by(status="Issue Requested")
        .order_by(BookIssue.requested_on.asc())
        .all()
    )
    return_requests = (
        BookIssue.query.filter_by(status="Return Requested")
        .order_by(BookIssue.requested_on.asc())
        .all()
    )
    active_issues = (
        BookIssue.query.filter_by(status="Issued")
        .order_by(BookIssue.due_date.asc())
        .all()
    )
    recent_history = (
        BookIssue.query.filter(BookIssue.status.in_(["Returned", "Rejected"]))
        .order_by(BookIssue.id.desc())
        .limit(15)
        .all()
    )

    book_query = LibraryBook.query
    if q:
        book_query = book_query.filter(
            LibraryBook.title.ilike(f"%{q}%")
            | LibraryBook.author.ilike(f"%{q}%")
            | LibraryBook.isbn.ilike(f"%{q}%")
        )
    if cat:
        book_query = book_query.filter_by(category=cat)
    books = book_query.order_by(LibraryBook.title.asc()).all()
    categories = [r[0] for r in db.session.query(LibraryBook.category).distinct().all()]

    stats = {
        "Total Titles": LibraryBook.query.count(),
        "Total Copies": sum(b.total_copies for b in LibraryBook.query.all()),
        "Pending Approvals": len(issue_requests) + len(return_requests),
        "Currently Issued": len(active_issues),
    }

    return render_template(
        "librarian/workspace.html",
        lib=current_user.librarian,
        stats=stats,
        issue_requests=issue_requests,
        return_requests=return_requests,
        active_issues=active_issues,
        recent_history=recent_history,
        books=books,
        categories=categories,
        q=q,
        cat=cat,
    )


@lib_bp.route("/library/books/add", methods=["POST"])
@role_required("librarian")
def add_book():
    isbn = request.form.get("isbn", "").strip()
    title = request.form.get("title", "").strip()
    author = request.form.get("author", "").strip()
    category = request.form.get("category", "Computer Science").strip()
    copies = max(1, int(request.form.get("total_copies", 5)))
    shelf = request.form.get("shelf_location", "Rack A-1").strip()

    existing = LibraryBook.query.filter_by(isbn=isbn).first()
    if existing:
        existing.total_copies += copies
        existing.available_copies += copies
        db.session.commit()
        flash(f"Updated stock for '{existing.title}' (+{copies} copies).", "success")
    else:
        book = LibraryBook(
            isbn=isbn,
            title=title,
            author=author,
            category=category,
            total_copies=copies,
            available_copies=copies,
            shelf_location=shelf,
        )
        db.session.add(book)
        db.session.commit()
        flash(f"New book '{book.title}' added to library catalog.", "success")
    return redirect(url_for("lib.workspace"))


@lib_bp.route("/library/books/<int:bid>/stock", methods=["POST"])
@role_required("librarian")
def update_stock(bid):
    book = db.get_or_404(LibraryBook, bid)
    delta = int(request.form.get("delta", 1))
    if book.total_copies + delta < (book.total_copies - book.available_copies):
        flash("Cannot reduce copies below currently issued count.", "danger")
    else:
        book.total_copies += delta
        book.available_copies += delta
        db.session.commit()
        flash(f"Updated copies for '{book.title}'.", "success")
    return redirect(url_for("lib.workspace"))


@lib_bp.route("/library/requests/<int:iid>/approve-issue", methods=["POST"])
@role_required("librarian")
def approve_issue(iid):
    issue = db.get_or_404(BookIssue, iid)
    if issue.status != "Issue Requested":
        flash("This request is no longer pending.", "warning")
        return redirect(url_for("lib.workspace"))

    if issue.book.available_copies < 1:
        flash(f"No copies available for '{issue.book.title}'.", "danger")
        return redirect(url_for("lib.workspace"))

    active_count = BookIssue.query.filter(
        BookIssue.student_id == issue.student_id,
        BookIssue.status.in_(["Issued", "Return Requested"]),
    ).count()
    if active_count >= 3:
        flash("Student already holds maximum 3 active books.", "warning")
        return redirect(url_for("lib.workspace"))

    loan_days = max(1, int(request.form.get("loan_days", 14)))
    issue.book.available_copies -= 1
    issue.status = "Issued"
    issue.issued_on = date.today()
    issue.due_date = date.today() + timedelta(days=loan_days)
    issue.approved_by_id = current_user.id
    issue.remarks = f"Approved by {current_user.name}"
    db.session.commit()

    flash(f"Approved issue of '{issue.book.title}' to {issue.student.user.name} (Due: {issue.due_date:%d %b %Y}).", "success")
    return redirect(url_for("lib.workspace"))


@lib_bp.route("/library/requests/<int:iid>/reject-issue", methods=["POST"])
@role_required("librarian")
def reject_issue(iid):
    issue = db.get_or_404(BookIssue, iid)
    if issue.status != "Issue Requested":
        return redirect(url_for("lib.workspace"))

    reason = request.form.get("remarks", "Request declined by Librarian").strip()
    issue.status = "Rejected"
    issue.approved_by_id = current_user.id
    issue.remarks = reason
    db.session.commit()
    flash(f"Rejected issue request from {issue.student.user.name}.", "info")
    return redirect(url_for("lib.workspace"))


@lib_bp.route("/library/requests/<int:iid>/approve-return", methods=["POST"])
@role_required("librarian")
def approve_return(iid):
    issue = db.get_or_404(BookIssue, iid)
    if issue.status not in ("Return Requested", "Issued"):
        flash("Book is not currently issued.", "warning")
        return redirect(url_for("lib.workspace"))

    fine = issue.computed_fine
    if fine > 0 and not issue.fine_paid:
        # Ensure unpaid FeeDemand exists for student
        demand = FeeDemand.query.filter_by(
            student_id=issue.student_id,
            fee_type="Library Fine",
            reference_id=issue.id,
            status="Unpaid",
        ).first()
        if not demand:
            demand = FeeDemand(
                student_id=issue.student_id,
                fee_type="Library Fine",
                title=f"Library Overdue Fine: {issue.book.title} ({issue.overdue_days} days)",
                semester=issue.student.semester,
                amount=fine,
                due_date=date.today(),
                status="Unpaid",
                reference_id=issue.id,
            )
            db.session.add(demand)
            db.session.commit()
        flash(
            f"Cannot approve return yet: {issue.student.user.name} has an unpaid overdue fine of ₹{fine:.2f}.",
            "danger",
        )
        return redirect(url_for("lib.workspace"))

    issue.status = "Returned"
    issue.returned_on = date.today()
    issue.approved_by_id = current_user.id
    issue.book.available_copies += 1
    db.session.commit()
    flash(f"Return approved for '{issue.book.title}' from {issue.student.user.name}. Stock restored.", "success")
    return redirect(url_for("lib.workspace"))
