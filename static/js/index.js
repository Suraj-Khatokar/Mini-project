// index.js
document.addEventListener('DOMContentLoaded', async function() {
    // Check auth status
    const token = localStorage.getItem('authToken');
    if (!token) {
        window.location.href = '/login.html';
        return;
    }

    try {
        // Load products
        const products = await api.products.getAll();
        renderProducts(products);
        
        // Load cart
        const cart = await api.cart.get();
        updateCartUI(cart);
    } catch (error) {
        console.error('Failed to load page data:', error);
    }
});

function renderProducts(products) {
    const container = document.getElementById('products-container');
    if (!container) return;

    container.innerHTML = products.map(product => `
        <div class="product-card">
            <img src="${product.imageUrl || '/static/images/placeholder.jpg'}" alt="${product.name}">
            <h3>${product.name}</h3>
            <p>$${product.price.toFixed(2)}</p>
            <button class="add-to-cart" data-id="${product.id}">Add to Cart</button>
        </div>
    `).join('');

    // Add event listeners to Add to Cart buttons
    document.querySelectorAll('.add-to-cart').forEach(button => {
        button.addEventListener('click', async (e) => {
            const productId = e.target.dataset.id;
            try {
                await api.cart.addItem(productId, 1);
                const cart = await api.cart.get();
                updateCartUI(cart);
                showNotification('Item added to cart!');
            } catch (error) {
                console.error('Failed to add item to cart:', error);
                showNotification('Failed to add item to cart', 'error');
            }
        });
    });
}

function updateCartUI(cart) {
    const cartCount = document.querySelector('.cart-count');
    if (cartCount) {
        const totalItems = cart.items.reduce((sum, item) => sum + item.quantity, 0);
        cartCount.textContent = totalItems;
        cartCount.style.display = totalItems > 0 ? 'flex' : 'none';
    }
}

function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.classList.add('show');
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }, 100);
}