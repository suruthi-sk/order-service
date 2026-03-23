import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../lib/api';
import { PackageSearch, Eye } from 'lucide-react';

const Orders = () => {
    const [orders, setOrders] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchOrders = async () => {
            try {
                const data = await api.getOrders();
                // data.items is the array of orders (based on standard pagination schema, assuming list returns { items: [], total: x})
                // Based on backend, if it's a list directly, we use data. Otherwise data.orders.
                // In the README: curl "http://localhost:8000/api/v1/orders?user_id={user_id}&page=1&page_size=10"
                setOrders(data.orders || data.items || data);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };
        fetchOrders();
    }, []);

    if (loading) {
        return <div className="page container flex justify-center items-center" style={{ minHeight: '60vh' }}><div className="text-gradient">Loading orders...</div></div>;
    }

    if (error) {
        return <div className="page container">Error fetching orders: {error}</div>;
    }

    return (
        <div className="page container">
            <div className="flex justify-between items-center" style={{ marginBottom: '40px' }}>
                <h1 className="text-gradient" style={{ fontSize: '2.5rem' }}>Order History</h1>
            </div>

            {orders.length === 0 ? (
                <div className="empty-state glass-panel">
                    <PackageSearch className="empty-icon" />
                    <h2 style={{ fontSize: '1.5rem', marginBottom: '16px' }}>No orders found</h2>
                    <p style={{ color: 'var(--text-secondary)' }}>You haven't placed any orders yet.</p>
                </div>
            ) : (
                <div className="glass-panel" style={{ overflow: 'hidden' }}>
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>Order ID</th>
                                <th>Date</th>
                                <th>Total</th>
                                <th>Status</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {orders.map(order => (
                                <tr key={order.order_id}>
                                    <td style={{ fontFamily: 'monospace', color: 'var(--text-secondary)' }}>
                                        {order.order_id.split('-')[0]}...
                                    </td>
                                    <td>{new Date(order.created_at).toLocaleDateString()}</td>
                                    <td style={{ fontWeight: '600' }}>₹{parseFloat(order.total_price).toFixed(2)}</td>
                                    <td>
                                        <span className={`status status-${order.status.toLowerCase()}`}>
                                            {order.status}
                                        </span>
                                    </td>
                                    <td>
                                        <Link to={`/orders/${order.order_id}`} className="btn-icon">
                                            <Eye size={16} />
                                        </Link>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
};

export default Orders;
