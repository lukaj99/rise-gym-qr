package com.risegym.qrpredictor.service

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.work.*
import com.risegym.qrpredictor.MainActivity
import com.risegym.qrpredictor.R
import com.risegym.qrpredictor.scraping.HybridQRFetcher
import com.risegym.qrpredictor.scraping.WebScraperInterface
import com.risegym.qrpredictor.security.SecureCredentialManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.util.concurrent.TimeUnit

/**
 * Background worker for periodic QR code updates
 * Uses WorkManager for reliable background execution
 */
class QRUpdateWorker(
    context: Context,
    params: WorkerParameters
) : CoroutineWorker(context, params) {
    
    companion object {
        private const val TAG = "QRUpdateWorker"
        private const val WORK_NAME = "qr_update_work"
        private const val CHANNEL_ID = "qr_updates"
        private const val NOTIFICATION_ID = 1001
        
        // Input/Output keys
        const val KEY_FORCE_REFRESH = "force_refresh"
        const val KEY_QR_CONTENT = "qr_content"
        const val KEY_FETCH_METHOD = "fetch_method"
        const val KEY_ERROR = "error"
        
        /**
         * Schedule periodic QR updates
         */
        fun schedulePeriodicWork(context: Context, intervalMinutes: Long = 15) {
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build()
            
            val workRequest = PeriodicWorkRequestBuilder<QRUpdateWorker>(
                intervalMinutes, TimeUnit.MINUTES
            )
                .setConstraints(constraints)
                .setBackoffCriteria(
                    BackoffPolicy.LINEAR,
                    60000L, // 1 minute backoff
                    TimeUnit.MILLISECONDS
                )
                .addTag(WORK_NAME)
                .build()
            
            WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                WORK_NAME,
                ExistingPeriodicWorkPolicy.REPLACE,
                workRequest
            )
            
            Log.d(TAG, "Scheduled periodic QR updates every $intervalMinutes minutes")
        }
        
        /**
         * Schedule one-time QR update
         */
        fun scheduleOneTimeWork(context: Context, forceRefresh: Boolean = false) {
            val inputData = workDataOf(
                KEY_FORCE_REFRESH to forceRefresh
            )
            
            val workRequest = OneTimeWorkRequestBuilder<QRUpdateWorker>()
                .setInputData(inputData)
                .setConstraints(
                    Constraints.Builder()
                        .setRequiredNetworkType(NetworkType.CONNECTED)
                        .build()
                )
                .build()
            
            WorkManager.getInstance(context).enqueue(workRequest)
            
            Log.d(TAG, "Scheduled one-time QR update")
        }
        
        /**
         * Cancel all scheduled work
         */
        fun cancelWork(context: Context) {
            WorkManager.getInstance(context).cancelUniqueWork(WORK_NAME)
            Log.d(TAG, "Cancelled QR update work")
        }
    }
    
    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        Log.d(TAG, "Starting QR update work...")
        
        try {
            // Initialize components
            val hybridFetcher = HybridQRFetcher(applicationContext)
            val credentialManager = SecureCredentialManager(applicationContext)
            
            // Check if we have credentials
            val credentials = credentialManager.getCredentials()
            if (credentials == null) {
                Log.w(TAG, "No stored credentials found")
                return@withContext Result.failure(
                    workDataOf(KEY_ERROR to "No credentials stored")
                )
            }
            
            // Set credentials in fetcher
            hybridFetcher.setCredentials(credentials.username, credentials.password)
            
            // Fetch QR code
            val forceRefresh = inputData.getBoolean(KEY_FORCE_REFRESH, false)
            val result = hybridFetcher.fetchQR()
            
            if (result.success) {
                Log.d(TAG, "QR fetch successful via ${result.source}")
                
                // Save result to shared preferences for the app to read
                saveQRResult(result)
                
                // Show notification if app is in background
                if (shouldShowNotification()) {
                    showUpdateNotification(result)
                }
                
                return@withContext Result.success(
                    workDataOf(
                        KEY_QR_CONTENT to result.qrContent,
                        KEY_FETCH_METHOD to result.source.name
                    )
                )
            } else {
                Log.e(TAG, "QR fetch failed: ${result.error}")
                return@withContext Result.retry()
            }
            
        } catch (e: Exception) {
            Log.e(TAG, "Worker error", e)
            return@withContext Result.failure(
                workDataOf(KEY_ERROR to e.message)
            )
        }
    }
    
    /**
     * Save QR result to shared preferences
     */
    private fun saveQRResult(result: WebScraperInterface.QRFetchResult) {
        val prefs = applicationContext.getSharedPreferences("qr_worker_result", Context.MODE_PRIVATE)
        prefs.edit().apply {
            putString("qr_content", result.qrContent)
            putString("fetch_method", result.source.name)
            putLong("timestamp", System.currentTimeMillis())
            apply()
        }
    }
    
    /**
     * Check if we should show a notification
     */
    private fun shouldShowNotification(): Boolean {
        // In a real app, check if the app is in foreground
        return true
    }
    
    /**
     * Show notification about QR update
     */
    private fun showUpdateNotification(result: WebScraperInterface.QRFetchResult) {
        createNotificationChannel()
        
        val intent = Intent(applicationContext, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        }
        
        val pendingIntent = PendingIntent.getActivity(
            applicationContext,
            0,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        
        val notification = NotificationCompat.Builder(applicationContext, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_menu_info_details)
            .setContentTitle("QR Code Updated")
            .setContentText("New QR code fetched via ${result.source}")
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .setContentIntent(pendingIntent)
            .setAutoCancel(true)
            .build()
        
        if (androidx.core.app.ActivityCompat.checkSelfPermission(
                applicationContext,
                android.Manifest.permission.POST_NOTIFICATIONS
            ) == android.content.pm.PackageManager.PERMISSION_GRANTED
        ) {
            NotificationManagerCompat.from(applicationContext).notify(NOTIFICATION_ID, notification)
        }
    }
    
    /**
     * Create notification channel for Android O+
     */
    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val name = "QR Updates"
            val descriptionText = "Notifications about QR code updates"
            val importance = NotificationManager.IMPORTANCE_DEFAULT
            val channel = NotificationChannel(CHANNEL_ID, name, importance).apply {
                description = descriptionText
            }
            
            val notificationManager = applicationContext.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            notificationManager.createNotificationChannel(channel)
        }
    }
}