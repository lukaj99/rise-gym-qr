package com.risegym.qrpredictor.utils

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Rect
import android.util.Log
import com.caverock.androidsvg.SVG

/**
 * Utility class for parsing SVG content to Bitmap
 */
object SVGUtils {
    private const val TAG = "SVGUtils"
    
    /**
     * Parse SVG content string to Bitmap
     */
    fun parseSVGToBitmap(svgContent: String, size: Int): Bitmap? {
        return try {
            // Validate SVG content
            if (svgContent.isBlank()) {
                Log.e(TAG, "SVG content is empty")
                return null
            }
            
            val svg = SVG.getFromString(svgContent)
            
            // First render the SVG at its native size
            val svgSize = 580
            val tempBitmap = Bitmap.createBitmap(svgSize, svgSize, Bitmap.Config.ARGB_8888)
            val tempCanvas = Canvas(tempBitmap)
            tempCanvas.drawColor(Color.WHITE)
            svg.renderToCanvas(tempCanvas)
            
            // Now create the final bitmap and draw the QR portion scaled
            val bitmap = Bitmap.createBitmap(size, size, Bitmap.Config.ARGB_8888)
            val canvas = Canvas(bitmap)
            canvas.drawColor(Color.WHITE)
            
            // The QR code is from 80,80 to 500,500 in the 580x580 SVG
            val srcRect = Rect(80, 80, 500, 500)  // QR code bounds in source
            
            // Add 5% padding on each side
            val padding = (size * 0.05f).toInt()
            val dstRect = Rect(padding, padding, size - padding, size - padding)
            
            val paint = Paint().apply {
                isFilterBitmap = true
                isAntiAlias = true
            }
            
            canvas.drawBitmap(tempBitmap, srcRect, dstRect, paint)
            
            // Clean up temp bitmap
            tempBitmap.recycle()
            
            Log.d(TAG, "Successfully parsed SVG to ${size}x${size} bitmap via intermediate")
            bitmap
        } catch (e: Exception) {
            Log.e(TAG, "Failed to parse SVG: ${e.message}", e)
            null
        }
    }
}