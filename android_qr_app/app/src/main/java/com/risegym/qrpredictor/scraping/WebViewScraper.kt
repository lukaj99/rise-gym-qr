package com.risegym.qrpredictor.scraping

import android.annotation.SuppressLint
import android.content.Context
import android.graphics.Bitmap
import android.util.Log
import android.webkit.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import kotlin.coroutines.resume

/**
 * WebView-based scraper for JavaScript-heavy pages
 * Fallback option when OkHttp scraping fails
 */
class WebViewScraper(private val context: Context) : WebScraperInterface {
    
    companion object {
        private const val TAG = "WebViewScraper"
        private const val LOGIN_URL = "https://risegyms.ez-runner.com/Account/Login.aspx"
        private const val DASHBOARD_URL = "https://risegyms.ez-runner.com/Account/Dashboard.aspx"
        private const val TIMEOUT_MS = 30000L
    }
    
    private var webView: WebView? = null
    private val cookieManager = CookieManager.getInstance()
    private val sharedPrefs = context.getSharedPreferences("rise_gym_webview", Context.MODE_PRIVATE)
    
    init {
        // Enable cookies for WebView
        cookieManager.setAcceptCookie(true)
        cookieManager.setAcceptThirdPartyCookies(webView, true)
    }
    
    @SuppressLint("SetJavaScriptEnabled")
    override suspend fun login(credentials: WebScraperInterface.Credentials): Boolean = withContext(Dispatchers.Main) {
        try {
            Log.d(TAG, "Starting WebView login...")
            
            return@withContext suspendCancellableCoroutine { continuation ->
                webView = WebView(context).apply {
                    settings.apply {
                        javaScriptEnabled = true
                        domStorageEnabled = true
                        cacheMode = WebSettings.LOAD_NO_CACHE
                        userAgentString = "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
                    }
                    
                    webViewClient = object : WebViewClient() {
                        override fun onPageFinished(view: WebView?, url: String?) {
                            Log.d(TAG, "Page loaded: $url")
                            
                            when {
                                url?.contains("Login") == true -> {
                                    // Fill and submit login form
                                    val js = """
                                        javascript:(function() {
                                            // Wait for form to be ready
                                            setTimeout(function() {
                                                var username = document.getElementById('MainContent_LoginUser_UserName');
                                                var password = document.getElementById('MainContent_LoginUser_Password');
                                                var submit = document.getElementById('MainContent_LoginUser_LoginButton');
                                                
                                                if (username && password && submit) {
                                                    username.value = '${credentials.username}';
                                                    password.value = '${credentials.password}';
                                                    submit.click();
                                                } else {
                                                    console.log('Login form not found');
                                                }
                                            }, 1000);
                                        })()
                                    """.trimIndent()
                                    
                                    view?.evaluateJavascript(js, null)
                                }
                                url?.contains("Dashboard") == true -> {
                                    // Login successful
                                    saveCookies()
                                    continuation.resume(true)
                                }
                            }
                        }
                        
                        override fun onReceivedError(view: WebView?, request: WebResourceRequest?, error: WebResourceError?) {
                            Log.e(TAG, "WebView error: ${error?.description}")
                            continuation.resume(false)
                        }
                    }
                    
                    // Load login page
                    loadUrl(LOGIN_URL)
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Login error", e)
            return@withContext false
        }
    }
    
    override suspend fun fetchQRCode(): WebScraperInterface.QRFetchResult = withContext(Dispatchers.Main) {
        try {
            Log.d(TAG, "Fetching QR code with WebView...")
            
            return@withContext suspendCancellableCoroutine { continuation ->
                webView = WebView(context).apply {
                    settings.apply {
                        javaScriptEnabled = true
                        domStorageEnabled = true
                        cacheMode = WebSettings.LOAD_DEFAULT
                    }
                    
                    // Restore cookies
                    loadCookies()
                    
                    webViewClient = object : WebViewClient() {
                        override fun onPageFinished(view: WebView?, url: String?) {
                            Log.d(TAG, "Dashboard loaded: $url")
                            
                            if (url?.contains("Login") == true) {
                                // Session expired
                                continuation.resume(
                                    WebScraperInterface.QRFetchResult(
                                        success = false,
                                        error = "Session expired - login required",
                                        source = WebScraperInterface.ScrapingMethod.WEBVIEW
                                    )
                                )
                                return
                            }
                            
                            // Extract QR code
                            val js = """
                                javascript:(function() {
                                    var qrElement = document.getElementById('qrImageDashboard');
                                    if (!qrElement) {
                                        return JSON.stringify({error: 'QR element not found'});
                                    }
                                    
                                    var svg = qrElement.querySelector('svg');
                                    if (!svg) {
                                        return JSON.stringify({error: 'SVG not found'});
                                    }
                                    
                                    // Try to find QR content
                                    var qrContent = null;
                                    var scripts = document.getElementsByTagName('script');
                                    for (var i = 0; i < scripts.length; i++) {
                                        var match = scripts[i].innerHTML.match(/9268\d{14}/);
                                        if (match) {
                                            qrContent = match[0];
                                            break;
                                        }
                                    }
                                    
                                    return JSON.stringify({
                                        svg: svg.outerHTML,
                                        content: qrContent,
                                        success: true
                                    });
                                })()
                            """.trimIndent()
                            
                            view?.evaluateJavascript(js) { result ->
                                try {
                                    val data = parseJsonResult(result)
                                    if (data.containsKey("error")) {
                                        continuation.resume(
                                            WebScraperInterface.QRFetchResult(
                                                success = false,
                                                error = data["error"] as? String,
                                                source = WebScraperInterface.ScrapingMethod.WEBVIEW
                                            )
                                        )
                                    } else {
                                        continuation.resume(
                                            WebScraperInterface.QRFetchResult(
                                                success = true,
                                                qrContent = data["content"] as? String,
                                                svgContent = data["svg"] as? String,
                                                source = WebScraperInterface.ScrapingMethod.WEBVIEW
                                            )
                                        )
                                    }
                                } catch (e: Exception) {
                                    continuation.resume(
                                        WebScraperInterface.QRFetchResult(
                                            success = false,
                                            error = "Failed to parse QR data: ${e.message}",
                                            source = WebScraperInterface.ScrapingMethod.WEBVIEW
                                        )
                                    )
                                }
                            }
                        }
                    }
                    
                    // Load dashboard
                    loadUrl(DASHBOARD_URL)
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error fetching QR code", e)
            return@withContext WebScraperInterface.QRFetchResult(
                success = false,
                error = e.message,
                source = WebScraperInterface.ScrapingMethod.WEBVIEW
            )
        }
    }
    
    override suspend fun isSessionValid(): Boolean = withContext(Dispatchers.Main) {
        val cookies = cookieManager.getCookie(DASHBOARD_URL)
        !cookies.isNullOrEmpty()
    }
    
    override suspend fun clearSession() {
        withContext(Dispatchers.Main) {
            cookieManager.removeAllCookies(null)
            cookieManager.flush()
            webView?.clearCache(true)
            webView?.clearHistory()
            sharedPrefs.edit().clear().apply()
        }
    }
    
    private fun saveCookies() {
        val cookies = cookieManager.getCookie(DASHBOARD_URL)
        if (!cookies.isNullOrEmpty()) {
            sharedPrefs.edit().putString("cookies", cookies).apply()
            Log.d(TAG, "Cookies saved")
        }
    }
    
    private fun loadCookies() {
        val cookies = sharedPrefs.getString("cookies", null)
        if (!cookies.isNullOrEmpty()) {
            cookies.split(";").forEach { cookie ->
                cookieManager.setCookie(DASHBOARD_URL, cookie.trim())
            }
            cookieManager.flush()
            Log.d(TAG, "Cookies loaded")
        }
    }
    
    private fun parseJsonResult(jsonString: String): Map<String, Any> {
        // Remove quotes and parse JSON manually
        val cleaned = jsonString.trim('"').replace("\\\"", "\"")
        val map = mutableMapOf<String, Any>()
        
        // Simple JSON parser for our specific case
        val regex = Regex(""""(\w+)":\s*"([^"]*)"|(error):\s*'([^']*)'""")
        regex.findAll(cleaned).forEach { match ->
            val key = match.groupValues[1].ifEmpty { match.groupValues[3] }
            val value = match.groupValues[2].ifEmpty { match.groupValues[4] }
            if (key.isNotEmpty()) {
                map[key] = value
            }
        }
        
        return map
    }
    
    fun cleanup() {
        webView?.destroy()
        webView = null
    }
}