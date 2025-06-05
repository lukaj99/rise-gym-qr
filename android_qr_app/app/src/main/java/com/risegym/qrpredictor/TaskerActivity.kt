package com.risegym.qrpredictor

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.widget.Toast

class TaskerActivity : Activity() {
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        when (intent?.action) {
            "com.risegym.qrpredictor.GENERATE_QR_IMAGE" -> {
                generateQRImage()
            }
            "com.risegym.qrpredictor.GET_QR_TEXT" -> {
                getQRText()
            }
            else -> {
                // Default action - generate QR
                generateQRImage()
            }
        }
    }
    
    private fun generateQRImage() {
        val serviceIntent = Intent(this, TaskerQRService::class.java).apply {
            action = TaskerQRService.ACTION_GENERATE_QR
        }
        startService(serviceIntent)
        
        // Set result for Tasker
        val resultIntent = Intent().apply {
            putExtra("qr_data", QRPatternGenerator.getCurrentQRContent())
            putExtra("time_block", QRPatternGenerator.getCurrentTimeBlockString())
            putExtra("status", "generating")
        }
        setResult(RESULT_OK, resultIntent)
        
        Toast.makeText(this, "QR code generated for Tasker", Toast.LENGTH_SHORT).show()
        finish()
    }
    
    private fun getQRText() {
        val qrData = QRPatternGenerator.getCurrentQRContent()
        val timeBlock = QRPatternGenerator.getCurrentTimeBlockString()
        val minutesUntilUpdate = QRPatternGenerator.getMinutesUntilNextUpdate()
        
        // Set result for Tasker
        val resultIntent = Intent().apply {
            putExtra("qr_data", qrData)
            putExtra("time_block", timeBlock)
            putExtra("minutes_until_update", minutesUntilUpdate)
            putExtra("status", "success")
        }
        setResult(RESULT_OK, resultIntent)
        
        finish()
    }
}