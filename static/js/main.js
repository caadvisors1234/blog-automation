/**
 * Main JavaScript for HPB Blog Automation
 *
 * Handles:
 * - Form submissions and validation
 * - Image upload and preview
 * - API interactions
 * - UI components
 * - Custom dialogs and toasts
 */

// ========================================
// Custom Dialog System
// ========================================

const dialog = {
    modal: null,
    backdrop: null,
    content: null,
    icon: null,
    title: null,
    message: null,
    actions: null,
    resolvePromise: null,

    init() {
        this.modal = document.getElementById('dialog-modal');
        this.backdrop = document.getElementById('dialog-backdrop');
        this.content = document.getElementById('dialog-content');
        this.icon = document.getElementById('dialog-icon');
        this.title = document.getElementById('dialog-title');
        this.message = document.getElementById('dialog-message');
        this.actions = document.getElementById('dialog-actions');

        if (this.backdrop) {
            this.backdrop.addEventListener('click', () => this.close(false));
        }

        // Close on Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.modal && !this.modal.classList.contains('hidden')) {
                this.close(false);
            }
        });
    },

    show(options) {
        if (!this.modal) this.init();
        if (!this.modal) return Promise.resolve(false);

        const {
            type = 'confirm', // 'confirm', 'alert', 'danger', 'success'
            title = '',
            message = '',
            confirmText = 'OK',
            cancelText = 'キャンセル',
            showCancel = true
        } = options;

        // Set icon based on type
        const iconHTML = {
            confirm: `<svg class="w-6 h-6 text-pink-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>`,
            alert: `<svg class="w-6 h-6 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>`,
            danger: `<svg class="w-6 h-6 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
            </svg>`,
            success: `<svg class="w-6 h-6 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>`
        };

        const iconBgClass = {
            confirm: 'bg-pink-50',
            alert: 'bg-blue-50',
            danger: 'bg-red-50',
            success: 'bg-green-50'
        };

        const confirmBtnClass = {
            confirm: 'text-pink-600 hover:bg-pink-50',
            alert: 'text-blue-600 hover:bg-blue-50',
            danger: 'text-red-600 hover:bg-red-50',
            success: 'text-green-600 hover:bg-green-50'
        };

        // Update icon
        this.icon.className = `w-12 h-12 mx-auto rounded-full flex items-center justify-center ${iconBgClass[type]}`;
        this.icon.innerHTML = iconHTML[type];

        // Update text
        this.title.textContent = title;
        this.message.textContent = message;

        // Update actions
        let actionsHTML = '';
        if (showCancel) {
            actionsHTML += `<button id="dialog-cancel" class="flex-1 py-3.5 text-body font-medium text-gray-600 hover:bg-gray-50 transition-colors">${cancelText}</button>`;
        }
        actionsHTML += `<button id="dialog-confirm" class="flex-1 py-3.5 text-body font-medium ${confirmBtnClass[type]} transition-colors ${showCancel ? 'border-l border-gray-100' : ''}">${confirmText}</button>`;
        this.actions.innerHTML = actionsHTML;

        // Show modal
        this.modal.classList.remove('hidden');
        this.modal.setAttribute('aria-hidden', 'false');
        document.body.style.overflow = 'hidden';

        // Focus confirm button
        setTimeout(() => {
            document.getElementById('dialog-confirm')?.focus();
        }, 100);

        return new Promise((resolve) => {
            this.resolvePromise = resolve;

            document.getElementById('dialog-confirm')?.addEventListener('click', () => {
                this.close(true);
            });

            document.getElementById('dialog-cancel')?.addEventListener('click', () => {
                this.close(false);
            });
        });
    },

    close(result) {
        if (!this.modal) return;

        this.modal.classList.add('hidden');
        this.modal.setAttribute('aria-hidden', 'true');
        document.body.style.overflow = '';

        if (this.resolvePromise) {
            this.resolvePromise(result);
            this.resolvePromise = null;
        }
    },

    // Convenience methods
    confirm(title, message, options = {}) {
        return this.show({ type: 'confirm', title, message, showCancel: true, ...options });
    },

    alert(title, message, options = {}) {
        return this.show({ type: 'alert', title, message, showCancel: false, confirmText: 'OK', ...options });
    },

    danger(title, message, options = {}) {
        return this.show({ type: 'danger', title, message, showCancel: true, confirmText: '削除', ...options });
    },

    success(title, message, options = {}) {
        return this.show({ type: 'success', title, message, showCancel: false, confirmText: 'OK', ...options });
    }
};

// ========================================
// Toast Notification System
// ========================================

const toast = {
    container: null,

    init() {
        this.container = document.getElementById('toast-container');
    },

    show(message, type = 'info', duration = 4000) {
        if (!this.container) this.init();
        if (!this.container) return;

        const iconPaths = {
            success: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
            error: 'M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
            warning: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z',
            info: 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z'
        };

        const iconColors = {
            success: 'text-green-500',
            error: 'text-red-500',
            warning: 'text-yellow-500',
            info: 'text-blue-500'
        };

        // Build toast element safely to prevent XSS
        const toastEl = document.createElement('div');
        toastEl.className = 'bg-white rounded-lg shadow-card-hover p-4 flex items-start space-x-3 animate-slide-up';

        // Icon container
        const iconContainer = document.createElement('div');
        iconContainer.className = 'flex-shrink-0';
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('class', `w-5 h-5 ${iconColors[type] || iconColors.info}`);
        svg.setAttribute('fill', 'none');
        svg.setAttribute('stroke', 'currentColor');
        svg.setAttribute('viewBox', '0 0 24 24');
        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('stroke-linecap', 'round');
        path.setAttribute('stroke-linejoin', 'round');
        path.setAttribute('stroke-width', '2');
        path.setAttribute('d', iconPaths[type] || iconPaths.info);
        svg.appendChild(path);
        iconContainer.appendChild(svg);

        // Message container - use textContent to prevent XSS
        const messageContainer = document.createElement('div');
        messageContainer.className = 'flex-1 min-w-0';
        const messageP = document.createElement('p');
        messageP.className = 'text-body text-gray-900';
        messageP.textContent = message; // Safe: textContent escapes HTML
        messageContainer.appendChild(messageP);

        // Close button
        const closeBtn = document.createElement('button');
        closeBtn.className = 'flex-shrink-0 p-1 text-gray-400 hover:text-gray-600 rounded transition-colors';
        closeBtn.setAttribute('aria-label', '閉じる');
        const closeSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        closeSvg.setAttribute('class', 'w-4 h-4');
        closeSvg.setAttribute('fill', 'none');
        closeSvg.setAttribute('stroke', 'currentColor');
        closeSvg.setAttribute('viewBox', '0 0 24 24');
        const closePath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        closePath.setAttribute('stroke-linecap', 'round');
        closePath.setAttribute('stroke-linejoin', 'round');
        closePath.setAttribute('stroke-width', '2');
        closePath.setAttribute('d', 'M6 18L18 6M6 6l12 12');
        closeSvg.appendChild(closePath);
        closeBtn.appendChild(closeSvg);

        // Assemble toast
        toastEl.appendChild(iconContainer);
        toastEl.appendChild(messageContainer);
        toastEl.appendChild(closeBtn);

        // Close button handler
        closeBtn.addEventListener('click', () => {
            this.remove(toastEl);
        });

        this.container.appendChild(toastEl);

        // Auto remove
        if (duration > 0) {
            setTimeout(() => this.remove(toastEl), duration);
        }

        return toastEl;
    },

    remove(toastEl) {
        if (!toastEl || !toastEl.parentNode) return;

        toastEl.style.opacity = '0';
        toastEl.style.transform = 'translateX(100%)';
        toastEl.style.transition = 'all 0.3s ease';

        setTimeout(() => {
            toastEl.remove();
        }, 300);
    },

    success(message, duration) {
        return this.show(message, 'success', duration);
    },

    error(message, duration) {
        return this.show(message, 'error', duration);
    },

    warning(message, duration) {
        return this.show(message, 'warning', duration);
    },

    info(message, duration) {
        return this.show(message, 'info', duration);
    }
};

// ========================================
// Image Lightbox System
// ========================================

const lightbox = {
    modal: null,
    backdrop: null,
    image: null,
    closeBtn: null,
    prevBtn: null,
    nextBtn: null,
    counter: null,
    images: [],
    currentIndex: 0,

    init() {
        this.modal = document.getElementById('lightbox-modal');
        this.backdrop = document.getElementById('lightbox-backdrop');
        this.image = document.getElementById('lightbox-image');
        this.closeBtn = document.getElementById('lightbox-close');
        this.prevBtn = document.getElementById('lightbox-prev');
        this.nextBtn = document.getElementById('lightbox-next');
        this.counter = document.getElementById('lightbox-counter');

        if (!this.modal) return;

        // Event listeners
        this.backdrop?.addEventListener('click', () => this.close());
        this.closeBtn?.addEventListener('click', () => this.close());
        this.prevBtn?.addEventListener('click', () => this.prev());
        this.nextBtn?.addEventListener('click', () => this.next());

        // Keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (this.modal.classList.contains('hidden')) return;

            switch (e.key) {
                case 'Escape':
                    this.close();
                    break;
                case 'ArrowLeft':
                    this.prev();
                    break;
                case 'ArrowRight':
                    this.next();
                    break;
            }
        });
    },

    open(imageSrc, imageAlt = '', allImages = null, startIndex = 0) {
        if (!this.modal) this.init();
        if (!this.modal) return;

        // Set images array for navigation
        if (allImages && Array.isArray(allImages)) {
            this.images = allImages;
            this.currentIndex = startIndex;
        } else {
            this.images = [{ src: imageSrc, alt: imageAlt }];
            this.currentIndex = 0;
        }

        this.showImage(this.currentIndex);

        // Show modal
        this.modal.classList.remove('hidden');
        this.modal.setAttribute('aria-hidden', 'false');
        document.body.style.overflow = 'hidden';

        // Update navigation buttons visibility
        this.updateNavigation();
    },

    showImage(index) {
        if (index < 0 || index >= this.images.length) return;

        const img = this.images[index];
        this.image.src = img.src;
        this.image.alt = img.alt || `画像 ${index + 1}`;
        this.currentIndex = index;

        // Update counter
        if (this.images.length > 1) {
            this.counter.textContent = `${index + 1} / ${this.images.length}`;
            this.counter.classList.remove('hidden');
        } else {
            this.counter.classList.add('hidden');
        }

        this.updateNavigation();
    },

    updateNavigation() {
        if (this.images.length <= 1) {
            this.prevBtn?.classList.add('hidden');
            this.nextBtn?.classList.add('hidden');
            return;
        }

        // Show/hide prev button
        if (this.currentIndex > 0) {
            this.prevBtn?.classList.remove('hidden');
        } else {
            this.prevBtn?.classList.add('hidden');
        }

        // Show/hide next button
        if (this.currentIndex < this.images.length - 1) {
            this.nextBtn?.classList.remove('hidden');
        } else {
            this.nextBtn?.classList.add('hidden');
        }
    },

    prev() {
        if (this.currentIndex > 0) {
            this.showImage(this.currentIndex - 1);
        }
    },

    next() {
        if (this.currentIndex < this.images.length - 1) {
            this.showImage(this.currentIndex + 1);
        }
    },

    close() {
        if (!this.modal) return;

        this.modal.classList.add('hidden');
        this.modal.setAttribute('aria-hidden', 'true');
        document.body.style.overflow = '';
        this.images = [];
        this.currentIndex = 0;
    }
};

// Make dialog, toast, and lightbox globally available
window.dialog = dialog;
window.toast = toast;
window.lightbox = lightbox;

// ========================================
// CSRF Token Helper
// ========================================

function getCSRFToken() {
    const cookieValue = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken='))
        ?.split('=')[1];
    return cookieValue;
}

// ========================================
// API Helper
// ========================================

function redirectToLoginIfNeeded(response) {
    if (response && response.status === 401) {
        // Avoid redirect loop when already on login page
        if (window.location.pathname.startsWith('/accounts/login')) {
            return;
        }
        const next = encodeURIComponent(
            window.location.pathname + window.location.search + window.location.hash
        );
        window.location.href = `/accounts/login/?next=${next}`;
    }
}

const api = {
    baseUrl: '/api',
    
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const headers = {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken(),
            ...options.headers
        };
        
        try {
            const response = await fetch(url, {
                ...options,
                headers
            });

            if (response.status === 401) {
                redirectToLoginIfNeeded(response);
            }
            
            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.detail || `HTTP ${response.status}`);
            }
            
            return response.json();
        } catch (error) {
            console.error(`API Error [${endpoint}]:`, error);
            throw error;
        }
    },
    
    get(endpoint) {
        return this.request(endpoint, { method: 'GET' });
    },
    
    post(endpoint, data) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },
    
    patch(endpoint, data) {
        return this.request(endpoint, {
            method: 'PATCH',
            body: JSON.stringify(data)
        });
    },
    
    delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    },
    
    // File upload (multipart/form-data)
    async upload(endpoint, formData) {
        const url = `${this.baseUrl}${endpoint}`;
        
        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCSRFToken()
                },
                body: formData
            });

            if (response.status === 401) {
                redirectToLoginIfNeeded(response);
            }
            
            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.detail || `HTTP ${response.status}`);
            }
            
            return response.json();
        } catch (error) {
            console.error(`Upload Error [${endpoint}]:`, error);
            throw error;
        }
    }
};

// ========================================
// Image Preview Handler
// ========================================

class ImagePreview {
    constructor(inputId, previewContainerId, maxImages = 4) {
        this.inputId = inputId;
        this.input = document.getElementById(inputId);
        this.container = document.getElementById(previewContainerId);
        this.maxImages = maxImages;
        this.images = [];

        if (this.input) {
            this.input.addEventListener('change', (e) => this.handleFiles(e.target.files));
        }

        // Setup drag and drop
        this.setupDragAndDrop();
    }

    setupDragAndDrop() {
        if (!this.container) return;

        // Prevent default drag behaviors on the entire container
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            this.container.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            });
        });

        // Highlight drop area when dragging over
        ['dragenter', 'dragover'].forEach(eventName => {
            this.container.addEventListener(eventName, () => {
                this.container.classList.add('drag-over');
            });
        });

        ['dragleave', 'drop'].forEach(eventName => {
            this.container.addEventListener(eventName, () => {
                this.container.classList.remove('drag-over');
            });
        });

        // Handle dropped files
        this.container.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            this.handleFiles(files);
        });
    }
    
    handleFiles(files) {
        const remainingSlots = this.maxImages - this.images.length;
        const filesToAdd = Array.from(files).slice(0, remainingSlots);
        
        filesToAdd.forEach(file => {
            if (file.type.startsWith('image/')) {
                this.addImage(file);
            }
        });
        
        this.updateInput();
    }
    
    addImage(file) {
        const reader = new FileReader();
        
        reader.onload = (e) => {
            const id = Date.now() + Math.random();
            this.images.push({ id, file, preview: e.target.result });
            this.render();
        };
        
        reader.readAsDataURL(file);
    }
    
    removeImage(id) {
        this.images = this.images.filter(img => img.id !== id);
        this.render();
        this.updateInput();
    }
    
    updateInput() {
        // Create a new DataTransfer to update the input files
        const dt = new DataTransfer();
        this.images.forEach(img => dt.items.add(img.file));
        this.input.files = dt.files;
    }
    
    render() {
        if (!this.container) return;
        
        this.container.innerHTML = '';
        
        this.images.forEach((img, index) => {
            const div = document.createElement('div');
            div.className = 'relative group';
            div.innerHTML = `
                <img src="${img.preview}" alt="Preview ${index + 1}" 
                     class="w-24 h-24 object-cover rounded-lg border border-gray-200">
                <div class="absolute -top-2 -left-2 w-6 h-6 bg-pink-500 rounded-full flex items-center justify-center text-xs font-bold text-white">
                    ${index + 1}
                </div>
                <button type="button" 
                        onclick="imagePreview.removeImage(${img.id})"
                        class="absolute -top-2 -right-2 w-6 h-6 bg-red-500 rounded-full flex items-center justify-center text-white opacity-0 group-hover:opacity-100 transition-opacity">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            `;
            this.container.appendChild(div);
        });
        
        // Add placeholder for remaining slots (labels keep file dialog reliable)
        const remaining = this.maxImages - this.images.length;
        for (let i = 0; i < remaining; i++) {
            const label = document.createElement('label');
            label.setAttribute('for', this.inputId);
            label.setAttribute('role', 'button');
            label.setAttribute('aria-label', '画像を追加');
            label.className = 'w-24 h-24 border-2 border-dashed border-gray-300 rounded-lg flex items-center justify-center text-gray-400 cursor-pointer hover:border-pink-500 hover:text-pink-500 transition-colors';
            label.innerHTML = `
                <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path>
                </svg>
            `;
            this.container.appendChild(label);
        }
    }
    
    getFiles() {
        return this.images.map(img => img.file);
    }
    
    clear() {
        this.images = [];
        this.render();
        this.updateInput();
    }
}

// ========================================
// Form Validation
// ========================================

class FormValidator {
    constructor(formId) {
        this.form = document.getElementById(formId);
        this.errors = {};
        
        if (this.form) {
            this.form.addEventListener('submit', (e) => this.handleSubmit(e));
        }
    }
    
    addRule(fieldName, rules) {
        if (!this.rules) this.rules = {};
        this.rules[fieldName] = rules;
    }
    
    validate() {
        this.errors = {};
        
        if (!this.rules) return true;
        
        for (const [fieldName, rules] of Object.entries(this.rules)) {
            const field = this.form.querySelector(`[name="${fieldName}"]`);
            if (!field) continue;
            
            const value = field.value.trim();
            
            for (const rule of rules) {
                if (rule.required && !value) {
                    this.errors[fieldName] = rule.message || '必須項目です';
                    break;
                }
                
                if (rule.minLength && value.length < rule.minLength) {
                    this.errors[fieldName] = rule.message || `${rule.minLength}文字以上で入力してください`;
                    break;
                }
                
                if (rule.maxLength && value.length > rule.maxLength) {
                    this.errors[fieldName] = rule.message || `${rule.maxLength}文字以内で入力してください`;
                    break;
                }
                
                if (rule.pattern && !rule.pattern.test(value)) {
                    this.errors[fieldName] = rule.message || '形式が正しくありません';
                    break;
                }
                
                if (rule.custom && !rule.custom(value)) {
                    this.errors[fieldName] = rule.message || '入力内容を確認してください';
                    break;
                }
            }
        }
        
        this.showErrors();
        return Object.keys(this.errors).length === 0;
    }
    
    showErrors() {
        // Clear previous errors
        this.form.querySelectorAll('.field-error').forEach(el => el.remove());
        this.form.querySelectorAll('.input-error').forEach(el => el.classList.remove('input-error', 'border-red-500'));
        
        // Show new errors
        for (const [fieldName, message] of Object.entries(this.errors)) {
            const field = this.form.querySelector(`[name="${fieldName}"]`);
            if (!field) continue;
            
            field.classList.add('input-error', 'border-red-500');
            
            const errorEl = document.createElement('p');
            errorEl.className = 'field-error text-red-500 text-sm mt-1';
            errorEl.textContent = message;
            field.parentNode.appendChild(errorEl);
        }
    }
    
    handleSubmit(e) {
        if (!this.validate()) {
            e.preventDefault();
        }
    }
}

// ========================================
// Blog Post Actions
// ========================================

const blogActions = {
    generateInProgress: false,
    publishInProgress: false,

    async generate(postId) {
        if (this.generateInProgress) {
            window.blogWS.showError('AI記事生成は既に進行中です。完了までお待ちください。');
            return;
        }
        this.generateInProgress = true;
        try {
            // Connect WebSocket to post
            window.blogWS.connect(postId);
            
            const result = await api.post(`/blog/posts/${postId}/generate/`);
            
            if (result.task_id) {
                console.log('Generation task started:', result.task_id);
                // Redirect to generating page
                window.location.href = `/blog/posts/${postId}/generating/`;
            }
            
            return result;
        } catch (error) {
            window.blogWS.showError('記事生成の開始に失敗しました: ' + error.message);
            throw error;
        } finally {
            this.generateInProgress = false;
        }
    },
    
    async publish(postId) {
        if (this.publishInProgress) {
            window.blogWS.showError('投稿処理は既に開始されています。完了までお待ちください。');
            return;
        }
        this.publishInProgress = true;
        try {
            // Connect WebSocket to post
            window.blogWS.connect(postId);
            window.blogWS.showProgress('SALON BOARDへの投稿を開始しています...', 0);
            
            const result = await api.post(`/blog/posts/${postId}/publish/`);
            
            if (result.task_id) {
                console.log('Publish task started:', result.task_id);
            }
            
            return result;
        } catch (error) {
            window.blogWS.showError('投稿の開始に失敗しました: ' + error.message);
            throw error;
        } finally {
            this.publishInProgress = false;
        }
    },
    
    async delete(postId) {
        const confirmed = await window.dialog.danger(
            '記事を削除',
            'この記事を削除してもよろしいですか？この操作は取り消せません。',
            { confirmText: '削除' }
        );

        if (!confirmed) {
            return;
        }

        try {
            await api.delete(`/blog/posts/${postId}/`);
            window.toast.success('記事を削除しました');

            // Redirect to list page
            setTimeout(() => {
                window.location.href = '/blog/posts/';
            }, 1000);
        } catch (error) {
            window.toast.error('削除に失敗しました: ' + error.message);
            throw error;
        }
    }
};

// ========================================
// Statistics Loader
// ========================================

async function loadDashboardStats() {
    try {
        const stats = await api.get('/blog/posts/stats/');
        
        // Update stat cards
        const elements = {
            'total-posts': stats.total,
            'monthly-posts': stats.this_month,
            'success-rate': `${stats.success_rate}%`,
            'generating-count': stats.generating
        };
        
        for (const [id, value] of Object.entries(elements)) {
            const el = document.getElementById(id);
            if (el) el.textContent = value;
        }
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

// ========================================
// Utility Functions
// ========================================

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('ja-JP', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function truncateText(text, maxLength = 100) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// ========================================
// Copy to Clipboard
// ========================================

async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        window.blogWS.showSuccess('クリップボードにコピーしました');
    } catch (error) {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        window.blogWS.showSuccess('クリップボードにコピーしました');
    }
}

// ========================================
// Initialize on DOM Load
// ========================================

document.addEventListener('DOMContentLoaded', () => {
    // Initialize image preview if element exists
    if (document.getElementById('image-input')) {
        window.imagePreview = new ImagePreview('image-input', 'image-preview-container', 4);
        window.imagePreview.render();
    }
    
    // Load dashboard stats if on dashboard page
    if (document.getElementById('dashboard-stats')) {
        loadDashboardStats();
    }
    
    // Setup confirm dialogs for dangerous actions
    document.querySelectorAll('[data-confirm]').forEach(el => {
        el.addEventListener('click', (e) => {
            if (!confirm(el.dataset.confirm)) {
                e.preventDefault();
            }
        });
    });
});
