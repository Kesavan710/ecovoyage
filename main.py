from fastapi import FastAPI, HTTPException, Depends, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from passlib.context import CryptContext
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
import os, traceback, secrets, httpx
from authlib.integrations.starlette_client import OAuth
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv



# Database setup
DATABASE_URL = "mysql+pymysql://fastapi_user:simplepass123@localhost/carbon_tracker"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(debug=True)
app.add_middleware(SessionMiddleware, secret_key=secrets.token_urlsafe(32))
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# OAuth setup
oauth = OAuth()
oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID", "your-google-client-id"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET", "your-google-client-secret"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",  # ✅ Fixed URL
    client_kwargs={"scope": "openid email profile"},
)

# Static & templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password = Column(String(200), nullable=True)
    oauth_provider = Column(String(50), nullable=True)
    oauth_id = Column(String(100), nullable=True)
    transports = relationship("Transport", back_populates="user", cascade="all, delete-orphan")

class Transport(Base):
    __tablename__ = "transport"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    transport_type = Column(String(50), nullable=False)
    distance = Column(Integer, nullable=False)
    carbon_emission = Column(Float, nullable=False)
    user = relationship("User", back_populates="transports")

Base.metadata.create_all(bind=engine)

# Schemas
class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TransportData(BaseModel):
    user_id: int
    transport_type: str
    distance: int
    carbon_emission: float

# DB Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/debug")
def debug_templates_and_static():
    return {
        "templates": os.listdir("templates"),
        "static": os.listdir("static"),
    }

@app.get("/routes")
def list_routes():
    return [route.path for route in app.router.routes]

# HTML responses
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    try:
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        traceback_str = traceback.format_exc()
        print("TEMPLATE RENDER ERROR:\n", traceback_str)
        return PlainTextResponse(f"Template render error:\n\n{traceback_str}", status_code=500)

@app.get("/second", response_class=HTMLResponse)
def get_second(request: Request):
    return templates.TemplateResponse("second.html", {"request": request})

@app.get("/progress", response_class=HTMLResponse)
def get_progress(request: Request):
    return templates.TemplateResponse("progress.html", {"request": request})

@app.get("/reward", response_class=HTMLResponse)
def get_reward(request: Request):
    return templates.TemplateResponse("reward.html", {"request": request})





@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/tips", response_class=HTMLResponse)
def tips(request: Request):
    return templates.TemplateResponse("tips.html", {"request": request})


@app.get("/tipss", response_class=HTMLResponse)
def get_tipss(request: Request):
    return templates.TemplateResponse("tipss.html", {"request": request})


@app.get("/evbook", response_class=HTMLResponse)
def get_ev(request: Request):
    return templates.TemplateResponse("evbook.html", {"request": request})
# OAuth routes
@app.get("/auth/google")
async def google_auth(request: Request):
    redirect_uri = request.url_for("google_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)

@app.get("/auth/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get("userinfo")
        if not user_info:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers={"Authorization": f'Bearer {token["access_token"]}'},
                )
                user_info = resp.json()

        existing_user = (
            db.query(User)
            .filter((User.email == user_info["email"]) | (User.oauth_id == user_info["id"]))
            .first()
        )

        if existing_user:
            if not existing_user.oauth_provider:
                existing_user.oauth_provider = "google"
                existing_user.oauth_id = user_info["id"]
                db.commit()
            user_id = existing_user.id
        else:
            new_user = User(
                name=user_info["name"],
                email=user_info["email"],
                oauth_provider="google",
                oauth_id=user_info["id"],
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            user_id = new_user.id

        response = RedirectResponse(url="/second")
        response.set_cookie(key="oauth_user_id", value=str(user_id), httponly=True)
        return response

    except Exception as e:
        print(f"OAuth callback error: {e}")
        return RedirectResponse(url="/?error=oauth_failed")

@app.get("/auth/user")
def get_oauth_user(request: Request):
    user_id = request.cookies.get("oauth_user_id")
    return {"user_id": int(user_id)} if user_id else {"user_id": None}

# Auth endpoints
@app.post("/signup")
def signup(user: SignupRequest, db: Session = Depends(get_db)):
    if not user.name or not user.email or not user.password:
        raise HTTPException(400, "All fields are required")
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(400, "Email already registered")
    hashed = pwd_context.hash(user.password)
    new = User(name=user.name, email=user.email, password=hashed)
    db.add(new); db.commit(); db.refresh(new)
    return {"message": "User created", "user_id": new.id}

@app.post("/login")
def login(user: LoginRequest, db: Session = Depends(get_db)):
    if not user.email or not user.password:
        raise HTTPException(400, "Email and password required")
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not db_user.password or not pwd_context.verify(user.password, db_user.password):
        raise HTTPException(401, "Invalid credentials")
    return {"message": "Login successful", "user_id": db_user.id}

# Transport endpoints
@app.post("/transport")
def save_transport(data: TransportData, db: Session = Depends(get_db)):
    t = Transport(
        user_id=data.user_id,
        transport_type=data.transport_type,
        distance=data.distance,
        carbon_emission=data.carbon_emission,
    )
    db.add(t); db.commit()
    return {"message": "Transport data saved"}

@app.get("/transport/emissions/{user_id}")
def get_transport_emissions(user_id: int, db: Session = Depends(get_db)):
    res = (
        db.query(Transport.transport_type, func.sum(Transport.carbon_emission).label("total_emission"))
        .filter(Transport.user_id == user_id)
        .group_by(Transport.transport_type)
        .all()
    )
    if not res:
        return {"message": "No transport data", "total": 0, "breakdown": {}}
    return {
        "total": sum(r.total_emission for r in res),
        "breakdown": {r.transport_type: r.total_emission for r in res},
    }

@app.get("/signup", response_class=HTMLResponse)
def get_signup(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
def get_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})
