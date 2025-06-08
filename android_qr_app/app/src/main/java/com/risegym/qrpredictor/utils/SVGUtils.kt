package com.risegym.qrpredictor.utils

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.util.Log
import org.xmlpull.v1.XmlPullParser
import org.xmlpull.v1.XmlPullParserFactory
import java.io.StringReader
import kotlin.math.roundToInt

object SVGUtils {
    private const val TAG = "SVGUtils"

    fun parseSVGToBitmap(svgContent: String, targetSize: Int = 800): Bitmap? {
        try {
            val factory = XmlPullParserFactory.newInstance()
            factory.isNamespaceAware = true
            val parser = factory.newPullParser()
            parser.setInput(StringReader(svgContent))

            var width = 0
            var height = 0
            val rectangles = mutableListOf<Rectangle>()

            var eventType = parser.eventType
            while (eventType != XmlPullParser.END_DOCUMENT) {
                when (eventType) {
                    XmlPullParser.START_TAG -> {
                        when (parser.name?.lowercase()) {
                            "svg" -> {
                                // Parse SVG dimensions
                                val widthStr = parser.getAttributeValue(null, "width")
                                val heightStr = parser.getAttributeValue(null, "height")
                                width = widthStr?.replace("px", "")?.toIntOrNull() ?: 0
                                height = heightStr?.replace("px", "")?.toIntOrNull() ?: 0
                            }
                            "rect" -> {
                                // Parse rectangle attributes
                                val x = parser.getAttributeValue(null, "x")?.toFloatOrNull() ?: 0f
                                val y = parser.getAttributeValue(null, "y")?.toFloatOrNull() ?: 0f
                                val rectWidth = parser.getAttributeValue(null, "width")?.toFloatOrNull() ?: 0f
                                val rectHeight = parser.getAttributeValue(null, "height")?.toFloatOrNull() ?: 0f
                                val fill = parser.getAttributeValue(null, "fill") ?: "black"
                                
                                rectangles.add(Rectangle(x, y, rectWidth, rectHeight, fill))
                            }
                        }
                    }
                }
                eventType = parser.next()
            }

            if (width == 0 || height == 0 || rectangles.isEmpty()) {
                Log.e(TAG, "Invalid SVG: width=$width, height=$height, rectangles=${rectangles.size}")
                return null
            }

            // Create bitmap
            val scale = targetSize.toFloat() / maxOf(width, height)
            val bitmapWidth = (width * scale).roundToInt()
            val bitmapHeight = (height * scale).roundToInt()
            
            val bitmap = Bitmap.createBitmap(bitmapWidth, bitmapHeight, Bitmap.Config.ARGB_8888)
            val canvas = Canvas(bitmap)
            val paint = Paint().apply {
                isAntiAlias = false // QR codes should have sharp edges
                style = Paint.Style.FILL
            }

            // Fill background with white
            canvas.drawColor(Color.WHITE)

            // Draw rectangles
            for (rect in rectangles) {
                paint.color = when (rect.fill.lowercase()) {
                    "black", "#000000", "#000" -> Color.BLACK
                    "white", "#ffffff", "#fff" -> Color.WHITE
                    else -> Color.BLACK
                }
                
                canvas.drawRect(
                    rect.x * scale,
                    rect.y * scale,
                    (rect.x + rect.width) * scale,
                    (rect.y + rect.height) * scale,
                    paint
                )
            }

            return bitmap
        } catch (e: Exception) {
            Log.e(TAG, "Error parsing SVG", e)
            return null
        }
    }

    private data class Rectangle(
        val x: Float,
        val y: Float,
        val width: Float,
        val height: Float,
        val fill: String
    )
}