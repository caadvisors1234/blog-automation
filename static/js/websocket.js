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
        this.connected = false;
        this.postId = null;

        // Watchdog for task monitoring
        this.isTaskRunning = false;
        this.lastMessageTime = 0;
        // Watchdog setting (60 seconds)
        this.WATCHDOG_TIMEOUT = 60000; // 60 seconds
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
        this.lastMessageTime = Date.now();
        const { type } = data;

        console.log(`[WebSocket] Received: ${type}`, data);

        const taskType = data.task_type || data.taskType || '';
        const isPublishTask = taskType === 'publish';

        switch (type) {
            case 'connection_established':
                this.emit('connection_established', data);
                break;

            case 'task_started':
                this.emit('task_started', data);
                if (isPublishTask) {
                    this.isTaskRunning = true;
                    this.startWatchdog();
                    this.showProgress(data.message || 'タスクを開始しました', 0);
                }
                break;

            case 'task_progress':
                this.emit('task_progress', data);
                if (isPublishTask) {
                    this.updateProgress(data.progress, data.message, data.step_id);
                }
                break;

            case 'task_completed':
                this.emit('task_completed', data);
                this.isTaskRunning = false;
                this.stopWatchdog();

                if (isPublishTask) {
                    // Force progress to 100% and show completion message
                    this.updateProgress(100, '投稿が完了しました！', 'STEP_SAVING');

                    // Show confetti or success effect here if desired in future

                    // Wait for user to see the 100% state before hiding
                    setTimeout(() => {
                        this.hideProgress();
                        this.showSuccess(data.message || '処理が完了しました');
                    }, 1500);
                } else {
                    this.showSuccess(data.message || '処理が完了しました');
                }
                break;

            case 'task_failed':
                this.emit('task_failed', data);
                this.isTaskRunning = false;
                this.stopWatchdog();

                this.showError(data.message || 'エラーが発生しました');
                if (isPublishTask) {
                    this.hideProgress();
                }
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
    // Watchdog Methods
    // ========================================

    /**
     * Start the task watchdog
     */
    startWatchdog() {
        this.stopWatchdog();
        this.lastMessageTime = Date.now();
        this.isTaskRunning = true;

        console.log('[WebSocket] Starting task watchdog');

        this.watchdogTimer = setInterval(() => {
            if (!this.isTaskRunning) return;

            const timeSinceLastMessage = Date.now() - this.lastMessageTime;
            if (timeSinceLastMessage > this.WATCHDOG_TIMEOUT) {
                this.handleTaskTimeout();
            }
        }, 5000); // Check every 5 seconds
    }

    /**
     * Stop the task watchdog
     */
    stopWatchdog() {
        if (this.watchdogTimer) {
            clearInterval(this.watchdogTimer);
            this.watchdogTimer = null;
        }
        this.isTaskRunning = false;
    }

    /**
     * Handle task timeout event
     */
    handleTaskTimeout() {
        console.warn('[WebSocket] Task timeout detected');
        this.stopWatchdog();

        // Update UI to show error in modal
        const titleEl = document.getElementById('progress-title');
        const messageEl = document.getElementById('progress-message');
        const barEl = document.getElementById('progress-bar');

        if (titleEl) {
            titleEl.textContent = '接続エラー';
            titleEl.classList.add('text-red-600');
        }

        if (messageEl) {
            messageEl.textContent = 'サーバーからの応答がありません。処理が停止した可能性があります。';
            messageEl.classList.add('text-red-600');
        }

        if (barEl) {
            barEl.classList.remove('bg-pink-500');
            barEl.classList.add('bg-red-500');
        }

        this.showError('処理が長時間停止しています。通信環境を確認するか、ページを更新してください。');
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
     * Show progress modal with advanced UI
     * @param {string} message - Progress message
     * @param {number} percent - Progress percentage
     */
    showProgress(message, percent = 0) {
        const modal = document.getElementById('progress-modal');
        const modalContent = document.getElementById('progress-modal-content');
        const messageEl = document.getElementById('progress-message');
        const titleEl = document.getElementById('progress-title');
        const barEl = document.getElementById('progress-bar');
        const percentEl = document.getElementById('progress-percent');
        const cheerEl = document.getElementById('cheer-message');

        if (modal) {
            // Show modal with animation
            modal.classList.remove('hidden');
            // Force reflow
            void modal.offsetWidth;
            modal.classList.remove('opacity-0');

            if (modalContent) {
                modalContent.classList.remove('opacity-0', 'scale-95');
                modalContent.classList.add('opacity-100', 'scale-100');
            }

            if (titleEl) titleEl.textContent = '処理中...';
            if (messageEl) messageEl.textContent = message;
            if (barEl) barEl.style.width = `${percent}%`;
            if (percentEl) percentEl.textContent = `${percent}%`;

            // Set initial random cheer message
            if (cheerEl && window.waitingContent) {
                this.updateCheerMessage();
                // Start rotation
                this.startMessageRotation();
            }

            // Set Step 1 active
            this.updateStep(percent < 10 ? 'STEP_PREPARING' : null);
        }
    }

    /**
     * Update progress bar and steps
     * @param {number} percent - Progress percentage
     * @param {string} message - Progress message
     * @param {string} stepId - Current Step ID (optional, from server)
     */
    updateProgress(percent, message, stepId = null) {
        const messageEl = document.getElementById('progress-message');
        const barEl = document.getElementById('progress-bar');
        const percentEl = document.getElementById('progress-percent');

        if (barEl) barEl.style.width = `${percent}%`;
        if (percentEl) percentEl.textContent = `${percent}%`;

        // Update main status message
        if (messageEl && message) {
            messageEl.textContent = message;

            // Add fade animation effect to text change
            messageEl.classList.remove('animate-pulse');
            void messageEl.offsetWidth;
            messageEl.classList.add('animate-pulse');
        }

        // Infer step from percentage if stepId is not provided
        if (!stepId) {
            if (percent < 20) stepId = 'STEP_PREPARING';
            else if (percent < 40) stepId = 'STEP_AUTH';
            else if (percent < 80) stepId = 'STEP_POSTING';
            else stepId = 'STEP_SAVING';
        }

        this.updateStep(stepId);
    }

    /**
     * Update active step indicator
     * @param {string} stepId - Step ID to activate
     */
    updateStep(stepId) {
        if (!stepId) return;

        const steps = ['STEP_PREPARING', 'STEP_AUTH', 'STEP_POSTING', 'STEP_SAVING'];
        const currentIndex = steps.indexOf(stepId);

        document.querySelectorAll('.step-item').forEach(el => {
            const elStep = el.dataset.step;
            const elIndex = steps.indexOf(elStep);
            const dot = el.querySelector('span');

            // Reset classes
            el.classList.remove('text-pink-600', 'font-bold', 'text-gray-400', 'text-gray-800');
            dot.classList.remove('bg-pink-500', 'bg-gray-200', 'bg-green-500', 'animate-pulse');

            if (elIndex < currentIndex) {
                // Completed
                el.classList.add('text-pink-600');
                dot.classList.add('bg-pink-500');
                // Checkmark could be added here
            } else if (elIndex === currentIndex) {
                // Current
                el.classList.add('text-gray-800', 'font-bold');
                dot.classList.add('bg-pink-500', 'animate-pulse');
            } else {
                // Future
                el.classList.add('text-gray-400');
                dot.classList.add('bg-gray-200');
            }
        });
    }

    /**
     * Start rotating cheer messages
     */
    startMessageRotation() {
        // Clear existing interval
        if (this.messageInterval) clearInterval(this.messageInterval);

        this.messageInterval = setInterval(() => {
            this.updateCheerMessage();
        }, 6000); // Rotate every 6 seconds
    }

    /**
     * Update the cheer message with animation
     */
    updateCheerMessage() {
        const cheerEl = document.getElementById('cheer-message');
        if (!cheerEl || !window.waitingContent) return;

        // Fade out
        cheerEl.classList.add('opacity-0', 'translate-y-2');

        setTimeout(() => {
            // Change text
            cheerEl.textContent = window.waitingContent.getRandomCheer();

            // Fade in
            cheerEl.classList.remove('opacity-0', 'translate-y-2');
        }, 500);
    }

    /**
     * Hide progress panel with animation
     */
    hideProgress() {
        const modal = document.getElementById('progress-modal');
        const modalContent = document.getElementById('progress-modal-content');

        // Stop rotation
        if (this.messageInterval) {
            clearInterval(this.messageInterval);
            this.messageInterval = null;
        }

        if (!modal) return;

        // Fade out animation
        modal.classList.add('opacity-0');
        if (modalContent) {
            modalContent.classList.remove('opacity-100', 'scale-100');
            modalContent.classList.add('opacity-0', 'scale-95');
        }

        setTimeout(() => {
            modal.classList.add('hidden');
            // Reset state
            const barEl = document.getElementById('progress-bar');
            const percentEl = document.getElementById('progress-percent');
            if (barEl) barEl.style.width = '0%';
            if (percentEl) percentEl.textContent = '0%';
        }, 300);
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

        const signature = `${type}:${message}`;
        const existing = Array.from(container.children).find(el => el.dataset.toastKey === signature);
        if (existing) {
            // Reset timer by removing and re-adding fade animation
            existing.style.opacity = '1';
            existing.style.transform = 'translateX(0)';
            existing.dataset.toastTimestamp = Date.now();
            return;
        }

        // Limit total toasts
        const maxToasts = 3;
        while (container.children.length >= maxToasts) {
            container.removeChild(container.firstChild);
        }

        const toast = document.createElement('div');
        toast.className = `rounded-lg p-4 border-l-4 shadow-card ${colors[type]} animate-slide-up max-w-sm`;
        toast.dataset.toastKey = signature;
        toast.dataset.toastTimestamp = Date.now();
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
    // Check if user is authenticated
    const userAuthenticated = document.body.dataset.authenticated === 'true';

    if (userAuthenticated) {
        window.blogWS.connect();

        // Setup keepalive ping every 30 seconds
        setInterval(() => {
            window.blogWS.ping();
        }, 30000);
    }
});
