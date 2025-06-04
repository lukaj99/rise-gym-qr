# Rise Gym QR Code Analysis Report
Generated: 2025-06-04T23:37:06.978635
Total QR codes analyzed: 47

## Key Findings
1. **No encryption detected** - QR codes contain plaintext data
2. **Fixed format**: `9268` (facility) + `MMDDYYYY` (date) + `HHMMSS` (time)
3. **Time encoding**: 2-hour slots with special suffixes
   - `0001` suffix for 00:00-01:59 slot
   - `0000` suffix for all other slots

## Pattern Details
```
Position  | Content      | Description
----------|--------------|-------------
0-3       | 9268         | Facility code (constant)
4-11      | MMDDYYYY     | Date
12-13     | HH           | 2-hour slot (00,02,04...22)
14-17     | MMSS         | Suffix (0001 or 0000)
```

## Time Slot Distribution
- 00:00-01:59: 2 QR codes
- 06:00-07:59: 5 QR codes
- 08:00-09:59: 20 QR codes
- 10:00-11:59: 17 QR codes
- 18:00-19:59: 1 QR codes
- 20:00-21:59: 1 QR codes
- 22:00-23:59: 1 QR codes