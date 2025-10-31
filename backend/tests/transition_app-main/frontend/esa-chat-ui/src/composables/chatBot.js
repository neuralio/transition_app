export function chatBot(activeComponents, graphData, profitGraphData, barChartData, wmsLayers, profitWmsLayers, geoJsonData, globalArea, pilotArea, serviceCalled, showPVindicator, mapExplanation) {
  const handleChatbotResponse = (response) => {
 
    const chart_data = response.chart_data
    const map_layers = response.map_layers
    const profit_chart_data = response.profit_chart_data
    const profit_layers = response.profit_layers
    const map_explanation = response.map_explanation
    const action = response.action
    const pilot = response.pilot

    activeComponents.value = {
      map: false,
      graph: false,
      simple_map: false,
      bar_chart: false,
      slider: false,

      profit_map: false,
      profit_graph: false,
      profit_slider: false
    }

    graphData.value = []
    profitGraphData.value = []
    barChartData.value = []
    wmsLayers.value =  []
    profitWmsLayers.value =[]
    pilotArea.value = pilot
    serviceCalled.value = null
    showPVindicator.value = false
    mapExplanation.value = null

    if (action == 'open_map') {
      activeComponents.value.map = true
      geoJsonData.value = null
      globalArea.value = null
      serviceCalled.value = null

    } else if (action == 'show_pv_indicator') {
      showPVindicator.value = true

    } else if (action == "crop_suitability") {
      graphData.value = chart_data
      wmsLayers.value = map_layers
      geoJsonData.value = globalArea.value
      serviceCalled.value = "Crop"

      if (profit_layers && profit_layers.length > 0) {
        profitGraphData.value = profit_chart_data
        profitWmsLayers.value = profit_layers

        activeComponents.value.profit_map = true
        activeComponents.value.profit_slider = true
        activeComponents.value.profit_graph = true
      }

      activeComponents.value.map = true
      activeComponents.value.slider = true
      activeComponents.value.graph = true

    } else if (action == 'pv_suitability') {
      graphData.value = chart_data
      wmsLayers.value = map_layers
      geoJsonData.value = globalArea.value
      serviceCalled.value = "PV"

      activeComponents.value.map = true
      activeComponents.value.slider = true
      activeComponents.value.graph = true
    
    } else if (action && action.includes('abm')) {
      barChartData.value = chart_data
      wmsLayers.value = map_layers
      geoJsonData.value = globalArea.value
      serviceCalled.value = action.toUpperCase()
      mapExplanation.value = map_explanation

      activeComponents.value.map = true
      activeComponents.value.slider = true
      activeComponents.value.graph = true

      if (chart_data && chart_data.length > 0)
        activeComponents.value.bar_chart = true
    }
  }

  return { handleChatbotResponse }
}