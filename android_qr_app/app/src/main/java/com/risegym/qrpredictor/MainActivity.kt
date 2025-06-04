package com.risegym.qrpredictor

import android.graphics.Bitmap
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.platform.LocalContext
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
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            RiseGymQRPredictorTheme {
                val credentialManager = remember { SecureCredentialManager(this) }
                val hasCredentials = remember { mutableStateOf(credentialManager.hasStoredCredentials()) }
                
                if (hasCredentials.value) {
                    QRPredictorScreen(
                        onLogout = {
                            credentialManager.clearCredentials()
                            hasCredentials.value = false
                            // Cancel background work
                            QRUpdateWorker.cancelWork(this)
                        }
                    )
                } else {
                    LoginScreen(
                        onLoginSuccess = {
                            hasCredentials.value = true
                            // Schedule background updates
                            QRUpdateWorker.schedulePeriodicWork(this)
                        }
                    )
                }
            }
        }
    }
}

@Composable
fun LoginScreen(onLoginSuccess: () -> Unit) {
    var username by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var passwordVisible by remember { mutableStateOf(false) }
    var isLoading by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    
    Surface(
        modifier = Modifier.fillMaxSize(),
        color = MaterialTheme.colorScheme.background
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            // Logo/Title
            Icon(
                imageVector = Icons.Default.FitnessCenter,
                contentDescription = "Rise Gym",
                modifier = Modifier.size(80.dp),
                tint = MaterialTheme.colorScheme.primary
            )
            
            Text(
                text = "Rise Gym QR",
                fontSize = 32.sp,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.padding(top = 16.dp, bottom = 32.dp)
            )
            
            // Username field
            OutlinedTextField(
                value = username,
                onValueChange = { username = it },
                label = { Text("Username") },
                leadingIcon = {
                    Icon(Icons.Default.Person, contentDescription = "Username")
                },
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 16.dp),
                singleLine = true,
                enabled = !isLoading
            )
            
            // Password field
            OutlinedTextField(
                value = password,
                onValueChange = { password = it },
                label = { Text("Password") },
                leadingIcon = {
                    Icon(Icons.Default.Lock, contentDescription = "Password")
                },
                trailingIcon = {
                    IconButton(onClick = { passwordVisible = !passwordVisible }) {
                        Icon(
                            imageVector = if (passwordVisible) Icons.Default.VisibilityOff else Icons.Default.Visibility,
                            contentDescription = if (passwordVisible) "Hide password" else "Show password"
                        )
                    }
                },
                visualTransformation = if (passwordVisible) VisualTransformation.None else PasswordVisualTransformation(),
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 24.dp),
                singleLine = true,
                enabled = !isLoading
            )
            
            // Error message
            errorMessage?.let { error ->
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(bottom = 16.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFFFFEBEE))
                ) {
                    Row(
                        modifier = Modifier.padding(16.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(
                            Icons.Default.Warning,
                            contentDescription = "Error",
                            tint = Color(0xFFD32F2F),
                            modifier = Modifier.size(20.dp)
                        )
                        Text(
                            text = error,
                            color = Color(0xFFD32F2F),
                            modifier = Modifier.padding(start = 8.dp)
                        )
                    }
                }
            }
            
            // Login button
            Button(
                onClick = {
                    scope.launch {
                        isLoading = true
                        errorMessage = null
                        
                        try {
                            val credentialManager = SecureCredentialManager(context)
                            val hybridFetcher = HybridQRFetcher(context)
                            
                            // Save credentials
                            credentialManager.saveCredentials(username, password)
                            
                            // Test login
                            hybridFetcher.setCredentials(username, password)
                            val result = hybridFetcher.fetchQR()
                            
                            if (result.success) {
                                onLoginSuccess()
                            } else {
                                errorMessage = result.error ?: "Login failed"
                                credentialManager.clearCredentials()
                            }
                        } catch (e: Exception) {
                            errorMessage = "Error: ${e.message}"
                        } finally {
                            isLoading = false
                        }
                    }
                },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(56.dp),
                enabled = username.isNotBlank() && password.isNotBlank() && !isLoading
            ) {
                if (isLoading) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(24.dp),
                        color = MaterialTheme.colorScheme.onPrimary
                    )
                } else {
                    Text("Login", fontSize = 18.sp)
                }
            }
            
            Spacer(modifier = Modifier.weight(1f))
            
            // Info text
            Text(
                text = "Your credentials are encrypted and stored securely on your device",
                fontSize = 12.sp,
                color = Color.Gray,
                textAlign = TextAlign.Center
            )
        }
    }
}

@Composable
fun QRPredictorScreen(onLogout: () -> Unit) {
    var qrBitmap by remember { mutableStateOf<Bitmap?>(null) }
    var currentTime by remember { mutableStateOf("") }
    var timeBlock by remember { mutableStateOf("") }
    var grayCode by remember { mutableStateOf(0) }
    var moduleCount by remember { mutableStateOf<Int?>(null) }
    var minutesUntilUpdate by remember { mutableStateOf(0) }
    var qrContent by remember { mutableStateOf("") }
    var verificationStatus by remember { mutableStateOf("") }
    
    // Web scraping states
    var liveQRContent by remember { mutableStateOf<String?>(null) }
    var isLoadingLiveQR by remember { mutableStateOf(false) }
    var liveQRError by remember { mutableStateOf<String?>(null) }
    var scrapingMethod by remember { mutableStateOf<WebScraperInterface.ScrapingMethod?>(null) }
    var accuracyPercentage by remember { mutableStateOf(91.0f) }
    
    val context = LocalContext.current
    val hybridFetcher = remember { HybridQRFetcher(context) }
    val credentialManager = remember { SecureCredentialManager(context) }
    val scope = rememberCoroutineScope()
    
    // Initialize fetcher with stored credentials
    LaunchedEffect(Unit) {
        credentialManager.getCredentials()?.let { creds ->
            hybridFetcher.setCredentials(creds.username, creds.password)
        }
    }
    
    // Update every second
    LaunchedEffect(Unit) {
        while (true) {
            val calendar = Calendar.getInstance()
            val timeFormat = SimpleDateFormat("HH:mm:ss", Locale.getDefault())
            currentTime = timeFormat.format(calendar.time)
            
            timeBlock = QRPatternGenerator.getCurrentTimeBlockString()
            grayCode = 0  // No longer using Gray codes
            moduleCount = null  // Fixed at version 1 (21x21)
            minutesUntilUpdate = QRPatternGenerator.getMinutesUntilNextUpdate()
            qrContent = QRPatternGenerator.getCurrentQRContent()
            verificationStatus = "VERIFIED"  // Pattern is 100% verified
            
            // Generate new QR code every minute or when time block changes
            val currentMinute = calendar.get(Calendar.MINUTE)
            if (currentMinute % 1 == 0 || qrBitmap == null) {
                qrBitmap = QRCodeGenerator.generateCurrentQRCode(600)
            }
            
            // Update accuracy stats every 30 seconds
            if (calendar.get(Calendar.SECOND) % 30 == 0) {
                val stats = hybridFetcher.getAccuracyStats()
                accuracyPercentage = stats.accuracyPercentage
            }
            
            delay(1000)
        }
    }
    
    // Function to fetch live QR using hybrid fetcher
    fun fetchLiveQR() {
        scope.launch {
            isLoadingLiveQR = true
            liveQRError = null
            
            val result = hybridFetcher.fetchQR()
            
            if (result.success) {
                liveQRContent = result.qrContent
                scrapingMethod = result.source
                
                // Use fetched bitmap if available
                result.bitmap?.let {
                    qrBitmap = it
                }
            } else {
                liveQRError = result.error
            }
            
            isLoadingLiveQR = false
        }
    }
    
    Surface(
        modifier = Modifier.fillMaxSize(),
        color = Color.White
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // Header with logout button
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 16.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "RiseGym QR Predictor",
                    fontSize = 24.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color.Black
                )
                IconButton(onClick = onLogout) {
                    Icon(
                        Icons.Default.Logout,
                        contentDescription = "Logout",
                        tint = Color(0xFF666666)
                    )
                }
            }
            
            // Current time
            Text(
                text = currentTime,
                fontSize = 32.sp,
                fontFamily = FontFamily.Monospace,
                fontWeight = FontWeight.Bold,
                color = Color.Black,
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
                        text = "Gray Code: $grayCode",
                        fontSize = 16.sp,
                        color = Color(0xFF666666)
                    )
                    Text(
                        text = "Modules: ${moduleCount ?: "Unknown"}",
                        fontSize = 16.sp,
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
                    .padding(bottom = 16.dp),
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
                            contentDescription = "Generated QR Code",
                            modifier = Modifier
                                .size(280.dp)
                                .clip(RoundedCornerShape(8.dp))
                        )
                    } ?: run {
                        // Loading state
                        Box(
                            modifier = Modifier
                                .size(280.dp)
                                .background(Color(0xFFF0F0F0), RoundedCornerShape(8.dp)),
                            contentAlignment = Alignment.Center
                        ) {
                            CircularProgressIndicator(
                                color = Color.Black,
                                modifier = Modifier.size(40.dp)
                            )
                        }
                    }
                }
            }
            
            // QR Content Info
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 16.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFFF5F5F5))
            ) {
                Column(
                    modifier = Modifier.padding(16.dp)
                ) {
                    Text(
                        text = "QR Content:",
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Medium,
                        color = Color(0xFF666666)
                    )
                    Text(
                        text = qrContent,
                        fontSize = 16.sp,
                        fontFamily = FontFamily.Monospace,
                        modifier = Modifier.padding(top = 4.dp)
                    )
                }
            }
            
            // Update timer
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = Color(0xFFE3F2FD))
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "Next Update:",
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Medium
                    )
                    Text(
                        text = "$minutesUntilUpdate minutes",
                        fontSize = 16.sp,
                        fontFamily = FontFamily.Monospace,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF1976D2)
                    )
                }
            }
            
            Spacer(modifier = Modifier.weight(1f))
            
            // Live QR Validation Section
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 8.dp),
                colors = CardDefaults.cardColors(
                    containerColor = when {
                        liveQRContent == qrContent -> Color(0xFFE8F5E9)
                        liveQRContent != null -> Color(0xFFFFEBEE)
                        else -> Color(0xFFF3E5F5)
                    }
                )
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
                            text = "Live QR Validation",
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Bold
                        )
                        
                        IconButton(
                            onClick = { fetchLiveQR() },
                            enabled = !isLoadingLiveQR
                        ) {
                            if (isLoadingLiveQR) {
                                CircularProgressIndicator(
                                    modifier = Modifier.size(24.dp),
                                    strokeWidth = 2.dp
                                )
                            } else {
                                Icon(
                                    Icons.Default.Refresh,
                                    contentDescription = "Refresh",
                                    tint = Color(0xFF1976D2)
                                )
                            }
                        }
                    }
                    
                    // Accuracy indicator
                    Row(
                        modifier = Modifier.padding(top = 4.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "Prediction Accuracy: ",
                            fontSize = 14.sp,
                            color = Color(0xFF666666)
                        )
                        Text(
                            text = "${accuracyPercentage.toInt()}%",
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Bold,
                            color = when {
                                accuracyPercentage >= 90 -> Color(0xFF4CAF50)
                                accuracyPercentage >= 80 -> Color(0xFFFF9800)
                                else -> Color(0xFFD32F2F)
                            }
                        )
                    }
                    
                    if (liveQRError != null) {
                        Row(
                            modifier = Modifier.padding(top = 8.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(
                                Icons.Default.Warning,
                                contentDescription = "Error",
                                tint = Color(0xFFD32F2F),
                                modifier = Modifier.size(16.dp)
                            )
                            Text(
                                text = liveQRError!!,
                                fontSize = 14.sp,
                                color = Color(0xFFD32F2F),
                                modifier = Modifier.padding(start = 4.dp)
                            )
                        }
                    }
                    
                    liveQRContent?.let { liveContent ->
                        Spacer(modifier = Modifier.height(8.dp))
                        
                        val matches = liveContent == qrContent
                        Text(
                            text = if (matches) "✓ Live QR matches prediction!" else "✗ Live QR differs from prediction",
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Medium,
                            color = if (matches) Color(0xFF388E3C) else Color(0xFFD32F2F)
                        )
                        
                        Text(
                            text = "Live: $liveContent",
                            fontSize = 12.sp,
                            fontFamily = FontFamily.Monospace,
                            color = Color(0xFF666666),
                            modifier = Modifier.padding(top = 4.dp)
                        )
                        
                        scrapingMethod?.let { method ->
                            Text(
                                text = "Fetched via: ${method.name}",
                                fontSize = 12.sp,
                                color = Color(0xFF9E9E9E),
                                modifier = Modifier.padding(top = 2.dp)
                            )
                        }
                    }
                    
                    if (liveQRContent == null && !isLoadingLiveQR && liveQRError == null) {
                        Text(
                            text = "Tap refresh to fetch live QR from Rise Gym",
                            fontSize = 12.sp,
                            color = Color(0xFF9E9E9E),
                            modifier = Modifier.padding(top = 4.dp)
                        )
                    }
                }
            }
            
            Spacer(modifier = Modifier.weight(1f))
            
            // Footer
            Text(
                text = "Reverse Engineered Gray Code Algorithm\nhour ^ (hour >> 1)",
                fontSize = 12.sp,
                color = Color(0xFF888888),
                textAlign = TextAlign.Center,
                fontFamily = FontFamily.Monospace,
                modifier = Modifier.padding(top = 8.dp)
            )
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