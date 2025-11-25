/**
 * Main JavaScript for HPB Blog Automation
 * 
 * Handles:
 * - Form submissions and validation
 * - Image upload and preview
 * - API interactions
 * - UI components
 */

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
        this.input = document.getElementById(inputId);
        this.container = document.getElementById(previewContainerId);
        this.maxImages = maxImages;
        this.images = [];
        
        if (this.input) {
            this.input.addEventListener('change', (e) => this.handleFiles(e.target.files));
        }
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
        
        // Add placeholder for remaining slots
        const remaining = this.maxImages - this.images.length;
        for (let i = 0; i < remaining; i++) {
            const div = document.createElement('div');
            div.className = 'w-24 h-24 border-2 border-dashed border-gray-300 rounded-lg flex items-center justify-center text-gray-400 cursor-pointer hover:border-pink-500 hover:text-pink-500 transition-colors';
            div.innerHTML = `
                <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path>
                </svg>
            `;
            div.onclick = () => this.input?.click();
            this.container.appendChild(div);
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
    async generate(postId) {
        try {
            // Connect WebSocket to post
            window.blogWS.connect(postId);
            window.blogWS.showProgress('AI記事生成を開始しています...', 0);
            
            const result = await api.post(`/blog/posts/${postId}/generate/`);
            
            if (result.task_id) {
                console.log('Generation task started:', result.task_id);
            }
            
            return result;
        } catch (error) {
            window.blogWS.showError('記事生成の開始に失敗しました: ' + error.message);
            throw error;
        }
    },
    
    async publish(postId) {
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
        }
    },
    
    async delete(postId) {
        if (!confirm('この記事を削除してもよろしいですか？')) {
            return;
        }
        
        try {
            await api.delete(`/blog/posts/${postId}/`);
            window.blogWS.showSuccess('記事を削除しました');
            
            // Redirect to list page
            setTimeout(() => {
                window.location.href = '/blog/posts/';
            }, 1000);
        } catch (error) {
            window.blogWS.showError('削除に失敗しました: ' + error.message);
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

