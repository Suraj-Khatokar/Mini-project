// cart.js
document.addEventListener('DOMContentLoaded', function() {
    // Initialize cart from localStorage or create empty cart
    let cart = JSON.parse(localStorage.getItem('cart')) || [];

    // Function to save cart to localStorage
    function saveCart() {
        localStorage.setItem('cart', JSON.stringify(cart));
        updateCartCount();
    }

    // Function to update cart count in the UI
    function updateCartCount() {
        const totalItems = cart.reduce((sum, item) => sum + item.quantity, 0);
        const countElements = document.querySelectorAll('.cart-count');
        
        countElements.forEach(el => {
            el.textContent = totalItems;
            el.style.display = totalItems > 0 ? 'flex' : 'none';
        });
    }

    // Function to add item to cart
    function addToCart(productId, name, price, quantity = 1, image = '') {
        const existingItem = cart.find(item => item.id === productId);
        
        if (existingItem) {
            existingItem.quantity += quantity;
        } else {
            cart.push({
                id: productId,
                name: name,
                price: price,
                quantity: quantity,
                image: image,
                addedAt: new Date().toISOString()
            });
        }
        
        saveCart();
        showNotification('Item added to cart!');
        return cart;
    }

    // Function to remove item from cart
    function removeFromCart(productId) {
        cart = cart.filter(item => item.id !== productId);
        saveCart();
        return cart;
    }

    // Function to update item quantity
    function updateQuantity(productId, quantity) {
        const item = cart.find(item => item.id === productId);
        if (item) {
            if (quantity < 1) {
                return removeFromCart(productId);
            }
            item.quantity = quantity;
            saveCart();
        }
        return cart;
    }

    // Function to get cart total
    function getCartTotal() {
        return cart.reduce((total, item) => total + (item.price * item.quantity), 0);
    }

    // Function to clear cart
    function clearCart() {
        cart = [];
        saveCart();
        return cart;
    }

    // Show notification
    function showNotification(message) {
        // Check if notification element exists, if not create it
        let notification = document.getElementById('cart-notification');
        if (!notification) {
            notification = document.createElement('div');
            notification.id = 'cart-notification';
            notification.style.cssText = `
                position: fixed;
                bottom: 20px;
                right: 20px;
                background: #4CAF50;
                color: white;
                padding: 15px 25px;
                border-radius: 4px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.2);
                z-index: 1000;
                transform: translateY(100px);
                opacity: 0;
                transition: all 0.3s ease;
            `;
            document.body.appendChild(notification);
        }

        notification.textContent = message;
        notification.style.transform = 'translateY(0)';
        notification.style.opacity = '1';

        // Hide after 3 seconds
        setTimeout(() => {
            notification.style.transform = 'translateY(100px)';
            notification.style.opacity = '0';
        }, 3000);
    }

    // Initialize cart count on page load
    updateCartCount();

    // Make functions available globally
    window.cartManager = {
        addToCart,
        removeFromCart,
        updateQuantity,
        getCart: () => [...cart],
        getCartTotal,
        clearCart,
        updateCartCount
    };

    // Handle add to cart buttons
    document.addEventListener('click', function(e) {
        const addToCartBtn = e.target.closest('.add-to-cart');
        if (addToCartBtn) {
            e.preventDefault();
            
            const productCard = addToCartBtn.closest('.product-card');
            const productId = productCard.dataset.id;
            const productName = productCard.querySelector('.product-name').textContent;
            const productPrice = parseFloat(productCard.querySelector('.product-price').dataset.price);
            const productImage = productCard.querySelector('img')?.src || '';
            
            addToCart(productId, productName, productPrice, 1, productImage);
        }
    });
});
