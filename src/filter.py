
import numpy as np

class KalmanFilter:
    def __init__(self, process_noise=1e-4, measurement_noise=1e-2):
        # State: [x, y, vx, vy]
        self.state = np.zeros(4, dtype=np.float32)
        
        # Identity matrix
        self.P = np.eye(4, dtype=np.float32) * 1.0 # Error covariance
        
        # State transition matrix (assuming constant velocity)
        # x' = x + vx
        # y' = y + vy
        self.F = np.eye(4, dtype=np.float32)
        self.F[0, 2] = 1.0
        self.F[1, 3] = 1.0
        
        # Measurement matrix (we only measure x and y)
        self.H = np.zeros((2, 4), dtype=np.float32)
        self.H[0, 0] = 1.0
        self.H[1, 1] = 1.0
        
        # Process noise covariance
        self.Q = np.eye(4, dtype=np.float32) * process_noise
        
        # Measurement noise covariance
        self.R = np.eye(2, dtype=np.float32) * measurement_noise

    def reset(self, x, y):
        """Reset state to specific position with zero velocity."""
        self.state = np.zeros(4, dtype=np.float32)
        self.state[0] = x
        self.state[1] = y
        self.P = np.eye(4, dtype=np.float32) * 1.0

    def predict(self):
        # Predict state
        self.state = np.dot(self.F, self.state)
        # Predict error covariance
        self.P = np.dot(np.dot(self.F, self.P), self.F.T) + self.Q
        return self.state[:2]

    def update(self, measurement):
        # measurement is [x, y]
        z = np.array(measurement, dtype=np.float32)
        
        # Measurement residual
        y = z - np.dot(self.H, self.state)
        
        # Residual covariance
        S = np.dot(np.dot(self.H, self.P), self.H.T) + self.R
        
        # Optimal Kalman gain
        K = np.dot(np.dot(self.P, self.H.T), np.linalg.inv(S))
        
        # Update state estimate
        self.state = self.state + np.dot(K, y)
        
        # Update error covariance
        I = np.eye(4, dtype=np.float32)
        self.P = np.dot((I - np.dot(K, self.H)), self.P)
        
        return self.state[:2]

class SignalFilter:
    def __init__(self, min_cutoff=1.0, beta=40.0, d_cutoff=1.0):
        # Using a simpler one-euro-filter like approach for adaptive smoothing
        # combined with Kalman for core state estimation
        self.kalman = KalmanFilter()
        
        self.prev_x = 0.0
        self.prev_y = 0.0
        self.alpha = 0.5
        
        # Adaptive parameters
        self.min_cutoff = min_cutoff # Minimum cutoff frequency
        self.beta = beta             # Speed coefficient
        self.d_cutoff = d_cutoff     # Cutoff for derivative
        
        self.last_time = None

    def reset(self, x, y):
        """Reset filter to a specific position to prevent slewing from 0."""
        self.kalman.reset(x, y)
        self.prev_x = x
        self.prev_y = y
        self.last_time = None

    def process(self, x, y, dt):
        """
        x, y: normalized coordinates
        dt: time delta in seconds
        """
        # First pass: Kalman Filter for prediction and noise reduction
        kx, ky = self.kalman.predict()
        kx, ky = self.kalman.update([x, y])
        
        # Second pass: Adaptive Exponential Smoothing
        # Calculate velocity based on filtered Kalman output
        dx = (kx - self.prev_x) / dt if dt > 0 else 0
        dy = (ky - self.prev_y) / dt if dt > 0 else 0
        velocity = np.sqrt(dx*dx + dy*dy)
        
        # Adaptive alpha based on speed
        # Higher speed -> higher alpha (less latency)
        # Lower speed -> lower alpha (more smooth)
        # Simple adaptive logic:
        # alpha = base_alpha + (velocity * gain) clamped to [0.01, 0.9]
        
        target_alpha = 0.05 + (velocity * 0.1)
        self.alpha = max(0.01, min(0.8, target_alpha))
        
        # Apply smoothing
        sx = self.alpha * kx + (1 - self.alpha) * self.prev_x
        sy = self.alpha * ky + (1 - self.alpha) * self.prev_y
        
        self.prev_x = sx
        self.prev_y = sy
        
        return sx, sy
