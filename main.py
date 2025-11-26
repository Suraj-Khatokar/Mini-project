from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, text
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
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    "DATABASE_URL", f"sqlite:///{Path(__file__).parent / 'smartorganic.db'}"
)
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
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.customer)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

    farmer_profile = relationship("FarmerProfile", back_populates="user", uselist=False)
    orders = relationship("Order", back_populates="customer")

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
        'role': user.role.value,
        'created_at': user.created_at.isoformat() if user.created_at else None,
        'farmer_profile': farmer_profile_to_dict(user.farmer_profile) if user.farmer_profile else None
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

# Seed data
def seed_products():
    if Product.query.count() > 0:
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
    db.session.add(sample_farmer)
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

# Initialize database
with app.app_context():
    db.create_all()
    seed_products()

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
        if role and user.role != UserRole(role):
            return jsonify({'detail': f'Please login as a {role} to continue.'}), 403

        # Generate token
        token = f"mock-token-{user.id}"
        
        return jsonify({
            'message': 'Login successful',
            'user': user_to_dict(user),
            'token': token
        })
        
    except Exception as e:
        logger.error(f"Login error for {data.get('email')}: {str(e)}")
        return jsonify({'detail': 'An error occurred during login. Please try again.'}), 500

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

@app.route('/health', methods=['GET'])
def healthcheck():
    return jsonify({'status': 'ok', 'timestamp': datetime.utcnow().isoformat()})

# ========== FIXED STATIC FILE SERVING ==========
# Specific routes for main pages
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)