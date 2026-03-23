import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCart } from '../context/CartContext';
import { api } from '../lib/api';
import { Trash2, Plus, Minus, ArrowRight, ShoppingBag } from 'lucide-react';

const Cart = () => {
    const { cart, removeFromCart, updateQuantity, totalPrice, clearCart } = useCart();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const navigate = useNavigate();

    const handleCheckout = async () => {
        if (cart.length === 0) return;
        setLoading(true);
        setError(null);
        try {
            const items = cart.map(item => ({
                product_id: item.product_id,
                quantity: item.quantity,
                price: item.price.toString()
            }));

            const session = await api.checkout(items);
            clearCart();
            navigate(`/orders/${session.order_id}`);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    if (cart.length === 0) {
        return (
            <div className="page container flex-col items-center justify-center" style={{ minHeight: '60vh' }}>
                <div className="empty-state">
                    <ShoppingBag className="empty-icon" />
                    <h2 style={{ fontSize: '2rem', marginBottom: '16px' }}>Your cart is empty</h2>
                    <p style={{ marginBottom: '32px' }}>Looks like you haven't added anything to your cart yet.</p>
                    <button className="btn btn-primary" onClick={() => navigate('/')}>
                        Start Shopping
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="page container">
            <h1 className="text-gradient" style={{ fontSize: '2.5rem', marginBottom: '40px' }}>Your Cart</h1>

            <div className="grid" style={{ gridTemplateColumns: '1fr 350px' }}>
                <div className="cart-items">
                    {cart.map(item => (
                        <div key={item.product_id} className="cart-item glass-panel">
                            <img src={item.image} alt={item.name} className="cart-item-img" />
                            <div className="cart-item-details">
                                <h3 style={{ fontSize: '1.2rem', marginBottom: '4px' }}>{item.name}</h3>
                                <p className="text-gradient" style={{ fontWeight: 'bold' }}>₹{item.price.toFixed(2)}</p>
                            </div>
                            <div className="flex items-center gap-4">
                                <div className="flex items-center glass-panel" style={{ padding: '4px', borderRadius: 'var(--border-radius-pill)' }}>
                                    <button className="btn-icon" onClick={() => updateQuantity(item.product_id, item.quantity - 1)} style={{ background: 'transparent', border: 'none', padding: '6px' }}>
                                        <Minus size={14} />
                                    </button>
                                    <span style={{ width: '30px', textAlign: 'center', fontWeight: '600' }}>{item.quantity}</span>
                                    <button className="btn-icon" onClick={() => updateQuantity(item.product_id, item.quantity + 1)} style={{ background: 'transparent', border: 'none', padding: '6px' }}>
                                        <Plus size={14} />
                                    </button>
                                </div>
                                <button className="btn-icon" onClick={() => removeFromCart(item.product_id)} style={{ color: 'var(--error)' }}>
                                    <Trash2 size={18} />
                                </button>
                            </div>
                        </div>
                    ))}
                </div>

                <div className="cart-summary glass-panel">
                    <h2 style={{ fontSize: '1.5rem', marginBottom: '24px' }}>Order Summary</h2>

                    <div className="flex justify-between" style={{ marginBottom: '16px', color: 'var(--text-secondary)' }}>
                        <span>Subtotal</span>
                        <span>₹{totalPrice.toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between" style={{ marginBottom: '24px', color: 'var(--text-secondary)' }}>
                        <span>Shipping</span>
                        <span>Free</span>
                    </div>

                    <div style={{ height: '1px', background: 'var(--surface-border)', margin: '24px 0' }}></div>

                    <div className="flex justify-between" style={{ marginBottom: '32px', fontSize: '1.25rem', fontWeight: 'bold' }}>
                        <span>Total</span>
                        <span className="text-gradient">₹{totalPrice.toFixed(2)}</span>
                    </div>

                    {error && (
                        <div style={{ padding: '12px', background: 'rgba(255, 77, 109, 0.1)', color: 'var(--error)', borderRadius: '8px', marginBottom: '24px', fontSize: '0.9rem' }}>
                            {error}
                        </div>
                    )}

                    <button
                        className="btn btn-primary"
                        style={{ width: '100%', padding: '16px' }}
                        onClick={handleCheckout}
                        disabled={loading}
                    >
                        {loading ? 'Processing...' : (
                            <span className="flex items-center gap-2 justify-center">
                                Checkout <ArrowRight size={18} />
                            </span>
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default Cart;
