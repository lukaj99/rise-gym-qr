package com.risegym.qrpredictor.service

import android.util.Log
import com.google.firebase.storage.FirebaseStorage
import com.google.firebase.storage.StorageReference
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.tasks.await
import kotlinx.coroutines.withContext
import java.text.SimpleDateFormat
import java.util.*

/**
 * Firebase-based QR code service for fetching QR codes from Firebase Storage
 * This is the sole source of QR codes, replacing all local generation and other cloud sources
 */
class FirebaseQRService {
    companion object {
        private const val TAG = "FirebaseQRService"
        private const val QR_FOLDER = "qr_codes"
        private const val LATEST_QR_FILE = "latest.svg"
        private const val METADATA_FILE = "metadata.json"
    }

    private val storage = FirebaseStorage.getInstance("gs://rise-gym-qr.firebasestorage.app")
    private val storageRef = storage.reference

    data class QRCodeData(
        val svgContent: String,
        val timestamp: Long,
        val timeSlot: String,
        val expiresAt: Long
    )

    /**
     * Fetch the latest QR code from Firebase Storage
     */
    suspend fun getLatestQRCode(): Result<QRCodeData> = withContext(Dispatchers.IO) {
        try {
            Log.d(TAG, "Fetching latest QR code from Firebase")
            
            // Get reference to the latest QR code
            val qrRef = storageRef.child("$QR_FOLDER/$LATEST_QR_FILE")
            
            // Check if file exists first
            try {
                qrRef.metadata.await()
            } catch (e: Exception) {
                Log.e(TAG, "Latest QR file does not exist in Firebase Storage")
                return@withContext Result.failure(Exception("No QR code available in Firebase"))
            }
            
            // Download the SVG content
            val maxDownloadSize = 1024L * 1024L // 1MB max
            val svgBytes = qrRef.getBytes(maxDownloadSize).await()
            val svgContent = String(svgBytes)
            
            // Validate SVG content
            if (svgContent.isBlank()) {
                Log.e(TAG, "Downloaded SVG content is empty")
                return@withContext Result.failure(Exception("QR code content is empty"))
            }
            
            // Get metadata
            val metadata = qrRef.metadata.await()
            val timestamp = metadata.updatedTimeMillis
            val timeSlot = metadata.getCustomMetadata("timeSlot") ?: getCurrentTimeSlot()
            val expiresAt = metadata.getCustomMetadata("expiresAt")?.toLongOrNull() 
                ?: calculateExpirationTime()
            
            Log.d(TAG, "Successfully fetched QR code for time slot: $timeSlot")
            
            Result.success(QRCodeData(
                svgContent = svgContent,
                timestamp = timestamp,
                timeSlot = timeSlot,
                expiresAt = expiresAt
            ))
        } catch (e: Exception) {
            Log.e(TAG, "Error fetching QR code from Firebase", e)
            Result.failure(e)
        }
    }

    /**
     * Get QR code for a specific time slot
     */
    suspend fun getQRCodeForTimeSlot(timeSlot: String): Result<QRCodeData> = withContext(Dispatchers.IO) {
        try {
            Log.d(TAG, "Fetching QR code for time slot: $timeSlot")
            
            // Try to get time slot specific file first
            val slotFileName = "slot_${timeSlot.replace(":", "")}.svg"
            val qrRef = storageRef.child("$QR_FOLDER/$slotFileName")
            
            return@withContext try {
                val svgBytes = qrRef.getBytes(1024L * 1024L).await()
                val svgContent = String(svgBytes)
                val metadata = qrRef.metadata.await()
                
                Result.success(QRCodeData(
                    svgContent = svgContent,
                    timestamp = metadata.updatedTimeMillis,
                    timeSlot = timeSlot,
                    expiresAt = calculateExpirationTime()
                ))
            } catch (e: Exception) {
                // Fallback to latest if specific slot not found
                Log.w(TAG, "Time slot specific QR not found, falling back to latest")
                getLatestQRCode()
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error fetching QR code for time slot", e)
            Result.failure(e)
        }
    }

    /**
     * Check if cached QR code is still valid
     */
    fun isQRCodeValid(timestamp: Long, expiresAt: Long): Boolean {
        val now = System.currentTimeMillis()
        return now < expiresAt
    }

    /**
     * Get current time slot (2-hour blocks)
     */
    private fun getCurrentTimeSlot(): String {
        val calendar = Calendar.getInstance()
        val hour = calendar.get(Calendar.HOUR_OF_DAY)
        val slotHour = (hour / 2) * 2
        return String.format("%02d:00-%02d:59", slotHour, slotHour + 1)
    }

    /**
     * Calculate when the current QR code expires
     */
    private fun calculateExpirationTime(): Long {
        val calendar = Calendar.getInstance()
        val currentHour = calendar.get(Calendar.HOUR_OF_DAY)
        val nextSlotHour = ((currentHour / 2) + 1) * 2
        
        calendar.set(Calendar.HOUR_OF_DAY, nextSlotHour)
        calendar.set(Calendar.MINUTE, 0)
        calendar.set(Calendar.SECOND, 0)
        calendar.set(Calendar.MILLISECOND, 0)
        
        return calendar.timeInMillis
    }

    /**
     * Listen for real-time updates to QR codes
     */
    fun addQRUpdateListener(onUpdate: (QRCodeData) -> Unit) {
        val qrRef = storageRef.child("$QR_FOLDER/$LATEST_QR_FILE")
        
        // Firebase Storage doesn't have real-time listeners like Realtime Database
        // So we'll need to poll or use Cloud Functions to trigger updates
        // For now, this is a placeholder for future implementation
        Log.d(TAG, "Real-time updates not yet implemented for Storage")
    }

    /**
     * Get all available time slots
     */
    suspend fun getAvailableTimeSlots(): Result<List<String>> = withContext(Dispatchers.IO) {
        try {
            val listResult = storageRef.child(QR_FOLDER).listAll().await()
            val timeSlots = mutableListOf<String>()
            
            for (item in listResult.items) {
                val name = item.name
                if (name.startsWith("slot_") && name.endsWith(".svg")) {
                    val slot = name.removePrefix("slot_").removeSuffix(".svg")
                    timeSlots.add(slot.chunked(2).joinToString(":"))
                }
            }
            
            Result.success(timeSlots.sorted())
        } catch (e: Exception) {
            Log.e(TAG, "Error listing time slots", e)
            Result.failure(e)
        }
    }

    /**
     * Prefetch QR codes for upcoming time slots
     */
    suspend fun prefetchUpcomingQRCodes() = withContext(Dispatchers.IO) {
        try {
            val currentSlot = getCurrentTimeSlot()
            val currentHour = currentSlot.substring(0, 2).toInt()
            
            // Prefetch next 2 time slots
            for (i in 1..2) {
                val nextHour = (currentHour + (i * 2)) % 24
                val nextSlot = String.format("%02d:00-%02d:59", nextHour, nextHour + 1)
                
                getQRCodeForTimeSlot(nextSlot)
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error prefetching QR codes", e)
        }
    }
}