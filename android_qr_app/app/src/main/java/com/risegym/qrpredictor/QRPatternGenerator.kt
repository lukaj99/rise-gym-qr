package com.risegym.qrpredictor

import java.util.*

/**
 * Generates QR patterns for Rise Gym based on reverse-engineered pattern
 * Pattern: 9268 + MMDDYYYY + HHMMSS
 * - 9268: Facility code
 * - MMDDYYYY: Date in US format
 * - HH: 2-hour time slot (00, 02, 04, ..., 22)
 * - MM: Always "00"
 * - SS: "01" for 00:00-01:59 slot, "00" for all other slots
 */
object QRPatternGenerator {
    
    private const val FACILITY_CODE = "9268"
    
    /**
     * Get current 2-hour time block (0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22)
     */
    fun getCurrentHourBlock(): Int {
        val calendar = Calendar.getInstance()
        val currentHour = calendar.get(Calendar.HOUR_OF_DAY)
        return (currentHour / 2) * 2
    }
    
    /**
     * Generate QR content string for given hour block
     * Format: 9268MMDDYYYY(HH)MM(SS)
     * SS is 01 for 00:00-01:59 slot, 00 for all others
     */
    fun generateQRContent(hourBlock: Int, calendar: Calendar = Calendar.getInstance()): String {
        val month = calendar.get(Calendar.MONTH) + 1  // Calendar.MONTH is 0-based
        val day = calendar.get(Calendar.DAY_OF_MONTH)
        val year = calendar.get(Calendar.YEAR)
        
        // Format date as MMDDYYYY
        val dateStr = String.format("%02d%02d%04d", month, day, year)
        
        // Time component: HHMMSS
        val timeStr = String.format("%02d00%02d", hourBlock, if (hourBlock == 0) 1 else 0)
        
        return "$FACILITY_CODE$dateStr$timeStr"
    }
    
    /**
     * Generate QR content for current time
     */
    fun getCurrentQRContent(): String {
        return generateQRContent(getCurrentHourBlock())
    }
    
    /**
     * Get minutes until next time block change
     */
    fun getMinutesUntilNextUpdate(): Int {
        val calendar = Calendar.getInstance()
        val currentHour = calendar.get(Calendar.HOUR_OF_DAY)
        val currentMinute = calendar.get(Calendar.MINUTE)
        
        // Calculate hours until next even hour
        val hoursUntilNext = if (currentHour % 2 == 0) 2 else 1
        
        // Total minutes until next update
        return (hoursUntilNext * 60) - currentMinute
    }
    
    /**
     * Get formatted time block string (e.g., "14:00-15:59")
     */
    fun getTimeBlockString(hourBlock: Int): String {
        val endHour = (hourBlock + 2) % 24
        return String.format("%02d:00-%02d:59", hourBlock, endHour - 1)
    }
    
    /**
     * Get current time block string
     */
    fun getCurrentTimeBlockString(): String {
        return getTimeBlockString(getCurrentHourBlock())
    }
    
    /**
     * Generate QR content for a specific date and time
     */
    fun generateQRContentForDateTime(year: Int, month: Int, day: Int, hour: Int): String {
        val calendar = Calendar.getInstance().apply {
            set(Calendar.YEAR, year)
            set(Calendar.MONTH, month - 1)  // Calendar months are 0-based
            set(Calendar.DAY_OF_MONTH, day)
            set(Calendar.HOUR_OF_DAY, hour)
        }
        
        val hourBlock = (hour / 2) * 2
        return generateQRContent(hourBlock, calendar)
    }
    
    /**
     * Parse QR content to extract components
     */
    data class QRComponents(
        val facilityCode: String,
        val date: String,
        val time: String,
        val timeSlot: String
    )
    
    fun parseQRContent(content: String): QRComponents? {
        if (content.length != 18 || !content.startsWith(FACILITY_CODE)) {
            return null
        }
        
        return try {
            val facility = content.substring(0, 4)
            val month = content.substring(4, 6)
            val day = content.substring(6, 8)
            val year = content.substring(8, 12)
            val hour = content.substring(12, 14)
            val suffix = content.substring(16, 18)
            
            QRComponents(
                facilityCode = facility,
                date = "$month/$day/$year",
                time = "$hour:00:00",
                timeSlot = getTimeBlockString(hour.toInt())
            )
        } catch (e: Exception) {
            null
        }
    }
}