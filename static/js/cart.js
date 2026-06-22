// Show toast notification
function showToast(message, type = 'success') {
    const toastContainer = document.querySelector('.toast-container');
    const toastId = 'toast-' + Date.now();
    const bgClass = type === 'success' ? 'bg-success' : (type === 'error' ? 'bg-danger' : 'bg-primary');
    
    const toastHTML = `
        <div id="${toastId}" class="toast align-items-center text-white ${bgClass} border-0" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body">
                    ${type === 'success' ? '<i class="bi bi-check-circle me-2"></i>' : '<i class="bi bi-exclamation-circle me-2"></i>'}
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `;
    
    toastContainer.insertAdjacentHTML('beforeend', toastHTML);
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, { delay: 3000 });
    toast.show();
    
    // Remove from DOM after hidden
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
}

// Update badge with animation
function updateCartBadge(count) {
    const badge = document.getElementById('cart-badge');
    if (badge) {
        badge.textContent = count;
        badge.classList.remove('pulse-animation');
        void badge.offsetWidth; // trigger reflow
        badge.classList.add('pulse-animation');
    }
}

// Add to Cart
async function addToCart(productId, quantity = 1) {
    try {
        const response = await fetch('/cart/add/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ product_id: productId, quantity: quantity })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            updateCartBadge(data.cart_count);
            showToast(data.message, 'success');
        } else {
            showToast(data.message || 'Bir hata oluştu.', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showToast('Bağlantı hatası.', 'error');
    }
}

// Update Cart Quantity
async function updateCart(itemId, quantity) {
    if (quantity < 1) {
        removeFromCart(itemId);
        return;
    }
    
    try {
        const response = await fetch('/cart/update/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ item_id: itemId, quantity: parseInt(quantity) })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            updateCartBadge(data.cart_count);
            // Reload page to reflect totals simply for now
            // In a fully SPA approach we would update DOM elements
            location.reload(); 
        } else {
            showToast(data.message || 'Bir hata oluştu.', 'error');
            // reset input
            document.getElementById(`qty-${itemId}`).value = document.getElementById(`qty-${itemId}`).defaultValue;
        }
    } catch (error) {
        console.error('Error:', error);
    }
}

// Remove from Cart
async function removeFromCart(itemId) {
    try {
        const response = await fetch('/cart/remove/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ item_id: itemId })
        });
        
        if (response.ok) {
            location.reload();
        }
    } catch (error) {
        console.error('Error:', error);
    }
}

// Apply Coupon
async function applyCoupon() {
    const code = document.getElementById('coupon_code').value;
    if (!code) return;
    
    try {
        const response = await fetch('/cart/apply-coupon/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ code: code })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast(data.message, 'success');
            setTimeout(() => location.reload(), 1500);
        } else {
            showToast(data.message, 'error');
        }
    } catch (error) {
        console.error('Error:', error);
    }
}

// Product details +/- buttons
function increaseQty() {
    const input = document.getElementById('product-quantity');
    if (input) input.value = parseInt(input.value) + 1;
}

function decreaseQty() {
    const input = document.getElementById('product-quantity');
    if (input && parseInt(input.value) > 1) {
        input.value = parseInt(input.value) - 1;
    }
}
