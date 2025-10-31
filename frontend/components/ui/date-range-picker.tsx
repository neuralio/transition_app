'use client'

/**
 * DateRangePicker Component - Using shadcn Calendar
 *
 * Allows users to select a date range for Sentinel-2 NDVI processing.
 * Uses the proper shadcn calendar component with range selection.
 *
 * Features:
 * - Visual calendar with date range selection
 * - Validation (end >= start)
 * - Formats: YYYY-MM-DD
 * - Callback when dates change
 * - NO default dates - user MUST select manually
 */

import * as React from 'react'
import { CalendarIcon } from 'lucide-react'
import { DateRange } from 'react-day-picker'
import { format } from 'date-fns'

import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Calendar } from '@/components/ui/calendar'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'

interface DateRangePickerProps {
  onDateChange?: (dateRange: { from: string; to: string }) => void
  className?: string
}

export function DateRangePicker({ onDateChange, className }: DateRangePickerProps) {
  // User MUST select dates - NO defaults!
  const [date, setDate] = React.useState<DateRange | undefined>(undefined)

  const handleDateSelect = (selectedDate: DateRange | undefined) => {
    setDate(selectedDate)

    // Convert to YYYY-MM-DD format and notify parent
    if (selectedDate?.from && selectedDate?.to) {
      const fromStr = format(selectedDate.from, 'yyyy-MM-dd')
      const toStr = format(selectedDate.to, 'yyyy-MM-dd')

      if (onDateChange) {
        onDateChange({ from: fromStr, to: toStr })
      }

      console.log('📅 Date range selected:', fromStr, '→', toStr)
    } else if (onDateChange && (!selectedDate?.from || !selectedDate?.to)) {
      // If incomplete selection, notify parent with empty values
      onDateChange({ from: '', to: '' })
    }
  }

  const isDateSelected = date?.from && date?.to

  return (
    <div className={cn('flex flex-col gap-2', className)}>
      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
        📅 Date Range (Sentinel-2 Data)
      </label>

      <Popover>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            className={cn(
              'w-full justify-start text-left font-normal',
              !date && 'text-muted-foreground'
            )}
          >
            <CalendarIcon className="mr-2 h-4 w-4" />
            {date?.from ? (
              date.to ? (
                <>
                  {format(date.from, 'LLL dd, y')} - {format(date.to, 'LLL dd, y')}
                </>
              ) : (
                format(date.from, 'LLL dd, y')
              )
            ) : (
              <span>Pick a date range</span>
            )}
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-0" align="start">
          <Calendar
            mode="range"
            defaultMonth={date?.from}
            selected={date}
            onSelect={handleDateSelect}
            numberOfMonths={2}
            disabled={(date) => date > new Date() || date < new Date('2015-01-01')}
          />
        </PopoverContent>
      </Popover>

      {!isDateSelected ? (
        <p className="text-xs text-orange-600 dark:text-orange-400 font-medium">
          ⚠️ Required: Select both start and end dates to enable NDVI processing
        </p>
      ) : (
        <p className="text-xs text-green-600 dark:text-green-400">
          ✓ Date range selected: {format(date.from, 'yyyy-MM-dd')} to {format(date.to, 'yyyy-MM-dd')}
        </p>
      )}

      <p className="text-xs text-gray-500 dark:text-gray-400">
        Select date range for NDVI/NDWI computation from Sentinel-2 (2015-present)
      </p>
    </div>
  )
}
