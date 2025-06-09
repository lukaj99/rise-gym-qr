package com.risegym.qrpredictor.service

import android.util.Log
import com.google.firebase.database.DataSnapshot
import com.google.firebase.database.DatabaseError
import com.google.firebase.database.FirebaseDatabase
import com.google.firebase.database.ValueEventListener
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

/**
 * Firebase Realtime Database service for fetching QR codes
 * Reads QR data from Firebase Realtime Database
 */
class FirebaseQRService {
    companion object {
        private const val TAG = "FirebaseQRService"
        private const val PATH_LATEST = "latest"
        private const val PATH_QR_CODES = "qr_codes"
        private const val DATABASE_URL = "https://rise-gym-qr-default-rtdb.europe-west1.firebasedatabase.app"
    }

    private val database = FirebaseDatabase.getInstance(DATABASE_URL)
    private val latestRef = database.getReference(PATH_LATEST)
    private val qrCodesRef = database.getReference(PATH_QR_CODES)

    data class QRCodeData(
        val svgContent: String,
        val bitmapBase64: String?,
        val timestamp: Long,
        val timeSlot: String,
        val expiresAt: Long
    )

    data class FirebaseQREntry(
        val timestamp: String = "",
        val svgContent: String = "",
        val bitmapBase64: String = "",
        val pattern: String = "",
        val uploadedAt: Long = 0L
    )

    /**
     * Fetch the latest QR code from Firebase Realtime Database
     */
    suspend fun getLatestQRCode(): Result<QRCodeData> = suspendCancellableCoroutine { continuation ->
        Log.d(TAG, "Fetching latest QR code from Firebase Database")
        
        // Fetch directly from /latest
        latestRef.addListenerForSingleValueEvent(object : ValueEventListener {
            override fun onDataChange(snapshot: DataSnapshot) {
                try {
                    if (!snapshot.exists()) {
                        Log.e(TAG, "No latest QR code found in database")
                        continuation.resume(Result.failure(Exception("No QR code available in database")))
                        return
                    }
                    
                    val qrEntry = snapshot.getValue(FirebaseQREntry::class.java)
                    
                    if (qrEntry == null || qrEntry.svgContent.isBlank()) {
                        Log.e(TAG, "Invalid QR data in database")
                        continuation.resume(Result.failure(Exception("Invalid QR data")))
                        return
                    }
                    
                    Log.d(TAG, "Successfully fetched QR code: ${qrEntry.pattern}")
                    
                    // Calculate time slot from pattern (format: 926806082025HHMMSS)
                    val hour = qrEntry.pattern.substring(12, 14).toIntOrNull() ?: 0
                    // Time slots are 2-hour blocks: 0-1:59, 2-3:59, 4-5:59, etc.
                    val slotStartHour = (hour / 2) * 2
                    val slotEndHour = slotStartHour + 2 - 1
                    val timeSlot = String.format("%d:00-%d:59", slotStartHour, slotEndHour)
                    
                    val qrData = QRCodeData(
                        svgContent = qrEntry.svgContent,
                        bitmapBase64 = qrEntry.bitmapBase64.takeIf { it.isNotBlank() },
                        timestamp = if (qrEntry.uploadedAt > 0) qrEntry.uploadedAt else parseTimestamp(qrEntry.timestamp),
                        timeSlot = timeSlot,
                        expiresAt = qrEntry.uploadedAt + 7200000 // 2 hours from upload
                    )
                    
                    continuation.resume(Result.success(qrData))
                } catch (e: Exception) {
                    Log.e(TAG, "Error parsing QR data", e)
                    continuation.resume(Result.failure(e))
                }
            }
            
            override fun onCancelled(error: DatabaseError) {
                Log.e(TAG, "Database error: ${error.message}")
                continuation.resume(Result.failure(error.toException()))
            }
        })
    }

    /**
     * Get QR code for a specific timestamp
     */
    suspend fun getQRCodeByTimestamp(timestamp: String): Result<QRCodeData> = suspendCancellableCoroutine { continuation ->
        Log.d(TAG, "Fetching QR code for timestamp: $timestamp")
        
        qrCodesRef.child(timestamp).addListenerForSingleValueEvent(object : ValueEventListener {
            override fun onDataChange(snapshot: DataSnapshot) {
                try {
                    if (!snapshot.exists()) {
                        continuation.resume(Result.failure(Exception("QR code not found for timestamp: $timestamp")))
                        return
                    }
                    
                    val qrEntry = snapshot.getValue(FirebaseQREntry::class.java)
                    if (qrEntry == null || qrEntry.svgContent.isBlank()) {
                        continuation.resume(Result.failure(Exception("Invalid QR data")))
                        return
                    }
                    
                    // Calculate time slot from pattern
                    val hour = qrEntry.pattern.substring(12, 14).toIntOrNull() ?: 0
                    // Time slots are 2-hour blocks: 0-1:59, 2-3:59, 4-5:59, etc.
                    val slotStartHour = (hour / 2) * 2
                    val slotEndHour = slotStartHour + 2 - 1
                    val timeSlot = String.format("%d:00-%d:59", slotStartHour, slotEndHour)
                    
                    val qrData = QRCodeData(
                        svgContent = qrEntry.svgContent,
                        bitmapBase64 = qrEntry.bitmapBase64.takeIf { it.isNotBlank() },
                        timestamp = if (qrEntry.uploadedAt > 0) qrEntry.uploadedAt else parseTimestamp(qrEntry.timestamp),
                        timeSlot = timeSlot,
                        expiresAt = qrEntry.uploadedAt + 7200000
                    )
                    
                    continuation.resume(Result.success(qrData))
                } catch (e: Exception) {
                    Log.e(TAG, "Error parsing QR data", e)
                    continuation.resume(Result.failure(e))
                }
            }
            
            override fun onCancelled(error: DatabaseError) {
                Log.e(TAG, "Database error: ${error.message}")
                continuation.resume(Result.failure(error.toException()))
            }
        })
    }

    /**
     * Listen for real-time updates to the most recent QR code
     */
    fun observeMostRecentQRCode(): Flow<Result<QRCodeData>> = callbackFlow {
        Log.d(TAG, "Starting real-time observation of most recent QR code")
        
        val listener = object : ValueEventListener {
            override fun onDataChange(snapshot: DataSnapshot) {
                try {
                    // Calculate current time slot using device local time
                    val calendar = java.util.Calendar.getInstance()
                    val currentHour = calendar.get(java.util.Calendar.HOUR_OF_DAY)
                    val currentTimeSlotHour = (currentHour / 2) * 2
                    
                    // Format timestamp for current time slot using local timezone
                    val dateFormat = java.text.SimpleDateFormat("yyyyMMdd", java.util.Locale.getDefault())
                    val dateStr = dateFormat.format(calendar.time)
                    val targetTimestamp = String.format("%s%02d0000", dateStr, currentTimeSlotHour)
                    
                    Log.d(TAG, "Looking for QR code for current time slot: $targetTimestamp (hour: $currentTimeSlotHour)")
                    
                    var currentSlotQR: QRCodeData? = null
                    var mostRecentQR: QRCodeData? = null
                    var mostRecentTimestamp = 0L
                    
                    for (child in snapshot.children) {
                        val qrEntry = child.getValue(FirebaseQREntry::class.java) ?: continue
                        
                        if (qrEntry.svgContent.isNotBlank() || qrEntry.bitmapBase64.isNotBlank()) {
                            val timestamp = parseTimestamp(qrEntry.timestamp)
                            
                            // Check if this is the current time slot QR
                            if (qrEntry.timestamp == targetTimestamp) {
                                val hour = qrEntry.pattern.substring(12, 14).toIntOrNull() ?: 0
                                val slotStartHour = (hour / 2) * 2
                                val slotEndHour = slotStartHour + 2 - 1
                                val timeSlot = String.format("%d:00-%d:59", slotStartHour, slotEndHour)
                                
                                currentSlotQR = QRCodeData(
                                    svgContent = qrEntry.svgContent,
                                    bitmapBase64 = qrEntry.bitmapBase64.takeIf { it.isNotBlank() },
                                    timestamp = if (qrEntry.uploadedAt > 0) qrEntry.uploadedAt else timestamp,
                                    timeSlot = timeSlot,
                                    expiresAt = qrEntry.uploadedAt + 7200000
                                )
                                Log.d(TAG, "Found QR for current time slot!")
                                break
                            }
                            
                            // Track most recent as fallback
                            if (timestamp > mostRecentTimestamp) {
                                mostRecentTimestamp = timestamp
                                
                                val hour = qrEntry.pattern.substring(12, 14).toIntOrNull() ?: 0
                                val slotStartHour = (hour / 2) * 2
                                val slotEndHour = slotStartHour + 2 - 1
                                val timeSlot = String.format("%d:00-%d:59", slotStartHour, slotEndHour)
                                
                                mostRecentQR = QRCodeData(
                                    svgContent = qrEntry.svgContent,
                                    bitmapBase64 = qrEntry.bitmapBase64.takeIf { it.isNotBlank() },
                                    timestamp = if (qrEntry.uploadedAt > 0) qrEntry.uploadedAt else timestamp,
                                    timeSlot = timeSlot,
                                    expiresAt = qrEntry.uploadedAt + 7200000
                                )
                            }
                        }
                    }
                    
                    // Prefer current time slot QR, fall back to most recent
                    val qrToSend = currentSlotQR ?: mostRecentQR
                    
                    if (qrToSend != null) {
                        Log.d(TAG, "Sending QR code: ${if (currentSlotQR != null) "Current time slot" else "Most recent fallback"}")
                        trySend(Result.success(qrToSend))
                    } else {
                        trySend(Result.failure(Exception("No QR codes available")))
                    }
                } catch (e: Exception) {
                    trySend(Result.failure(e))
                }
            }
            
            override fun onCancelled(error: DatabaseError) {
                trySend(Result.failure(error.toException()))
            }
        }
        
        // Listen to changes in the qr_codes path
        qrCodesRef.orderByKey().limitToLast(20).addValueEventListener(listener)
        
        awaitClose {
            qrCodesRef.removeEventListener(listener)
        }
    }

    /**
     * Listen for real-time updates to QR codes (from /latest)
     */
    fun observeLatestQRCode(): Flow<Result<QRCodeData>> = callbackFlow {
        Log.d(TAG, "Starting real-time QR code observation")
        
        val listener = object : ValueEventListener {
            override fun onDataChange(snapshot: DataSnapshot) {
                try {
                    if (!snapshot.exists()) {
                        trySend(Result.failure(Exception("No QR codes available")))
                        return
                    }
                    
                    val qrEntry = snapshot.getValue(FirebaseQREntry::class.java)
                    
                    if (qrEntry != null && qrEntry.svgContent.isNotBlank()) {
                        val hour = qrEntry.pattern.substring(12, 14).toIntOrNull() ?: 0
                        // Time slots are 2-hour blocks: 0-1:59, 2-3:59, 4-5:59, etc.
                        val slotStartHour = (hour / 2) * 2
                        val slotEndHour = slotStartHour + 1
                        val timeSlot = "${slotStartHour}:00-${slotEndHour}:59"
                        
                        val qrData = QRCodeData(
                            svgContent = qrEntry.svgContent,
                            bitmapBase64 = qrEntry.bitmapBase64.takeIf { it.isNotBlank() },
                            timestamp = if (qrEntry.uploadedAt > 0) qrEntry.uploadedAt else parseTimestamp(qrEntry.timestamp),
                            timeSlot = timeSlot,
                            expiresAt = qrEntry.uploadedAt + 7200000
                        )
                        trySend(Result.success(qrData))
                    } else {
                        trySend(Result.failure(Exception("Invalid QR data")))
                    }
                } catch (e: Exception) {
                    trySend(Result.failure(e))
                }
            }
            
            override fun onCancelled(error: DatabaseError) {
                trySend(Result.failure(error.toException()))
            }
        }
        
        latestRef.addValueEventListener(listener)
        
        awaitClose {
            latestRef.removeEventListener(listener)
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
     * Get all available QR codes (for debugging)
     */
    suspend fun getAllQRCodes(): Result<List<Pair<String, QRCodeData>>> = suspendCancellableCoroutine { continuation ->
        qrCodesRef.orderByChild("timestamp").addListenerForSingleValueEvent(object : ValueEventListener {
            override fun onDataChange(snapshot: DataSnapshot) {
                try {
                    val qrCodes = mutableListOf<Pair<String, QRCodeData>>()
                    
                    for (child in snapshot.children) {
                        val key = child.key ?: continue
                        val qrEntry = child.getValue(FirebaseQREntry::class.java) ?: continue
                        
                        if (qrEntry.svgContent.isNotBlank()) {
                            val hour = qrEntry.pattern.substring(12, 14).toIntOrNull() ?: 0
                            // Time slots are 2-hour blocks: 0-1:59, 2-3:59, 4-5:59, etc.
                            val slotStartHour = (hour / 2) * 2
                            val slotEndHour = slotStartHour + 2 - 1
                            val timeSlot = String.format("%d:00-%d:59", slotStartHour, slotEndHour)
                            
                            val qrData = QRCodeData(
                                svgContent = qrEntry.svgContent,
                                bitmapBase64 = qrEntry.bitmapBase64.takeIf { it.isNotBlank() },
                                timestamp = if (qrEntry.uploadedAt > 0) qrEntry.uploadedAt else parseTimestamp(qrEntry.timestamp),
                                timeSlot = timeSlot,
                                expiresAt = qrEntry.uploadedAt + 7200000
                            )
                            qrCodes.add(key to qrData)
                        }
                    }
                    
                    continuation.resume(Result.success(qrCodes))
                } catch (e: Exception) {
                    continuation.resume(Result.failure(e))
                }
            }
            
            override fun onCancelled(error: DatabaseError) {
                continuation.resume(Result.failure(error.toException()))
            }
        })
    }

    /**
     * Parse timestamp string to Long
     */
    private fun parseTimestamp(timestamp: String): Long {
        return try {
            // Expected format: YYYYMMDDHHMMSS (e.g., 20250609072217)
            if (timestamp.length == 14) {
                val dateFormat = java.text.SimpleDateFormat("yyyyMMddHHmmss", java.util.Locale.getDefault())
                // Use default timezone (device local time)
                dateFormat.parse(timestamp)?.time ?: System.currentTimeMillis()
            } else {
                System.currentTimeMillis()
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to parse timestamp: $timestamp", e)
            System.currentTimeMillis()
        }
    }

    /**
     * Get the most recent QR code from the database
     */
    suspend fun getMostRecentQRCode(): Result<QRCodeData> = suspendCancellableCoroutine { continuation ->
        Log.d(TAG, "Fetching most recent QR code")
        
        // Calculate current time slot using device local time
        val calendar = java.util.Calendar.getInstance()
        val currentHour = calendar.get(java.util.Calendar.HOUR_OF_DAY)
        val currentTimeSlotHour = (currentHour / 2) * 2
        
        // Format timestamp for current time slot using local timezone
        val dateFormat = java.text.SimpleDateFormat("yyyyMMdd", java.util.Locale.getDefault())
        val dateStr = dateFormat.format(calendar.time)
        val targetTimestamp = String.format("%s%02d0000", dateStr, currentTimeSlotHour)
        
        Log.d(TAG, "Looking for QR code for current time slot: $targetTimestamp (hour: $currentTimeSlotHour)")
        
        // Query QR codes ordered by timestamp, limited to last 20
        qrCodesRef.orderByKey().limitToLast(20).addListenerForSingleValueEvent(object : ValueEventListener {
            override fun onDataChange(snapshot: DataSnapshot) {
                try {
                    var currentSlotQR: QRCodeData? = null
                    var mostRecentQR: QRCodeData? = null
                    var mostRecentTimestamp = 0L
                    
                    for (child in snapshot.children) {
                        val qrEntry = child.getValue(FirebaseQREntry::class.java) ?: continue
                        
                        if (qrEntry.svgContent.isNotBlank() || qrEntry.bitmapBase64.isNotBlank()) {
                            val timestamp = parseTimestamp(qrEntry.timestamp)
                            
                            // Check if this is the current time slot QR
                            if (qrEntry.timestamp == targetTimestamp) {
                                val hour = qrEntry.pattern.substring(12, 14).toIntOrNull() ?: 0
                                val slotStartHour = (hour / 2) * 2
                                val slotEndHour = slotStartHour + 2 - 1
                                val timeSlot = String.format("%d:00-%d:59", slotStartHour, slotEndHour)
                                
                                currentSlotQR = QRCodeData(
                                    svgContent = qrEntry.svgContent,
                                    bitmapBase64 = qrEntry.bitmapBase64.takeIf { it.isNotBlank() },
                                    timestamp = if (qrEntry.uploadedAt > 0) qrEntry.uploadedAt else timestamp,
                                    timeSlot = timeSlot,
                                    expiresAt = qrEntry.uploadedAt + 7200000
                                )
                                Log.d(TAG, "Found QR for current time slot!")
                                break
                            }
                            
                            // Track most recent as fallback
                            if (timestamp > mostRecentTimestamp) {
                                mostRecentTimestamp = timestamp
                                
                                val hour = qrEntry.pattern.substring(12, 14).toIntOrNull() ?: 0
                                val slotStartHour = (hour / 2) * 2
                                val slotEndHour = slotStartHour + 2 - 1
                                val timeSlot = String.format("%d:00-%d:59", slotStartHour, slotEndHour)
                                
                                mostRecentQR = QRCodeData(
                                    svgContent = qrEntry.svgContent,
                                    bitmapBase64 = qrEntry.bitmapBase64.takeIf { it.isNotBlank() },
                                    timestamp = if (qrEntry.uploadedAt > 0) qrEntry.uploadedAt else timestamp,
                                    timeSlot = timeSlot,
                                    expiresAt = qrEntry.uploadedAt + 7200000
                                )
                            }
                        }
                    }
                    
                    // Prefer current time slot QR, fall back to most recent
                    val qrToReturn = currentSlotQR ?: mostRecentQR
                    
                    if (qrToReturn != null) {
                        Log.d(TAG, "Returning QR code: ${if (currentSlotQR != null) "Current time slot" else "Most recent fallback"}")
                        continuation.resume(Result.success(qrToReturn))
                    } else {
                        continuation.resume(Result.failure(Exception("No QR codes found")))
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "Error finding most recent QR", e)
                    continuation.resume(Result.failure(e))
                }
            }
            
            override fun onCancelled(error: DatabaseError) {
                continuation.resume(Result.failure(error.toException()))
            }
        })
    }

    /**
     * Get QR code for current time slot
     */
    suspend fun getCurrentTimeSlotQRCode(): Result<QRCodeData> = suspendCancellableCoroutine { continuation ->
        Log.d(TAG, "Fetching QR code for current time slot")
        
        // Calculate current time slot
        val now = System.currentTimeMillis()
        val calendar = java.util.Calendar.getInstance()
        val currentHour = calendar.get(java.util.Calendar.HOUR_OF_DAY)
        val currentTimeSlotHour = (currentHour / 2) * 2 // 0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22
        
        // Format timestamp for this time slot (YYYYMMDDHHMMSS)
        val dateFormat = java.text.SimpleDateFormat("yyyyMMdd", java.util.Locale.getDefault())
        val dateStr = dateFormat.format(calendar.time)
        val timeSlotTimestamp = String.format("%s%02d0000", dateStr, currentTimeSlotHour)
        
        Log.d(TAG, "Looking for QR code with timestamp: $timeSlotTimestamp")
        
        // First try to get from qr_codes/timestamp
        qrCodesRef.child(timeSlotTimestamp).addListenerForSingleValueEvent(object : ValueEventListener {
            override fun onDataChange(snapshot: DataSnapshot) {
                if (snapshot.exists()) {
                    try {
                        val qrEntry = snapshot.getValue(FirebaseQREntry::class.java)
                        if (qrEntry != null && qrEntry.svgContent.isNotBlank()) {
                            val hour = qrEntry.pattern.substring(12, 14).toIntOrNull() ?: 0
                            val slotStartHour = (hour / 2) * 2
                            val slotEndHour = slotStartHour + 2 - 1
                            val timeSlot = String.format("%d:00-%d:59", slotStartHour, slotEndHour)
                            
                            val qrData = QRCodeData(
                                svgContent = qrEntry.svgContent,
                                bitmapBase64 = qrEntry.bitmapBase64.takeIf { it.isNotBlank() },
                                timestamp = if (qrEntry.uploadedAt > 0) qrEntry.uploadedAt else parseTimestamp(qrEntry.timestamp),
                                timeSlot = timeSlot,
                                expiresAt = qrEntry.uploadedAt + 7200000
                            )
                            
                            Log.d(TAG, "Found QR code for current time slot")
                            continuation.resume(Result.success(qrData))
                            return
                        }
                    } catch (e: Exception) {
                        Log.e(TAG, "Error parsing QR data", e)
                    }
                }
                
                // If not found, fall back to latest
                Log.d(TAG, "No QR code found for current time slot, falling back to latest")
                latestRef.addListenerForSingleValueEvent(object : ValueEventListener {
                    override fun onDataChange(latestSnapshot: DataSnapshot) {
                        try {
                            if (!latestSnapshot.exists()) {
                                continuation.resume(Result.failure(Exception("No QR code available")))
                                return
                            }
                            
                            val qrEntry = latestSnapshot.getValue(FirebaseQREntry::class.java)
                            if (qrEntry == null || qrEntry.svgContent.isBlank()) {
                                continuation.resume(Result.failure(Exception("Invalid QR data")))
                                return
                            }
                            
                            val hour = qrEntry.pattern.substring(12, 14).toIntOrNull() ?: 0
                            val slotStartHour = (hour / 2) * 2
                            val slotEndHour = slotStartHour + 2 - 1
                            val timeSlot = String.format("%d:00-%d:59", slotStartHour, slotEndHour)
                            
                            val qrData = QRCodeData(
                                svgContent = qrEntry.svgContent,
                                bitmapBase64 = qrEntry.bitmapBase64.takeIf { it.isNotBlank() },
                                timestamp = if (qrEntry.uploadedAt > 0) qrEntry.uploadedAt else parseTimestamp(qrEntry.timestamp),
                                timeSlot = timeSlot,
                                expiresAt = qrEntry.uploadedAt + 7200000
                            )
                            
                            continuation.resume(Result.success(qrData))
                        } catch (e: Exception) {
                            continuation.resume(Result.failure(e))
                        }
                    }
                    
                    override fun onCancelled(error: DatabaseError) {
                        continuation.resume(Result.failure(error.toException()))
                    }
                })
            }
            
            override fun onCancelled(error: DatabaseError) {
                Log.e(TAG, "Database error: ${error.message}")
                continuation.resume(Result.failure(error.toException()))
            }
        })
    }

    /**
     * Prefetch upcoming QR codes (no-op for database since it's real-time)
     */
    suspend fun prefetchUpcomingQRCodes() {
        // Real-time database doesn't need prefetching
        Log.d(TAG, "Prefetch not needed for Realtime Database")
    }
}