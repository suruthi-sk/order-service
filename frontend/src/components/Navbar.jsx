import React from 'react';
import { NavLink, Link } from 'react-router-dom';
import { ShoppingCart, Package } from 'lucide-react';
import { useCart } from '../context/CartContext';

const Navbar = () => {
    const { totalItems } = useCart();

    return (
        <nav className="navbar glass-panel">
            <Link to="/" className="nav-logo">
                <span className="text-gradient">YouTech</span>
                <span> Store</span>
            </Link>
            <div className="nav-links">
                <NavLink to="/" className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>
                    Home
                </NavLink>
                <NavLink to="/orders" className={({ isActive }) => isActive ? "nav-link active" : "nav-link flex items-center gap-2"}>
                    <Package size={18} />
                    Orders
                </NavLink>
                <NavLink to="/cart" className={({ isActive }) => isActive ? "nav-link active" : "nav-link flex items-center gap-2"}>
                    <ShoppingCart size={18} />
                    Cart
                    {totalItems > 0 && <span className="badge">{totalItems}</span>}
                </NavLink>
            </div>
        </nav>
    );
};

export default Navbar;
