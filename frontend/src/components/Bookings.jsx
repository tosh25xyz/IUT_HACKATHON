import { useState, useEffect } from 'react'
import api from '../api/axios'

function Bookings() {
  const [bookings, setBookings] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  useEffect(() => {
    fetchBookings()
  }, [])

  const fetchBookings = async () => {
    try {
      const { data } = await api.get('/bookings?page=1&limit=50')
      setBookings(data.items)
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to load bookings')
    } finally {
      setLoading(false)
    }
  }

  const handleCancel = async (bookingId) => {
    if (!confirm('Are you sure you want to cancel this booking?')) return

    try {
      const { data } = await api.post(`/bookings/${bookingId}/cancel`)
      setSuccess(`Booking cancelled. Refund: $${(data.refund_amount_cents / 100).toFixed(2)} (${data.refund_percent}%)`)
      fetchBookings()
      setTimeout(() => setSuccess(''), 5000)
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to cancel booking')
      setTimeout(() => setError(''), 5000)
    }
  }

  const formatDate = (isoString) => {
    return new Date(isoString).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  if (loading) return <div className="loading">Loading bookings...</div>

  return (
    <div className="card">
      <h3>My Bookings</h3>
      
      {error && <div className="error">{error}</div>}
      {success && <div className="success">{success}</div>}

      {bookings.length === 0 ? (
        <div className="empty-state">
          <p>You don't have any bookings yet.</p>
          <p>Go to the Rooms tab to make your first booking!</p>
        </div>
      ) : (
        <div className="booking-list">
          {bookings.map(booking => (
            <div key={booking.id} className={`booking-item ${booking.status}`}>
              <div className="booking-header">
                <span className="booking-ref">#{booking.reference_code}</span>
                <span className={`booking-status ${booking.status}`}>
                  {booking.status.toUpperCase()}
                </span>
              </div>
              <div className="booking-details">
                <div><strong>Start:</strong> {formatDate(booking.start_time)}</div>
                <div><strong>End:</strong> {formatDate(booking.end_time)}</div>
                <div><strong>Price:</strong> ${(booking.price_cents / 100).toFixed(2)}</div>
              </div>
              {booking.status === 'confirmed' && (
                <div className="booking-actions">
                  <button 
                    className="btn btn-danger" 
                    onClick={() => handleCancel(booking.id)}
                  >
                    Cancel Booking
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default Bookings
