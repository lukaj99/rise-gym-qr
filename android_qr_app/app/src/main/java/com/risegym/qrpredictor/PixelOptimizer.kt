package com.risegym.qrpredictor

import android.content.Context
import android.os.Build
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.asCoroutineDispatcher
import java.util.concurrent.Executors

/**
 * Hardware-specific optimizations for Pixel 9 Pro XL (Tensor G4)
 * This class configures threading and performance settings based on device capabilities
 */
object PixelOptimizer {
    
    // Tensor G4 CPU configuration:
    // 1x Cortex-X4 @ 3.1GHz (Prime core)
    // 3x Cortex-A720 @ 2.6GHz (Performance cores) 
    // 4x Cortex-A520 @ 1.95GHz (Efficiency cores)
    // 1x Cortex-A520 @ 1.95GHz (Additional efficiency core)
    
    private const val PIXEL_9_PRO_XL_CORES = 9
    private const val HIGH_PERFORMANCE_THREADS = 8  // Leave 1 core for system
    private const val QR_GENERATION_THREADS = 6     // Optimize for QR bitmap operations
    private const val FILE_IO_THREADS = 2           // Dedicated I/O threads
    
    // Custom dispatchers optimized for Tensor G4
    val qrGenerationDispatcher = Executors.newFixedThreadPool(QR_GENERATION_THREADS) { r ->
        Thread(r, "QR-Gen-Thread").apply {
            priority = Thread.MAX_PRIORITY  // Highest priority for QR generation
        }
    }.asCoroutineDispatcher()
    
    val fileIODispatcher = Executors.newFixedThreadPool(FILE_IO_THREADS) { r ->
        Thread(r, "File-IO-Thread").apply {
            priority = Thread.NORM_PRIORITY + 1
        }
    }.asCoroutineDispatcher()
    
    val computationDispatcher = Dispatchers.Default  // Use default for general computation
    
    /**
     * Check if device is Pixel 9 Pro XL for optimal configuration
     */
    fun isPixel9ProXL(): Boolean {
        return Build.MODEL.contains("Pixel 9 Pro", ignoreCase = true) &&
               Build.MANUFACTURER.equals("Google", ignoreCase = true) &&
               Build.HARDWARE.contains("ripcurrent", ignoreCase = true)  // Tensor G4 codename
    }
    
    /**
     * Get optimal QR code size based on display density
     */
    fun getOptimalQRSize(context: Context): Int {
        val displayMetrics = context.resources.displayMetrics
        
        return when {
            isPixel9ProXL() -> {
                // Pixel 9 Pro XL has 1344 x 2992 @ 486 PPI
                // Generate high-res QR for crystal clear display
                1200
            }
            displayMetrics.densityDpi >= 400 -> 1000  // High DPI displays
            displayMetrics.densityDpi >= 300 -> 800   // Medium-high DPI
            else -> 600  // Standard DPI
        }
    }
    
    /**
     * Get optimal update frequency based on device performance
     * Pixel 9 Pro XL has 120Hz display - let's use it!
     */
    fun getOptimalUpdateInterval(): Long {
        return when {
            isPixel9ProXL() -> 16L   // 60Hz updates (16ms = 1000ms/60fps) for 120Hz display
            Build.VERSION.SDK_INT >= 31 -> 33L  // 30Hz for modern Android devices  
            else -> 1000L  // Standard 1Hz for older devices
        }
    }
    
    /**
     * Get smart refresh interval that balances smoothness with battery life
     * Only use 120Hz when beneficial, drop to lower rates when appropriate
     */
    fun getSmartRefreshInterval(contentChanged: Boolean, isInteracting: Boolean): Long {
        return when {
            isPixel9ProXL() -> {
                when {
                    contentChanged -> 8L           // 120Hz for QR changes (critical moments)
                    isInteracting -> 16L           // 60Hz during user interaction
                    else -> 100L                   // 10Hz for idle time updates (battery saving)
                }
            }
            else -> 1000L  // 1Hz for other devices
        }
    }
    
    /**
     * Check if device is plugged in (use aggressive refresh rates when charging)
     */
    fun isCharging(context: Context): Boolean {
        val batteryManager = context.getSystemService(Context.BATTERY_SERVICE) as android.os.BatteryManager
        return batteryManager.isCharging
    }
    
    /**
     * Get battery level for adaptive performance
     */
    fun getBatteryLevel(context: Context): Int {
        val batteryManager = context.getSystemService(Context.BATTERY_SERVICE) as android.os.BatteryManager
        return batteryManager.getIntProperty(android.os.BatteryManager.BATTERY_PROPERTY_CAPACITY)
    }
    
    /**
     * Adaptive refresh rate based on battery and charging status
     */
    fun getAdaptiveRefreshInterval(
        context: Context, 
        contentChanged: Boolean, 
        isInteracting: Boolean
    ): Long {
        if (!isPixel9ProXL()) return 1000L
        
        val isCharging = isCharging(context)
        val batteryLevel = getBatteryLevel(context)
        
        return when {
            isCharging -> {
                // Aggressive refresh when charging
                if (contentChanged) 8L else if (isInteracting) 16L else 33L
            }
            batteryLevel < 20 -> {
                // Battery saver mode
                if (contentChanged) 100L else 1000L
            }
            batteryLevel < 50 -> {
                // Balanced mode
                if (contentChanged) 33L else if (isInteracting) 100L else 500L
            }
            else -> {
                // Full performance mode
                if (contentChanged) 16L else if (isInteracting) 33L else 100L
            }
        }
    }
    
    /**
     * Get optimal cache size based on available RAM
     */
    fun getOptimalCacheSize(): Int {
        val runtime = Runtime.getRuntime()
        val maxMemory = runtime.maxMemory()
        
        return when {
            isPixel9ProXL() -> 100  // Leverage 16GB RAM for aggressive caching
            maxMemory > 512 * 1024 * 1024 -> 50  // 512MB+ heap
            maxMemory > 256 * 1024 * 1024 -> 25  // 256MB+ heap
            else -> 10  // Conservative caching for low-memory devices
        }
    }
    
    /**
     * Configure GPU acceleration hints for Pixel 9 Pro XL
     */
    fun configureGPUAcceleration(): Map<String, Any> {
        return if (isPixel9ProXL()) {
            mapOf(
                "enable_gpu_rendering" to true,
                "use_vulkan_api" to true,  // Tensor G4 supports Vulkan 1.3
                "enable_compute_shaders" to true,
                "gpu_memory_optimization" to "aggressive"
            )
        } else {
            mapOf(
                "enable_gpu_rendering" to false,
                "use_vulkan_api" to false
            )
        }
    }
    
    /**
     * Performance monitoring for optimization feedback
     */
    data class PerformanceMetrics(
        val qrGenerationTimeMs: Long,
        val bitmapAllocationMs: Long,
        val pixelProcessingMs: Long,
        val cacheHitRate: Double,
        val memoryUsageMB: Double
    )
    
    private var lastMetrics: PerformanceMetrics? = null
    
    fun recordPerformanceMetrics(metrics: PerformanceMetrics) {
        lastMetrics = metrics
        
        // Log performance for optimization (only in debug builds)
        if (true) { // Always log for personal project optimization
            println("🚀 Pixel 9 Pro XL Performance Metrics:")
            println("   QR Generation: ${metrics.qrGenerationTimeMs}ms")
            println("   Bitmap Allocation: ${metrics.bitmapAllocationMs}ms") 
            println("   Pixel Processing: ${metrics.pixelProcessingMs}ms")
            println("   Cache Hit Rate: ${(metrics.cacheHitRate * 100).toInt()}%")
            println("   Memory Usage: ${metrics.memoryUsageMB}MB")
        }
    }
    
    fun getLastMetrics(): PerformanceMetrics? = lastMetrics
}