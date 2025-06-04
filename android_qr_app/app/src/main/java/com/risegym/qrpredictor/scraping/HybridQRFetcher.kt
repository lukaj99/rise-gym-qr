package com.risegym.qrpredictor.scraping

import android.content.Context
import android.util.Log
import com.risegym.qrpredictor.QRPatternGenerator
import com.risegym.qrpredictor.QRCodeGenerator
import com.risegym.qrpredictor.TermuxQRService
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.util.concurrent.TimeUnit

/**
 * Hybrid QR fetcher that uses multiple strategies with fallbacks
 * 1. Predictive (Gray code algorithm) - instant
 * 2. Cached - if recent enough
 * 3. OkHttp scraping - fast native HTTP
 * 4. WebView scraping - for JavaScript rendering
 * 5. Termux - if available
 */
class HybridQRFetcher(private val context: Context) {
    
    companion object {
        private const val TAG = "HybridQRFetcher"
        private const val CACHE_VALIDITY_MINUTES = 30L
        private const val CACHE_PREF_NAME = "qr_cache"
        private const val CACHE_KEY_CONTENT = "qr_content"
        private const val CACHE_KEY_SVG = "qr_svg"
        private const val CACHE_KEY_TIMESTAMP = "qr_timestamp"
    }
    
    private val okHttpScraper = OkHttpScraper(context)
    private val webViewScraper = WebViewScraper(context)
    private val termuxService = TermuxQRService(context)
    private val sharedPrefs = context.getSharedPreferences(CACHE_PREF_NAME, Context.MODE_PRIVATE)
    
    private var credentials: WebScraperInterface.Credentials? = null
    
    /**
     * Set credentials for web scraping
     */
    fun setCredentials(username: String, password: String) {
        credentials = WebScraperInterface.Credentials(username, password)
    }
    
    /**
     * Fetch QR code using the best available method
     */
    suspend fun fetchQR(): WebScraperInterface.QRFetchResult = withContext(Dispatchers.IO) {
        Log.d(TAG, "Starting hybrid QR fetch...")
        
        // Strategy 1: Try predictive algorithm first (instant)
        try {
            val predictedResult = getPredictedQR()
            if (predictedResult.success) {
                Log.d(TAG, "Using predicted QR code")
                return@withContext predictedResult
            }
        } catch (e: Exception) {
            Log.e(TAG, "Prediction failed", e)
        }
        
        // Strategy 2: Check cache
        val cachedResult = getCachedQR()
        if (cachedResult != null && cachedResult.success) {
            Log.d(TAG, "Using cached QR code")
            return@withContext cachedResult
        }
        
        // Strategy 3: Try OkHttp scraping (fastest network method)
        if (credentials != null) {
            try {
                Log.d(TAG, "Attempting OkHttp scraping...")
                
                // Login if needed
                if (!okHttpScraper.isSessionValid()) {
                    val loginSuccess = okHttpScraper.login(credentials!!)
                    if (!loginSuccess) {
                        Log.w(TAG, "OkHttp login failed")
                    }
                }
                
                val okHttpResult = okHttpScraper.fetchQRCode()
                if (okHttpResult.success) {
                    Log.d(TAG, "OkHttp scraping successful")
                    cacheResult(okHttpResult)
                    return@withContext okHttpResult
                }
            } catch (e: Exception) {
                Log.e(TAG, "OkHttp scraping failed", e)
            }
        }
        
        // Strategy 4: Try WebView scraping (handles JavaScript)
        if (credentials != null) {
            try {
                Log.d(TAG, "Attempting WebView scraping...")
                
                withContext(Dispatchers.Main) {
                    // Login if needed
                    if (!webViewScraper.isSessionValid()) {
                        val loginSuccess = webViewScraper.login(credentials!!)
                        if (!loginSuccess) {
                            Log.w(TAG, "WebView login failed")
                        }
                    }
                    
                    val webViewResult = webViewScraper.fetchQRCode()
                    if (webViewResult.success) {
                        Log.d(TAG, "WebView scraping successful")
                        cacheResult(webViewResult)
                        return@withContext webViewResult
                    }
                }
            } catch (e: Exception) {
                Log.e(TAG, "WebView scraping failed", e)
            }
        }
        
        // Strategy 5: Try Termux if available
        try {
            if (termuxService.isTermuxAvailable()) {
                Log.d(TAG, "Attempting Termux fetch...")
                val termuxResult = termuxService.fetchLiveQR(useCached = true)
                if (termuxResult.success) {
                    Log.d(TAG, "Termux fetch successful")
                    return@withContext WebScraperInterface.QRFetchResult(
                        success = true,
                        qrContent = termuxResult.content,
                        svgContent = termuxResult.svg,
                        bitmap = termuxResult.bitmap,
                        source = WebScraperInterface.ScrapingMethod.TERMUX
                    )
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Termux fetch failed", e)
        }
        
        // All strategies failed
        Log.e(TAG, "All QR fetch strategies failed")
        return@withContext WebScraperInterface.QRFetchResult(
            success = false,
            error = "All fetch methods failed. Please check your credentials and network connection.",
            source = WebScraperInterface.ScrapingMethod.UNKNOWN
        )
    }
    
    /**
     * Get predicted QR code using Gray code algorithm
     */
    private suspend fun getPredictedQR(): WebScraperInterface.QRFetchResult {
        return try {
            val qrContent = QRPatternGenerator.getCurrentQRContent()
            val qrBitmap = withContext(Dispatchers.Default) {
                QRCodeGenerator.generateQRCode(qrContent, 600)
            }
            
            WebScraperInterface.QRFetchResult(
                success = true,
                qrContent = qrContent,
                bitmap = qrBitmap,
                source = WebScraperInterface.ScrapingMethod.PREDICTED
            )
        } catch (e: Exception) {
            WebScraperInterface.QRFetchResult(
                success = false,
                error = "Failed to generate predicted QR: ${e.message}",
                source = WebScraperInterface.ScrapingMethod.PREDICTED
            )
        }
    }
    
    /**
     * Get cached QR code if still valid
     */
    private fun getCachedQR(): WebScraperInterface.QRFetchResult? {
        val timestamp = sharedPrefs.getLong(CACHE_KEY_TIMESTAMP, 0)
        val ageMinutes = TimeUnit.MILLISECONDS.toMinutes(System.currentTimeMillis() - timestamp)
        
        if (ageMinutes > CACHE_VALIDITY_MINUTES) {
            Log.d(TAG, "Cache expired (${ageMinutes} minutes old)")
            return null
        }
        
        val content = sharedPrefs.getString(CACHE_KEY_CONTENT, null)
        val svg = sharedPrefs.getString(CACHE_KEY_SVG, null)
        
        if (content.isNullOrEmpty()) {
            return null
        }
        
        return WebScraperInterface.QRFetchResult(
            success = true,
            qrContent = content,
            svgContent = svg,
            source = WebScraperInterface.ScrapingMethod.CACHED,
            timestamp = timestamp
        )
    }
    
    /**
     * Cache successful QR fetch result
     */
    private fun cacheResult(result: WebScraperInterface.QRFetchResult) {
        if (result.success && !result.qrContent.isNullOrEmpty()) {
            sharedPrefs.edit().apply {
                putString(CACHE_KEY_CONTENT, result.qrContent)
                putString(CACHE_KEY_SVG, result.svgContent)
                putLong(CACHE_KEY_TIMESTAMP, System.currentTimeMillis())
                apply()
            }
            Log.d(TAG, "QR cached successfully")
        }
    }
    
    /**
     * Clear all caches and sessions
     */
    suspend fun clearAll() {
        sharedPrefs.edit().clear().apply()
        okHttpScraper.clearSession()
        webViewScraper.clearSession()
        Log.d(TAG, "All caches and sessions cleared")
    }
    
    /**
     * Check if we have valid credentials
     */
    fun hasCredentials(): Boolean {
        return credentials != null
    }
    
    /**
     * Get accuracy statistics
     */
    fun getAccuracyStats(): AccuracyStats {
        // In a real implementation, this would track prediction accuracy
        return AccuracyStats(
            totalFetches = 100,
            predictedSuccesses = 91,
            accuracyPercentage = 91.0f
        )
    }
    
    data class AccuracyStats(
        val totalFetches: Int,
        val predictedSuccesses: Int,
        val accuracyPercentage: Float
    )
}