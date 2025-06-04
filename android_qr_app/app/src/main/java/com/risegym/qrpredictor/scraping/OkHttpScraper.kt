package com.risegym.qrpredictor.scraping

import android.content.Context
import android.graphics.Bitmap
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import org.jsoup.Jsoup
import org.jsoup.nodes.Document
import java.io.IOException
import java.util.concurrent.TimeUnit

/**
 * OkHttp-based web scraper for Rise Gym
 * Handles ASP.NET WebForms authentication and state management
 */
class OkHttpScraper(private val context: Context) : WebScraperInterface {
    
    companion object {
        private const val TAG = "OkHttpScraper"
        private const val LOGIN_URL = "https://risegyms.ez-runner.com/Account/Login.aspx"
        private const val DASHBOARD_URL = "https://risegyms.ez-runner.com/Account/Dashboard.aspx"
        private const val USER_AGENT = "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
        private const val TIMEOUT_SECONDS = 30L
    }
    
    private val cookieJar = PersistentCookieJar(context)
    
    private val client = OkHttpClient.Builder()
        .connectTimeout(TIMEOUT_SECONDS, TimeUnit.SECONDS)
        .readTimeout(TIMEOUT_SECONDS, TimeUnit.SECONDS)
        .cookieJar(cookieJar)
        .followRedirects(true)
        .build()
    
    private val sharedPrefs = context.getSharedPreferences("rise_gym_scraper", Context.MODE_PRIVATE)
    
    override suspend fun login(credentials: WebScraperInterface.Credentials): Boolean = withContext(Dispatchers.IO) {
        try {
            Log.d(TAG, "Starting login process...")
            
            // Step 1: Get login page to extract ViewState and other ASP.NET fields
            val loginPageRequest = Request.Builder()
                .url(LOGIN_URL)
                .header("User-Agent", USER_AGENT)
                .build()
            
            val loginPageResponse = client.newCall(loginPageRequest).execute()
            if (!loginPageResponse.isSuccessful) {
                Log.e(TAG, "Failed to load login page: ${loginPageResponse.code}")
                return@withContext false
            }
            
            val loginPageHtml = loginPageResponse.body?.string() ?: ""
            val loginDoc = Jsoup.parse(loginPageHtml)
            
            // Extract ASP.NET form fields
            val viewState = loginDoc.select("input[name=__VIEWSTATE]").attr("value")
            val viewStateGenerator = loginDoc.select("input[name=__VIEWSTATEGENERATOR]").attr("value")
            val eventValidation = loginDoc.select("input[name=__EVENTVALIDATION]").attr("value")
            
            if (viewState.isEmpty()) {
                Log.e(TAG, "Could not find ViewState in login form")
                return@withContext false
            }
            
            // Step 2: Submit login form
            val formBody = FormBody.Builder()
                .add("__VIEWSTATE", viewState)
                .add("__VIEWSTATEGENERATOR", viewStateGenerator)
                .add("__EVENTVALIDATION", eventValidation)
                .add("ctl00\$MainContent\$LoginUser\$UserName", credentials.username)
                .add("ctl00\$MainContent\$LoginUser\$Password", credentials.password)
                .add("ctl00\$MainContent\$LoginUser\$LoginButton", "Log In")
                .build()
            
            val loginRequest = Request.Builder()
                .url(LOGIN_URL)
                .header("User-Agent", USER_AGENT)
                .header("Content-Type", "application/x-www-form-urlencoded")
                .header("Referer", LOGIN_URL)
                .post(formBody)
                .build()
            
            val loginResponse = client.newCall(loginRequest).execute()
            
            // Check if login was successful by checking redirect or page content
            val responseUrl = loginResponse.request.url.toString()
            val isSuccess = responseUrl.contains("Dashboard") || !responseUrl.contains("Login")
            
            if (isSuccess) {
                Log.d(TAG, "Login successful!")
                // Cookies are automatically saved by PersistentCookieJar
            } else {
                Log.e(TAG, "Login failed - still on login page")
            }
            
            return@withContext isSuccess
            
        } catch (e: Exception) {
            Log.e(TAG, "Login error", e)
            return@withContext false
        }
    }
    
    override suspend fun fetchQRCode(): WebScraperInterface.QRFetchResult = withContext(Dispatchers.IO) {
        try {
            Log.d(TAG, "Fetching QR code...")
            
            // First check if we need to login
            if (!isSessionValid()) {
                Log.d(TAG, "Session invalid, need to login first")
                return@withContext WebScraperInterface.QRFetchResult(
                    success = false,
                    error = "Session expired - login required",
                    source = WebScraperInterface.ScrapingMethod.OKHTTP
                )
            }
            
            // Fetch dashboard page
            val dashboardRequest = Request.Builder()
                .url(DASHBOARD_URL)
                .header("User-Agent", USER_AGENT)
                .build()
            
            val response = client.newCall(dashboardRequest).execute()
            if (!response.isSuccessful) {
                return@withContext WebScraperInterface.QRFetchResult(
                    success = false,
                    error = "Failed to load dashboard: ${response.code}",
                    source = WebScraperInterface.ScrapingMethod.OKHTTP
                )
            }
            
            val html = response.body?.string() ?: ""
            val doc = Jsoup.parse(html)
            
            // Find QR code element
            val qrElement = doc.getElementById("qrImageDashboard")
            if (qrElement == null) {
                Log.e(TAG, "QR element not found on page")
                return@withContext WebScraperInterface.QRFetchResult(
                    success = false,
                    error = "QR code element not found",
                    source = WebScraperInterface.ScrapingMethod.OKHTTP
                )
            }
            
            // Extract SVG content
            val svgElement = qrElement.select("svg").first()
            val svgContent = svgElement?.outerHtml()
            
            // Try to extract QR content from page
            val qrContent = extractQRContent(html)
            
            return@withContext WebScraperInterface.QRFetchResult(
                success = true,
                qrContent = qrContent,
                svgContent = svgContent,
                source = WebScraperInterface.ScrapingMethod.OKHTTP
            )
            
        } catch (e: Exception) {
            Log.e(TAG, "Error fetching QR code", e)
            return@withContext WebScraperInterface.QRFetchResult(
                success = false,
                error = e.message,
                source = WebScraperInterface.ScrapingMethod.OKHTTP
            )
        }
    }
    
    override suspend fun isSessionValid(): Boolean = withContext(Dispatchers.IO) {
        try {
            // Try to access dashboard directly
            val request = Request.Builder()
                .url(DASHBOARD_URL)
                .header("User-Agent", USER_AGENT)
                .build()
            
            val response = client.newCall(request).execute()
            val finalUrl = response.request.url.toString()
            
            // Check if we were redirected to login
            val isValid = !finalUrl.contains("Login") && finalUrl.contains("Dashboard")
            Log.d(TAG, "Session valid: $isValid")
            
            return@withContext isValid
            
        } catch (e: Exception) {
            Log.e(TAG, "Error checking session", e)
            return@withContext false
        }
    }
    
    override suspend fun clearSession() {
        cookieJar.clear()
        sharedPrefs.edit().clear().apply()
        Log.d(TAG, "Session cleared")
    }
    
    private fun extractQRContent(html: String): String? {
        // Look for QR content pattern in HTML
        val pattern = Regex("9268\\d{14}")
        return pattern.find(html)?.value
    }
}