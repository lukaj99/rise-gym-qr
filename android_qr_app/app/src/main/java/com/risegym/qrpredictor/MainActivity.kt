package com.risegym.qrpredictor

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.os.Bundle
import android.provider.Settings
import android.util.Base64
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.core.view.WindowCompat
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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.google.firebase.FirebaseApp
import com.risegym.qrpredictor.ui.theme.RiseGymQRPredictorTheme
import com.risegym.qrpredictor.service.FirebaseQRService
import com.risegym.qrpredictor.utils.SVGUtils
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*
import android.util.Log
import kotlinx.coroutines.isActive

class MainActivity : ComponentActivity() {
    private var originalBrightness: Float = -1f
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        
        FirebaseApp.initializeApp(this)
        
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
            originalBrightness = window.attributes.screenBrightness
        } catch (e: Settings.SettingNotFoundException) {
            originalBrightness = WindowManager.LayoutParams.BRIGHTNESS_OVERRIDE_NONE
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
            WindowManager.LayoutParams.BRIGHTNESS_OVERRIDE_NONE
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
    var timeSlot by remember { mutableStateOf("") }
    var minutesUntilUpdate by remember { mutableStateOf(0) }
    var isLoading by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var lastUpdateTime by remember { mutableStateOf<Long>(0) }
    var currentTimeSlot by remember { mutableStateOf("") }
    
    val scope = rememberCoroutineScope()
    val firebaseService = remember { FirebaseQRService() }
    
    // Function to manually refresh QR from Firebase
    val fetchQRCode: suspend () -> Unit = {
        isLoading = true
        errorMessage = null
        
        try {
            val result = firebaseService.getMostRecentQRCode()
            
            result.fold(
                onSuccess = { qrData ->
                    Log.d("MainActivity", "Successfully fetched QR from Firebase")
                    
                    val bitmap = if (!qrData.bitmapBase64.isNullOrBlank()) {
                        // Use base64 PNG if available
                        try {
                            val decodedBytes = Base64.decode(qrData.bitmapBase64, Base64.DEFAULT)
                            BitmapFactory.decodeByteArray(decodedBytes, 0, decodedBytes.size)
                        } catch (e: Exception) {
                            Log.e("MainActivity", "Failed to decode base64 PNG, falling back to SVG", e)
                            SVGUtils.parseSVGToBitmap(qrData.svgContent, 800)
                        }
                    } else {
                        // Fall back to SVG
                        SVGUtils.parseSVGToBitmap(qrData.svgContent, 800)
                    }
                    
                    if (bitmap != null) {
                        qrBitmap?.recycle()
                        qrBitmap = bitmap
                        timeSlot = qrData.timeSlot
                        lastUpdateTime = qrData.timestamp
                        Log.d("MainActivity", "QR timestamp: ${qrData.timestamp}, Date: ${Date(qrData.timestamp)}")
                    } else {
                        errorMessage = "Failed to parse QR code"
                    }
                },
                onFailure = { e ->
                    Log.e("MainActivity", "Failed to fetch QR", e)
                    errorMessage = "Error: ${e.message}"
                }
            )
        } catch (e: Exception) {
            Log.e("MainActivity", "Unexpected error", e)
            errorMessage = "Unexpected error: ${e.message}"
        } finally {
            isLoading = false
        }
    }
    
    // Update current time and calculate minutes until next update
    LaunchedEffect(Unit) {
        var previousTimeSlot = ""
        while (isActive) {
            val calendar = Calendar.getInstance()
            val timeFormat = SimpleDateFormat("HH:mm:ss", Locale.getDefault())
            currentTime = timeFormat.format(calendar.time)
            
            // Calculate current time slot
            val currentHour = calendar.get(Calendar.HOUR_OF_DAY)
            val slotStartHour = (currentHour / 2) * 2
            val slotEndHour = slotStartHour + 2 - 1
            currentTimeSlot = String.format("%d:00-%d:59", slotStartHour, slotEndHour)
            
            // Check if time slot has changed
            if (previousTimeSlot.isNotEmpty() && previousTimeSlot != currentTimeSlot) {
                Log.d("MainActivity", "Time slot changed from $previousTimeSlot to $currentTimeSlot, refreshing QR")
                scope.launch { fetchQRCode() }
            }
            previousTimeSlot = currentTimeSlot
            
            // Calculate minutes until next 2-hour block
            val currentMinute = calendar.get(Calendar.MINUTE)
            val hoursUntilNext = if (currentHour % 2 == 0) 2 else 1
            minutesUntilUpdate = (hoursUntilNext * 60) - currentMinute
            
            delay(1000) // Update every second
        }
    }
    
    // Listen for real-time updates from Firebase
    LaunchedEffect(Unit) {
        firebaseService.observeMostRecentQRCode().collect { result ->
            result.fold(
                onSuccess = { qrData ->
                    Log.d("MainActivity", "Received real-time QR update from Firebase")
                    
                    val bitmap = if (!qrData.bitmapBase64.isNullOrBlank()) {
                        // Use base64 PNG if available
                        try {
                            val decodedBytes = Base64.decode(qrData.bitmapBase64, Base64.DEFAULT)
                            BitmapFactory.decodeByteArray(decodedBytes, 0, decodedBytes.size)
                        } catch (e: Exception) {
                            Log.e("MainActivity", "Failed to decode base64 PNG, falling back to SVG", e)
                            SVGUtils.parseSVGToBitmap(qrData.svgContent, 800)
                        }
                    } else {
                        // Fall back to SVG
                        SVGUtils.parseSVGToBitmap(qrData.svgContent, 800)
                    }
                    
                    if (bitmap != null) {
                        qrBitmap?.recycle()
                        qrBitmap = bitmap
                        timeSlot = qrData.timeSlot
                        lastUpdateTime = qrData.timestamp
                        errorMessage = null
                        Log.d("MainActivity", "Real-time QR timestamp: ${qrData.timestamp}, Date: ${Date(qrData.timestamp)}")
                    } else {
                        errorMessage = "Failed to parse QR code"
                    }
                },
                onFailure = { e ->
                    Log.e("MainActivity", "Real-time update error", e)
                    errorMessage = "Error: ${e.message}"
                }
            )
        }
    }
    
    // Prefetch upcoming QR codes
    LaunchedEffect(Unit) {
        delay(5000) // Wait 5 seconds after initial load
        firebaseService.prefetchUpcomingQRCodes()
    }
    
    Surface(
        modifier = Modifier.fillMaxSize(),
        color = MaterialTheme.colorScheme.background
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .systemBarsPadding() // Add padding for status bar and navigation bar
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
                
                Spacer(modifier = Modifier.weight(1f))
                
                // Refresh button
                IconButton(
                    onClick = { 
                        scope.launch { fetchQRCode() }
                    },
                    enabled = !isLoading
                ) {
                    if (isLoading) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(24.dp),
                            strokeWidth = 2.dp
                        )
                    } else {
                        Icon(
                            imageVector = Icons.Default.Refresh,
                            contentDescription = "Refresh QR Code",
                            tint = MaterialTheme.colorScheme.primary
                        )
                    }
                }
            }
            
            // Firebase status indicator
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 16.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFFF5F5F5))
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        imageVector = Icons.Default.Cloud,
                        contentDescription = "Cloud",
                        tint = if (errorMessage == null) Color(0xFF4CAF50) else Color(0xFFFF5252),
                        modifier = Modifier.size(24.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Column {
                        Text(
                            text = "Firebase Cloud",
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Medium
                        )
                        Text(
                            text = if (errorMessage == null) "Connected" else "Error",
                            fontSize = 12.sp,
                            color = Color(0xFF666666)
                        )
                    }
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
            
            // Time slot info
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 16.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFFF5F5F5))
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        text = "Current Time Slot: $currentTimeSlot",
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Medium
                    )
                    if (timeSlot.isNotEmpty() && timeSlot != currentTimeSlot) {
                        Text(
                            text = "QR Code: $timeSlot",
                            fontSize = 14.sp,
                            color = Color(0xFFFF6B6B),
                            fontWeight = FontWeight.Medium,
                            modifier = Modifier.padding(top = 4.dp)
                        )
                    }
                    Text(
                        text = "Next update in $minutesUntilUpdate minutes",
                        fontSize = 14.sp,
                        color = Color(0xFF666666),
                        modifier = Modifier.padding(top = 4.dp)
                    )
                }
            }
            
            // QR Code Display
            Card(
                modifier = Modifier
                    .size(320.dp)
                    .padding(bottom = 16.dp),
                colors = CardDefaults.cardColors(containerColor = Color.White),
                elevation = CardDefaults.cardElevation(defaultElevation = 8.dp)
            ) {
                Box(
                    modifier = Modifier
                        .fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) {
                    when {
                        errorMessage != null -> {
                            Column(
                                horizontalAlignment = Alignment.CenterHorizontally
                            ) {
                                Icon(
                                    imageVector = Icons.Default.Warning,
                                    contentDescription = "Error",
                                    tint = Color(0xFFFF6B6B),
                                    modifier = Modifier.size(48.dp)
                                )
                                Spacer(modifier = Modifier.height(8.dp))
                                Text(
                                    text = errorMessage ?: "Unknown error",
                                    color = Color(0xFFFF6B6B),
                                    fontSize = 14.sp,
                                    textAlign = TextAlign.Center,
                                    modifier = Modifier.padding(horizontal = 16.dp)
                                )
                            }
                        }
                        isLoading -> {
                            Column(
                                horizontalAlignment = Alignment.CenterHorizontally
                            ) {
                                CircularProgressIndicator(
                                    modifier = Modifier.size(40.dp)
                                )
                                Spacer(modifier = Modifier.height(8.dp))
                                Text(
                                    text = "Loading from Firebase...",
                                    fontSize = 14.sp,
                                    color = Color(0xFF666666)
                                )
                            }
                        }
                        qrBitmap != null -> {
                            Image(
                                bitmap = qrBitmap!!.asImageBitmap(),
                                contentDescription = "QR Code",
                                modifier = Modifier.fillMaxSize()
                            )
                        }
                        else -> {
                            Text(
                                text = "No QR code available",
                                color = Color(0xFF666666),
                                fontSize = 14.sp
                            )
                        }
                    }
                }
            }
            
            // Last update info
            if (lastUpdateTime > 0) {
                val currentTime = System.currentTimeMillis()
                val timeDiff = currentTime - lastUpdateTime
                val displayText = if (timeDiff < 60000) { // Less than 1 minute
                    "Last updated: just now"
                } else if (timeDiff < 3600000) { // Less than 1 hour
                    val minutes = timeDiff / 60000
                    "Last updated: $minutes minute${if (minutes > 1) "s" else ""} ago"
                } else {
                    val dateFormat = SimpleDateFormat("HH:mm:ss", Locale.getDefault())
                    "Last updated: ${dateFormat.format(Date(lastUpdateTime))}"
                }
                
                Text(
                    text = displayText,
                    fontSize = 12.sp,
                    color = Color(0xFF666666),
                    modifier = Modifier.padding(top = 8.dp)
                )
                
                // Debug info
                Log.d("MainActivity", "Last update timestamp: $lastUpdateTime (${Date(lastUpdateTime)})")
            }
        }
    }
}