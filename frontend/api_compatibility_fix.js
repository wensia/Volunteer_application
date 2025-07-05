/**
 * API兼容性修复方案
 * 解决不同设备上API响应不一致的问题
 */

// API配置
const API_CONFIG = {
    // 多个API端点，支持故障转移
    endpoints: [
        '', // 相对路径，用于同域部署
        'http://localhost:8008', // 本地开发
        window.location.origin, // 当前域名
    ],
    timeout: 10000, // 10秒超时
    retryCount: 3, // 重试次数
    retryDelay: 1000, // 重试延迟
};

// 网络检测
class NetworkDetector {
    static async checkConnectivity() {
        try {
            const response = await fetch('/', { 
                method: 'HEAD',
                cache: 'no-cache',
                timeout: 3000
            });
            return response.ok;
        } catch {
            return false;
        }
    }
    
    static async checkCORS(url) {
        try {
            const response = await fetch(url + '/api-info', {
                method: 'GET',
                mode: 'cors',
                timeout: 5000
            });
            return response.ok;
        } catch {
            return false;
        }
    }
}

// 增强的API客户端
class EnhancedApiClient {
    constructor() {
        this.baseURL = '';
        this.initialized = false;
        this.cache = new Map();
        this.requestQueue = [];
        this.isOnline = navigator.onLine;
        
        // 监听网络状态变化
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.processQueue();
        });
        
        window.addEventListener('offline', () => {
            this.isOnline = false;
        });
    }
    
    // 自动检测最佳API端点
    async initialize() {
        if (this.initialized) return;
        
        console.log('🔍 正在检测API端点...');
        
        for (const endpoint of API_CONFIG.endpoints) {
            try {
                const testUrl = endpoint ? endpoint : window.location.origin;
                const isAccessible = await NetworkDetector.checkCORS(testUrl);
                
                if (isAccessible) {
                    this.baseURL = endpoint;
                    this.initialized = true;
                    console.log(`✅ API端点检测成功: ${testUrl}`);
                    return;
                }
            } catch (error) {
                console.log(`❌ API端点检测失败: ${endpoint}`, error);
            }
        }
        
        // 如果所有端点都失败，使用相对路径
        this.baseURL = '';
        this.initialized = true;
        console.log('⚠️ 使用相对路径作为API端点');
    }
    
    // 构建完整URL
    buildURL(path) {
        if (!path.startsWith('/')) {
            path = '/' + path;
        }
        return this.baseURL + path;
    }
    
    // 增强的fetch，支持重试和超时
    async enhancedFetch(url, options = {}) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), API_CONFIG.timeout);
        
        try {
            const response = await fetch(url, {
                ...options,
                signal: controller.signal,
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    // 添加缓存控制
                    'Cache-Control': 'no-cache',
                    ...options.headers
                }
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return response;
        } catch (error) {
            clearTimeout(timeoutId);
            throw error;
        }
    }
    
    // 带重试机制的请求
    async requestWithRetry(url, options = {}) {
        let lastError;
        
        for (let i = 0; i <= API_CONFIG.retryCount; i++) {
            try {
                return await this.enhancedFetch(url, options);
            } catch (error) {
                lastError = error;
                
                if (i < API_CONFIG.retryCount) {
                    console.log(`⏳ 请求失败，${API_CONFIG.retryDelay}ms后重试 (${i + 1}/${API_CONFIG.retryCount})`);
                    await new Promise(resolve => setTimeout(resolve, API_CONFIG.retryDelay));
                }
            }
        }
        
        throw lastError;
    }
    
    // 查询排名
    async queryRank(score, year = null) {
        await this.initialize();
        
        if (!this.isOnline) {
            throw new Error('网络连接异常，请检查网络设置');
        }
        
        const cacheKey = `rank_${score}_${year || 'default'}`;
        
        // 检查缓存
        const cached = this.cache.get(cacheKey);
        if (cached && Date.now() - cached.timestamp < 5 * 60 * 1000) {
            return cached.data;
        }
        
        const url = this.buildURL('/rank');
        const body = JSON.stringify({ score, year });
        
        try {
            const response = await this.requestWithRetry(url, {
                method: 'POST',
                body: body
            });
            
            const data = await response.json();
            
            // 缓存结果
            this.cache.set(cacheKey, {
                data,
                timestamp: Date.now()
            });
            
            return data;
            
        } catch (error) {
            // 如果是网络错误，尝试添加到队列
            if (error.name === 'AbortError' || error.name === 'TypeError') {
                return this.addToQueue('queryRank', { score, year });
            }
            throw this.handleError(error);
        }
    }
    
    // 获取统计信息
    async getStats(year = null) {
        await this.initialize();
        
        const cacheKey = `stats_${year || 'default'}`;
        const cached = this.cache.get(cacheKey);
        
        if (cached && Date.now() - cached.timestamp < 10 * 60 * 1000) {
            return cached.data;
        }
        
        const url = this.buildURL('/stats') + (year ? `?year=${year}` : '');
        
        try {
            const response = await this.requestWithRetry(url);
            const data = await response.json();
            
            this.cache.set(cacheKey, {
                data,
                timestamp: Date.now()
            });
            
            return data;
            
        } catch (error) {
            throw this.handleError(error);
        }
    }
    
    // 添加到请求队列
    addToQueue(method, params) {
        return new Promise((resolve, reject) => {
            this.requestQueue.push({
                method,
                params,
                resolve,
                reject,
                timestamp: Date.now()
            });
        });
    }
    
    // 处理队列中的请求
    async processQueue() {
        if (!this.isOnline || this.requestQueue.length === 0) {
            return;
        }
        
        const queue = [...this.requestQueue];
        this.requestQueue = [];
        
        for (const request of queue) {
            try {
                const result = await this[request.method](request.params);
                request.resolve(result);
            } catch (error) {
                request.reject(error);
            }
        }
    }
    
    // 错误处理
    handleError(error) {
        console.error('API请求错误:', error);
        
        if (error.name === 'AbortError') {
            return new Error('请求超时，请稍后重试');
        }
        
        if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
            return new Error('网络连接失败，请检查网络设置或稍后重试');
        }
        
        if (error.message.includes('HTTP 404')) {
            return new Error('API接口不存在，请联系管理员');
        }
        
        if (error.message.includes('HTTP 500')) {
            return new Error('服务器内部错误，请稍后重试');
        }
        
        if (error.message.includes('CORS')) {
            return new Error('跨域请求被阻止，请使用相同域名访问');
        }
        
        return error;
    }
    
    // 清除缓存
    clearCache() {
        this.cache.clear();
    }
    
    // 获取状态信息
    getStatus() {
        return {
            baseURL: this.baseURL,
            initialized: this.initialized,
            isOnline: this.isOnline,
            queueLength: this.requestQueue.length,
            cacheSize: this.cache.size
        };
    }
}

// 创建全局API实例
window.apiClient = new EnhancedApiClient();

// 导出给前端使用
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { EnhancedApiClient, NetworkDetector };
} 