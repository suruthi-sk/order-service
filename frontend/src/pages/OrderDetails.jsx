import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../lib/api';
import { Package, Truck, CheckCircle, ArrowLeft, RefreshCw, XCircle, Clock } from 'lucide-react';

const OrderDetails = () => {
    const { id } = useParams();
    const [order, setOrder] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [updating, setUpdating] = useState(false);

    const fetchOrder = async () => {
        try {
            const data = await api.getOrder(id);
            setOrder(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchOrder();
    }, [id]);

    const handleUpdateStatus = async (newStatus) => {
        setUpdating(true);
        try {
            await api.updateOrderStatus(id, newStatus);
            await fetchOrder(); // refresh order internally
        } catch (err) {
            alert(err.message);
        } finally {
            setUpdating(false);
        }
    };

    if (loading) {
        return <div className="page container flex justify-center items-center" style={{ minHeight: '60vh' }}><div className="text-gradient">Loading details...</div></div>;
    }

    if (error || !order) {
        return <div className="page container">Error: {error || 'Order not found'}</div>;
    }

    const statusList = ['pending', 'confirmed', 'processing', 'shipped', 'delivered'];
    const currentStatusIndex = statusList.indexOf(order.status.toLowerCase());
    const isCancelled = order.status.toLowerCase() === 'cancelled';

    return (
        <div className="page container">
            <Link to="/orders" className="flex items-center gap-2" style={{ color: 'var(--text-secondary)', marginBottom: '24px' }}>
                <ArrowLeft size={16} /> Back to Orders
            </Link>

            <div className="flex justify-between items-center" style={{ marginBottom: '40px' }}>
                <div>
                    <h1 className="text-gradient" style={{ fontSize: '2.5rem', marginBottom: '8px' }}>Order Details</h1>
                    <p style={{ color: 'var(--text-muted)', fontFamily: 'monospace' }}>#{order.order_id}</p>
                </div>
                <div style={{ textAlign: 'right' }}>
                    <span className={`status status-${order.status.toLowerCase()}`} style={{ fontSize: '1rem', padding: '8px 16px' }}>
                        {order.status}
                    </span>
                    <p style={{ marginTop: '8px', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                        {new Date(order.created_at).toLocaleString()}
                    </p>
                </div>
            </div>

            <div className="glass-panel" style={{ padding: '32px', marginBottom: '32px' }}>
                <h2 style={{ fontSize: '1.25rem', marginBottom: '24px' }}>Order Progress</h2>

                {isCancelled ? (
                    <div className="flex-col items-center justify-center" style={{ padding: '24px', color: 'var(--error)' }}>
                        <XCircle size={48} style={{ marginBottom: '16px' }} />
                        <h3 style={{ fontSize: '1.2rem' }}>This order was cancelled</h3>
                    </div>
                ) : (
                    <div className="timeline">
                        {statusList.map((st, i) => {
                            const active = i <= currentStatusIndex;
                            let Icon = Clock;
                            if (st === 'confirmed' || st === 'processing') Icon = RefreshCw;
                            if (st === 'shipped') Icon = Truck;
                            if (st === 'delivered') Icon = CheckCircle;
                            if (st === 'pending') Icon = Package;

                            return (
                                <div key={st} className={`timeline-step ${active ? 'active' : ''}`}>
                                    <div className="timeline-dot">
                                        <Icon size={16} />
                                    </div>
                                    <span className="timeline-label">{st}</span>
                                </div>
                            );
                        })}
                    </div>
                )}

                {/* User can only cancel an order if it is still pending */}
                {!isCancelled && order.status.toLowerCase() === 'pending' && (
                    <div className="flex justify-center gap-4" style={{ marginTop: '40px' }}>
                        <button
                            className="btn btn-secondary"
                            disabled={updating}
                            onClick={() => handleUpdateStatus('cancelled')}
                            style={{ color: 'var(--error)' }}
                        >
                            Cancel Order
                        </button>
                    </div>
                )}
            </div>

            <div className="grid grid-cols-2" style={{ gap: '32px' }}>
                <div className="glass-panel" style={{ padding: '32px' }}>
                    <h2 style={{ fontSize: '1.25rem', marginBottom: '24px' }}>Order Items</h2>
                    <div className="flex-col gap-4">
                        {order.items && order.items.map((item, i) => (
                            <div key={i} className="flex justify-between items-center" style={{ paddingBottom: '16px', borderBottom: '1px solid var(--surface-border)' }}>
                                <div>
                                    <h4 style={{ fontSize: '1rem', fontWeight: '500' }}>Product ID: <span style={{ fontFamily: 'monospace', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{item.product_id.split('-')[0]}...</span></h4>
                                    <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>Qty: {item.quantity}</p>
                                </div>
                                <div style={{ fontWeight: '600' }}>
                                    ₹{(parseFloat(item.price) * item.quantity).toFixed(2)}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="glass-panel" style={{ padding: '32px', height: 'fit-content' }}>
                    <h2 style={{ fontSize: '1.25rem', marginBottom: '24px' }}>Summary</h2>
                    <div className="flex justify-between" style={{ marginBottom: '16px', color: 'var(--text-secondary)' }}>
                        <span>Subtotal</span>
                        <span>₹{order.total_price ? parseFloat(order.total_price).toFixed(2) : '0.00'}</span>
                    </div>
                    <div className="flex justify-between" style={{ marginBottom: '24px', color: 'var(--text-secondary)' }}>
                        <span>Shipping</span>
                        <span>Free</span>
                    </div>
                    <div style={{ height: '1px', background: 'var(--surface-border)', margin: '24px 0' }}></div>
                    <div className="flex justify-between" style={{ fontSize: '1.25rem', fontWeight: 'bold' }}>
                        <span>Total</span>
                        <span className="text-gradient">₹{order.total_price ? parseFloat(order.total_price).toFixed(2) : '0.00'}</span>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default OrderDetails;
