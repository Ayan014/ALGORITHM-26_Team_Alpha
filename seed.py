import random
from datetime import date, timedelta
from app import create_app, db
from app.models import (
    User, Department, Student, Faculty, Librarian, Course, Notice,
    Attendance, Mark, StudyMaterial, TimetableSlot,
    ExamEnrollment, FeeDemand, Payment, LibraryBook, BookIssue
)

app = create_app()

with app.app_context():
    db.drop_all()
    db.create_all()

    depts = [
        Department(code="CSE", name="Computer Science & Engineering"),
        Department(code="ECE", name="Electronics & Communication"),
        Department(code="ME", name="Mechanical Engineering"),
    ]
    db.session.add_all(depts)
    db.session.commit()

    def make_user(name, email, role, pw="password123"):
        u = User(name=name, email=email, role=role)
        u.set_password(pw)
        db.session.add(u)
        db.session.commit()
        return u

    admin_u = make_user("Dr. S. Mukherjee", "admin@college.edu", "admin", "admin123")

    # Librarian Account
    lib_u = make_user("Mrs. Nandita Basu", "librarian@college.edu", "librarian", "password123")
    librarian_prof = Librarian(
        user_id=lib_u.id,
        staff_id="LIB-001",
        designation="Chief Librarian",
        phone="+91-9830099887",
    )
    db.session.add(librarian_prof)

    faculty_data = [
        ("Dr. Anirban Rao", "faculty1@college.edu", "EMP101", "Professor"),
        ("Prof. Poulami Sen", "faculty2@college.edu", "EMP102", "Associate Professor"),
        ("Dr. Karthik Iyer", "faculty3@college.edu", "EMP103", "Assistant Professor"),
        ("Prof. Ritu Sharma", "faculty4@college.edu", "EMP104", "Assistant Professor"),
    ]
    fac_list = []
    for name, email, emp_id, desig in faculty_data:
        u = make_user(name, email, "faculty")
        f = Faculty(user_id=u.id, employee_id=emp_id, department_id=depts[0].id, designation=desig, phone="+91-9830011223")
        db.session.add(f)
        fac_list.append(f)
    db.session.commit()

    courses_data = [
        ("CS101", "Programming & Problem Solving in Python", 1, 4, fac_list[0].id),
        ("CS102", "Data Structures & Algorithms", 1, 4, fac_list[1].id),
        ("CS103", "Database Management Systems", 1, 4, fac_list[2].id),
        ("CS104", "Discrete Mathematics & Logic", 1, 3, fac_list[3].id),
    ]
    courses = []
    for code, title, sem, cr, fid in courses_data:
        c = Course(code=code, title=title, semester=sem, credits=cr, department_id=depts[0].id, faculty_id=fid)
        db.session.add(c)
        courses.append(c)
    db.session.commit()

    slots = [
        TimetableSlot(course_id=courses[0].id, day_of_week="Monday", start_time="10:00 AM", end_time="11:30 AM", room="LH-101"),
        TimetableSlot(course_id=courses[1].id, day_of_week="Monday", start_time="12:00 PM", end_time="01:30 PM", room="LH-102"),
        TimetableSlot(course_id=courses[2].id, day_of_week="Tuesday", start_time="10:00 AM", end_time="11:30 AM", room="DB-Lab 2"),
        TimetableSlot(course_id=courses[3].id, day_of_week="Wednesday", start_time="11:00 AM", end_time="12:30 PM", room="LH-101"),
        TimetableSlot(course_id=courses[0].id, day_of_week="Thursday", start_time="02:00 PM", end_time="04:00 PM", room="Python Lab 1"),
        TimetableSlot(course_id=courses[1].id, day_of_week="Friday", start_time="10:00 AM", end_time="11:30 AM", room="LH-103"),
        TimetableSlot(course_id=courses[2].id, day_of_week="Saturday", start_time="10:30 AM", end_time="12:00 PM", room="LH-101"),
    ]
    db.session.add_all(slots)

    sample_names = [
        "Aarav Chatterjee", "Sneha Das", "Rohan Roy", "Priya Nair", "Subham Ghosh",
        "Ananya Mondal", "Vikramaditya Sen", "Ishita Banerjee", "Sourav Pal", "Megha Dutta",
        "Debjit Bose", "Tania Khatun", "Arjun Verma", "Ritika Saha", "Kunal Sharma",
        "Nandini Mitra", "Sayan Kar", "Pooja Kumari", "Abhishek Dey", "Swati Halder",
    ]
    students = []
    for idx, full_name in enumerate(sample_names, 1):
        u = make_user(full_name, f"student{idx}@college.edu", "student")
        st = Student(
            user_id=u.id,
            roll_no=f"CSE26{idx:03d}",
            reg_no=f"10023726{idx:04d}",
            admission_year=2026,
            department_id=depts[0].id,
            semester=1,
            section="A",
            phone=f"+91-98745{idx:05d}",
            guardian_name=f"Guardian of {full_name.split()[0]}",
            address="Nazrul Hostel Block A, Campus Road",
        )
        db.session.add(st)
        students.append(st)
    db.session.commit()

    random.seed(42)
    for st in students:
        for c in courses:
            prob = 0.90 if not (st.id == 1 and c.code == "CS104") else 0.65
            for d in range(12):
                db.session.add(
                    Attendance(
                        student_id=st.id,
                        course_id=c.id,
                        date=date.today() - timedelta(days=d + 1),
                        present=random.random() < prob,
                    )
                )
            db.session.add(
                Mark(
                    student_id=st.id,
                    course_id=c.id,
                    exam_type="Internal",
                    marks=random.choice([36, 40, 42, 45, 47]),
                    max_marks=50,
                )
            )
            db.session.add(
                Mark(
                    student_id=st.id,
                    course_id=c.id,
                    exam_type="Midterm",
                    marks=random.choice([68, 74, 81, 86, 91]),
                    max_marks=100,
                )
            )

        db.session.add(
            FeeDemand(
                student_id=st.id,
                fee_type="Semester Fee",
                title="Semester 1 Academic & Tuition Fee",
                semester=1,
                amount=24500.0,
                due_date=date.today() + timedelta(days=20),
                status="Unpaid",
            )
        )
        enr = ExamEnrollment(
            student_id=st.id,
            semester=1,
            exam_session="End-Semester Examinations 2026",
            fee_amount=1200.0,
            status="Pending",
        )
        db.session.add(enr)
        db.session.flush()
        db.session.add(
            FeeDemand(
                student_id=st.id,
                fee_type="Exam Fee",
                title="Semester 1 Exam Enrollment Fee",
                semester=1,
                amount=1200.0,
                due_date=date.today() + timedelta(days=12),
                status="Unpaid",
                reference_id=enr.id,
            )
        )

    s1 = students[0]
    p1 = Payment(
        receipt_no="RCPT-20261101-A91F2C",
        student_id=s1.id,
        fee_type="Hostel / Lab Fee",
        title="Admission & Laboratory Caution Deposit",
        amount=5000.0,
        gateway="Razorpay UPI (GPay)",
        razorpay_order_id="order_init_998811",
        razorpay_payment_id="pay_init_776655",
        status="Success",
    )
    db.session.add(p1)

    db.session.add_all([
        StudyMaterial(
            course_id=courses[0].id,
            faculty_id=fac_list[0].id,
            title="Unit 1 & 2: Python Functions, Decorators & File Handling",
            material_type="Lecture Notes",
            content="Complete lecture notes covering lambda functions, list comprehensions, exception handling, and CSV/JSON file I/O.",
        ),
        StudyMaterial(
            course_id=courses[2].id,
            faculty_id=fac_list[2].id,
            title="Assignment 2: ER Diagram & 3NF Normalization",
            material_type="Assignment",
            due_date=date.today() + timedelta(days=7),
            content="Design a normalized relational schema (up to 3NF) for a Hospital Management System and write 10 SQL join queries.",
        ),
    ])

    books = [
        LibraryBook(isbn="978-0134685991", title="Effective Java (3rd Edition)", author="Joshua Bloch", category="Programming", total_copies=5, available_copies=4, shelf_location="CS-A1"),
        LibraryBook(isbn="978-0262046305", title="Introduction to Algorithms (CLRS)", author="Thomas H. Cormen", category="Algorithms", total_copies=6, available_copies=5, shelf_location="CS-A2"),
        LibraryBook(isbn="978-0078022159", title="Database System Concepts", author="Abraham Silberschatz", category="Databases", total_copies=5, available_copies=5, shelf_location="CS-B1"),
        LibraryBook(isbn="978-1492056812", title="Fluent Python", author="Luciano Ramalho", category="Programming", total_copies=4, available_copies=4, shelf_location="CS-A3"),
        LibraryBook(isbn="978-0132350884", title="Clean Code", author="Robert C. Martin", category="Software Engineering", total_copies=5, available_copies=5, shelf_location="CS-C1"),
    ]
    db.session.add_all(books)
    db.session.flush()

    # 1 Overdue issued book for student1 (Rs 50 fine)
    db.session.add(
        BookIssue(
            student_id=s1.id,
            book_id=books[0].id,
            status="Issued",
            issued_on=date.today() - timedelta(days=19),
            due_date=date.today() - timedelta(days=5),
            approved_by_id=lib_u.id,
            remarks="Approved by Mrs. Nandita Basu",
        )
    )
    # 1 Active issued book for student1 (on time)
    db.session.add(
        BookIssue(
            student_id=s1.id,
            book_id=books[1].id,
            status="Issued",
            issued_on=date.today() - timedelta(days=3),
            due_date=date.today() + timedelta(days=11),
            approved_by_id=lib_u.id,
            remarks="Approved by Mrs. Nandita Basu",
        )
    )
    # 1 Pending Issue Request from student2 for Librarian to approve!
    db.session.add(
        BookIssue(
            student_id=students[1].id,
            book_id=books[2].id,
            status="Issue Requested",
            remarks="Awaiting Librarian approval",
        )
    )

    notices = [
        Notice(
            title="End-Semester Examination Form Fill-up & Admit Card Schedule",
            category="Exam",
            pinned=True,
            body="All Semester 1 students are instructed to complete their online Exam Enrollment and pay the examination fee of ₹1,200 through the CampusHub portal. Admit Cards will be generated automatically upon payment confirmation.",
            author_id=admin_u.id,
        ),
        Notice(
            title="Semester 1 Tuition Fee Payment Window Open",
            category="Fees",
            pinned=True,
            body="The portal is now open for Semester 1 Academic & Tuition Fee payment via Razorpay (UPI, Cards, NetBanking). Download your official payment receipt immediately after transaction.",
            author_id=admin_u.id,
        ),
        Notice(
            title="Central Library Issue & Return Approval Policy",
            category="Library",
            pinned=False,
            body="Students can submit book issue or return requests online. Physical handover and Librarian approval are mandatory to complete issue/return. Overdue fine is ₹10/day.",
            author_id=lib_u.id,
        ),
    ]
    db.session.add_all(notices)

    db.session.commit()
    print("Database seeded successfully!")
    print("Admin     : admin@college.edu / admin123")
    print("Faculty   : faculty1@college.edu / password123")
    print("Librarian : librarian@college.edu / password123")
    print("Student   : student1@college.edu / password123")
