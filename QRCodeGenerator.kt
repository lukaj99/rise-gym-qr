package com.risegym.qrpredictor

import android.graphics.Bitmap
import android.graphics.Color
import com.google.zxing.BarcodeFormat
import com.google.zxing.EncodeHintType
import com.google.zxing.qrcode.QRCodeWriter
import com.google.zxing.qrcode.decoder.ErrorCorrectionLevel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import java.util.concurrent.ConcurrentHashMap

/**
 * Generates QR codes with proper module configuration and padding
 * Optimized for multi-threading on Pixel 9 Pro XL (Tensor G4)
 */
object QRCodeGenerator {
    
    // Thread-safe cache for QR codes (leveraging 16GB RAM on Pixel 9 Pro XL)
    private val qrCache = ConcurrentHashMap<String, Bitmap>()
    
    /**
     * Generate QR code bitmap with proper padding for scanning
     * 
     * @param content The text content to encode
     * @param size The desired size of the QR code (including padding)
     * @param moduleCount Expected module count (for validation, optional)
     * @return Bitmap with QR code and black padding bars
     */
    fun generateQRCodeWithPadding(
        content: String, 
        size: Int = 800,
        moduleCount: Int? = null
    ): Bitmap {
        val qrCodeWriter = QRCodeWriter()
        
        // Configure QR generation hints - Use Q level for 100% match!
        val hints = hashMapOf<EncodeHintType, Any>().apply {
            put(EncodeHintType.ERROR_CORRECTION, ErrorCorrectionLevel.Q)  // Q level for pixel-perfect match
            put(EncodeHintType.MARGIN, 4) // Quiet zone margin (4 modules)
            put(EncodeHintType.CHARACTER_SET, "UTF-8")
            put(EncodeHintType.QR_VERSION, 1) // Force version 1 (21x21 modules)
        }
        
        try {
            // Generate QR code matrix
            val bitMatrix = qrCodeWriter.encode(content, BarcodeFormat.QR_CODE, size, size, hints)
            
            // Create bitmap with black padding
            val bitmap = Bitmap.createBitmap(size, size, Bitmap.Config.RGB_565)
            
            // Calculate actual QR area (exclude padding)
            val qrStartX = findQRStart(bitMatrix, true)
            val qrStartY = findQRStart(bitMatrix, false)
            val qrEndX = findQREnd(bitMatrix, true)
            val qrEndY = findQREnd(bitMatrix, false)
            
            val qrWidth = qrEndX - qrStartX + 1
            val qrHeight = qrEndY - qrStartY + 1
            
            // Add extra padding for better scanning
            val paddingSize = size / 8 // 12.5% padding on each side
            val qrDisplaySize = size - (2 * paddingSize)
            
            // Calculate center position
            val offsetX = paddingSize
            val offsetY = paddingSize
            
            // Fill entire bitmap with white first
            for (x in 0 until size) {
                for (y in 0 until size) {
                    bitmap.setPixel(x, y, Color.WHITE)
                }
            }
            
            // Draw QR code in center with proper scaling
            for (x in 0 until qrDisplaySize) {
                for (y in 0 until qrDisplaySize) {
                    // Map display coordinates to matrix coordinates
                    val matrixX = qrStartX + (x * qrWidth / qrDisplaySize)
                    val matrixY = qrStartY + (y * qrHeight / qrDisplaySize)
                    
                    if (matrixX < bitMatrix.width && matrixY < bitMatrix.height) {
                        val color = if (bitMatrix[matrixX, matrixY]) Color.BLACK else Color.WHITE
                        bitmap.setPixel(offsetX + x, offsetY + y, color)
                    }
                }
            }
            
            // Add black padding bars around the QR code for better scanning contrast
            addPaddingBars(bitmap, paddingSize)
            
            return bitmap
            
        } catch (e: Exception) {
            // Fallback: create simple error bitmap
            return createErrorBitmap(size, "QR Generation Failed")
        }
    }
    
    /**
     * Generate QR code for current time block with aggressive caching
     * Optimized for Pixel 9 Pro XL's 16GB RAM
     */
    suspend fun generateCurrentQRCode(size: Int = 800): Bitmap = withContext(Dispatchers.Default) {
        val content = QRPatternGenerator.getCurrentQRContent()
        val cacheKey = "${content}_${size}"
        
        // Check cache first (utilizing 16GB RAM)
        qrCache[cacheKey]?.let { cachedBitmap ->
            if (!cachedBitmap.isRecycled) {
                return@withContext cachedBitmap
            } else {
                qrCache.remove(cacheKey)
            }
        }
        
        // Generate new QR code on background thread
        val newBitmap = generateQRCodeWithPaddingAsync(content, size)
        
        // Cache for future use (but limit cache size to prevent OOM)
        if (qrCache.size < 50) { // Allow up to 50 cached QR codes
            qrCache[cacheKey] = newBitmap
        }
        
        newBitmap
    }
    
    /**
     * Multi-threaded QR generation leveraging Tensor G4's 9 cores
     */
    private suspend fun generateQRCodeWithPaddingAsync(
        content: String, 
        size: Int = 800,
        moduleCount: Int? = null
    ): Bitmap = coroutineScope {
        val qrCodeWriter = QRCodeWriter()
        
        // Configure QR generation hints - Use Q level for 100% match!
        val hints = hashMapOf<EncodeHintType, Any>().apply {
            put(EncodeHintType.ERROR_CORRECTION, ErrorCorrectionLevel.Q)  // Q level for pixel-perfect match
            put(EncodeHintType.MARGIN, 4) // Quiet zone margin (4 modules)
            put(EncodeHintType.CHARACTER_SET, "UTF-8")
            put(EncodeHintType.QR_VERSION, 1) // Force version 1 (21x21 modules)
        }
        
        try {
            // Generate QR code matrix on background thread
            val bitMatrix = async(Dispatchers.Default) {
                qrCodeWriter.encode(content, BarcodeFormat.QR_CODE, size, size, hints)
            }.await()
            
            // Parallel calculation of QR boundaries
            val boundaryCalculation = async(Dispatchers.Default) {
                val qrStartX = findQRStart(bitMatrix, true)
                val qrStartY = findQRStart(bitMatrix, false)
                val qrEndX = findQREnd(bitMatrix, true)
                val qrEndY = findQREnd(bitMatrix, false)
                
                QuadTuple(qrStartX, qrStartY, qrEndX, qrEndY)
            }
            
            // Create bitmap while boundaries are being calculated
            val bitmap = async(Dispatchers.Default) {
                Bitmap.createBitmap(size, size, Bitmap.Config.RGB_565)
            }
            
            val boundaries = boundaryCalculation.await()
            val resultBitmap = bitmap.await()
            
            // Parallel pixel processing using multiple cores
            val numThreads = 8 // Utilize 8 of Tensor G4's 9 cores for pixel operations
            val pixelJobs = (0 until numThreads).map { threadIndex ->
                async(Dispatchers.Default) {
                    drawQRSection(
                        resultBitmap, bitMatrix, boundaries, 
                        size, threadIndex, numThreads
                    )
                }
            }
            
            // Wait for all pixel operations to complete
            pixelJobs.forEach { it.await() }
            
            // Add padding bars on separate thread
            async(Dispatchers.Default) {
                val paddingSize = size / 8
                addPaddingBars(resultBitmap, paddingSize)
            }.await()
            
            resultBitmap
            
        } catch (e: Exception) {
            // Fallback: create simple error bitmap
            createErrorBitmap(size, "QR Generation Failed")
        }
    }
    
    private data class QuadTuple(val qrStartX: Int, val qrStartY: Int, val qrEndX: Int, val qrEndY: Int)
    
    /**
     * Draw QR code section optimized for multi-core processing
     */
    private fun drawQRSection(
        bitmap: Bitmap,
        bitMatrix: com.google.zxing.common.BitMatrix,
        boundaries: QuadTuple,
        size: Int,
        threadIndex: Int,
        numThreads: Int
    ) {
        val (qrStartX, qrStartY, qrEndX, qrEndY) = boundaries
        val qrWidth = qrEndX - qrStartX + 1
        val qrHeight = qrEndY - qrStartY + 1
        
        val paddingSize = size / 8
        val qrDisplaySize = size - (2 * paddingSize)
        val offsetX = paddingSize
        val offsetY = paddingSize
        
        // Divide work among threads
        val rowsPerThread = size / numThreads
        val startRow = threadIndex * rowsPerThread
        val endRow = if (threadIndex == numThreads - 1) size else (threadIndex + 1) * rowsPerThread
        
        // Fill background with white
        for (y in startRow until endRow) {
            for (x in 0 until size) {
                bitmap.setPixel(x, y, Color.WHITE)
            }
        }
        
        // Draw QR code section
        for (y in maxOf(startRow, paddingSize) until minOf(endRow, paddingSize + qrDisplaySize)) {
            for (x in paddingSize until paddingSize + qrDisplaySize) {
                val qrX = x - offsetX
                val qrY = y - offsetY
                
                if (qrX >= 0 && qrX < qrDisplaySize && qrY >= 0 && qrY < qrDisplaySize) {
                    val matrixX = qrStartX + (qrX * qrWidth / qrDisplaySize)
                    val matrixY = qrStartY + (qrY * qrHeight / qrDisplaySize)
                    
                    if (matrixX < bitMatrix.width && matrixY < bitMatrix.height) {
                        val color = if (bitMatrix[matrixX, matrixY]) Color.BLACK else Color.WHITE
                        bitmap.setPixel(x, y, color)
                    }
                }
            }
        }
    }
    
    /**
     * Find start position of actual QR data (excluding quiet zone)
     */
    private fun findQRStart(bitMatrix: com.google.zxing.common.BitMatrix, horizontal: Boolean): Int {
        val size = if (horizontal) bitMatrix.width else bitMatrix.height
        
        for (i in 0 until size) {
            for (j in 0 until (if (horizontal) bitMatrix.height else bitMatrix.width)) {
                val x = if (horizontal) i else j
                val y = if (horizontal) j else i
                if (bitMatrix[x, y]) {
                    return i
                }
            }
        }
        return 0
    }
    
    /**
     * Find end position of actual QR data (excluding quiet zone)
     */
    private fun findQREnd(bitMatrix: com.google.zxing.common.BitMatrix, horizontal: Boolean): Int {
        val size = if (horizontal) bitMatrix.width else bitMatrix.height
        
        for (i in size - 1 downTo 0) {
            for (j in 0 until (if (horizontal) bitMatrix.height else bitMatrix.width)) {
                val x = if (horizontal) i else j
                val y = if (horizontal) j else i
                if (bitMatrix[x, y]) {
                    return i
                }
            }
        }
        return size - 1
    }
    
    /**
     * Add black padding bars around QR code for better scanning
     */
    private fun addPaddingBars(bitmap: Bitmap, paddingSize: Int) {
        val width = bitmap.width
        val height = bitmap.height
        
        // Top and bottom black bars
        for (x in 0 until width) {
            for (y in 0 until paddingSize / 4) {
                bitmap.setPixel(x, y, Color.BLACK)
                bitmap.setPixel(x, height - 1 - y, Color.BLACK)
            }
        }
        
        // Left and right black bars  
        for (y in 0 until height) {
            for (x in 0 until paddingSize / 4) {
                bitmap.setPixel(x, y, Color.BLACK)
                bitmap.setPixel(width - 1 - x, y, Color.BLACK)
            }
        }
    }
    
    /**
     * Create error bitmap when QR generation fails
     */
    private fun createErrorBitmap(size: Int, message: String): Bitmap {
        val bitmap = Bitmap.createBitmap(size, size, Bitmap.Config.RGB_565)
        
        // Fill with gray
        for (x in 0 until size) {
            for (y in 0 until size) {
                bitmap.setPixel(x, y, Color.GRAY)
            }
        }
        
        return bitmap
    }
    
    /**
     * Generate QR code with content (for backward compatibility)
     */
    fun generateQRCode(content: String, size: Int = 800): Bitmap {
        return generateQRCodeWithPadding(content, size)
    }
    
    /**
     * Validate QR code format
     */
    fun validateQRCode(content: String): Boolean {
        // Validate Rise Gym QR format: 9268MMDDYYYYHHMMSS (18 chars)
        if (content.length != 18 || !content.startsWith("9268")) {
            return false
        }
        
        return try {
            // Validate date components
            val month = content.substring(4, 6).toInt()
            val day = content.substring(6, 8).toInt()
            val year = content.substring(8, 12).toInt()
            val hour = content.substring(12, 14).toInt()
            val suffix = content.substring(16, 18)
            
            // Check valid ranges
            month in 1..12 && 
            day in 1..31 && 
            year in 2020..2030 && 
            hour in 0..22 && 
            hour % 2 == 0 && 
            (suffix == "00" || suffix == "01")
            
        } catch (e: Exception) {
            false
        }
    }
}