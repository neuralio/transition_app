<template>
  <div :class="['chart-wrapper', { dark: isDark }]">
    <!-- Top explanation -->
    <div class="flex flex-col max-w-[100%] items-start top-explanation" v-if="validationExplanation">
      <div
          class="relative p-3 rounded-lg text-sm bg-gray-200 dark:bg-gray-700 dark:text-white text-gray-900 rounded-bl-none"
          v-html="validationExplanation"
          style="line-height: 1.4;"
      ></div>
    </div>

    <!-- Loading Overlay -->
    <div v-if="loading" class="loading-overlay">
      <p>Data loading...</p>
      <p>Please wait...</p>
    </div>

    <!-- Chart Container -->
    <div :id="chartId" class="chart-container"></div>

    <!-- Bottom explanation -->
    <div class="flex flex-col max-w-[100%] items-start bottom-explanation" v-if="chartExplanation">
      <div
          class="relative p-3 rounded-lg text-sm bg-gray-200 dark:bg-gray-700 dark:text-white text-gray-900 rounded-bl-none"
          v-html="chartExplanation"
          style="line-height: 1.4;"
      ></div>
    </div>
  </div> 
</template>
  
<script setup>
  import * as echarts from 'echarts'
  import { ref, onMounted, watch, defineProps, nextTick, toRaw } from 'vue'

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
    chartId: {
      type: String,
      required: true
    }
  })

  const chartInstance = ref(null) // To store the ECharts instance
  const loading = ref(false)
  const validationExplanation = ref("")
  const chartExplanation = ref("")
  const validationScenario = ref("")


  watch(() => props.datasets, (newVal) => {
      if (newVal.length > 0) {
        handleDataUpdate(newVal)
      }
    },
    { deep: true }
  )


  watch(() => props.isDark, async (newVal) => {
    console.log("Display mode changed. Re-initializing bar chart...")

    if (chartInstance.value) {
      chartInstance.value.dispose()
    }

    await nextTick()
    initChart() // recreate chart instance
    if (props.datasets.length > 0) {
      updateChart(props.datasets)
    }
  })

  onMounted(() => {
    nextTick(() => {
      initChart() // Initialize chart after component mounts

      if (props.datasets.length === 0) {
        console.log("No data to plot...")
      } else {
        // Delay a little to ensure chart container is sized and ready
        setTimeout(() => {
          // Props provided, use them to update the chart
          handleDataUpdate(props.datasets)
        }, 100)  // 100ms
      }   
    }) 
  })

  const initChart = () => {
    // Initialize the ECharts instance
    const chartDom = document.getElementById(props.chartId)
    if (chartDom && chartDom.offsetWidth > 0 && chartDom.offsetHeight > 0) {
      if (echarts.getInstanceByDom(chartDom)) {
        echarts.dispose(chartDom)
      }
      chartInstance.value = echarts.init(chartDom)
    } else {
      console.error("⛔ Chart DOM not fully ready:", props.chartId)
    }
  }

  const deepUnwrap = (val) => {
    if (Array.isArray(val)) {
      return val.map(deepUnwrap)
    } else if (val !== null && typeof val === 'object') {
      const raw = {}
      for (const key in val) {
        raw[key] = deepUnwrap(val[key])
      }
      return raw
    } else {
      return val
    }
  }

  const handleDataUpdate = (newData) => {
    loading.value = true // Show loading state during data preparation

    // Use manual deep unwrap instead of structuredClone
    const rawData = deepUnwrap(toRaw(newData))

    setTimeout(() => {
      updateChart(rawData)
      loading.value = false  // Hide loading once chart is updated
    }, 0)  // Short delay for smoother UI experience
  }

  const updateChart = async (dataSets) => {
    if (!dataSets || dataSets.length === 0) {
      console.warn("No data provided to update chart.")
      return   // Exit if no data is available or chart instance is missing
    }

    if (!chartInstance.value) {
      console.warn("Chart instance not found. Re-initializing...")
      initChart()
      if (!chartInstance.value) return
    }


    if (!Array.isArray(dataSets)) {
      console.error("updateChart expects an array but got:", dataSets)
      return
    }

    const chartData = dataSets[0] || {} // Only using first object for now

    validationExplanation.value = chartData.validation_explanation || ""
    chartExplanation.value = chartData.explanation || ""
    validationScenario.value = chartData.scenario || ""

    const offset = parseFloat((chartData.offset ?? 0).toFixed(3))
    const features = chartData.data || []


    if (!Array.isArray(features) || features.length === 0) {
      console.warn("❗Invalid chart data: 'features' missing or not an array.", chartData)
      return
    }

    const categories = features.map(f => f.feature)
    // const contributions = features.map(f => parseFloat((f.values?.[0] ?? 0).toFixed(2)))
    const contributions = features.map(f => {
      const raw = Array.isArray(f.values) && typeof f.values[0] === 'number' ? f.values[0] : 0
      return parseFloat(raw.toFixed(3))
    })

    if (contributions.some(c => isNaN(c))) {
      console.error("❌ Found NaN in contributions array:", contributions)
      return
    }

    const cumulative = []
    const baseSeries = []
    let base = offset

    // Calculate starting base for each feature bar (for stacking)
    for (const c of contributions) {
      baseSeries.push(base)
      cumulative.push(base + c)
    }

    const textColor = props.isDark ? '#fff' : '#333'
    const bgColor = props.isDark ? '#1f2937' : '#fff'

    const colorPalette = [ "#009688", "#dbdea4", "#d64bde", "#4ba3de", "#f76a6a", "#9e9e9e", "#997fdb", "#7cd69d", "#88abbd", "#4bded7", "#4b67de"]

    const minVal = base
    const maxVal = Math.max(...cumulative)

    if (!Array.isArray(categories) || categories.length === 0 || !contributions.length) {
      console.error("Invalid data: cannot render chart with empty features or contributions")
      return
    }

    const colorFunction = (params) => colorPalette[params.dataIndex % colorPalette.length]
    const labelFormatter = (p) => {
      return p.value === 0 ? `            ${p.value.toFixed(3)}` : p.value.toFixed(3)
    }

    const options = {
      title: {
        text: `${(props.serviceCalled).toUpperCase() || 'Model'} Feature Contributions ${validationScenario.value}`,
        left: 'center',
        textStyle: {
          color: textColor,
          fontWeight: 'bold'
        }
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: (params) =>
          params
            .map(p => `${p.seriesName || p.name}: ${p.value.toFixed(3)}`)
            .join('<br/>')
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true
      },
      xAxis: {
        type: 'value',
        min: minVal,
        max: maxVal,
        axisLabel: {
          color: textColor,
          formatter: val => val.toFixed(3)
        },
        axisLine: { lineStyle: { color: textColor } },
        splitLine: {
          show: true,
          lineStyle: {
            type: 'dashed',
            color: props.isDark ? '#444' : '#ddd'
          }
        }
      },
      yAxis: {
        type: 'category',
        data: categories,
        axisLabel: {
        color: textColor,
          formatter: (label) => `  ${label}` // prepend spaces to move left
        },
        axisLine: { lineStyle: { color: textColor } },
        axisTick: { show: false }
      },
      series: [
        {
          name: 'Base',
          type: 'bar',
          stack: 'total',
          itemStyle: { color: 'transparent' },
          data: baseSeries
        },
        {
          name: 'Feature Contribution',
          type: 'bar',
          stack: 'total',
          label: {
            show: true,
            position: 'inside',
            formatter: labelFormatter,
            color: textColor
          },
          itemStyle: {
            color:  colorFunction
          },
          data: contributions
        }
      ],
      backgroundColor: bgColor,
      markLine: {
        symbol: 'none',
        lineStyle: {
          color: '#888',
          type: 'solid'
        },
        label: {
          formatter: `Offset: ${offset.toFixed(3)}`,
          position: 'start',
          color: textColor
        },
        data: [{ xAxis: offset }]
      }
    };

    try {
      const allSeriesValid = options.series.every(
        s => s && typeof s.type === 'string'
      )

      if (!allSeriesValid) {
        console.error("❌ Invalid series in chart config:", options.series)
        return
      }


      if (!options.series || options.series.some(s => !s.type)) {
        console.error("❌ Chart config is invalid — missing 'type' in series", options.series)
        return
      }

      await nextTick()

      chartInstance.value.setOption(options, true)
      chartInstance.value.resize()
    } catch (e) {
      console.error("🔥 Error setting chart options:", e)
    }
  }
</script>

<style scoped>
  .chart-wrapper {
    position: relative;
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
    margin: 10px 0 0 0;
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

  .explanation {
    font-size: 14px;
    line-height: 1.5;
    margin: 20px 0px;
    padding: 10px;
    border-radius: 6px;
    background-color: #f9f9f9;
    color: #333;
    border-left: 4px solid #ccc;
  }

  .dark .explanation {
    background-color: #2c2c2c;
    color: #eee;
    border-left-color: #888;
  }

  .top-explanation {
    margin-top: 10px;
    margin-bottom: 10px;
  }

  .bottom-explanation {
    margin-top: 10px;
    margin-bottom: 30px;
  }
</style>
  