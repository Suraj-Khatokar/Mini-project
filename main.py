from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, text, inspect

from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum
import os
from pathlib import Path
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import jwt
import logging
from typing import Optional, List

# Initialize Flask app
app = Flask(__name__)

# MySQL configuration with dummy credentials
MYSQL_CONFIG = {
    'user': 'root',
    'password': 'Kesavan%402005',
    'host': 'localhost',
    'port': '3306',
    'database': 'smartorganic',
}

# Default to MySQL, fallback to SQLite if MySQL is not available
SQLITE_URI = f"sqlite:///{Path(__file__).parent / 'smartorganic.db'}"
MYSQL_URI = f"mysql+pymysql://{MYSQL_CONFIG['user']}:{MYSQL_CONFIG['password']}@{MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{MYSQL_CONFIG['database']}"

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', MYSQL_URI)
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 280,
    'pool_pre_ping': True,
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Change in production

# Initialize database
db = SQLAlchemy(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserRole(str, Enum):
    customer = "customer"
    farmer = "farmer"

# Database Models
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True, index=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.customer)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

    farmer_profile = relationship("FarmerProfile", back_populates="user", uselist=False)
    orders = relationship("Order", back_populates="customer")
    addresses = relationship("Address", back_populates="customer", cascade="all, delete-orphan")

class FarmerProfile(db.Model):
    __tablename__ = "farmer_profiles"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    farm_name = db.Column(db.String(255), nullable=False)
    farm_location = db.Column(db.String(255), nullable=False)
    primary_products = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="farmer_profile")
    products = relationship("Product", back_populates="farmer")
    batches = relationship("Batch", back_populates="farmer")

class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    price_inr = db.Column(db.Integer, nullable=False)
    unit = db.Column(db.String(50), default="kg")
    description = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500), nullable=False)
    organic_certified = db.Column(db.Boolean, default=True)
    iot_verified = db.Column(db.Boolean, default=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey("farmer_profiles.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

    farmer = relationship("FarmerProfile", back_populates="products")
    sensor_readings = relationship("SensorReading", back_populates="product")
    order_items = relationship("OrderItem", back_populates="product")

class SensorReading(db.Model):
    __tablename__ = "sensor_readings"
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"))
    soil_moisture = db.Column(db.Float, nullable=False)
    temperature = db.Column(db.Float, nullable=False)
    humidity = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(255), default="Optimal")
    recorded_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

    product = relationship("Product", back_populates="sensor_readings")

class ContactMessage(db.Model):
    __tablename__ = "contact_messages"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    resolved = db.Column(db.Boolean, default=False)

class Order(db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    total_price_inr = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(50), default="pending")
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

    customer = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")

class OrderItem(db.Model):
    __tablename__ = "order_items"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"))
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="SET NULL"))
    quantity = db.Column(db.Integer, nullable=False)
    unit_price_inr = db.Column(db.Integer, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")

class Batch(db.Model):
    __tablename__ = "batches"
    id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey("farmer_profiles.id", ondelete="CASCADE"))
    batch_code = db.Column(db.String(50), nullable=False)
    product_name = db.Column(db.String(255), nullable=False)
    harvest_date = db.Column(db.Date, nullable=True)
    quantity = db.Column(db.Integer, nullable=False)
    unit = db.Column(db.String(50), default="kg")
    status = db.Column(db.String(50), default="harvested")
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

    farmer = relationship("FarmerProfile", back_populates="batches")

class Address(db.Model):
    __tablename__ = "addresses"
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = db.Column(db.String(20), default="home")  # home, work, other
    street_address = db.Column(db.Text, nullable=False)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100), nullable=False)
    postal_code = db.Column(db.String(20), nullable=False)
    country = db.Column(db.String(100), default="India")
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    customer = relationship("User", back_populates="addresses")

# Helper functions
def hash_password(password: str) -> str:
    return generate_password_hash(password)

def verify_password(plain_password: str, hashed: str) -> bool:
    return check_password_hash(hashed, plain_password)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1] if "Bearer" in request.headers['Authorization'] else None
        
        if not token or not token.startswith("mock-token-"):
            return jsonify({'message': 'Invalid authentication credentials'}), 401
        
        try:
            user_id = int(token.replace("mock-token-", ""))
            current_user = User.query.get(user_id)
            if not current_user:
                return jsonify({'message': 'User not found'}), 404
        except Exception:
            return jsonify({'message': 'Invalid authentication credentials'}), 401
        
        return f(current_user, *args, **kwargs)
    return decorated

# Serialization helpers
def user_to_dict(user):
    return {
        'id': user.id,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
        'phone': user.phone,
        'role': user.role.value if user.role else 'customer',
        'created_at': user.created_at.isoformat() if user.created_at else None,
        'farmer_profile': farmer_profile_to_dict(user.farmer_profile) if user.farmer_profile else None,
        'addresses': [address_to_dict(addr) for addr in user.addresses] if user.addresses else []
    }

def address_to_dict(address):
    return {
        'id': address.id,
        'type': address.type,
        'street_address': address.street_address,
        'city': address.city,
        'state': address.state,
        'postal_code': address.postal_code,
        'country': address.country,
        'is_default': address.is_default,
        'created_at': address.created_at.isoformat() if address.created_at else None,
        'updated_at': address.updated_at.isoformat() if address.updated_at else None
    }

def farmer_profile_to_dict(profile):
    if not profile:
        return None
    return {
        'id': profile.id,
        'farm_name': profile.farm_name,
        'farm_location': profile.farm_location,
        'primary_products': profile.primary_products,
        'created_at': profile.created_at.isoformat() if profile.created_at else None
    }

def product_to_dict(product):
    return {
        'id': product.id,
        'name': product.name,
        'category': product.category,
        'price_inr': product.price_inr,
        'unit': product.unit,
        'description': product.description,
        'image_url': product.image_url,
        'organic_certified': product.organic_certified,
        'iot_verified': product.iot_verified,
        'farmer_id': product.farmer_id,
        'created_at': product.created_at.isoformat() if product.created_at else None,
        'farmer': farmer_profile_to_dict(product.farmer) if product.farmer else None,
        'sensor_readings': [sensor_reading_to_dict(sr) for sr in product.sensor_readings]
    }

def sensor_reading_to_dict(sensor_reading):
    return {
        'soil_moisture': sensor_reading.soil_moisture,
        'temperature': sensor_reading.temperature,
        'humidity': sensor_reading.humidity,
        'status': sensor_reading.status,
        'recorded_at': sensor_reading.recorded_at.isoformat() if sensor_reading.recorded_at else None
    }

def contact_message_to_dict(message):
    return {
        'id': message.id,
        'name': message.name,
        'email': message.email,
        'subject': message.subject,
        'message': message.message,
        'created_at': message.created_at.isoformat() if message.created_at else None,
        'resolved': message.resolved
    }

def order_to_dict(order):
    return {
        'id': order.id,
        'customer_id': order.customer_id,
        'total_price_inr': order.total_price_inr,
        'status': order.status,
        'created_at': order.created_at.isoformat() if order.created_at else None,
        'items': [order_item_to_dict(item) for item in order.items]
    }

def order_item_to_dict(item):
    return {
        'product_id': item.product_id,
        'quantity': item.quantity,
        'unit_price_inr': item.unit_price_inr
    }

def batch_to_dict(batch):
    return {
        'id': batch.id,
        'farmer_id': batch.farmer_id,
        'batch_code': batch.batch_code,
        'product_name': batch.product_name,
        'harvest_date': batch.harvest_date.isoformat() if batch.harvest_date else None,
        'quantity': batch.quantity,
        'unit': batch.unit,
        'status': batch.status,
        'created_at': batch.created_at.isoformat() if batch.created_at else None,
    }

# Seed data
def seed_products():
    if Product.query.count() > 0:
        return

    # Create sample farmer
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
    db.session.add(sample_farmer)
    db.session.flush()
    
    # Create sample customer
    sample_customer = User(
        first_name="John",
        last_name="Doe",
        email="customer@smartorganic.com",
        password_hash=hash_password("password123"),
        role=UserRole.customer,
    )
    db.session.add(sample_customer)
    db.session.flush()

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
        product = Product(farmer_id=sample_farmer.id, **product_data)
        db.session.add(product)
        db.session.flush()
        db.session.add(
            SensorReading(
                product_id=product.id,
                soil_moisture=67.5,
                temperature=26.3,
                humidity=65.0,
                status="Optimal organic conditions verified",
            )
        )

    db.session.commit()

# Initialize database and perform simple migrations
with app.app_context():
    db.create_all()
    seed_products()

    # Simple migration: ensure 'phone' column exists on users table
    try:
        engine = db.engine
        inspector = inspect(engine)
        user_columns = [col['name'] for col in inspector.get_columns('users')]

        if 'phone' not in user_columns:
            # Add nullable phone column for existing databases created before this field was added
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN phone VARCHAR(20) NULL"))
                conn.commit()
            logger.info("Added missing 'phone' column to users table")
    except Exception as e:
        # Log but don't crash app if migration check fails
        logger.error(f"Error ensuring users.phone column exists: {e}")

# CORS handling
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# Routes
@app.route('/api/auth/signup', methods=['POST'])
def signup():
    try:
        data = request.get_json()
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=data.get('email').lower()).first()
        if existing_user:
            return jsonify({'detail': 'Email already registered.'}), 400

        # Create new user
        user = User(
            first_name=data.get('first_name', '').strip(),
            last_name=data.get('last_name', '').strip(),
            email=data.get('email', '').lower(),
            password_hash=hash_password(data.get('password', '')),
            role=UserRole(data.get('role', 'customer'))
        )
        db.session.add(user)
        db.session.flush()

        # Create farmer profile if role is farmer
        if user.role == UserRole.farmer:
            farmer_profile_data = data.get('farmer_profile')
            if not farmer_profile_data:
                return jsonify({'detail': 'Farmer profile details are required for farmer sign up.'}), 400
            
            profile = FarmerProfile(
                user_id=user.id,
                farm_name=farmer_profile_data.get('farm_name', ''),
                farm_location=farmer_profile_data.get('farm_location', ''),
                primary_products=farmer_profile_data.get('primary_products', '')
            )
            db.session.add(profile)

        db.session.commit()
        return jsonify(user_to_dict(user)), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'detail': f'Error creating user: {str(e)}'}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email', '').lower()
        password = data.get('password', '')
        role = data.get('role')
        
        # Find user by email
        user = User.query.filter(func.lower(User.email) == email).first()
        
        # Verify user exists and password is correct
        if not user or not verify_password(password, user.password_hash):
            return jsonify({'detail': 'Invalid email or password.'}), 401

        # If role is specified, verify it matches
        if role and user.role.value != role.lower():
            return jsonify({
                'detail': f'Please login as a {role} to continue.',
                'user_role': user.role.value  # Include actual role for debugging
            }), 403

        # Generate token
        token = f"mock-token-{user.id}"
        
        user_data = user_to_dict(user)
        print(f"Login successful for {user.email} with role {user_data['role']}")  # Debug log
        
        return jsonify({
            'message': 'Login successful',
            'user': user_data,
            'token': token
        })
        
    except Exception as e:
        # Log full error server-side and return the actual message for debugging
        try:
            logger.error(f"Login error for {data.get('email') if data else 'unknown'}: {str(e)}")
        except Exception:
            logger.error(f"Login error (logging failed): {str(e)}")

        return jsonify({'detail': str(e)}), 500

@app.route('/api/products', methods=['GET'])
def list_products():
    try:
        category = request.args.get('category')
        price = request.args.get('price')
        certification = request.args.get('certification')
        
        query = Product.query

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

        products = query.order_by(Product.created_at.desc()).all()
        return jsonify([product_to_dict(product) for product in products])
    
    except Exception as e:
        return jsonify({'detail': str(e)}), 500

@app.route('/api/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    try:
        product = Product.query.get(product_id)
        if not product:
            return jsonify({'detail': 'Product not found'}), 404
        return jsonify(product_to_dict(product))
    except Exception as e:
        return jsonify({'detail': str(e)}), 500

@app.route('/api/contact', methods=['POST'])
def submit_contact_form():
    try:
        data = request.get_json()
        message = ContactMessage(
            name=data.get('name', ''),
            email=data.get('email', ''),
            subject=data.get('subject', ''),
            message=data.get('message', '')
        )
        db.session.add(message)
        db.session.commit()
        return jsonify(contact_message_to_dict(message)), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'detail': str(e)}), 500

@app.route('/api/orders', methods=['POST'])
def create_order():
    try:
        data = request.get_json()
        items = data.get('items', [])
        customer_id = data.get('customer_id')
        
        if not items:
            return jsonify({'detail': 'Order requires at least one item.'}), 400

        customer = User.query.get(customer_id)
        if not customer:
            return jsonify({'detail': 'Customer not found.'}), 404

        total_price = 0
        order_items = []

        for item in items:
            product = Product.query.get(item.get('product_id'))
            if not product:
                return jsonify({'detail': f"Product {item.get('product_id')} not found."}), 404
            
            quantity = item.get('quantity', 1)
            line_price = product.price_inr * quantity
            total_price += line_price
            order_items.append(OrderItem(
                product_id=product.id,
                quantity=quantity,
                unit_price_inr=product.price_inr
            ))

        order = Order(customer_id=customer.id, total_price_inr=total_price, items=order_items)
        db.session.add(order)
        db.session.commit()
        return jsonify(order_to_dict(order)), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'detail': str(e)}), 500

@app.route('/api/orders/<int:customer_id>', methods=['GET'])
def list_orders(customer_id):
    try:
        orders = Order.query.filter_by(customer_id=customer_id).order_by(Order.created_at.desc()).all()
        return jsonify([order_to_dict(order) for order in orders])
    except Exception as e:
        return jsonify({'detail': str(e)}), 500

@app.route('/api/customer/stats/<int:customer_id>', methods=['GET'])
def get_customer_stats(customer_id):
    try:
        # Get customer orders
        orders = Order.query.filter_by(customer_id=customer_id).all()
        
        # Calculate statistics
        total_orders = len(orders)
        total_spent = sum(order.total_price_inr for order in orders)
        
        # Get order status breakdown
        status_counts = {}
        for order in orders:
            status_counts[order.status] = status_counts.get(order.status, 0) + 1
        
        return jsonify({
            'total_orders': total_orders,
            'total_spent': total_spent,
            'status_breakdown': status_counts,
            'recent_orders': [order_to_dict(order) for order in orders[:5]]  # Last 5 orders
        })
    except Exception as e:
        return jsonify({'detail': str(e)}), 500

@app.route('/api/customer/profile/<int:customer_id>', methods=['GET', 'PUT'])
@token_required
def get_customer_profile(current_user, customer_id):
    try:
        # Ensure user can only access their own profile
        if current_user.id != customer_id:
            return jsonify({'detail': 'Access denied'}), 403
            
        user = User.query.get(customer_id)
        if not user:
            return jsonify({'detail': 'Customer not found'}), 404
        
        if request.method == 'PUT':
            # Update user profile (phone number)
            data = request.get_json()
            if not data:
                return jsonify({'detail': 'No data provided for update.'}), 400
            
            # Update phone number if provided
            if 'phone' in data:
                user.phone = data['phone'].strip() if data['phone'] else None
            
            db.session.commit()
            
        return jsonify(user_to_dict(user))
    except Exception as e:
        db.session.rollback()
        return jsonify({'detail': str(e)}), 500

@app.route('/api/customer/addresses', methods=['GET', 'POST'])
@token_required
def manage_addresses(current_user):
    try:
        if request.method == 'GET':
            # Get all addresses for the current user
            addresses = Address.query.filter_by(customer_id=current_user.id).order_by(Address.is_default.desc(), Address.created_at.desc()).all()
            return jsonify([address_to_dict(addr) for addr in addresses])
        
        elif request.method == 'POST':
            # Create new address
            data = request.get_json()
            if not data:
                return jsonify({'detail': 'No data provided for address creation.'}), 400
            
            # Validate required fields
            required_fields = ['street_address', 'city', 'state', 'postal_code']
            for field in required_fields:
                if not data.get(field) or not data[field].strip():
                    return jsonify({'detail': f'{field} is required.'}), 400
            
            # If this is set as default, unset other default addresses
            if data.get('is_default'):
                Address.query.filter_by(customer_id=current_user.id, is_default=True).update({'is_default': False})
            
            # Create new address
            address = Address(
                customer_id=current_user.id,
                type=data.get('type', 'home'),
                street_address=data['street_address'].strip(),
                city=data['city'].strip(),
                state=data['state'].strip(),
                postal_code=data['postal_code'].strip(),
                country=data.get('country', 'India').strip(),
                is_default=data.get('is_default', False)
            )
            
            db.session.add(address)
            db.session.commit()
            
            return jsonify(address_to_dict(address)), 201
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'detail': str(e)}), 500

@app.route('/api/customer/addresses/<int:address_id>', methods=['PUT', 'DELETE'])
@token_required
def manage_single_address(current_user, address_id):
    try:
        address = Address.query.get(address_id)
        if not address:
            return jsonify({'detail': 'Address not found.'}), 404
        
        # Ensure user can only manage their own addresses
        if address.customer_id != current_user.id:
            return jsonify({'detail': 'Access denied.'}), 403
        
        if request.method == 'PUT':
            # Update address
            data = request.get_json()
            if not data:
                return jsonify({'detail': 'No data provided for update.'}), 400
            
            # Validate required fields
            required_fields = ['street_address', 'city', 'state', 'postal_code']
            for field in required_fields:
                if not data.get(field) or not data[field].strip():
                    return jsonify({'detail': f'{field} is required.'}), 400
            
            # If this is set as default, unset other default addresses
            if data.get('is_default') and not address.is_default:
                Address.query.filter_by(customer_id=current_user.id, is_default=True).update({'is_default': False})
            
            # Update address fields
            address.type = data.get('type', address.type)
            address.street_address = data['street_address'].strip()
            address.city = data['city'].strip()
            address.state = data['state'].strip()
            address.postal_code = data['postal_code'].strip()
            address.country = data.get('country', address.country).strip()
            address.is_default = data.get('is_default', address.is_default)
            address.updated_at = datetime.utcnow()
            
            db.session.commit()
            return jsonify(address_to_dict(address))
        
        elif request.method == 'DELETE':
            # Delete address
            db.session.delete(address)
            db.session.commit()
            return jsonify({'message': 'Address deleted successfully.'})
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'detail': str(e)}), 500

@app.route('/api/farmer/profile', methods=['GET', 'PUT'])
@token_required
def farmer_profile(current_user):
    try:
        # Ensure user is a farmer
        if current_user.role != UserRole.farmer:
            return jsonify({'detail': 'Access denied. Only farmers can access this endpoint.'}), 403
        
        farmer_profile = FarmerProfile.query.filter_by(user_id=current_user.id).first()
        if not farmer_profile:
            return jsonify({'detail': 'Farmer profile not found.'}), 404
        
        if request.method == 'GET':
            return jsonify(farmer_profile_to_dict(farmer_profile))
        
        # PUT request - update profile
        data = request.get_json()
        if not data:
            return jsonify({'detail': 'No data provided for update.'}), 400
        
        # Update fields if provided
        if 'farm_name' in data and data['farm_name'].strip():
            farmer_profile.farm_name = data['farm_name'].strip()
        if 'farm_location' in data and data['farm_location'].strip():
            farmer_profile.farm_location = data['farm_location'].strip()
        if 'primary_products' in data and data['primary_products'].strip():
            farmer_profile.primary_products = data['primary_products'].strip()
        
        return jsonify(farmer_profile_to_dict(farmer_profile))
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'detail': str(e)}), 500

@app.route('/api/farmers/<int:farmer_id>/batches', methods=['GET', 'POST'])
@token_required
def manage_batches(current_user, farmer_id):
    try:
        # Verify the farmer profile belongs to the current user
        farmer_profile = FarmerProfile.query.filter_by(id=farmer_id, user_id=current_user.id).first()
        if not farmer_profile:
            return jsonify({'detail': 'Farmer profile not found or access denied.'}), 404
        
        if request.method == 'GET':
            # Get all batches for this farmer
            batches = Batch.query.filter_by(farmer_id=farmer_id).order_by(Batch.created_at.desc()).all()
            return jsonify([batch_to_dict(batch) for batch in batches])
        
        elif request.method == 'POST':
            # Create new batch
            data = request.get_json()
            if not data:
                return jsonify({'detail': 'No data provided.'}), 400
            
            # Validate required fields
            if not data.get('product_name') or not data['product_name'].strip():
                return jsonify({'detail': 'Product name is required.'}), 400
            
            if not data.get('quantity') or data['quantity'] <= 0:
                return jsonify({'detail': 'Quantity must be greater than 0.'}), 400
            
            # Generate unique batch code
            import uuid
            batch_code = f"BATCH-{str(uuid.uuid4())[:8].upper()}"
            
            # Parse harvest date if provided
            harvest_date = None
            if data.get('harvest_date'):
                try:
                    harvest_date = datetime.strptime(data['harvest_date'], '%Y-%m-%d').date()
                except ValueError:
                    return jsonify({'detail': 'Invalid harvest date format. Use YYYY-MM-DD.'}), 400
            
            # Create new batch
            batch = Batch(
                farmer_id=farmer_id,
                batch_code=batch_code,
                product_name=data['product_name'].strip(),
                harvest_date=harvest_date,
                quantity=int(data['quantity']),
                unit=data.get('unit', 'kg'),
                status=data.get('status', 'harvested')
            )
            
            db.session.add(batch)
            db.session.commit()
            
            return jsonify(batch_to_dict(batch)), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'detail': str(e)}), 500

@app.route('/health', methods=['GET'])
def healthcheck():
    return jsonify({'status': 'ok', 'timestamp': datetime.utcnow().isoformat()})
@app.route('/login')
def serve_login():
    static_dir = Path(__file__).parent / 'static'
    return send_from_directory(static_dir, 'login.html')

@app.route('/signup')
def serve_signup():
    static_dir = Path(__file__).parent / 'static'
    return send_from_directory(static_dir, 'signup.html')

@app.route('/marketplace')
def serve_marketplace():
    static_dir = Path(__file__).parent / 'static'
    return send_from_directory(static_dir, 'marketplace.html')

@app.route('/about')
def serve_about():
    static_dir = Path(__file__).parent / 'static'
    return send_from_directory(static_dir, 'about.html')

@app.route('/contact')
def serve_contact():
    static_dir = Path(__file__).parent / 'static'
    return send_from_directory(static_dir, 'contact.html')

# General static file serving
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_static(path):
    static_dir = Path(__file__).parent / 'static'
    
    # If path is empty, serve index.html
    if not path:
        return send_from_directory(static_dir, 'index.html')
    
    # Try to serve the requested file
    file_path = static_dir / path
    if file_path.exists() and file_path.is_file():
        return send_from_directory(static_dir, path)
    
    # Fallback to index.html for SPA routing
    return send_from_directory(static_dir, 'index.html')

# Handle direct HTML file requests
@app.route('/<string:page_name>.html')
def serve_html_page(page_name):
    static_dir = Path(__file__).parent / 'static'
    file_path = static_dir / f'{page_name}.html'
    
    if file_path.exists():
        return send_from_directory(static_dir, f'{page_name}.html')
    
    # Fallback to index.html for unknown pages
    return send_from_directory(static_dir, 'index.html')

with app.app_context():
    try:
        print("Creating database tables...")
        db.create_all()
        print("Seeding products...")
        seed_products()
        print("Database initialized successfully!")
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        raise

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)