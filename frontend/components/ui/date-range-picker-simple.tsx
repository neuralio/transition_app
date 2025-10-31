'use client'

/**
 * DateRangePicker Component (Simplified - No Popover)
 *
 * Allows users to select a date range for Sentinel-2 NDVI processing.
 * Simple version without Popover dependency.
 *
 * Features:
 * - Start date and end date selection
 * - Validation (end >= start)
 * - Formats: YYYY-MM-DD
 * - Callback when dates change
 */

import React, { useState } from 'react'
import { CalendarIcon } from 'lucide-react'

interface DateRange {
  from: string  // YYYY-MM-DD format
  to: string    // YYYY-MM-DD format
}

interface DateRangePickerProps {
  onDateChange?: (dateRange: DateRange) => void
  className?: string
}

export function DateRangePicker({ onDateChange, className = '' }: DateRangePickerProps) {
  // User MUST select dates - NO defaults, NO hardcoded values!
  const [dateRange, setDateRange] = useState<DateRange>({
    from: '',
    to: ''
  })

  const handleStartDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newStart = e.target.value
    const newRange = { ...dateRange, from: newStart }
    setDateRange(newRange)
    if (onDateChange) {
      onDateChange(newRange)
    }
  }

  const handleEndDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newEnd = e.target.value
    const newRange = { ...dateRange, to: newEnd }
    setDateRange(newRange)
    if (onDateChange) {
      onDateChange(newRange)
    }
  }

  const isValidRange = dateRange.from <= dateRange.to

  return (
    <div className={`flex flex-col gap-2 ${className}`}>
      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
        📅 Date Range (Sentinel-2 Data)
      </label>

      <div className="flex flex-col gap-2 p-3 border border-gray-300 dark:border-gray-700 rounded-md bg-white dark:bg-gray-900">
        <div className="flex items-center gap-2">
          <CalendarIcon className="h-4 w-4 text-gray-500" />
          <span className="text-sm text-gray-600 dark:text-gray-400">
            {dateRange.from && dateRange.to ? (
              <span>{dateRange.from} → {dateRange.to}</span>
            ) : (
              <span>Select date range</span>
            )}
          </span>
        </div>

        <div className="flex flex-col gap-2">
          <div>
            <label className="text-xs text-gray-600 dark:text-gray-400">
              Start Date
            </label>
            <input
              type="date"
              value={dateRange.from}
              onChange={handleStartDateChange}
              className="w-full mt-1 px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-md bg-white dark:bg-gray-900 text-sm"
            />
          </div>

          <div>
            <label className="text-xs text-gray-600 dark:text-gray-400">
              End Date
            </label>
            <input
              type="date"
              value={dateRange.to}
              onChange={handleEndDateChange}
              className="w-full mt-1 px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-md bg-white dark:bg-gray-900 text-sm"
            />
          </div>

          {!isValidRange && (
            <p className="text-xs text-red-500">
              End date must be after start date
            </p>
          )}
        </div>
      </div>

      {!dateRange.from || !dateRange.to ? (
        <p className="text-xs text-orange-600 dark:text-orange-400 font-medium">
          ⚠️ Required: Select both start and end dates to enable NDVI processing
        </p>
      ) : (
        <p className="text-xs text-green-600 dark:text-green-400">
          ✓ Date range selected ({dateRange.from} to {dateRange.to})
        </p>
      )}
    </div>
  )
}
