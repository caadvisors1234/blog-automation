/**
 * WebSocket Manager for Blog Progress Updates
 * 
 * Handles real-time communication with the server for:
 * - Blog post generation progress
 * - SALON BOARD publishing progress
 * - Task status updates
 */

class BlogWebSocket {
    constructor() {
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.listeners = new Map();
        this.connected = false;
        this.postId = null;
    }

    /**
     * Connect to WebSocket server
     * @param {number|null} postId - Optional post ID for post-specific updates
     */
    connect(postId = null) {
        this.postId = postId;
        
        // Determine WebSocket URL
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        let path = '/ws/blog/progress/';
        
        if (postId) {
            path = `/ws/blog/progress/${postId}/`;
        }
        
        const wsUrl = `${protocol}//${host}${path}`;
        
        console.log(`[WebSocket] Connecting to ${wsUrl}`);
        
        try {
            this.socket = new WebSocket(wsUrl);
            this.setupEventHandlers();
        } catch (error) {
            console.error('[WebSocket] Connection error:', error);
            this.handleReconnect();
        }
    }

    /**
     * Connect to a specific Celery task
     * @param {string} taskId - Celery task ID
     */
    connectToTask(taskId) {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        const wsUrl = `${protocol}//${host}/ws/task/${taskId}/`;
        
        console.log(`[WebSocket] Connecting to task ${taskId}`);
        
        try {
            this.socket = new WebSocket(wsUrl);
            this.setupEventHandlers();
        } catch (error) {
            console.error('[WebSocket] Task connection error:', error);
        }
    }

    /**
     * Setup WebSocket event handlers
     */
    setupEventHandlers() {
        this.socket.onopen = (event) => {
            console.log('[WebSocket] Connected');
            this.connected = true;
            this.reconnectAttempts = 0;
            this.updateConnectionStatus(true);
            this.emit('connected', event);
        };

        this.socket.onclose = (event) => {
            console.log(`[WebSocket] Disconnected (code: ${event.code})`);
            this.connected = false;
            this.updateConnectionStatus(false);
            this.emit('disconnected', event);
            
            // Attempt reconnect for normal closures
            if (event.code !== 1000 && event.code !== 4001) {
                this.handleReconnect();
            }
        };

        this.socket.onerror = (error) => {
            console.error('[WebSocket] Error:', error);
            this.emit('error', error);
        };

        this.socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleMessage(data);
            } catch (error) {
                console.error('[WebSocket] Parse error:', error);
            }
        };
    }

    /**
     * Handle incoming WebSocket messages
     * @param {Object} data - Parsed message data
     */
    handleMessage(data) {
        const { type } = data;
        
        console.log(`[WebSocket] Received: ${type}`, data);
        
        switch (type) {
            case 'connection_established':
                this.emit('connection_established', data);
                break;
                
            case 'task_started':
                this.emit('task_started', data);
                this.showProgress(data.message || 'タスクを開始しました', 0);
                break;
                
            case 'task_progress':
                this.emit('task_progress', data);
                this.updateProgress(data.progress, data.message);
                break;
                
            case 'task_completed':
                this.emit('task_completed', data);
                this.showSuccess(data.message || '処理が完了しました');
                this.hideProgress();
                break;
                
            case 'task_failed':
                this.emit('task_failed', data);
                this.showError(data.message || 'エラーが発生しました');
                this.hideProgress();
                break;
                
            case 'status_update':
                this.emit('status_update', data);
                break;
                
            case 'task_status':
                this.emit('task_status', data);
                break;
                
            case 'pong':
                // Keepalive response
                break;
                
            default:
                console.log(`[WebSocket] Unknown message type: ${type}`);
                this.emit(type, data);
        }
    }

    /**
     * Handle reconnection logic
     */
    handleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.log('[WebSocket] Max reconnect attempts reached');
            this.showError('サーバーとの接続が切断されました。ページを更新してください。');
            return;
        }

        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
        
        console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
        
        setTimeout(() => {
            this.connect(this.postId);
        }, delay);
    }

    /**
     * Subscribe to specific post updates
     * @param {number} postId - Post ID to subscribe to
     */
    subscribeToPost(postId) {
        if (this.connected && this.socket) {
            this.socket.send(JSON.stringify({
                type: 'subscribe_post',
                post_id: postId
            }));
        }
    }

    /**
     * Unsubscribe from post updates
     */
    unsubscribeFromPost() {
        if (this.connected && this.socket) {
            this.socket.send(JSON.stringify({
                type: 'unsubscribe_post'
            }));
        }
    }

    /**
     * Send keepalive ping
     */
    ping() {
        if (this.connected && this.socket) {
            this.socket.send(JSON.stringify({
                type: 'ping',
                timestamp: Date.now()
            }));
        }
    }

    /**
     * Close WebSocket connection
     */
    disconnect() {
        if (this.socket) {
            this.socket.close(1000, 'Client disconnect');
            this.socket = null;
        }
    }

    /**
     * Add event listener
     * @param {string} event - Event name
     * @param {Function} callback - Callback function
     */
    on(event, callback) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, []);
        }
        this.listeners.get(event).push(callback);
    }

    /**
     * Remove event listener
     * @param {string} event - Event name
     * @param {Function} callback - Callback function
     */
    off(event, callback) {
        if (this.listeners.has(event)) {
            const callbacks = this.listeners.get(event);
            const index = callbacks.indexOf(callback);
            if (index > -1) {
                callbacks.splice(index, 1);
            }
        }
    }

    /**
     * Emit event to listeners
     * @param {string} event - Event name
     * @param {*} data - Event data
     */
    emit(event, data) {
        if (this.listeners.has(event)) {
            this.listeners.get(event).forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`[WebSocket] Listener error for ${event}:`, error);
                }
            });
        }
    }

    // ========================================
    // UI Helper Methods
    // ========================================

    /**
     * Update connection status indicator
     * @param {boolean} connected - Connection status
     */
    updateConnectionStatus(connected) {
        const statusEl = document.getElementById('connection-status');
        if (statusEl) {
            const dot = statusEl.querySelector('span:first-child');
            const text = statusEl.querySelector('span:last-child');
            
            if (connected) {
                dot.className = 'w-2 h-2 rounded-full bg-green-500 animate-pulse';
                text.textContent = 'システム稼働中';
            } else {
                dot.className = 'w-2 h-2 rounded-full bg-red-500';
                text.textContent = '接続中断';
            }
        }
    }

    /**
     * Show progress modal
     * @param {string} message - Progress message
     * @param {number} percent - Progress percentage
     */
    showProgress(message, percent = 0) {
        const modal = document.getElementById('progress-modal');
        const messageEl = document.getElementById('progress-message');
        const barEl = document.getElementById('progress-bar');
        const percentEl = document.getElementById('progress-percent');
        
        if (modal) {
            modal.classList.remove('hidden');
            if (messageEl) messageEl.textContent = message;
            if (barEl) barEl.style.width = `${percent}%`;
            if (percentEl) percentEl.textContent = `${percent}%`;
        }
    }

    /**
     * Update progress bar
     * @param {number} percent - Progress percentage
     * @param {string} message - Progress message
     */
    updateProgress(percent, message) {
        const messageEl = document.getElementById('progress-message');
        const barEl = document.getElementById('progress-bar');
        const percentEl = document.getElementById('progress-percent');
        
        if (barEl) barEl.style.width = `${percent}%`;
        if (percentEl) percentEl.textContent = `${percent}%`;
        if (messageEl && message) messageEl.textContent = message;
    }

    /**
     * Hide progress modal
     */
    hideProgress() {
        const modal = document.getElementById('progress-modal');
        if (modal) {
            setTimeout(() => {
                modal.classList.add('hidden');
            }, 500);
        }
    }

    /**
     * Show success toast
     * @param {string} message - Success message
     */
    showSuccess(message) {
        this.showToast(message, 'success');
    }

    /**
     * Show error toast
     * @param {string} message - Error message
     */
    showError(message) {
        this.showToast(message, 'error');
    }

    /**
     * Show toast notification
     * @param {string} message - Toast message
     * @param {string} type - Toast type (success, error, warning, info)
     */
    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const colors = {
            success: 'border-l-green-500 bg-white',
            error: 'border-l-red-500 bg-white',
            warning: 'border-l-yellow-500 bg-white',
            info: 'border-l-pink-500 bg-white'
        };

        const icons = {
            success: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>',
            error: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>',
            warning: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>',
            info: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>'
        };

        const iconColors = {
            success: 'text-green-600',
            error: 'text-red-600',
            warning: 'text-yellow-600',
            info: 'text-pink-600'
        };

        const toast = document.createElement('div');
        toast.className = `rounded-lg p-4 border-l-4 shadow-card ${colors[type]} animate-slide-up max-w-sm`;
        toast.innerHTML = `
            <div class="flex items-start space-x-3">
                <svg class="w-5 h-5 ${iconColors[type]} flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    ${icons[type]}
                </svg>
                <p class="text-body text-gray-700 flex-1">${message}</p>
                <button onclick="this.parentElement.parentElement.remove()" class="text-gray-400 hover:text-gray-600 transition-colors">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
        `;

        container.appendChild(toast);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100px)';
            toast.style.transition = 'all 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    }
}

// Create global instance
window.blogWS = new BlogWebSocket();

// Auto-connect on page load (if user is authenticated)
document.addEventListener('DOMContentLoaded', () => {
    // Check if user is authenticated (you can customize this check)
    const userAuthenticated = document.body.dataset.authenticated === 'true';
    
    if (userAuthenticated) {
        window.blogWS.connect();
        
        // Setup keepalive ping every 30 seconds
        setInterval(() => {
            window.blogWS.ping();
        }, 30000);
    }
});

