/* 主JavaScript文件 - 自动化流程系统 */

// 深色模式切换
function toggleDarkMode() {
    document.body.classList.toggle('dark-theme');
    const isDarkMode = document.body.classList.contains('dark-theme');
    localStorage.setItem('dark_mode', isDarkMode ? 'enabled' : 'disabled');
}

// 加载用户深色模式偏好
function loadUserThemePreference() {
    const darkMode = localStorage.getItem('dark_mode');
    if (darkMode === 'enabled') {
        document.body.classList.add('dark-theme');
    }
}

// 通用消息提示
function showToast(message, type = 'info', duration = 3000) {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type} show`;
    toast.innerText = message;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.classList.add('hide');
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 500);
    }, duration);
}

// 确认对话框
function confirmAction(message, onConfirm, onCancel) {
    const confirmed = window.confirm(message);
    if (confirmed && typeof onConfirm === 'function') {
        onConfirm();
    } else if (!confirmed && typeof onCancel === 'function') {
        onCancel();
    }
}

// AJAX请求封装
function ajaxRequest(url, method = 'GET', data = null, onSuccess, onError) {
    const xhr = new XMLHttpRequest();
    xhr.open(method, url, true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
    
    xhr.onload = function() {
        if (xhr.status >= 200 && xhr.status < 300) {
            if (typeof onSuccess === 'function') {
                onSuccess(JSON.parse(xhr.responseText));
            }
        } else {
            if (typeof onError === 'function') {
                onError(xhr.statusText);
            }
        }
    };
    
    xhr.onerror = function() {
        if (typeof onError === 'function') {
            onError('请求失败');
        }
    };
    
    if (data) {
        xhr.send(JSON.stringify(data));
    } else {
        xhr.send();
    }
}

// 文件类型图标映射
const fileIconMap = {
    'pdf': 'bi-file-earmark-pdf',
    'doc': 'bi-file-earmark-word',
    'docx': 'bi-file-earmark-word',
    'xls': 'bi-file-earmark-excel',
    'xlsx': 'bi-file-earmark-excel',
    'ppt': 'bi-file-earmark-ppt',
    'pptx': 'bi-file-earmark-ppt',
    'txt': 'bi-file-earmark-text',
    'md': 'bi-markdown',
    'ofd': 'bi-file-earmark'
};

// 获取文件类型图标
function getFileIcon(filename) {
    const extension = filename.split('.').pop().toLowerCase();
    return fileIconMap[extension] || 'bi-file-earmark';
}

// 格式化文件大小
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// 格式化日期时间
function formatDateTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// 初始化文件上传区域拖放功能
function initFileDropZone(dropZoneId, inputId, onFilesSelected) {
    const dropZone = document.getElementById(dropZoneId);
    const fileInput = document.getElementById(inputId);
    
    if (!dropZone || !fileInput) return;
    
    dropZone.addEventListener('click', () => {
        fileInput.click();
    });
    
    fileInput.addEventListener('change', () => {
        if (typeof onFilesSelected === 'function') {
            onFilesSelected(fileInput.files);
        }
    });
    
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
        });
    });
    
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.add('drag-over');
        });
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.remove('drag-over');
        });
    });
    
    dropZone.addEventListener('drop', (e) => {
        if (typeof onFilesSelected === 'function') {
            onFilesSelected(e.dataTransfer.files);
        }
    });
}

// 处理导航菜单响应式行为
function initResponsiveNavigation() {
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('sidebar');
    const content = document.getElementById('content');
    
    if (!sidebarToggle || !sidebar || !content) return;
    
    sidebarToggle.addEventListener('click', () => {
        sidebar.classList.toggle('active');
        content.classList.toggle('active');
    });
    
    // 在小屏幕上点击导航菜单外部时收起菜单
    document.addEventListener('click', (e) => {
        const isSmallScreen = window.innerWidth <= 768;
        const clickedOutsideSidebar = !sidebar.contains(e.target) && e.target !== sidebarToggle;
        
        if (isSmallScreen && sidebar.classList.contains('active') && clickedOutsideSidebar) {
            sidebar.classList.remove('active');
            content.classList.remove('active');
        }
    });
}

// 刷新验证码
function refreshCaptcha(captchaImgId) {
    const captchaImg = document.getElementById(captchaImgId);
    if (captchaImg) {
        captchaImg.src = '/api/auth/captcha?' + new Date().getTime();
    }
}

// 文档就绪时执行
document.addEventListener('DOMContentLoaded', () => {
    loadUserThemePreference();
    initResponsiveNavigation();
    
    // 初始化验证码点击刷新功能
    const captchaImg = document.getElementById('captchaImage');
    if (captchaImg) {
        captchaImg.addEventListener('click', () => {
            refreshCaptcha('captchaImage');
        });
    }
}); 