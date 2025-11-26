from __future__ import annotations

import os
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Generator, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, constr
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SqlEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    func,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship, sessionmaker
from passlib.context import CryptContext

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SQLITE_URL = f"sqlite:///{BASE_DIR / 'smartorganic.db'}"
DATABASE_URL = os.getenv(
    "DATABASE_URL", "mysql+pymysql://user:Kesavan%402005@localhost:3306/smartorganic"
)

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL, connect_args={"check_same_thread": False}, future=True
    )
else:
    engine = create_engine(
        DATABASE_URL,
        future=True,
        pool_pre_ping=True,
    )
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class UserRole(str, Enum):
    customer = "customer"
    farmer = "farmer"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(SqlEnum(UserRole), nullable=False, default=UserRole.customer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    farmer_profile = relationship("FarmerProfile", back_populates="user", uselist=False)
    orders = relationship("Order", back_populates="customer")


class FarmerProfile(Base):
    __tablename__ = "farmer_profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    farm_name = Column(String(255), nullable=False)
    farm_location = Column(String(255), nullable=False)
    primary_products = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="farmer_profile")
    products = relationship("Product", back_populates="farmer")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    price_inr = Column(Integer, nullable=False)
    unit = Column(String(50), default="kg")
    description = Column(Text, nullable=False)
    image_url = Column(String(500), nullable=False)
    organic_certified = Column(Boolean, default=True)
    iot_verified = Column(Boolean, default=True)
    farmer_id = Column(Integer, ForeignKey("farmer_profiles.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    farmer = relationship("FarmerProfile", back_populates="products")
    sensor_readings = relationship(
        "SensorReading",
        back_populates="product",
        order_by="desc(SensorReading.recorded_at)",
        cascade="all, delete-orphan",
    )
    order_items = relationship("OrderItem", back_populates="product")


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"))
    soil_moisture = Column(Float, nullable=False)
    temperature = Column(Float, nullable=False)
    humidity = Column(Float, nullable=False)
    status = Column(String(255), default="Optimal")
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())

    product = relationship("Product", back_populates="sensor_readings")


class ContactMessage(Base):
    __tablename__ = "contact_messages"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved = Column(Boolean, default=False)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    total_price_inr = Column(Integer, nullable=False)
    status = Column(String(50), default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    customer = relationship("User", back_populates="orders")
    items = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"))
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"))
    quantity = Column(Integer, nullable=False)
    unit_price_inr = Column(Integer, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")


def create_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed: str) -> bool:
    return pwd_context.verify(plain_password, hashed)


async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    if not token or not token.startswith("mock-token-"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(token.replace("mock-token-", ""))
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return user
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


# --------------------- Pydantic Schemas ---------------------
class FarmerProfileIn(BaseModel):
    farm_name: str
    farm_location: str
    primary_products: str


class FarmerProfileOut(FarmerProfileIn):
    id: int

    class Config:
        orm_mode = True


class UserOut(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: EmailStr
    role: UserRole
    created_at: datetime
    farmer_profile: Optional[FarmerProfileOut] = None

    class Config:
        orm_mode = True


class SignupRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: constr(min_length=6)
    role: UserRole = UserRole.customer
    farmer_profile: Optional[FarmerProfileIn] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    role: Optional[UserRole] = None


class AuthResponse(BaseModel):
    message: str
    user: UserOut
    token: str


class SensorReadingOut(BaseModel):
    soil_moisture: float
    temperature: float
    humidity: float
    status: str
    recorded_at: datetime

    class Config:
        orm_mode = True


class SensorReadingCreate(BaseModel):
    soil_moisture: float
    temperature: float
    humidity: float
    status: str = "Optimal"


class ProductBase(BaseModel):
    name: str
    category: str
    price_inr: int
    unit: str = "kg"
    description: str
    image_url: str
    organic_certified: bool = True
    iot_verified: bool = True
    farmer_id: Optional[int] = None

    class Config:
        orm_mode = True


class ProductOut(ProductBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True


class ProductDetail(ProductOut):
    farmer: Optional[FarmerProfileOut] = None
    sensor_readings: List[SensorReadingOut] = Field(default_factory=list)


class ProductFilter(BaseModel):
    category: Optional[str] = None
    price_band: Optional[str] = Field(
        default=None, description="Expected values: low, medium, high"
    )
    certification: Optional[str] = Field(
        default=None, description="organic or iot maps to boolean flags"
    )


class ContactMessageIn(BaseModel):
    name: str
    email: EmailStr
    subject: str
    message: str


class ContactMessageOut(ContactMessageIn):
    id: int
    created_at: datetime
    resolved: bool

    class Config:
        orm_mode = True


class OrderItemIn(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)


class OrderCreate(BaseModel):
    customer_id: int
    items: List[OrderItemIn]


class OrderItemOut(BaseModel):
    product_id: int
    quantity: int
    unit_price_inr: int

    class Config:
        orm_mode = True


class OrderOut(BaseModel):
    id: int
    customer_id: Optional[int]
    total_price_inr: int
    status: str
    created_at: datetime
    items: List[OrderItemOut]

    class Config:
        orm_mode = True


# --------------------- FastAPI Application ---------------------
app = FastAPI(
    title="Smart Organic Connect API",
    description="Backend service for IoT + Blockchain driven marketplace.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


from fastapi.staticfiles import StaticFiles

# Mount static files directory
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

@app.middleware("http")
async def serve_static_assets(request: Request, call_next):
    path = request.url.path
    
    # Skip API and docs paths
    if path.startswith("/api") or path.startswith("/docs") or path.startswith("/openapi") or path.startswith("/static"):
        return await call_next(request)
    
    # Try to find the file in the static directory first
    static_path = BASE_DIR / "static" / path.lstrip("/")
    if static_path.is_file():
        return FileResponse(static_path)
    
    # Then try the root directory
    root_path = BASE_DIR / path.lstrip("/")
    if root_path.is_file():
        return FileResponse(root_path)
    
    # If not found, serve index.html for SPA routing
    index_path = BASE_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    
    # If index.html doesn't exist, continue with the request
    return await call_next(request)


def seed_products(db: Session) -> None:
    if db.query(Product).count() > 0:
        return

    sample_farmer = FarmerProfile(
        user=User(
            first_name="Rajesh",
            last_name="Kumar",
            email="farmer@smartorganic.com",
            password_hash=hash_password("password123"),
            role=UserRole.farmer,
        ),
        farm_name="Rajesh Organic Farms",
        farm_location="Bangalore, India",
        primary_products="Vegetables, Fruits",
    )
    db.add(sample_farmer)
    db.flush()

    sample_products = [
        {
            "name": "Organic Tomatoes",
            "category": "vegetables",
            "price_inr": 120,
            "unit": "kg",
            "description": "Fresh organic tomatoes grown with IoT monitoring.",
            "image_url": "https://images.unsplash.com/photo-1592924357228-91a4daadcfea?auto=format&fit=crop&w=500&q=80",
        },
        {
            "name": "Fresh Spinach",
            "category": "vegetables",
            "price_inr": 80,
            "unit": "bunch",
            "description": "Nutrient-rich organic spinach harvested daily.",
            "image_url": "https://images.unsplash.com/photo-1576045057995-568f588f82fb?auto=format&fit=crop&w=500&q=80",
        },
        {
            "name": "Organic Rice",
            "category": "grains",
            "price_inr": 65,
            "unit": "kg",
            "description": "Traditionally grown organic rice variety.",
            "image_url": "https://images.unsplash.com/photo-1586201375761-83865001e31c?auto=format&fit=crop&w=500&q=80",
        },
        {
            "name": "Pure Honey",
            "category": "dairy",
            "price_inr": 350,
            "unit": "jar",
            "description": "Unprocessed forest honey verified via IoT trackers.",
            "image_url": "https://images.unsplash.com/photo-1558642452-9d2a7deb7f62?auto=format&fit=crop&w=500&q=80",
        },
        {
            "name": "Organic Apples",
            "category": "fruits",
            "price_inr": 200,
            "unit": "kg",
            "description": "Crisp apples from Himalayan organic orchards.",
            "image_url": "https://images.unsplash.com/photo-1568702846914-96b305d2aaeb?auto=format&fit=crop&w=500&q=80",
        },
        {
            "name": "Fresh Carrots",
            "category": "vegetables",
            "price_inr": 60,
            "unit": "kg",
            "description": "Sweet crunchy carrots tracked end-to-end.",
            "image_url": "https://images.unsplash.com/photo-1598170845058-32b9d6a5da37?auto=format&fit=crop&w=500&q=80",
        },
        {
            "name": "Organic Bananas",
            "category": "fruits",
            "price_inr": 90,
            "unit": "dozen",
            "description": "Naturally ripened bananas with zero chemicals.",
            "image_url": "https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e?auto=format&fit=crop&w=500&q=80",
        },
    ]

    for product_data in sample_products:
        product = Product(
            farmer_id=sample_farmer.id,
            **product_data,
        )
        db.add(product)
        db.flush()
        db.add(
            SensorReading(
                product_id=product.id,
                soil_moisture=67.5,
                temperature=26.3,
                humidity=65.0,
                status="Optimal organic conditions verified",
            )
        )

    db.commit()


@app.on_event("startup")
def on_startup() -> None:
    create_db()
    with SessionLocal() as db:
        seed_products(db)


# --------------------- Routes ---------------------
@app.post("/api/auth/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, db: Session = Depends(get_db)) -> UserOut:
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == payload.email.lower()).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered."
            )

        # Create new user
        user = User(
            first_name=payload.first_name.strip(),
            last_name=payload.last_name.strip(),
            email=payload.email.lower(),
            password_hash=hash_password(payload.password),
            role=payload.role,
        )
        db.add(user)
        db.flush()  # Flush to get the user ID

        # Create farmer profile if role is farmer
        if payload.role == UserRole.farmer:
            if not payload.farmer_profile:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Farmer profile details are required for farmer sign up.",
                )
            profile = FarmerProfile(user_id=user.id, **payload.farmer_profile.dict())
            db.add(profile)

        db.commit()
        db.refresh(user)
        return user
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating user: {str(e)}"
        )


@app.post("/api/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    try:
        # Find user by email (case-insensitive search)
        user = db.query(User).filter(
            func.lower(User.email) == payload.email.lower()
        ).first()
        
        # Verify user exists and password is correct
        if not user or not verify_password(payload.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password."
            )

        # If role is specified, verify it matches
        if payload.role and user.role != payload.role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Please login as a {payload.role} to continue."
            )

        # Generate token (in production, use proper JWT)
        token = f"mock-token-{user.id}"
        
        # Convert user to Pydantic model for proper serialization
        user_data = UserOut.from_orm(user)
        
        return {
            "message": "Login successful",
            "user": user_data.dict(),
            "token": token
        }
        
    except HTTPException as he:
        # Re-raise HTTP exceptions as is
        raise
    except Exception as e:
        # Log the error for debugging
        logger.error(f"Login error for {payload.email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login. Please try again."
        )


@app.get("/api/products", response_model=List[ProductOut])
def list_products(
    category: Optional[str] = Query(
        default=None, description="Category filter such as fruits, vegetables, grains."
    ),
    price: Optional[str] = Query(
        default=None, description="low (<100), medium (100-300), high (>300)"
    ),
    certification: Optional[str] = Query(
        default=None, description="organic or iot for badges"
    ),
    db: Session = Depends(get_db),
) -> List[ProductOut]:
    query = db.query(Product)

    if category and category != "all":
        query = query.filter(Product.category == category)

    if price and price != "all":
        if price == "low":
            query = query.filter(Product.price_inr < 100)
        elif price == "medium":
            query = query.filter(Product.price_inr.between(100, 300))
        elif price == "high":
            query = query.filter(Product.price_inr > 300)

    if certification and certification != "all":
        if certification == "organic":
            query = query.filter(Product.organic_certified.is_(True))
        elif certification == "iot":
            query = query.filter(Product.iot_verified.is_(True))

    return query.order_by(Product.created_at.desc()).all()


@app.get("/api/products/{product_id}", response_model=ProductDetail)
def get_product(product_id: int, db: Session = Depends(get_db)) -> ProductDetail:
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
    return product


@app.post("/api/products", response_model=ProductDetail, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductBase, db: Session = Depends(get_db)) -> ProductDetail:
    if payload.farmer_id:
        farmer = db.query(FarmerProfile).filter_by(id=payload.farmer_id).first()
        if not farmer:
            raise HTTPException(status_code=404, detail="Farmer profile not found.")

    product = Product(**payload.dict())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@app.post(
    "/api/products/{product_id}/sensor",
    response_model=SensorReadingOut,
    status_code=status.HTTP_201_CREATED,
)
def add_sensor_reading(
    product_id: int, payload: SensorReadingCreate, db: Session = Depends(get_db)
) -> SensorReadingOut:
    product = db.query(Product).filter_by(id=product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")

    sensor_reading = SensorReading(product_id=product_id, **payload.dict())
    db.add(sensor_reading)
    db.commit()
    db.refresh(sensor_reading)
    return sensor_reading


@app.post("/api/contact", response_model=ContactMessageOut, status_code=status.HTTP_201_CREATED)
def submit_contact_form(
    payload: ContactMessageIn, db: Session = Depends(get_db)
) -> ContactMessageOut:
    message = ContactMessage(**payload.dict())
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


@app.post("/api/orders", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(payload: OrderCreate, db: Session = Depends(get_db)) -> OrderOut:
    if not payload.items:
        raise HTTPException(status_code=400, detail="Order requires at least one item.")

    customer = db.query(User).filter_by(id=payload.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found.")

    total_price = 0
    order_items: List[OrderItem] = []

    for item in payload.items:
        product = db.query(Product).filter_by(id=item.product_id).first()
        if not product:
            raise HTTPException(
                status_code=404, detail=f"Product {item.product_id} not found."
            )
        line_price = product.price_inr * item.quantity
        total_price += line_price
        order_items.append(
            OrderItem(
                product_id=product.id,
                quantity=item.quantity,
                unit_price_inr=product.price_inr,
            )
        )

    order = Order(customer_id=customer.id, total_price_inr=total_price, items=order_items)
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


@app.get("/api/orders/{customer_id}", response_model=List[OrderOut])
def list_orders(customer_id: int, db: Session = Depends(get_db)) -> List[OrderOut]:
    return (
        db.query(Order)
        .filter(Order.customer_id == customer_id)
        .order_by(Order.created_at.desc())
        .all()
    )


@app.get("/health")
def healthcheck() -> dict:
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.get("/", include_in_schema=False)
def serve_index() -> FileResponse:
    index_path = BASE_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Front-end index.html file is missing.",
        )
    return FileResponse(index_path)

