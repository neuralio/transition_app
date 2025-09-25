<template>
  <div :class="['chart-wrapper', { dark: isDark }]">
    <!-- Loading Overlay -->
    <div v-if="loading" class="loading-overlay">
      <p>Data loading...</p>
      <p>Please wait...</p>
    </div>
    <!-- Chart Container -->
    <div :id="graphId" class="chart-container"></div>
  </div> 
</template>
  
<script setup>
  import * as echarts from 'echarts'
  import { ref, onMounted, watch, defineEmits, defineProps, nextTick } from 'vue'

  const props = defineProps({
    isDark: {
      type: Boolean,
      default: false
    },
    datasets: {
      type: Array, // Accepts multiple datasets (years, scores, layer name)
      default: () => [],
    },
    serviceCalled: {
      type: String,
      default: null
    },
    graphId: {
      type: String,
      required: true
    }
  })

  const emit = defineEmits([
      'trigger-wms-click'
  ])

  const chartInstance = ref(null) // To store the ECharts instance
  const chartDom = ref(null)
  const parentElement = ref(null)
  const loading = ref(false)

  watch(() => props.datasets, (newVal) => {
      if (newVal.length > 0) {
        handleDataUpdate(newVal)
      }
    },
    { deep: true }
  )


  watch(() => props.isDark, (newVal) => {
    console.log("Display mode changed. Re-initializing line chart...")

    if (chartInstance.value) {
      chartInstance.value.dispose()
    }

    initChart() // recreate chart instance
    if (props.datasets.length > 0) {
      updateChart(props.datasets)
    }
  })


  onMounted(() => {
    initChart() // Initialize chart after component mounts

    if (props.datasets.length === 0) {
      console.log("No data to plot...")
      emit('trigger-wms-click')
    } else {
      // Props provided, use them to update the chart
      handleDataUpdate(props.datasets)
    }    
  })

  const initChart = () => {
    // Initialize the ECharts instance
    chartDom.value = document.getElementById(props.graphId)
    chartInstance.value = echarts.init(chartDom.value)

    parentElement.value = chartDom.value.parentElement;
    const observer = new ResizeObserver(() => {
      chartInstance.value?.resize()
    })

    observer.observe(chartDom.value)
  }

  const handleDataUpdate = (newData) => {
    loading.value = true // Show loading state during data preparation
    setTimeout(() => {
      updateChart(newData)
      loading.value = false  // Hide loading once chart is updated
    }, 0)  // Short delay for smoother UI experience
  }

  const updateChart = async (dataSets) => {
    if (!dataSets || dataSets.length === 0 || !chartInstance.value) {
      console.warn("No chart instance or data to update.")
      return   // Exit if no data is available or chart instance is missing
    }

    // Get the union of all years
    const allYearsSet = new Set()

    dataSets.forEach((dataset, i) => {
      if (!dataset || !Array.isArray(dataset.years) || !Array.isArray(dataset.scores)) {
        console.error(`❌ Dataset #${i} is invalid:`, dataset)
      }
    })

    dataSets.forEach((dataset) => {
      dataset.years.forEach((year) => allYearsSet.add(Number(year)))
    })
    const allYears = Array.from(allYearsSet).sort((a, b) => a - b)

    // Align scores for each dataset
    const seriesData = dataSets.map((dataset) => {
      // Create a year-to-score map
      const yearToScore = {}
      dataset.years.forEach((year, index) => {
        yearToScore[Number(year)] = Number(dataset.scores[index])
      })

      // Align scores to match allYears
      const alignedScores = allYears.map((year) => {
        return yearToScore[year] !== undefined ? yearToScore[year] : null
      })

      return {
        name: dataset.layerName,
        type: "line",
        data: alignedScores,
        connectNulls: true, // Connect null values if any
      }
    })

    const textColor = props.isDark ? '#fff' : '#333'
    const bgColor = props.isDark ? '#1f2937' : '#fff'  // dark:bg-gray-800

    const options = {
      title: {
        text: props.graphId.startsWith('profit') ? 'Crop Profits (€)' : `${props.serviceCalled} Suitability Scores`,
        left: "center",
        textStyle: {
          color: textColor,
          fontWeight: "bold",
        },
      },
      tooltip: {
        trigger: "item",
        backgroundColor: props.isDark ? "#333" : "#ffffff",
        borderColor: "#ccc",
        borderWidth: 1,
        textStyle: { color: props.isDark ? "#fff" : "#000" },
        formatter: (params) => {
          // Tooltip to show scores for all datasets at a specific year
          // Ensure params is treated as an array
          const items = Array.isArray(params) ? params : [params]
          
          // Safely access the year and series data
          const year = items[0]?.name || "N/A"  // X-axis year value
          const details = items
            .filter((p) => p.value !== null) // Filter out null values
            .map((p) => `${p.seriesName}: ${p.value}`)
            .join("<br/>")

          return `<strong>Year: ${year}</strong><br/>${details}`
        },
      },
      legend: {
        data: dataSets.map((dataset) => dataset.layerName),
        bottom: "10px",
        show: true,
        orient: "horizontal",
        left: "center",
        textStyle: { color: textColor },
      },
      grid: {
        top: "60px",
        bottom: "60px",
        left: "50px",
        right: "50px",
        containLabel: true,
      },
      xAxis: {
        type: "category",
        data: allYears,
        axisLine: {
          lineStyle: { color: textColor },
        },
        axisLabel: {
          color: textColor,
        },
      },
      yAxis: {
        type: "value",
        splitLine: {
          lineStyle: { type: "dashed", color: props.isDark ? "#444" : "#ddd" },
        },
        axisLine: {
          lineStyle: { color: textColor },
        },
        axisLabel: {
          color: textColor,
        },
      },
      series: seriesData,
      colorBy: "series",
      color: [ "#009688", "#f5fa93", "#d64bde", "#4ba3de", "#f76a6a", "#9e9e9e", "#744bde", "#4bde80", "#607d8b", "#4bded7", "#4b67de" ],
      backgroundColor: bgColor,
    };

      await nextTick()
      chartInstance.value.setOption(options)
      await nextTick()

      setTimeout(() => {
        if (chartInstance.value && typeof chartInstance.value.resize === 'function') {
          new ResizeObserver(() => {
            chartInstance.value.resize({})
          }).observe(chartDom.value)
        } else {
          console.warn("🚫 chartInstance not ready or resize not available", chartInstance.value)
        }
      }, 50)  // Wait briefly for layout to settle
  }
</script>

<style scoped>
  .chart-wrapper {
    position: relative;
    width: 100%;
    min-width: 100%;
  }

  .chart-wrapper.dark .loading-overlay {
    background-color: rgba(30, 30, 30, 0.9);
    color: white;
  }

  .chart-container {
    height: 450px;
    width: 100%;
    min-width: 100%;
    background: #ffffff; /* White background */
    border: 1px solid #ccc; /* Light gray border */
    border-radius: 4px; /* Rounded corners */
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1); /* Subtle shadow */
    padding: 10px; /* Add a small padding */
    margin: 20px 0 0 0;
    box-sizing: border-box;
    overflow: hidden;
  }

  .dark .chart-container {
    background: #1f2937;
  }

  .loading-overlay {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    display: flex;
    justify-content: center;
    align-items: center;
    background-color: rgba(255, 255, 255, 0.8);
    color: #333;
    font-size: 18px;
    font-weight: bold;
    z-index: 10; /* Ensure it appears above the chart */
  }
</style>
  