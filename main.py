from fastapi import FastAPI, Depends,  HTTPException, Header
from typing import Union, Optional
from fastapi.encoders import jsonable_encoder
import uvicorn
from sqlalchemy import create_engine,Integer, String,Column
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel, ValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from passlib.context import CryptContext
from jose import jwt, JWTError 
from datetime import datetime, timedelta

#Database connection URL
SQLALCHEY_DATABASE_URL = 'mysql+pymysql://root:@localhost:3306/fasttest'
engine = create_engine(SQLALCHEY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit = False, autoflush=False, bind=engine)

Base = declarative_base()

#model to create new table called users
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    username = Column(String(50))
    password = Column(String(255))
    status = Column(String(10))

Base.metadata.create_all(engine)

app = FastAPI()

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#user schema for reg
class UserModel(BaseModel):
    name: str
    username: str
    password: str
    status: str

class UserCreate(UserModel):
    pass 

#user schema to update user
class GetUser(BaseModel):
    id: int
    name: str
    username: str
    password: str
    status: str

class Config:
    orm_mode = True

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Security settings
SECRET_KEY = "3885cac067064bf3098f62854c211e68e78fcdc0abacf5935a39a509cec31964"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

#Token create
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

#Verify Token
def verify_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


#select all users
@app.get("/users/")
async def read_users(db:Session = Depends(get_db)):
    users = db.query(User).all()
   ## return [{"id": user.id, "name": user.name, "username": user.username, "password": user.password, "status": user.status} for user in users]
    return users

#Register new user    
@app.post('/new_user/')
async def create_user(newuser: UserCreate, db:Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == newuser.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="User already registered")
    
    try:
        if not newuser.name:
            raise HTTPException(status_code=422, detail="Name is required")
        if not newuser.username:
            raise HTTPException(status_code=422, detail="UserName is required")
        if not newuser.password:
            raise HTTPException(status_code=422, detail="Password is required")
        if not newuser.status:
            raise HTTPException(status_code=422, detail="status is required")
        #Encrypt password
        hashed_password = password_context.hash(newuser.password)    
        user = User(name=newuser.name, username=newuser.username, password=hashed_password, status=newuser.status)
        db.add(user)
        db.commit()
        db.refresh(user)
        return {"message": "User created successfully", "user": user}
    except ValidationError as e:
        #raise HTTPException(status_code=400, detail="Invalid user data")
        print (e.errors())
        return {"detail": e.errors()}

#Get user by ID
@app.get("/profile/{userid}")
async def read_users(userid: int, db:Session = Depends(get_db)):   
        users = db.query(User).filter(User.id == userid).first()       
        if users is None:
            raise HTTPException(status_code=404, detail="User not found")
        return users

#Delete user with userid
@app.delete("/del_users/{user_id}")    
async def delete_user(user_id: int, db:Session = Depends(get_db)):
    users = db.query(User).filter(User.id == user_id).first()
    if users is None:
         raise HTTPException(status_code=404, detail="User not found")
    db.delete(users)
    db.commit()
    return {"message": "User deleted"}

#Update user    
@app.put('/updateuser/{userid}')
async def update_user(userid: int, userupdate: UserCreate, db:Session = Depends(get_db)):
    try:
        users = db.query(User).filter(User.id == userid).first()
        if users is None:
            raise HTTPException(status_code=404, detail="User not found")
        users.name = userupdate.name
        users.username = userupdate.username
        users.password = userupdate.password
        users.status = userupdate.status
        db.commit()
        db.refresh(users)
        return {"message": "User updated successfully", "user": users}
    except ValidationError as e:
        return {"detail": e.errors()}


#Authenticated login
@app.post("/login")
def login(user: OAuth2PasswordRequestForm = Depends(), db=Depends(get_db)):

    db_user = db.query(User).filter(User.username == user.username ).first()   

    if not db_user or not password_context.verify(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

#Login
@app.post("/login2")
def login2(username: str, password: str, db: Session =  Depends(get_db)):
    
        users = db.query(User).filter(User.username == username).first()
          
        if users.username == username and users.password == password:         
            return {'success': 'Login Successful'}      
        else:
            return {'failure':  'wrong password or email address'}
        
#protected user
@app.get("/protected")
def protected_route(authorization: Optional[str] = Header(None), db: Session =  Depends(get_db)):
        
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header is missing")

    try:
        token_prefix, token = authorization.split(" ")
        if token_prefix.lower() != "bearer":
             raise HTTPException(status_code=401, detail="Invalid authorization type")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authorization header format")

    try:
       users = db.query(User).filter(User.username == username).first()       
       if users is None:
            raise HTTPException(status_code=404, detail="User not found")
       return users
        
    except ValidationError as e:
        return {"detail": e.errors()} 
    
              
#Index page
@app.get("/")
async def index():
    return {"message": "Hello World"}
