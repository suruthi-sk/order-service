import React, { useState } from 'react';
import { useCart } from '../context/CartContext';
import { ShoppingBag, Check } from 'lucide-react';

// Using mock products as there is no backend product list endpoint
const mockProducts = [
    {
        product_id: "c2eebc99-9c0b-4ef8-bb6d-6bb9bd380a33",
        name: "Nebula Wireless Headphones",
        price: 11999.00,
        image: "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&q=80&w=400"
    },
    {
        product_id: "d3eebc99-9c0b-4ef8-bb6d-6bb9bd380a44",
        name: "Aura Smart Watch",
        price: 15999.00,
        image: "https://images.unsplash.com/photo-1546868871-7041f2a55e12?auto=format&fit=crop&q=80&w=400"
    },
    {
        product_id: "e4eebc99-9c0b-4ef8-bb6d-6bb9bd380a55",
        name: "Cosmic Audio Interface",
        price: 7999.00,
        image: "https://images.unsplash.com/photo-1598488035139-bdbb2231ce04?auto=format&fit=crop&q=80&w=400"
    },
    {
        product_id: "f5eebc99-9c0b-4ef8-bb6d-6bb9bd380a66",
        name: "Starlight Keychron Keyboard",
        price: 9999.00,
        image: "https://images.unsplash.com/photo-1595225476474-87563907a212?auto=format&fit=crop&q=80&w=400"
    }
];

const ProductCard = ({ product }) => {
    const { addToCart } = useCart();
    const [added, setAdded] = useState(false);

    const handleAdd = () => {
        addToCart(product);
        setAdded(true);
        setTimeout(() => setAdded(false), 2000);
    };

    return (
        <div className="product-card glass-panel">
            <img src={product.image} alt={product.name} className="product-image" loading="lazy" />
            <div className="product-info">
                <h3 className="product-title">{product.name}</h3>
                <p className="product-price">₹{product.price.toFixed(2)}</p>
                <button
                    onClick={handleAdd}
                    className="btn btn-primary"
                    style={{ width: '100%', marginTop: 'auto' }}
                >
                    {added ? <><Check size={18} /> Added</> : <><ShoppingBag size={18} /> Add to Cart</>}
                </button>
            </div>
        </div>
    );
};

const Home = () => {
    return (
        <div className="page container">
            <header style={{ textAlign: 'center', marginBottom: '60px' }}>
                <h1 className="text-gradient" style={{ fontSize: '3rem', marginBottom: '16px' }}>
                    Welcome to YouTech Store
                </h1>
                <p style={{ color: 'var(--text-secondary)', fontSize: '1.2rem', maxWidth: '600px', margin: '0 auto' }}>
                    Elevate your daily experience with our curated premium accessories.
                </p>
            </header>

            <div className="grid grid-cols-4">
                {mockProducts.map(p => (
                    <ProductCard key={p.product_id} product={p} />
                ))}
            </div>
        </div>
    );
};

export default Home;
