package com.risegym.qrpredictor.security

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import android.util.Log
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/**
 * Secure credential storage using Android Keystore
 * Encrypts sensitive data like usernames and passwords
 */
class SecureCredentialManager(private val context: Context) {
    
    companion object {
        private const val TAG = "SecureCredentialManager"
        private const val KEYSTORE_PROVIDER = "AndroidKeyStore"
        private const val KEY_ALIAS = "RiseGymCredentialsKey"
        private const val SHARED_PREFS_NAME = "secure_credentials"
        private const val PREF_USERNAME = "encrypted_username"
        private const val PREF_PASSWORD = "encrypted_password"
        private const val PREF_IV = "encryption_iv"
        private const val TRANSFORMATION = "AES/GCM/NoPadding"
        private const val GCM_TAG_LENGTH = 128
    }
    
    private val keyStore: KeyStore = KeyStore.getInstance(KEYSTORE_PROVIDER).apply {
        load(null)
    }
    
    private val sharedPrefs = context.getSharedPreferences(SHARED_PREFS_NAME, Context.MODE_PRIVATE)
    
    init {
        // Generate encryption key if it doesn't exist
        if (!keyStore.containsAlias(KEY_ALIAS)) {
            generateSecretKey()
        }
    }
    
    /**
     * Save credentials securely
     */
    fun saveCredentials(username: String, password: String): Boolean {
        return try {
            val secretKey = getSecretKey()
            
            // Encrypt username
            val encryptedUsername = encrypt(username, secretKey)
            // Encrypt password
            val encryptedPassword = encrypt(password, secretKey)
            
            // Save encrypted data
            sharedPrefs.edit().apply {
                putString(PREF_USERNAME, encryptedUsername.cipherText)
                putString(PREF_PASSWORD, encryptedPassword.cipherText)
                putString(PREF_IV, encryptedUsername.iv) // IV can be the same for both
                apply()
            }
            
            Log.d(TAG, "Credentials saved securely")
            true
        } catch (e: Exception) {
            Log.e(TAG, "Failed to save credentials", e)
            false
        }
    }
    
    /**
     * Retrieve decrypted credentials
     */
    fun getCredentials(): Credentials? {
        return try {
            val encryptedUsername = sharedPrefs.getString(PREF_USERNAME, null)
            val encryptedPassword = sharedPrefs.getString(PREF_PASSWORD, null)
            val iv = sharedPrefs.getString(PREF_IV, null)
            
            if (encryptedUsername == null || encryptedPassword == null || iv == null) {
                Log.d(TAG, "No stored credentials found")
                return null
            }
            
            val secretKey = getSecretKey()
            
            // Decrypt credentials
            val username = decrypt(encryptedUsername, iv, secretKey)
            val password = decrypt(encryptedPassword, iv, secretKey)
            
            Credentials(username, password)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to retrieve credentials", e)
            null
        }
    }
    
    /**
     * Check if credentials are stored
     */
    fun hasStoredCredentials(): Boolean {
        return sharedPrefs.contains(PREF_USERNAME) && sharedPrefs.contains(PREF_PASSWORD)
    }
    
    /**
     * Clear stored credentials
     */
    fun clearCredentials() {
        sharedPrefs.edit().clear().apply()
        Log.d(TAG, "Credentials cleared")
    }
    
    /**
     * Generate a new secret key in Android Keystore
     */
    private fun generateSecretKey() {
        val keyGenerator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, KEYSTORE_PROVIDER)
        
        val keyGenParameterSpec = KeyGenParameterSpec.Builder(
            KEY_ALIAS,
            KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT
        )
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .setKeySize(256)
            .setUserAuthenticationRequired(false) // Set to true for additional security
            .build()
        
        keyGenerator.init(keyGenParameterSpec)
        keyGenerator.generateKey()
        
        Log.d(TAG, "Secret key generated")
    }
    
    /**
     * Get secret key from Keystore
     */
    private fun getSecretKey(): SecretKey {
        return keyStore.getKey(KEY_ALIAS, null) as SecretKey
    }
    
    /**
     * Encrypt data using AES/GCM
     */
    private fun encrypt(plainText: String, secretKey: SecretKey): EncryptedData {
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, secretKey)
        
        val iv = cipher.iv
        val cipherText = cipher.doFinal(plainText.toByteArray(Charsets.UTF_8))
        
        return EncryptedData(
            cipherText = Base64.encodeToString(cipherText, Base64.DEFAULT),
            iv = Base64.encodeToString(iv, Base64.DEFAULT)
        )
    }
    
    /**
     * Decrypt data using AES/GCM
     */
    private fun decrypt(cipherText: String, iv: String, secretKey: SecretKey): String {
        val cipher = Cipher.getInstance(TRANSFORMATION)
        val gcmParameterSpec = GCMParameterSpec(GCM_TAG_LENGTH, Base64.decode(iv, Base64.DEFAULT))
        cipher.init(Cipher.DECRYPT_MODE, secretKey, gcmParameterSpec)
        
        val plainText = cipher.doFinal(Base64.decode(cipherText, Base64.DEFAULT))
        return String(plainText, Charsets.UTF_8)
    }
    
    /**
     * Data class for credentials
     */
    data class Credentials(
        val username: String,
        val password: String
    )
    
    /**
     * Data class for encrypted data
     */
    private data class EncryptedData(
        val cipherText: String,
        val iv: String
    )
}