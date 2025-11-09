// Sample product data with guaranteed working images
const products = [
    {
        id: 1,
        name: "Organic Tomatoes",
        price: "₹120/kg",
        image: "https://images.unsplash.com/photo-1592924357228-91a4daadcfea?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=500&q=80",
        category: "vegetables",
        verified: true,
        organic: true,
        farmer: "Rajesh Organic Farms"
    },
    {
        id: 2,
        name: "Fresh Spinach",
        price: "₹80/bunch",
        image: "https://images.unsplash.com/photo-1576045057995-568f588f82fb?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=500&q=80",
        category: "vegetables",
        verified: true,
        organic: true,
        farmer: "Green Valley Farms"
    },
    {
        id: 3,
        name: "Organic rice",
        price: "₹65/kg",
        image: "https://images.unsplash.com/photo-1586201375761-83865001e31c?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80", 
        category: "grains",
        verified: true,
        organic: true,
        farmer: "Traditional Grains Co."
    },
    {
        id: 4,
        name: "Pure Honey",
        price: "₹350/jar",
        image: "https://images.unsplash.com/photo-1558642452-9d2a7deb7f62?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=500&q=80",
        category: "dairy",
        verified: true,
        organic: true,
        farmer: "Nature's Beehive"
    },
    {
        id: 5,
        name: "Organic Apples",
        price: "₹200/kg",
        image: "https://images.unsplash.com/photo-1568702846914-96b305d2aaeb?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=500&q=80",
        category: "fruits",
        verified: true,
        organic: true,
        farmer: "Apple Orchards Ltd."
    },
    {
        id: 6,
        name: "Fresh Carrots",
        price: "₹60/kg",
        image: "https://images.unsplash.com/photo-1598170845058-32b9d6a5da37?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=500&q=80",
        category: "vegetables",
        verified: true,
        organic: true,
        farmer: "Green Roots Farm"
    },
    {
        id: 7,
        name: "Organic Bananas",
        price: "₹90/dozen",
        image: "https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=500&q=80",
        category: "fruits",
        verified: true,
        organic: true,
        farmer: "Tropical Fruits Co."
    }
];

// Function to render products
function renderProducts(productsToRender) {
    const productGrid = document.getElementById('productGrid');
    if (!productGrid) return;
    
    productGrid.innerHTML = '';
    
    productsToRender.forEach(product => {
        const productCard = document.createElement('div');
        productCard.className = 'product-card';
        productCard.innerHTML = `
            <img src="${product.image}" alt="${product.name}" class="product-image">
            <div class="product-info">
                <h3 class="product-name">${product.name}</h3>
                <div class="product-price">${product.price}</div>
                <div class="badges">
                    ${product.verified ? '<span class="badge badge-verified">Verified by IoT</span>' : ''}
                    ${product.organic ? '<span class="badge badge-organic">Organic Certified</span>' : ''}
                </div>
                <div class="product-actions">
                    <button class="btn btn-outline btn-small" onclick="viewProduct(${product.id})">View Details</button>
                    <button class="btn btn-primary btn-small" onclick="addToCart(${product.id})">Add to Cart</button>
                </div>
            </div>
        `;
        productGrid.appendChild(productCard);
    });
}

// Function to filter products
function filterProducts() {
    const category = document.getElementById('category')?.value;
    const price = document.getElementById('price')?.value;
    const certification = document.getElementById('certification')?.value;
    
    if (!category || !price || !certification) return;
    
    let filteredProducts = products;
    
    // Filter by category
    if (category !== 'all') {
        filteredProducts = filteredProducts.filter(product => product.category === category);
    }
    
    // Filter by price
    if (price !== 'all') {
        filteredProducts = filteredProducts.filter(product => {
            const priceValue = parseInt(product.price.replace(/[^0-9]/g, ''));
            if (price === 'low') return priceValue < 100;
            if (price === 'medium') return priceValue >= 100 && priceValue <= 300;
            if (price === 'high') return priceValue > 300;
            return true;
        });
    }
    
    // Filter by certification
    if (certification !== 'all') {
        if (certification === 'organic') {
            filteredProducts = filteredProducts.filter(product => product.organic);
        } else if (certification === 'iot') {
            filteredProducts = filteredProducts.filter(product => product.verified);
        }
    }
    
    renderProducts(filteredProducts);
}

// Function to view product details
function viewProduct(productId) {
    window.location.href = `product.html?id=${productId}`;
}

// Function to add product to cart
function addToCart(productId) {
    const isLoggedIn = localStorage.getItem('userLoggedIn');
    
    if (!isLoggedIn) {
        alert('Please login to add items to your cart');
        // window.location.href = 'login.html';
        return;
    }
    
    let cart = JSON.parse(localStorage.getItem('cart')) || [];
    const product = products.find(p => p.id === productId);
    
    if (product) {
        const existingItem = cart.find(item => item.id === productId);
        
        if (existingItem) {
            existingItem.quantity += 1;
        } else {
            cart.push({
                ...product,
                quantity: 1
            });
        }
        
        localStorage.setItem('cart', JSON.stringify(cart));
        alert('Product added to cart!');
    }
}

// Particle Animation Function
function initializeParticleAnimation() {
    const canvas = document.getElementById('particle-canvas');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    let particles = [];
    
    function resizeCanvas() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    }
    
    class Particle {
        constructor() {
            this.reset();
        }
        
        reset() {
            this.x = Math.random() * canvas.width;
            this.y = Math.random() * canvas.height;
            this.vx = (Math.random() - 0.5) * 1.5;
            this.vy = (Math.random() - 0.5) * 1.5;
            this.size = Math.random() * 2 + 0.5;
            this.alpha = Math.random() * 0.6 + 0.2;
            this.color = `rgba(0, 255, 198, ${this.alpha})`;
        }
        
        update() {
            this.x += this.vx;
            this.y += this.vy;
            
            if (this.x < -50 || this.x > canvas.width + 50 || this.y < -50 || this.y > canvas.height + 50) {
                this.reset();
            }
        }
        
        draw() {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
            ctx.fillStyle = this.color;
            ctx.fill();
        }
    }
    
    function createParticles() {
        particles = [];
        const particleCount = Math.min(80, Math.floor((canvas.width * canvas.height) / 15000));
        
        for (let i = 0; i < particleCount; i++) {
            particles.push(new Particle());
        }
    }
    
    function drawConnections() {
        for (let i = 0; i < particles.length; i++) {
            for (let j = i + 1; j < particles.length; j++) {
                const dx = particles[i].x - particles[j].x;
                const dy = particles[i].y - particles[j].y;
                const distance = Math.sqrt(dx * dx + dy * dy);
                
                if (distance < 120) {
                    const opacity = 1 - (distance / 120);
                    ctx.beginPath();
                    ctx.strokeStyle = `rgba(0, 255, 198, ${opacity * 0.15})`;
                    ctx.lineWidth = 0.8;
                    ctx.moveTo(particles[i].x, particles[i].y);
                    ctx.lineTo(particles[j].x, particles[j].y);
                    ctx.stroke();
                }
            }
        }
    }
    
    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        particles.forEach(particle => {
            particle.update();
            particle.draw();
        });
        
        drawConnections();
        
        requestAnimationFrame(animate);
    }
    
    resizeCanvas();
    createParticles();
    animate();
    
    window.addEventListener('resize', () => {
        resizeCanvas();
        createParticles();
    });
}

// Initialize the page
document.addEventListener('DOMContentLoaded', () => {
    initializeParticleAnimation();
    
    if (document.getElementById('productGrid')) {
        renderProducts(products);
        
        const categoryFilter = document.getElementById('category');
        const priceFilter = document.getElementById('price');
        const certificationFilter = document.getElementById('certification');
        
        if (categoryFilter) categoryFilter.addEventListener('change', filterProducts);
        if (priceFilter) priceFilter.addEventListener('change', filterProducts);
        if (certificationFilter) certificationFilter.addEventListener('change', filterProducts);
    }
});