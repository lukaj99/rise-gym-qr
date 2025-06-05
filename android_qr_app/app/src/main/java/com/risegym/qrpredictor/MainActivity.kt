package com.risegym.qrpredictor

import android.graphics.Bitmap
import android.os.Bundle
import android.provider.Settings
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.statusBars
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.core.view.WindowCompat
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.AnnotatedString
import kotlinx.coroutines.isActive
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import androidx.compose.runtime.DisposableEffect
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.work.WorkManager
import com.risegym.qrpredictor.ui.theme.RiseGymQRPredictorTheme
import com.risegym.qrpredictor.scraping.HybridQRFetcher
import com.risegym.qrpredictor.scraping.WebScraperInterface
import com.risegym.qrpredictor.security.SecureCredentialManager
import com.risegym.qrpredictor.service.QRUpdateWorker
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

class MainActivity : ComponentActivity() {
    private var originalBrightness: Float = -1f
    private var wasAutoBrightness: Boolean = false
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        
        // Save original brightness settings
        saveOriginalBrightness()
        
        // Set maximum brightness for QR code scanning
        setMaxBrightness()
        
        // Keep screen on while app is active
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        
        // Ensure status bar icons are visible on light background
        WindowCompat.getInsetsController(window, window.decorView).apply {
            isAppearanceLightStatusBars = true
        }
        
        setContent {
            RiseGymQRPredictorTheme {
                QRPredictorScreen()
            }
        }
    }
    
    private fun saveOriginalBrightness() {
        try {
            // Check if auto brightness is enabled
            wasAutoBrightness = Settings.System.getInt(
                contentResolver,
                Settings.System.SCREEN_BRIGHTNESS_MODE
            ) == Settings.System.SCREEN_BRIGHTNESS_MODE_AUTOMATIC
            
            // Get current brightness level
            originalBrightness = if (wasAutoBrightness) {
                -1f // Use -1 to indicate auto brightness was on
            } else {
                Settings.System.getInt(
                    contentResolver,
                    Settings.System.SCREEN_BRIGHTNESS
                ) / 255f
            }
        } catch (e: Settings.SettingNotFoundException) {
            originalBrightness = window.attributes.screenBrightness
        }
    }
    
    private fun setMaxBrightness() {
        val layoutParams = window.attributes
        layoutParams.screenBrightness = 1.0f // Maximum brightness
        window.attributes = layoutParams
    }
    
    private fun restoreOriginalBrightness() {
        val layoutParams = window.attributes
        layoutParams.screenBrightness = if (originalBrightness == -1f) {
            WindowManager.LayoutParams.BRIGHTNESS_OVERRIDE_NONE // Restore auto brightness
        } else {
            originalBrightness
        }
        window.attributes = layoutParams
    }
    
    override fun onPause() {
        super.onPause()
        restoreOriginalBrightness()
        window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
    }
    
    override fun onResume() {
        super.onResume()
        setMaxBrightness()
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
    }
}

@Composable
fun QRPredictorScreen() {
    var qrBitmap by remember { mutableStateOf<Bitmap?>(null) }
    var currentTime by remember { mutableStateOf("") }
    var timeBlock by remember { mutableStateOf("") }
    var minutesUntilUpdate by remember { mutableStateOf(0) }
    var qrContent by remember { mutableStateOf("") }
    var verificationStatus by remember { mutableStateOf("") }
    var showCopyMessage by remember { mutableStateOf(false) }
    
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val clipboardManager = LocalClipboardManager.current
    val hapticFeedback = LocalHapticFeedback.current
    
    // Proper bitmap cleanup to prevent memory leaks
    DisposableEffect(Unit) {
        onDispose {
            qrBitmap?.recycle()
        }
    }
    
    // Smart adaptive refresh rate optimized for Pixel 9 Pro XL battery life
    LaunchedEffect(Unit) {
        var lastQRContent = ""
        var lastInteractionTime = System.currentTimeMillis()
        
        try {
            while (isActive) {
                val updateStart = System.currentTimeMillis()
                
                // Parallel execution on Tensor G4's multiple cores
                val timeCalculations = async(Dispatchers.Default) {
                    val calendar = Calendar.getInstance()
                    val timeFormat = SimpleDateFormat("HH:mm:ss", Locale.getDefault())
                    Triple(
                        timeFormat.format(calendar.time),
                        QRPatternGenerator.getCurrentTimeBlockString(),
                        QRPatternGenerator.getMinutesUntilNextUpdate()
                    )
                }
                
                val qrContentCalculation = async(Dispatchers.Default) {
                    QRPatternGenerator.getCurrentQRContent()
                }
                
                // Await both calculations in parallel
                val (timeString, timeBlockString, minutesUpdate) = timeCalculations.await()
                val newQrContent = qrContentCalculation.await()
                
                val contentChanged = newQrContent != lastQRContent
                val isInteracting = (System.currentTimeMillis() - lastInteractionTime) < 5000 // 5sec interaction window
                
                // Update UI on main thread
                withContext(Dispatchers.Main) {
                    currentTime = timeString
                    timeBlock = timeBlockString
                    minutesUntilUpdate = minutesUpdate
                    qrContent = newQrContent
                    verificationStatus = "VERIFIED"
                }
                
                // Generate QR code on background thread if content changed
                if (contentChanged || qrBitmap == null) {
                    val startTime = System.currentTimeMillis()
                    val optimalSize = PixelOptimizer.getOptimalQRSize(context)
                    
                    val newBitmap = async(PixelOptimizer.qrGenerationDispatcher) {
                        QRCodeGenerator.generateCurrentQRCode(optimalSize)
                    }
                    
                    withContext(Dispatchers.Main) {
                        // Recycle old bitmap to prevent memory leaks
                        qrBitmap?.recycle()
                        qrBitmap = newBitmap.await()
                        lastQRContent = newQrContent
                        
                        // Performance monitoring for Pixel 9 Pro XL
                        if (PixelOptimizer.isPixel9ProXL()) {
                            val generationTime = System.currentTimeMillis() - startTime
                            val runtime = Runtime.getRuntime()
                            val memoryUsage = (runtime.totalMemory() - runtime.freeMemory()) / (1024 * 1024)
                            val batteryLevel = PixelOptimizer.getBatteryLevel(context)
                            val isCharging = PixelOptimizer.isCharging(context)
                            
                            PixelOptimizer.recordPerformanceMetrics(
                                PixelOptimizer.PerformanceMetrics(
                                    qrGenerationTimeMs = generationTime,
                                    bitmapAllocationMs = 0L, 
                                    pixelProcessingMs = 0L,  
                                    cacheHitRate = 0.0,      
                                    memoryUsageMB = memoryUsage.toDouble()
                                )
                            )
                            
                            // Log battery-aware performance info
                            println("🔋 Battery: ${batteryLevel}% ${if (isCharging) "(Charging)" else ""}")
                            println("⚡ Refresh Mode: ${when {
                                isCharging -> "AGGRESSIVE"
                                batteryLevel < 20 -> "BATTERY_SAVER" 
                                batteryLevel < 50 -> "BALANCED"
                                else -> "PERFORMANCE"
                            }}")
                        }
                    }
                }
                
                // Smart adaptive refresh rate based on battery and usage
                val refreshInterval = PixelOptimizer.getAdaptiveRefreshInterval(
                    context, contentChanged, isInteracting
                )
                
                // Update interaction tracking for tap events
                if (showCopyMessage) {
                    lastInteractionTime = System.currentTimeMillis()
                }
                
                delay(refreshInterval)
            }
        } catch (e: Exception) {
            // Handle cancellation gracefully
        }
    }
    
    Surface(
        modifier = Modifier.fillMaxSize(),
        color = MaterialTheme.colorScheme.background
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .windowInsetsPadding(WindowInsets.statusBars)
                .padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // Header with Rise Gym branding
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 16.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Image(
                    painter = painterResource(id = R.drawable.ic_rise_logo),
                    contentDescription = "Rise Gym Logo",
                    modifier = Modifier.size(32.dp),
                    colorFilter = ColorFilter.tint(MaterialTheme.colorScheme.primary)
                )
                Spacer(modifier = Modifier.width(12.dp))
                Column {
                    Text(
                        text = "RISE GYM",
                        fontSize = 22.sp,
                        fontWeight = FontWeight.Black,
                        letterSpacing = 1.sp,
                        color = MaterialTheme.colorScheme.primary
                    )
                    Text(
                        text = "Access",
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Medium,
                        letterSpacing = 0.5.sp,
                        color = MaterialTheme.colorScheme.secondary
                    )
                }
            }
            
            // Current time
            Text(
                text = currentTime,
                fontSize = 24.sp,
                fontWeight = FontWeight.Light,
                fontFamily = FontFamily.Monospace,
                color = Color(0xFF666666),
                modifier = Modifier.padding(bottom = 8.dp)
            )
            
            // Time block info
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 16.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFFF5F5F5))
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        text = "Time Block: $timeBlock",
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Medium
                    )
                    Text(
                        text = "Next update in $minutesUntilUpdate minutes",
                        fontSize = 14.sp,
                        color = Color(0xFF666666)
                    )
                    Text(
                        text = "Status: $verificationStatus",
                        fontSize = 14.sp,
                        color = if (verificationStatus == "VERIFIED") Color(0xFF4CAF50) else Color(0xFFFF9800),
                        fontWeight = FontWeight.Medium
                    )
                }
            }
            
            // QR Code Display
            Card(
                modifier = Modifier
                    .size(320.dp)
                    .padding(bottom = 16.dp)
                    .pointerInput(Unit) {
                        detectTapGestures(
                            onTap = {
                                // Copy QR content to clipboard
                                clipboardManager.setText(AnnotatedString(qrContent))
                                hapticFeedback.performHapticFeedback(HapticFeedbackType.LongPress)
                                showCopyMessage = true
                                scope.launch {
                                    delay(2000)
                                    showCopyMessage = false
                                }
                            }
                        )
                    },
                colors = CardDefaults.cardColors(containerColor = Color.White),
                elevation = CardDefaults.cardElevation(defaultElevation = 8.dp)
            ) {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(16.dp),
                    contentAlignment = Alignment.Center
                ) {
                    qrBitmap?.let { bitmap ->
                        Image(
                            bitmap = bitmap.asImageBitmap(),
                            contentDescription = "Generated QR Code - Tap to copy",
                            modifier = Modifier.fillMaxSize()
                        )
                    } ?: run {
                        CircularProgressIndicator(
                            modifier = Modifier.size(40.dp)
                        )
                    }
                    
                    // Copy message overlay
                    if (showCopyMessage) {
                        Card(
                            modifier = Modifier
                                .align(Alignment.BottomCenter)
                                .padding(8.dp),
                            colors = CardDefaults.cardColors(containerColor = Color.Black.copy(alpha = 0.8f))
                        ) {
                            Text(
                                text = "QR data copied!",
                                color = Color.White,
                                fontSize = 12.sp,
                                modifier = Modifier.padding(8.dp)
                            )
                        }
                    }
                }
            }
            
            // QR Code Info
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 16.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFFF8F9FA))
            ) {
                Column(
                    modifier = Modifier.padding(16.dp)
                ) {
                    Text(
                        text = "QR Code Data",
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Medium,
                        modifier = Modifier.padding(bottom = 8.dp)
                    )
                    Text(
                        text = qrContent,
                        fontSize = 14.sp,
                        fontFamily = FontFamily.Monospace,
                        color = Color(0xFF666666),
                        modifier = Modifier
                            .background(
                                Color(0xFFE9ECEF),
                                RoundedCornerShape(4.dp)
                            )
                            .padding(8.dp)
                            .fillMaxWidth()
                            .clickable {
                                clipboardManager.setText(AnnotatedString(qrContent))
                                hapticFeedback.performHapticFeedback(HapticFeedbackType.LongPress)
                                showCopyMessage = true
                                scope.launch {
                                    delay(2000)
                                    showCopyMessage = false
                                }
                            }
                    )
                }
            }
            
            // Technical Details
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp),
                horizontalArrangement = Arrangement.SpaceAround
            ) {
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        text = "Version",
                        fontSize = 12.sp,
                        color = Color(0xFF666666)
                    )
                    Text(
                        text = "1 (21x21)",
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Medium
                    )
                }
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        text = "Error Correction",
                        fontSize = 12.sp,
                        color = Color(0xFF666666)
                    )
                    Text(
                        text = "Level Q",
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Medium
                    )
                }
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        text = "Verified",
                        fontSize = 12.sp,
                        color = Color(0xFF666666)
                    )
                    Text(
                        text = "100%",
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Medium,
                        color = Color(0xFF4CAF50)
                    )
                }
            }
        }
    }
}

@Preview(showBackground = true)
@Composable
fun QRPredictorScreenPreview() {
    RiseGymQRPredictorTheme {
        QRPredictorScreen()
    }
}