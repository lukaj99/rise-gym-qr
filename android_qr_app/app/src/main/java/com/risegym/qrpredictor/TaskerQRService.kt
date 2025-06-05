package com.risegym.qrpredictor

import android.app.Service
import android.content.Intent
import android.graphics.Bitmap
import android.os.IBinder
import android.os.Environment
import java.io.File
import java.io.FileOutputStream
import java.io.IOException
import kotlinx.coroutines.*

class TaskerQRService : Service() {
    
    override fun onBind(intent: Intent?): IBinder? = null
    
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_GENERATE_QR -> {
                generateQRForTasker()
            }
            ACTION_GET_QR_DATA -> {
                getQRDataForTasker()
            }
        }
        return START_NOT_STICKY
    }
    
    private fun generateQRForTasker() {
        // Use coroutine scope for parallel operations on Pixel 9 Pro XL
        val serviceScope = CoroutineScope(Dispatchers.Default + SupervisorJob())
        
        serviceScope.launch {
            try {
                // Parallel QR generation and data collection
                val qrBitmapDeferred = async { 
                    QRCodeGenerator.generateCurrentQRCode(1000) // Higher res for Pixel 9 Pro XL
                }
                val qrDataDeferred = async { 
                    QRPatternGenerator.getCurrentQRContent() 
                }
                val timeBlockDeferred = async { 
                    QRPatternGenerator.getCurrentTimeBlockString() 
                }
                val minutesUpdateDeferred = async { 
                    QRPatternGenerator.getMinutesUntilNextUpdate() 
                }
                
                // Await all parallel operations
                val qrBitmap = qrBitmapDeferred.await()
                val qrData = qrDataDeferred.await()
                val timeBlock = timeBlockDeferred.await()
                val minutesUpdate = minutesUpdateDeferred.await()
                
                // Parallel file operations
                val fileOpsDeferred = async(Dispatchers.IO) {
                    // Save to external storage accessible by Tasker
                    val externalDir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_PICTURES)
                    val qrDir = File(externalDir, "RiseGymQR")
                    if (!qrDir.exists()) {
                        qrDir.mkdirs()
                    }
                    
                    // Parallel file writing
                    val imageWriteJob = async {
                        val qrFile = File(qrDir, "current_qr.png")
                        FileOutputStream(qrFile).use { outputStream ->
                            qrBitmap.compress(Bitmap.CompressFormat.PNG, 100, outputStream)
                        }
                        qrFile
                    }
                    
                    val textWriteJob = async {
                        val dataFile = File(qrDir, "current_qr_data.txt")
                        dataFile.writeText(qrData)
                        dataFile
                    }
                    
                    Pair(imageWriteJob.await(), textWriteJob.await())
                }
                
                val (qrFile, dataFile) = fileOpsDeferred.await()
                
                // Broadcast result for Tasker on main thread
                withContext(Dispatchers.Main) {
                    val resultIntent = Intent(BROADCAST_QR_GENERATED).apply {
                        putExtra("qr_image_path", qrFile.absolutePath)
                        putExtra("qr_data_path", dataFile.absolutePath)
                        putExtra("qr_data", qrData)
                        putExtra("time_block", timeBlock)
                        putExtra("minutes_until_update", minutesUpdate)
                        putExtra("generation_time_ms", System.currentTimeMillis())
                    }
                    sendBroadcast(resultIntent)
                }
                
            } catch (e: Exception) {
                // Broadcast error on main thread
                withContext(Dispatchers.Main) {
                    val errorIntent = Intent(BROADCAST_QR_ERROR).apply {
                        putExtra("error", e.message)
                    }
                    sendBroadcast(errorIntent)
                }
            } finally {
                stopSelf()
            }
        }
    }
    
    private fun getQRDataForTasker() {
        val qrData = QRPatternGenerator.getCurrentQRContent()
        val timeBlock = QRPatternGenerator.getCurrentTimeBlockString()
        val minutesUntilUpdate = QRPatternGenerator.getMinutesUntilNextUpdate()
        
        val resultIntent = Intent(BROADCAST_QR_DATA).apply {
            putExtra("qr_data", qrData)
            putExtra("time_block", timeBlock)
            putExtra("minutes_until_update", minutesUntilUpdate)
        }
        sendBroadcast(resultIntent)
        
        stopSelf()
    }
    
    companion object {
        const val ACTION_GENERATE_QR = "com.risegym.qrpredictor.GENERATE_QR"
        const val ACTION_GET_QR_DATA = "com.risegym.qrpredictor.GET_QR_DATA"
        const val BROADCAST_QR_GENERATED = "com.risegym.qrpredictor.QR_GENERATED"
        const val BROADCAST_QR_DATA = "com.risegym.qrpredictor.QR_DATA"
        const val BROADCAST_QR_ERROR = "com.risegym.qrpredictor.QR_ERROR"
    }
}