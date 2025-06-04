package com.risegym.qrpredictor.scraping

import android.content.Context
import okhttp3.Cookie
import okhttp3.CookieJar
import okhttp3.HttpUrl
import java.util.concurrent.ConcurrentHashMap

/**
 * Persistent cookie storage for OkHttp
 * Saves cookies to SharedPreferences for session persistence
 */
class PersistentCookieJar(private val context: Context) : CookieJar {
    
    private val cookieStore = ConcurrentHashMap<String, List<Cookie>>()
    private val sharedPrefs = context.getSharedPreferences("rise_gym_cookies", Context.MODE_PRIVATE)
    
    init {
        loadPersistedCookies()
    }
    
    override fun saveFromResponse(url: HttpUrl, cookies: List<Cookie>) {
        val key = url.host
        cookieStore[key] = cookies
        
        // Persist cookies
        val serializedCookies = cookies.joinToString("|") { cookie ->
            serializeCookie(cookie)
        }
        sharedPrefs.edit().putString(key, serializedCookies).apply()
    }
    
    override fun loadForRequest(url: HttpUrl): List<Cookie> {
        val key = url.host
        return cookieStore[key] ?: emptyList()
    }
    
    fun clear() {
        cookieStore.clear()
        sharedPrefs.edit().clear().apply()
    }
    
    private fun loadPersistedCookies() {
        sharedPrefs.all.forEach { (host, cookiesString) ->
            if (cookiesString is String) {
                val cookies = cookiesString.split("|").mapNotNull { cookieString ->
                    deserializeCookie(host, cookieString)
                }
                if (cookies.isNotEmpty()) {
                    cookieStore[host] = cookies
                }
            }
        }
    }
    
    private fun serializeCookie(cookie: Cookie): String {
        return buildString {
            append(cookie.name).append("=").append(cookie.value)
            append(";domain=").append(cookie.domain)
            append(";path=").append(cookie.path)
            if (cookie.expiresAt != Long.MAX_VALUE) {
                append(";expires=").append(cookie.expiresAt)
            }
            if (cookie.secure) append(";secure")
            if (cookie.httpOnly) append(";httpOnly")
        }
    }
    
    private fun deserializeCookie(host: String, cookieString: String): Cookie? {
        return try {
            val parts = cookieString.split(";").map { it.trim() }
            val nameValue = parts[0].split("=", limit = 2)
            if (nameValue.size != 2) return null
            
            val builder = Cookie.Builder()
                .name(nameValue[0])
                .value(nameValue[1])
                .domain(host)
            
            parts.drop(1).forEach { part ->
                val keyValue = part.split("=", limit = 2)
                when (keyValue[0]) {
                    "domain" -> builder.domain(keyValue.getOrElse(1) { host })
                    "path" -> builder.path(keyValue.getOrElse(1) { "/" })
                    "expires" -> keyValue.getOrNull(1)?.toLongOrNull()?.let { builder.expiresAt(it) }
                    "secure" -> builder.secure()
                    "httpOnly" -> builder.httpOnly()
                }
            }
            
            builder.build()
        } catch (e: Exception) {
            null
        }
    }
}