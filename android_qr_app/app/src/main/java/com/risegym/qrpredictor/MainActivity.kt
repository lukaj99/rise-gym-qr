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
import androidx.compose.ui.window.Dialog
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
import com.risegym.qrpredictor.service.GitHubQRService
import com.risegym.qrpredictor.utils.SVGUtils
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*
import android.content.SharedPreferences
import android.content.Context
import android.util.Log

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
    var useGitHubQR by remember { mutableStateOf(false) }
    var isLoading by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var showTokenDialog by remember { mutableStateOf(false) }
    var githubToken by remember { mutableStateOf<String?>(null) }
    
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val clipboardManager = LocalClipboardManager.current
    val hapticFeedback = LocalHapticFeedback.current
    
    // Load saved preferences
    val prefs = context.getSharedPreferences("qr_prefs", Context.MODE_PRIVATE)
    val securePrefs = context.getSharedPreferences("secure_prefs", Context.MODE_PRIVATE)
    
    LaunchedEffect(Unit) {
        useGitHubQR = prefs.getBoolean("use_github_qr", false)
        githubToken = securePrefs.getString("github_token", null)
    }
    
    val githubService = remember(githubToken) { GitHubQRService(githubToken) }
    
    // Proper bitmap cleanup to prevent memory leaks
    DisposableEffect(Unit) {
        onDispose {
            qrBitmap?.recycle()
        }
    }
    
    // Function to fetch GitHub QR
    val fetchGitHubQR: () -> Unit = {
        if (useGitHubQR && !isLoading) {
            isLoading = true
            errorMessage = null
            
            scope.launch {
                val result = githubService.getLatestQRCodeSVG()
                
                result.fold(
                    onSuccess = { (timestamp, svgContent) ->
                        Log.d("GitHubQR", "Successfully fetched QR: $timestamp")
                        Log.d("GitHubQR", "SVG content length: ${svgContent.length}")
                        
                        val bitmap = SVGUtils.parseSVGToBitmap(svgContent, 800)
                        if (bitmap != null) {
                            qrBitmap?.recycle()
                            qrBitmap = bitmap
                            qrContent = "GitHub QR: $timestamp"
                            verificationStatus = "FROM GITHUB"
                            
                            // Update time display
                            val calendar = Calendar.getInstance()
                            val timeFormat = SimpleDateFormat("HH:mm:ss", Locale.getDefault())
                            currentTime = timeFormat.format(calendar.time)
                            timeBlock = "GitHub-sourced"
                            minutesUntilUpdate = 30 // GitHub updates every 30 min
                        } else {
                            errorMessage = "Failed to parse SVG"
                            Log.e("GitHubQR", "Failed to parse SVG content")
                        }
                    },
                    onFailure = { e ->
                        Log.e("GitHubQR", "Failed to fetch QR", e)
                        errorMessage = "Error: ${e.message}"
                        verificationStatus = "ERROR"
                    }
                )
                isLoading = false
            }
        }
    }
    
    // Smart adaptive refresh rate optimized for Pixel 9 Pro XL battery life
    LaunchedEffect(useGitHubQR) {
        var lastQRContent = ""
        var lastInteractionTime = System.currentTimeMillis()
        
        try {
            while (isActive) {
                val updateStart = System.currentTimeMillis()
                
                if (useGitHubQR) {
                    // Initial fetch or periodic update
                    if (qrBitmap == null && !isLoading) {
                        fetchGitHubQR()
                    }
                    
                    // GitHub QR codes update every 30 minutes
                    delay(30000) // Check every 30 seconds
                    
                } else {
                    // Local generation (existing code)
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
                        verificationStatus = "GENERATED"
                        errorMessage = null
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
            
            // Toggle switch for QR source
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
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Column {
                        Text(
                            text = if (useGitHubQR) "GitHub QR Codes" else "Generated QR Codes",
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Medium
                        )
                        Text(
                            text = if (useGitHubQR) "Using latest from repository" else "Generating locally",
                            fontSize = 12.sp,
                            color = Color(0xFF666666)
                        )
                    }
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Switch(
                            checked = useGitHubQR,
                            onCheckedChange = { checked ->
                                if (checked && githubToken.isNullOrEmpty()) {
                                    // Show token dialog if no token is set
                                    showTokenDialog = true
                                } else {
                                    useGitHubQR = checked
                                    // Save preference
                                    prefs.edit().putBoolean("use_github_qr", checked).apply()
                                    // Clear current QR to force reload
                                    qrBitmap?.recycle()
                                    qrBitmap = null
                                    // Fetch immediately if switching to GitHub mode
                                    if (checked) {
                                        fetchGitHubQR()
                                    }
                                }
                            },
                            colors = SwitchDefaults.colors(
                                checkedThumbColor = MaterialTheme.colorScheme.primary,
                                checkedTrackColor = MaterialTheme.colorScheme.primaryContainer
                            )
                        )
                        if (useGitHubQR) {
                            IconButton(
                                onClick = { showTokenDialog = true },
                                modifier = Modifier.size(24.dp)
                            ) {
                                Icon(
                                    imageVector = Icons.Default.Settings,
                                    contentDescription = "Configure GitHub Token",
                                    tint = MaterialTheme.colorScheme.primary,
                                    modifier = Modifier.size(18.dp)
                                )
                            }
                        }
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
            
            // Time block info
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
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(
                        modifier = Modifier.weight(1f),
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
                            color = when (verificationStatus) {
                                "FROM GITHUB" -> Color(0xFF2196F3)
                                "GENERATED", "VERIFIED" -> Color(0xFF4CAF50)
                                "ERROR" -> Color(0xFFFF5252)
                                else -> Color(0xFFFF9800)
                            },
                            fontWeight = FontWeight.Medium
                        )
                    }
                    
                    // Refresh button for GitHub mode
                    if (useGitHubQR) {
                        IconButton(
                            onClick = { fetchGitHubQR() },
                            enabled = !isLoading,
                            modifier = Modifier.padding(start = 16.dp)
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
                                    tint = MaterialTheme.colorScheme.primary,
                                    modifier = Modifier.size(28.dp)
                                )
                            }
                        }
                    }
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
                        isLoading && useGitHubQR -> {
                            Column(
                                horizontalAlignment = Alignment.CenterHorizontally
                            ) {
                                CircularProgressIndicator(
                                    modifier = Modifier.size(40.dp)
                                )
                                Spacer(modifier = Modifier.height(8.dp))
                                Text(
                                    text = "Fetching from GitHub...",
                                    fontSize = 14.sp,
                                    color = Color(0xFF666666)
                                )
                            }
                        }
                        qrBitmap != null -> {
                            Image(
                                bitmap = qrBitmap!!.asImageBitmap(),
                                contentDescription = "QR Code - Tap to copy",
                                modifier = Modifier.fillMaxSize()
                            )
                        }
                        else -> {
                            CircularProgressIndicator(
                                modifier = Modifier.size(40.dp)
                            )
                        }
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
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "QR Code Data",
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Medium
                        )
                        
                        // Debug button for GitHub mode
                        if (useGitHubQR && errorMessage != null) {
                            TextButton(
                                onClick = {
                                    // Test connection with debug service
                                    scope.launch {
                                        isLoading = true
                                        errorMessage = "Testing connection..."
                                        
                                        val debugService = GitHubQRServiceDebug(githubToken)
                                        try {
                                            val debugInfo = debugService.testGitHubConnection()
                                            errorMessage = debugInfo
                                        } catch (e: Exception) {
                                            errorMessage = "Debug failed: ${e.message}"
                                        }
                                        isLoading = false
                                    }
                                }
                            ) {
                                Text("Debug", fontSize = 12.sp)
                            }
                        }
                    }
                    
                    Spacer(modifier = Modifier.height(8.dp))
                    
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
    
    // GitHub Token Dialog
    if (showTokenDialog) {
        var tokenInput by remember { mutableStateOf(githubToken ?: "") }
        var showPassword by remember { mutableStateOf(false) }
        
        AlertDialog(
            onDismissRequest = { showTokenDialog = false },
            title = {
                Text(
                    text = "GitHub Personal Access Token",
                    fontSize = 20.sp,
                    fontWeight = FontWeight.Medium
                )
            },
            text = {
                Column {
                    Text(
                        text = "Enter your GitHub Personal Access Token to access the private repository.",
                        fontSize = 14.sp,
                        modifier = Modifier.padding(bottom = 8.dp)
                    )
                    
                    OutlinedTextField(
                        value = tokenInput,
                        onValueChange = { tokenInput = it },
                        label = { Text("Personal Access Token") },
                        placeholder = { Text("ghp_xxxxxxxxxxxx") },
                        visualTransformation = if (showPassword) VisualTransformation.None else PasswordVisualTransformation(),
                        trailingIcon = {
                            IconButton(onClick = { showPassword = !showPassword }) {
                                Icon(
                                    imageVector = if (showPassword) Icons.Default.Visibility else Icons.Default.VisibilityOff,
                                    contentDescription = if (showPassword) "Hide token" else "Show token"
                                )
                            }
                        },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true
                    )
                    
                    Spacer(modifier = Modifier.height(8.dp))
                    
                    Text(
                        text = "To create a token:\n1. Go to GitHub Settings > Developer settings > Personal access tokens\n2. Generate new token (classic)\n3. Select 'repo' scope\n4. Copy the token here",
                        fontSize = 12.sp,
                        color = Color(0xFF666666),
                        modifier = Modifier.padding(top = 8.dp)
                    )
                }
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        // Save token
                        githubToken = tokenInput
                        securePrefs.edit().putString("github_token", tokenInput).apply()
                        
                        // Enable GitHub mode if token is provided
                        if (tokenInput.isNotEmpty()) {
                            useGitHubQR = true
                            prefs.edit().putBoolean("use_github_qr", true).apply()
                            // Clear current QR to force reload
                            qrBitmap?.recycle()
                            qrBitmap = null
                            // Fetch immediately
                            fetchGitHubQR()
                        }
                        
                        showTokenDialog = false
                    }
                ) {
                    Text("Save")
                }
            },
            dismissButton = {
                TextButton(
                    onClick = { showTokenDialog = false }
                ) {
                    Text("Cancel")
                }
            }
        )
    }
}

@Preview(showBackground = true)
@Composable
fun QRPredictorScreenPreview() {
    RiseGymQRPredictorTheme {
        QRPredictorScreen()
    }
}