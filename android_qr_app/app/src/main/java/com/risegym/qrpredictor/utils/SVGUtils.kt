package com.risegym.qrpredictor.utils

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
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
            
            // Create bitmap with white background
            val bitmap = Bitmap.createBitmap(size, size, Bitmap.Config.ARGB_8888)
            val canvas = Canvas(bitmap)
            canvas.drawColor(Color.WHITE)
            
            // Get SVG dimensions
            val docWidth = svg.documentWidth
            val docHeight = svg.documentHeight
            
            // Calculate scale to fit the bitmap while maintaining aspect ratio
            val scale = minOf(size.toFloat() / docWidth, size.toFloat() / docHeight)
            
            // Center the SVG in the bitmap
            canvas.save()
            canvas.translate(
                (size - docWidth * scale) / 2f,
                (size - docHeight * scale) / 2f
            )
            canvas.scale(scale, scale)
            
            // Render SVG to bitmap
            svg.renderToCanvas(canvas)
            canvas.restore()
            
            Log.d(TAG, "Successfully parsed SVG (${docWidth}x${docHeight}) to ${size}x${size} bitmap")
            bitmap
        } catch (e: Exception) {
            Log.e(TAG, "Failed to parse SVG: ${e.message}", e)
            null
        }
    }
}