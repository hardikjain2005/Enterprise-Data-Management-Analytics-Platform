from datetime import date

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class Department(Base):
    __tablename__ = "departments"

    department_id: Mapped[int] = mapped_column(primary_key=True)
    department_name: Mapped[str] = mapped_column(String(60), unique=True)
    location: Mapped[str] = mapped_column(String(60))


class Employee(Base):
    __tablename__ = "employees"

    employee_id: Mapped[int] = mapped_column(primary_key=True)
    employee_code: Mapped[str] = mapped_column(String(20), unique=True)
    first_name: Mapped[str] = mapped_column(String(50))
    last_name: Mapped[str] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(120))
    job_title: Mapped[str] = mapped_column(String(80))
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.department_id"))
    manager_id: Mapped[int | None] = mapped_column(ForeignKey("employees.employee_id"))
    hire_date: Mapped[date]
    salary: Mapped[float] = mapped_column(Numeric(10, 2))
    is_active: Mapped[bool]

    department: Mapped[Department] = relationship()
