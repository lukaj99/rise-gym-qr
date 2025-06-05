# Add project specific ProGuard rules here.
# You can control the set of applied configuration files using the
# proguardFiles setting in build.gradle.kts.
#
# For more details, see
#   http://developer.android.com/guide/developing/tools/proguard.html

# If your project uses WebView with JS, uncomment the following
# and specify the fully qualified class name to the JavaScript interface
# class:
#-keepclassmembers class fqcn.of.javascript.interface.for.webview {
#   public *;
#}

# Keep ZXing classes
-keep class com.google.zxing.** { *; }
-keep class com.journeyapps.barcodescanner.** { *; }

# Keep OkHttp classes
-dontwarn okhttp3.**
-keep class okhttp3.** { *; }
-dontwarn okio.**

# Keep Compose classes
-keep class androidx.compose.** { *; }
-dontwarn androidx.compose.**

# Keep coroutines
-keepnames class kotlinx.coroutines.internal.MainDispatcherFactory {}
-keepnames class kotlinx.coroutines.CoroutineExceptionHandler {}

# Keep Tasker integration classes
-keep class com.risegym.qrpredictor.TaskerActivity { *; }
-keep class com.risegym.qrpredictor.TaskerQRService { *; }

# Keep app classes for reflection
-keep class com.risegym.qrpredictor.QRPatternGenerator { *; }
-keep class com.risegym.qrpredictor.QRCodeGenerator { *; }

# Uncomment this to preserve the line number information for
# debugging stack traces.
#-keepattributes SourceFile,LineNumberTable

# If you keep the line number information, uncomment this to
# hide the original source file name.
#-renamesourcefileattribute SourceFile