package com.risegym.qrpredictor.scraping

import android.graphics.Bitmap

/**
 * Interface for different web scraping implementations
 */
interface WebScraperInterface {
    
    /**
     * Result of a QR fetch operation
     */
    data class QRFetchResult(
        val success: Boolean,
        val qrContent: String? = null,
        val svgContent: String? = null,
        val bitmap: Bitmap? = null,
        val error: String? = null,
        val source: ScrapingMethod = ScrapingMethod.UNKNOWN,
        val timestamp: Long = System.currentTimeMillis()
    )
    
    /**
     * Scraping method used
     */
    enum class ScrapingMethod {
        OKHTTP,
        WEBVIEW,
        TERMUX,
        CACHED,
        PREDICTED,
        UNKNOWN
    }
    
    /**
     * Authentication credentials
     */
    data class Credentials(
        val username: String,
        val password: String
    )
    
    /**
     * Login to Rise Gym portal
     */
    suspend fun login(credentials: Credentials): Boolean
    
    /**
     * Fetch QR code from the portal
     */
    suspend fun fetchQRCode(): QRFetchResult
    
    /**
     * Check if session is still valid
     */
    suspend fun isSessionValid(): Boolean
    
    /**
     * Clear saved session
     */
    suspend fun clearSession()
}