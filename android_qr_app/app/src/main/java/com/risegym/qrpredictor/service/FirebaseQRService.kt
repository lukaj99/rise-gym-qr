package com.risegym.qrpredictor.service

import android.util.Log
import com.google.firebase.database.*
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import kotlinx.coroutines.tasks.await

class FirebaseQRService {
    companion object {
        private const val TAG = "FirebaseQRService"
        private const val QR_CODES_PATH = "qr_codes"
        private const val LATEST_PATH = "latest"
    }
    
    private val database = FirebaseDatabase.getInstance()
    private val qrCodesRef = database.getReference(QR_CODES_PATH)
    private val latestRef = database.getReference(LATEST_PATH)
    
    data class QRCodeData(
        val timestamp: String = "",
        val svgContent: String = "",
        val bitmapBase64: String = "",
        val pattern: String = "",
        val uploadedAt: Long = 0
    )
    
    /**
     * Listen for real-time updates to the latest QR code
     */
    fun observeLatestQRCode(): Flow<Result<QRCodeData>> = callbackFlow {
        val listener = object : ValueEventListener {
            override fun onDataChange(snapshot: DataSnapshot) {
                Log.d(TAG, "onDataChange triggered. Snapshot exists: ${snapshot.exists()}")
                try {
                    val qrCodeData = snapshot.getValue(QRCodeData::class.java)
                    if (qrCodeData != null) {
                        trySend(Result.success(qrCodeData))
                    } else {
                        trySend(Result.failure(Exception("No QR code data available")))
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "Error parsing QR code data", e)
                    trySend(Result.failure(e))
                }
            }
            
            override fun onCancelled(error: DatabaseError) {
                Log.e(TAG, "onCancelled triggered. Firebase database error: ${error.message}", error.toException())
                trySend(Result.failure(Exception(error.message)))
            }
        }
        
        Log.d(TAG, "Attaching ValueEventListener to 'latest' ref.")
        latestRef.addValueEventListener(listener)
        
        awaitClose {
            latestRef.removeEventListener(listener)
        }
    }
    
    /**
     * Get the latest QR code once (no real-time updates)
     */
    suspend fun getLatestQRCode(): Result<QRCodeData> {
        return try {
            val snapshot = latestRef.get().await()
            val qrCodeData = snapshot.getValue(QRCodeData::class.java)
            if (qrCodeData != null) {
                Result.success(qrCodeData)
            } else {
                Result.failure(Exception("No QR code data available"))
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error fetching latest QR code", e)
            Result.failure(e)
        }
    }
    
    /**
     * Get all QR codes (for history/debugging)
     */
    suspend fun getAllQRCodes(): Result<List<QRCodeData>> {
        return try {
            val snapshot = qrCodesRef.get().await()
            val qrCodes = mutableListOf<QRCodeData>()
            
            snapshot.children.forEach { dataSnapshot ->
                dataSnapshot.getValue(QRCodeData::class.java)?.let {
                    qrCodes.add(it)
                }
            }
            
            // Sort by timestamp descending
            qrCodes.sortByDescending { it.timestamp }
            Result.success(qrCodes)
        } catch (e: Exception) {
            Log.e(TAG, "Error fetching all QR codes", e)
            Result.failure(e)
        }
    }
    
    /**
     * Test Firebase connection
     */
    suspend fun testConnection(): Result<Boolean> {
        return try {
            // Try to read a simple value
            val snapshot = database.getReference(".info/connected").get().await()
            val connected = snapshot.getValue(Boolean::class.java) ?: false
            Result.success(connected)
        } catch (e: Exception) {
            Log.e(TAG, "Firebase connection test failed", e)
            Result.failure(e)
        }
    }
    
    /**
     * Initialize Firebase with custom database URL if needed
     */
    fun initialize(databaseUrl: String? = null) {
        if (databaseUrl != null) {
            try {
                database.reference.database.useEmulator("10.0.2.2", 9000) // For local testing
            } catch (e: Exception) {
                Log.w(TAG, "Firebase already initialized or emulator not available")
            }
        }
    }
}