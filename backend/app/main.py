from fastapi import FastAPI
from app.api.v1 import employee, payroll, tax
from backend.app.database.database import engine, Base

# Initialize FastAPI app
app = FastAPI()

# Create all the database tables
Base.metadata.create_all(bind=engine)

# Include routes
app.include_router(employee.router, prefix="/employees", tags=["Employees"])
app.include_router(payroll.router, prefix="/payrolls", tags=["Payrolls"])
app.include_router(tax.router, prefix="/taxes", tags=["Taxes"])
