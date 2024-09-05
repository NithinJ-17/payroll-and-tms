import uuid  # Import UUID for generating unique employee IDs
from datetime import datetime
import logging
from fastapi import APIRouter, HTTPException, Depends, Header
from jwt import PyJWTError
import jwt
from app.models.employee_signup import EmployeeSignup  # Assuming you have a similar employee model
from app.database.connection import db
from app.utils import hash_password, verify_password
from app.state import TOKENS
from app.models.employee_login import EmployeeLogin  # Assuming you have an employee login model
from app.auth import create_access_token
from app.config import JWT_ALGORITHM, JWT_EXPIRATION_DELTA, JWT_SECRET
from app.models.session import UserSession

router = APIRouter()

@router.post("/employee/signup")
async def employee_signup(employee: EmployeeSignup):
    try:
        # Check for duplicate email
        existing_email = await db.employees.find_one({"email": employee.email})
        if existing_email:
            logging.warning(f"Signup attempt with existing email: {employee.email}")
            raise HTTPException(status_code=400, detail="Email already in use")
        
        # Generate a unique employee ID
        employee_id = str(uuid.uuid4())
        
        hashed_password = hash_password(employee.password)
        new_employee = {
            "employee_id": employee_id,  # Assign the generated employee ID
            "name": employee.name,
            "email": employee.email,
            "password": hashed_password
        }
        
        # Insert the new employee into the employees collection
        await db.employees.insert_one(new_employee)
        logging.info(f"New employee {employee_id} created successfully with email {employee.email}.")
        
        # Create a record for the new employee (can be a role, department, etc.)
        employee_record = {
            "employee_id": employee_id,
            "role": employee.role,  # Assuming you have a role field in EmployeeSignup model
            "start_date": datetime.utcnow()
        }
        await db.employee_records.insert_one(employee_record)
        logging.info(f"Record created for employee {employee_id}.")

        return {"message": "Employee created successfully"}
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logging.error(f"Error during signup for employee with email {employee.email}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.post("/employee/login")
async def employee_login(login_data: EmployeeLogin):
    try:
        # Retrieve employee by email
        employee = await db.employees.find_one({"email": login_data.email})
        if not employee or not verify_password(login_data.password, employee["password"]):
            logging.warning(f"Failed login attempt for email: {login_data.email}")
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Generate JWT token
        token = create_access_token(user_id=employee["employee_id"])
        name = employee['name']

        expiration_time = datetime.utcnow() + JWT_EXPIRATION_DELTA
        session = UserSession(token=token, created_at=datetime.utcnow(), expires_at=expiration_time)
        await db.sessions.insert_one({"employee_id": employee["employee_id"], "session": session.dict()})

        logging.info(f"Employee {employee['employee_id']} logged in successfully.")
        return {"employee": name, "token": token}
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logging.error(f"Error during login for email {login_data.email}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.post("/employee/logout")
async def employee_logout(x_token: str = Header(...)):
    try:
        payload = jwt.decode(x_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        employee_id = payload.get("sub")
        if employee_id is None:
            logging.warning("Logout attempt with invalid credentials.")
            raise HTTPException(status_code=401, detail="Invalid credentials")

        delete_result = await db.sessions.delete_one({"employee_id": employee_id, "session.token": x_token})
        if delete_result.deleted_count == 0:
            logging.warning(f"Logout attempt with invalid token for employee_id: {employee_id}")
            raise HTTPException(status_code=401, detail="Invalid token")

        logging.info(f"Employee {employee_id} logged out successfully.")
        return {"message": "Logged out successfully"}
    
    except PyJWTError as e:
        logging.error(f"JWT verification failed during logout: {e}")
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    except Exception as e:
        logging.error(f"Error during logout: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/employee_id")
async def get_employee_id(x_token: str = Header(...)):
    try:
        payload = jwt.decode(x_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        employee_id = payload.get("sub")
        if employee_id is None:
            logging.warning("Attempt to retrieve employee_id with invalid credentials.")
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        session = await db.sessions.find_one({"employee_id": employee_id, "session.token": x_token})
        if not session:
            logging.warning(f"Invalid or expired token for employee {employee_id}")
            raise HTTPException(status_code=401, detail="Invalid token or session expired")
        
        logging.info(f"Employee ID {employee_id} retrieved successfully.")
        return {"employee_id": employee_id}
    
    except PyJWTError as e:
        logging.error(f"JWT verification failed: {e}")
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    except Exception as e:
        logging.error(f"Error retrieving employee_id: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/employee_id_by_email")
async def get_employee_id_by_email(email: str):
    try:
        employee = await db.employees.find_one({"email": email})
        if not employee:
            logging.warning(f"Employee with email {email} not found.")
            raise HTTPException(status_code=404, detail="Employee not found")

        logging.info(f"Employee ID {employee['employee_id']} retrieved successfully for email {email}.")
        return {"employee_id": employee["employee_id"]}
    
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logging.error(f"Error retrieving employee ID for email {email}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
