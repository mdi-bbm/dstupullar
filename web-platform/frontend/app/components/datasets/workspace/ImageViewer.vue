<template>
  <div class="image-viewer">
    
    <div v-if="loading" class="loading">
      <v-progress-circular indeterminate></v-progress-circular>
    </div>
    
    <div v-else-if="records && records.length > 0" class="gallery">

      <div class="gallery-controls">

        <div class="image-name">
          {{ currentImageName }}

          <div v-if="currentRecord" class="annotation-indicators">
            <v-chip v-if="currentRecord.detection_link" size="x-small" color="#2746f1" text-color="white">
              {{ $t('imageviewer.detection') }}
            </v-chip>

            <v-chip v-if="currentRecord.segmentation_link" size="x-small" color="green" text-color="white">
              {{ $t('imageviewer.segmentation') }}
            </v-chip>
          </div>
        </div>
        
        <v-dialog v-if="currentRecord" v-model="deleteDialog" max-width="400">
          <template v-slot:activator="{ props: activatorProps }">
            <v-btn 
              :disabled = "!props.is_admin && !props.is_editor"
              icon 
              color="error" 
              size="small"
              v-bind="activatorProps"
              :title="$t('imageviewer.delete_record')"
            >
              <v-icon>mdi-delete</v-icon>
            </v-btn>
          </template>
          
          <v-card>
            <v-card-title>{{ $t('imageviewer.delete_record_title') }}</v-card-title>
            <v-card-text>{{ $t('imageviewer.delete_record_text') }} "{{ currentImageName }}"?</v-card-text>
            <v-card-actions>
              <v-spacer></v-spacer>
              <v-btn @click="deleteDialog = false">{{ $t('imageviewer.cancel') }}</v-btn>
              <v-btn color="error" @click="confirmDelete">{{ $t('imageviewer.delete') }}</v-btn>
            </v-card-actions>
          </v-card>
        </v-dialog>
  
      </div>
 
      <div class="main-image" ref ="mainImageEl">
        <div 
          class="canvas-container" 
          ref="containerEl" 
          @mousedown="handleMouseDown"
          @mousemove="handleMouseMove"
          @mouseup="handleMouseUp"
          @mouseleave="handleMouseLeave"
          @contextmenu.prevent="handleContextMenu"
          @wheel="handleWheelOnCanvas"
        >
          <img 
            ref="imageEl"
            :src="currentRecord?.record_link" 
            :alt="`Image ${currentIndex + 1}`"
            @load="onImageLoad"
            class="main-image-content"
         
          />
          <canvas 
            ref="canvasEl"
            class="annotation-canvas"
            :class="{ 'canvas-visible': showAnnotations || isDrawing }"
          ></canvas>
        </div>
      </div>
      
      <div 
        class="thumbnails"
        ref="thumbnailsContainer"
        @wheel="handleWheelScroll"
        >
        <v-tooltip
          v-for="(record, index) in records"
          :key="record.record_id"
          location="top"
        >
          <template v-slot:activator="{ props: activatorProps }">
            <div 
              v-bind="activatorProps"
              class="thumbnail"
              :class="{ 'active': index === currentIndex }"
              
              >
              <div class="checkbox-wrapper">
                <v-checkbox
                  :disabled = "!props.is_admin && !props.is_editor"
                  :model-value="getCheckboxValue(record)"
                  @update:model-value="handleCheckboxClick(record)"
                  class="thumbnail-checkbox"
                  hide-details
                  @click.stop
                ></v-checkbox>
              </div>

              <img :src="record.record_link" @click="$emit('select-image', index)"/>
              <div v-if="record.detection_link" class="thumb-indicator detection"></div>
              <div v-if="record.segmentation_link" class="thumb-indicator segmentation"></div>

            </div>
          </template>

          <span>{{ getImageName(record.record_link) }}</span>
        </v-tooltip>
      </div>
    </div>
    
    <div v-else class="no-images">
      <v-icon>mdi-image-off</v-icon>
      <p>{{ $t('imageviewer.no_images') }}</p>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick, onUnmounted } from 'vue'
const { authPost, authDelete } = useAuthFetch()
import panzoom from 'panzoom'
let panzoomInstance = null
const props = defineProps({
  asset: Object,
  records: Array,
  currentIndex: Number,
  loading: Boolean,
  annotationMode: String,
  activeTool: String,
  activeClass: Object, 
  lableProperties: Object, 
  imageSettings: Object,
  brushSettings: Object, 
  selectedScale: Object, 
  is_admin: Boolean, 
  is_editor: Boolean
})
const { t } = useI18n()
const emit = defineEmits(['next', 'prev', 'select-image', 'delete-record', 'update-brush-size', 'validation-record'])

const imageEl = ref(null)
const canvasEl = ref(null)
const containerEl = ref(null)
const mainImageEl = ref(null)
const ctx = ref(null)
const showAnnotations = ref(true)
const imageLoaded = ref(false)
const imageNaturalSize = ref({ width: 0, height: 0 })
const resizeObserver = ref(null)
const deleteDialog = ref(false)
const isDrawing = ref(false)
const currentAnnotation = ref(null)
const startX = ref(0)
const startY = ref(0)
const annotations = ref([]) 
const thumbnailsContainer = ref(null)
const lastX = ref(0)
const lastY = ref(0)
const isErasing = ref(false)
const lastEraseX = ref(0)
const lastEraseY = ref(0)
const zoomLevel = ref(1)    
const canvasInitialized = ref(false)
const translateX = ref(0)
const translateY = ref(0)
const maskImageData = ref(null)
const rulerState = ref({
  isMeasuring: false,
  startPoint: { x: 0, y: 0 },
  endPoint: { x: 0, y: 0 },
  distance: 0,
  realDistance: 0
})

const startRulerMeasurement = (event) => {
  const rect = canvasEl.value.getBoundingClientRect()
  const scaleX = canvasEl.value.width / rect.width  
  const scaleY = canvasEl.value.height / rect.height 
  
  const x = (event.clientX - rect.left) * scaleX  
  const y = (event.clientY - rect.top) * scaleY   
  
  rulerState.value = {
    isMeasuring: true,
    startPoint: { x, y },
    endPoint: { x, y },
    distance: 0,
    realDistance: 0
  }

  drawAnnotations()
}

const updateRulerMeasurement = (event) => {
  if (!rulerState.value.isMeasuring) return
  
  const rect = canvasEl.value.getBoundingClientRect()
  const scaleX = canvasEl.value.width / rect.width  
  const scaleY = canvasEl.value.height / rect.height
  
  const x = (event.clientX - rect.left) * scaleX  
  const y = (event.clientY - rect.top) * scaleY  
  
  rulerState.value.endPoint = { x, y }

  const dx = x - rulerState.value.startPoint.x
  const dy = y - rulerState.value.startPoint.y
  const pixelDistance = Math.sqrt(dx * dx + dy * dy)
  
  rulerState.value.distance = pixelDistance

  if (props.selectedScale) {
    rulerState.value.realDistance = pixelDistance * parseFloat(props.selectedScale.value_per_pixel)
  }

  drawAnnotations()
}
const finishRulerMeasurement = () => {
  rulerState.value.isMeasuring = false
}

const drawRuler = () => {
  if (!ctx.value) return

  const { startPoint, endPoint, distance } = rulerState.value
  
  ctx.value.save()

  ctx.value.strokeStyle = '#ff0000'
  ctx.value.lineWidth = 2
  ctx.value.setLineDash([5, 5])

  ctx.value.beginPath()
  ctx.value.moveTo(startPoint.x, startPoint.y)
  ctx.value.lineTo(endPoint.x, endPoint.y)
  ctx.value.stroke()
  
  ctx.value.setLineDash([])
  
  ctx.value.fillStyle = '#ff0000'
  ctx.value.beginPath()
  ctx.value.arc(startPoint.x, startPoint.y, 4, 0, Math.PI * 2)
  ctx.value.fill()
  
  ctx.value.beginPath()
  ctx.value.arc(endPoint.x, endPoint.y, 4, 0, Math.PI * 2)
  ctx.value.fill()

  const midX = (startPoint.x + endPoint.x) / 2
  const midY = (startPoint.y + endPoint.y) / 2

  ctx.value.fillStyle = props.activeClass.color
  ctx.value.lineWidth = 1
  ctx.value.font = '20px Arial'
  ctx.value.textAlign = 'center'
  ctx.value.textBaseline = 'bottom'
  
  const text = `${rulerState.value.realDistance.toFixed(2)}${props.selectedScale.unit}`
  ctx.value.strokeText(text, midX, midY - 10)
  ctx.value.fillText(text, midX, midY - 10)
  ctx.value.restore()
}

const confirmDelete = async () => {
  if (!currentRecord.value) return
  
  try {
    await authDelete(`/api/record/${currentRecord.value.record_id}/`)
    deleteDialog.value = false
    emit('delete-record')
    currentRecord.value = null
  } catch (error) {
    console.error('Error deleting record:', error)
  }
}
const getCheckboxValue = (record) => {
  return props.annotationMode === 'detection' 
    ? record.validation_bbox_flag 
    : record.validation_mask_flag
}

const handleCheckboxClick = async (record) => {
  try {
    const response = await authPost(`/api/record/validation/${record.record_id}/`, {
      mode: props.annotationMode.charAt(0).toUpperCase() + props.annotationMode.slice(1)
    })
    emit('validation-record', response.data)
   

    
  } catch (error) {
    console.error('Error updating validation:', error)
  }
}


const handleWheelScroll = (event) => {
  if (!thumbnailsContainer.value) return
  event.preventDefault()
  thumbnailsContainer.value.scrollLeft += event.deltaY
}

const currentRecord = computed(() => {
  return props.records?.[props.currentIndex]
})

const getImageName = (url) => {
  if (!url) return ''
  const path = url.split('?')[0]
  return path.split('/').pop() || 'Изображение'
}

const currentImageName = computed(() => {
  if (!props.records || props.records.length === 0) return ''
  return getImageName(currentRecord.value?.record_link)
})

const calculateScaleFactor = () => {
  if (!imageNaturalSize.value.width || !imageNaturalSize.value.height || !mainImageEl.value) {
    return 1
  }

  const containerWidth = mainImageEl.value.clientWidth - 40 
  const containerHeight = mainImageEl.value.clientHeight - 40

  const widthRatio = containerWidth / imageNaturalSize.value.width
  const heightRatio = containerHeight / imageNaturalSize.value.height
  
  return Math.min(widthRatio, heightRatio, 1)
}

const updateCanvasSize = () => {
  if (!canvasEl.value || !imageEl.value || !imageNaturalSize.value.width) return
  
  const baseScale = calculateScaleFactor()
  const scaledWidth = imageNaturalSize.value.width * baseScale 
  const scaledHeight = imageNaturalSize.value.height * baseScale 
  
  if (!canvasInitialized.value) {
    canvasEl.value.width = imageNaturalSize.value.width
    canvasEl.value.height = imageNaturalSize.value.height
    canvasInitialized.value = true
  }
  
  canvasEl.value.style.width = scaledWidth + 'px'
  canvasEl.value.style.height = scaledHeight + 'px'
  imageEl.value.style.width = scaledWidth + 'px'
  imageEl.value.style.height = scaledHeight + 'px'
  
  if (containerEl.value) {
    containerEl.value.style.width = scaledWidth + 'px'
    containerEl.value.style.height = scaledHeight + 'px'
  }
  
  if (imageLoaded.value && props.annotationMode === 'detection') {
    drawAnnotations()
  }
}

const onImageLoad = async () => {
  if (!imageEl.value) return


  imageNaturalSize.value = {
    width: imageEl.value.naturalWidth,
    height: imageEl.value.naturalHeight
  }
  canvasInitialized.value = false
  imageLoaded.value = true
  updateCanvasSize()
  await nextTick()
  initCanvas()
  await getAnnotationData()
  updateCursor(props.activeTool)
}


const initPanzoom = () => {
  if (panzoomInstance) {
    panzoomInstance.dispose()
  }
  
  if (containerEl.value && imageLoaded.value && props.activeTool === 'zoom') {
    let innerContainer = containerEl.value.querySelector('.inner-zoom-container')
    if (!innerContainer) {
      innerContainer = document.createElement('div')
      innerContainer.className = 'inner-zoom-container'
      innerContainer.style.width = '100%'
      innerContainer.style.height = '100%'
      innerContainer.style.position = 'relative'
      
      while (containerEl.value.firstChild) {
        innerContainer.appendChild(containerEl.value.firstChild)
      }
      containerEl.value.appendChild(innerContainer)
    }
    innerContainer.style.transform = 'none'
    panzoomInstance = panzoom(innerContainer, {
      zoomSpeed: 0.1,
      minZoom: 1,
      maxZoom: 5,
      bounds: true,
      boundsPadding: 0,
      
 
      filterKey: () => true
    })

    panzoomInstance.on('zoom', (e) => {
      zoomLevel.value = e.getTransform().scale
      limitPanToContent(innerContainer)
    })
    
  
 
    panzoomInstance.on('pan', (e) => {
      const transform = e.getTransform()
      translateX.value = transform.x
      translateY.value = transform.y
      limitPanToContent(innerContainer)
      
    })
    
    panzoomInstance.on('panstart', () => {
      updateCursor(props.activeTool, false) 
    })
    
    panzoomInstance.on('panend', () => {
      updateCursor(props.activeTool, true) 
    })
  }
}

const limitPanToContent = (innerContainer) => {
  if (!panzoomInstance || !innerContainer || !containerEl.value) return

  const transform = panzoomInstance.getTransform()
  const scale = transform.scale
  const originalWidth = innerContainer.offsetWidth
  const originalHeight = innerContainer.offsetHeight
  const containerWidth = containerEl.value.offsetWidth
  const containerHeight = containerEl.value.offsetHeight
  const scaledWidth = originalWidth * scale
  const scaledHeight = originalHeight * scale
  const maxX = 0
  const maxY = 0
  const minX = -Math.max(0, scaledWidth - containerWidth)
  const minY = -Math.max(0, scaledHeight - containerHeight)
  const clampedX = Math.min(maxX, Math.max(minX, transform.x))
  const clampedY = Math.min(maxY, Math.max(minY, transform.y))

  if (transform.x !== clampedX || transform.y !== clampedY) {
    panzoomInstance.moveTo(clampedX, clampedY)
  }
}

const initCanvas = () => {
  if (!canvasEl.value || !imageEl.value) return
  ctx.value = canvasEl.value.getContext('2d')
}

const drawAnnotations = async () => {
  
  if (!ctx.value || !imageLoaded.value) return
  
  if (props.annotationMode === 'segmentation' && rulerState.value.isMeasuring && !maskImageData.value) {
    maskImageData.value = ctx.value.getImageData(0, 0, canvasEl.value.width, canvasEl.value.height)
  }

  ctx.value.clearRect(0, 0, canvasEl.value.width, canvasEl.value.height)
  ctx.value.globalAlpha = 1

  if (maskImageData.value && props.annotationMode === 'segmentation') {
    ctx.value.putImageData(maskImageData.value, 0, 0)
  }

  annotations.value.forEach(annotation => {
    ctx.value.strokeStyle = annotation.class.color
    ctx.value.lineWidth = 2
    ctx.value.strokeRect(annotation.x, annotation.y, annotation.width, annotation.height)
    ctx.value.fillStyle = annotation.class.color
    ctx.value.font = '12px Arial'
    ctx.value.fillText(annotation.class.name, annotation.x, annotation.y - 5)
  })
  
  if (currentAnnotation.value) {
    ctx.value.strokeStyle = currentAnnotation.value.class.color
    ctx.value.lineWidth = 2
    ctx.value.setLineDash([5, 5]) 
    ctx.value.strokeRect(
      currentAnnotation.value.x,
      currentAnnotation.value.y,
      currentAnnotation.value.width,
      currentAnnotation.value.height
    )
    ctx.value.setLineDash([]) 
  }
  
  if (rulerState.value && rulerState.value.isMeasuring) {
    drawRuler()
  }

}

const getAnnotationData = async () => {
  annotations.value = []
  if (!ctx.value) return

  if (props.annotationMode === 'detection' && currentRecord.value?.detection_link) {
    await drawDetectionAnnotations()
  }
  
  if (props.annotationMode === 'segmentation' && currentRecord.value?.segmentation_link) {
    await drawSegmentationAnnotations()
  }
  await drawAnnotations()
}

const handleMouseDown = (event) => {
  if (!props.activeClass || !imageLoaded.value) {
    return
  }
  
  const rect = canvasEl.value.getBoundingClientRect()
  const scaleX = canvasEl.value.width / rect.width
  const scaleY = canvasEl.value.height / rect.height
  
  const x = (event.clientX - rect.left) * scaleX
  const y = (event.clientY - rect.top) * scaleY
  if (event.button === 0) {
    if (!props.activeClass) return

    if (props.activeTool === 'rectangle') {
      startX.value = x
      startY.value = y
      
      isDrawing.value = true
      currentAnnotation.value = {
        type: 'rectangle',
        class: props.activeClass,
        x: startX.value,
        y: startY.value,
        width: 0,
        height: 0
      }
    }
    
    else if (props.activeTool === 'brush') {
      isDrawing.value = true
      lastX.value = x
      lastY.value = y
      
      
      drawBrushPoint(x, y)
    }
    else if (props.activeTool === 'ruler') {
      startRulerMeasurement(event)
    }
  }
  else if (event.button === 2) {
    isErasing.value = true
    lastEraseX.value = x
    lastEraseY.value = y
    eraseAtPoint(x, y) 
  }
}
const handleMouseMove = (event) => {
  const rect = canvasEl.value.getBoundingClientRect()
  const scaleX = canvasEl.value.width / rect.width
  const scaleY = canvasEl.value.height / rect.height
  
  const currentX = (event.clientX - rect.left) * scaleX
  const currentY = (event.clientY - rect.top) * scaleY
  
  if (isDrawing.value) {
    if (props.activeTool === 'rectangle') {
      const x = Math.min(startX.value, currentX)
      const y = Math.min(startY.value, currentY)
      const width = Math.abs(currentX - startX.value)
      const height = Math.abs(currentY - startY.value)
      
      currentAnnotation.value = {
        type: 'rectangle',
        class: props.activeClass,
        x: x,
        y: y,
        width: width,
        height: height
      }
      drawAnnotations()
    }
    
    else if (props.activeTool === 'brush') {
      drawBrushLine(lastX.value, lastY.value, currentX, currentY)
      lastX.value = currentX
      lastY.value = currentY
    }
   
  }
  else if (props.activeTool === 'ruler') {
    updateRulerMeasurement(event)
  }

  if (isErasing.value) {
    eraseLine(lastEraseX.value, lastEraseY.value, currentX, currentY)
    lastEraseX.value = currentX
    lastEraseY.value = currentY
  }
}

const handleMouseUp = (event) => {
  if (event.button === 0) {
    isDrawing.value = false
    
    if (props.activeTool === 'rectangle') {
      if (Math.abs(currentAnnotation.value.width) > 5 && Math.abs(currentAnnotation.value.height) > 5) {
        annotations.value.push({ ...currentAnnotation.value })
      }
      drawAnnotations()
    }
    else if (props.activeTool === 'ruler') {
      finishRulerMeasurement()
    }
  }
  else if (event.button === 2) {
    isErasing.value = false
  }
  currentAnnotation.value = null
}

const drawBrushPoint = (x, y) => {
  if (!ctx.value) return
  
  ctx.value.fillStyle = props.activeClass.color
  ctx.value.globalAlpha = 1
  
  ctx.value.beginPath()
  ctx.value.arc(x, y, props.brushSettings.size, 0, Math.PI * 2)
  ctx.value.fill()
  
  ctx.value.globalAlpha = 1
}

const drawBrushLine = (fromX, fromY, toX, toY) => {
  if (!ctx.value) return

  ctx.value.save()
  ctx.value.strokeStyle = props.activeClass.color
  ctx.value.lineWidth = props.brushSettings.size * 2
  ctx.value.lineCap = 'round'
  ctx.value.lineJoin = 'round' 
  ctx.value.globalAlpha = 1
  
  ctx.value.beginPath()
  ctx.value.moveTo(fromX, fromY)
  ctx.value.lineTo(toX, toY)
  ctx.value.stroke()

  ctx.value.restore()
}

const handleMouseLeave = () => {

  if (isDrawing.value && props.activeTool === 'rectangle') {
    
    currentAnnotation.value = null
    drawAnnotations()
  }
  isDrawing.value = false
  isErasing.value = false

}

const handleContextMenu = (event) => {
  event.preventDefault()
  
  if (!imageLoaded.value) return
  
  const rect = canvasEl.value.getBoundingClientRect()
  const scaleX = canvasEl.value.width / rect.width
  const scaleY = canvasEl.value.height / rect.height
  const clickX = (event.clientX - rect.left) * scaleX
  const clickY = (event.clientY - rect.top) * scaleY

  if (props.annotationMode === 'detection') {
    if (annotations.value.length === 0) return
    
    const annotationToDelete = findClosestAnnotation(clickX, clickY)
    
    if (annotationToDelete) {
      const index = annotations.value.indexOf(annotationToDelete)
      if (index !== -1) {
        annotations.value.splice(index, 1)
        emit('annotation-deleted', annotationToDelete)
        drawAnnotations()
      }
    }
  }
}

const handleWheelOnCanvas = (event) => {
  if (props.activeTool === 'brush') {
    event.preventDefault()

    const delta = Math.sign(event.deltaY) 
    let newSize = props.brushSettings.size - delta
    newSize = Math.max(1, Math.min(newSize, 50)) 
    
    if (newSize !== props.brushSettings.size) {
      emit('update-brush-size', newSize)
      updateCursor(props.activeTool)
    }
  } 
}

const eraseLine = (fromX, fromY, toX, toY) => {
  if (!ctx.value) return

  ctx.value.save()
  ctx.value.globalCompositeOperation = 'destination-out'
  ctx.value.lineWidth = props.brushSettings.size * 2
  ctx.value.lineCap = 'round'
  
  ctx.value.beginPath()
  ctx.value.moveTo(fromX, fromY)
  ctx.value.lineTo(toX, toY)
  ctx.value.stroke()
  
  ctx.value.globalCompositeOperation = 'source-over'
  ctx.value.restore()
}

const eraseAtPoint = (x, y) => {
  if (!ctx.value) return
  
  ctx.value.save()
  ctx.value.globalCompositeOperation = 'destination-out'

  ctx.value.beginPath()
  ctx.value.arc(x, y, props.brushSettings.size * 1.5, 0, Math.PI * 2)
  ctx.value.fill()
  
  ctx.value.globalCompositeOperation = 'source-over'
  ctx.value.restore()
}

const findClosestAnnotation = (x, y) => {
  if (annotations.value.length === 0) return null
  
  let closestAnnotation = null
  let minDistance = Infinity
  let smallestArea = Infinity 
  
  annotations.value.forEach(annotation => {
    if (annotation.type !== 'rectangle') return
    
    const left = annotation.x
    const right = annotation.x + annotation.width
    const top = annotation.y
    const bottom = annotation.y + annotation.height
    const area = annotation.width * annotation.height 

    const isInside = x >= left && x <= right && y >= top && y <= bottom
    
    if (isInside) {
      if (area < smallestArea) {
        smallestArea = area
        closestAnnotation = annotation
        minDistance = 0
      }
    } else {
      let closestX = x
      let closestY = y
      
      if (x < left) closestX = left
      else if (x > right) closestX = right
      
      if (y < top) closestY = top
      else if (y > bottom) closestY = bottom
      
      const distanceX = x - closestX
      const distanceY = y - closestY
      const distance = Math.sqrt(distanceX * distanceX + distanceY * distanceY)
      
      if (distance < minDistance) {
        minDistance = distance
        closestAnnotation = annotation
      }
    }
  })
  
  return closestAnnotation
}

const drawDetectionAnnotations = async () => {
  try {
    annotations.value = []
    const response = await fetch(currentRecord.value.detection_link)
    const data = await response.json()
    
    const imageKey = Object.keys(data)[0]
    const boxes = data[imageKey]
    
    boxes.forEach(box => {
      annotations.value.push({
        type: 'rectangle',
        class: { name: box.label_name, color: props.lableProperties[box.label_name] }, 
        x: box.bbox_x,
        y: box.bbox_y,
        width: box.bbox_width,
        height: box.bbox_height
      })
    })
   
  } catch (error) {
    console.error('Error loading detection annotations:', error)
  }
}

const drawSegmentationAnnotations = async () => {
  try {
    const response = await fetch(currentRecord.value.segmentation_link)
    const blob = await response.blob()
    const imgUrl = URL.createObjectURL(blob)
    
    const maskImg = new Image()
    maskImg.onload = () => {
      ctx.value.drawImage(
        maskImg, 
        0, 0, 
        imageNaturalSize.value.width, 
        imageNaturalSize.value.height
      )
      URL.revokeObjectURL(imgUrl)
    }
    
    maskImg.onerror = (error) => {
      console.error('Error loading mask image:', error)
      URL.revokeObjectURL(imgUrl)
    }
    
    maskImg.src = imgUrl
    
  } catch (error) {
    console.error('Error loading segmentation annotations:', error)
  }
}

const handleResize = () => {
  if (imageLoaded.value) {
    updateCanvasSize()
  }
}

watch(() => props.currentIndex, async () => {
  annotations.value = []
  currentAnnotation.value = null
  imageLoaded.value = false
  if (panzoomInstance) {
    panzoomInstance.dispose()
    panzoomInstance = null
    initPanzoom()
  }
})

watch(() => props.annotationMode, () => {
  if (showAnnotations.value && imageLoaded.value) {
    annotations.value = []
    getAnnotationData()
    initPanzoom()
  }
})

watch(showAnnotations, (val) => {
  if (val && imageLoaded.value) {
    drawAnnotations()
  }
})

const updateCursor = (tool, panorzoom = true) => {
  let cursorStyle = 'default'
  
  if (tool === 'rectangle') {
    cursorStyle = 'crosshair'
  } else if (tool === 'brush') {
    const baseSize = props.brushSettings.size 

    let compensation = 1
    if (imageEl.value && imageEl.value.naturalWidth > 0) {
      compensation = imageEl.value.clientWidth / imageEl.value.naturalWidth * zoomLevel.value
    } 
    const radius = baseSize * compensation
    const diameter = radius * 2

    cursorStyle = `url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="${diameter}" height="${diameter}" viewBox="0 0 ${diameter} ${diameter}"><circle cx="${radius}" cy="${radius}" r="${radius}" fill="${props.activeClass?.color.replace('#', '%23')}" opacity="1"/></svg>') ${radius} ${radius}, auto`
  }else if (tool === 'zoom') {
    if (panorzoom) {
      cursorStyle = 'zoom-in' 
    }
    else {
      cursorStyle = 'grabbing'
    }
   
  }
    
  if (containerEl.value) {
    containerEl.value.style.cursor = cursorStyle
  }
  
  if (imageEl.value) {
    imageEl.value.style.cursor = cursorStyle
  }
}

const applyImageFilters = () => {
  if (!imageEl.value) return
  imageEl.value.style.filter = `
    brightness(${props.imageSettings.brightness})
    contrast(${props.imageSettings.contrast})
  `
}

watch(() => props.imageSettings, () => {
  applyImageFilters() 
  if (canvasEl.value) {
    canvasEl.value.style.opacity = props.imageSettings.opacity
  }
}, { deep: true })

watch(() => props.brushSettings, () => {
  updateCursor(props.activeTool)
}, { deep: true })


const clearAnnotations = () => {
  annotations.value = []
  drawAnnotations()
}

const getSegmentationMask = () => {
  if (!canvasEl.value) return null

  const tempCanvas = document.createElement('canvas')
  tempCanvas.width = canvasEl.value.width
  tempCanvas.height = canvasEl.value.height
  const tempCtx = tempCanvas.getContext('2d')
  
  tempCtx.drawImage(canvasEl.value, 0, 0)
  
  return new Promise((resolve) => {
    tempCanvas.toBlob(resolve, 'image/png')
  })
}

watch(() => props.activeTool, (newTool) => {
  updateCursor(newTool)
  if (newTool === 'zoom' && !panzoomInstance) {
    initPanzoom()
  } 
  else if (newTool !== 'zoom' && panzoomInstance) {
    panzoomInstance.pause()
  }
  else if (newTool === 'zoom' && panzoomInstance) {
    panzoomInstance.resume()
  }
  else if (newTool === 'brush') {
    drawAnnotations()
  }
}, { immediate: true })

watch(() => props.activeClass, () => {
  updateCursor(props.activeTool)
}, { deep: true })

watch(containerEl, (newContainer) => {
  if (newContainer) {
    updateCursor(props.activeTool)
  }
})

watch(imageEl, (newImage) => {
  if (newImage) {
    updateCursor(props.activeTool)
  }
}) 

onMounted(() => {
  resizeObserver.value = new ResizeObserver(handleResize)
  if (containerEl.value) {
    resizeObserver.value.observe(containerEl.value)
  }
  window.addEventListener('resize', handleResize)

  
})

onUnmounted(() => {
  if (resizeObserver.value) {
    resizeObserver.value.disconnect()
  }
  window.removeEventListener('resize', handleResize)
   if (panzoomInstance) {
    panzoomInstance.dispose()
  }
})

defineExpose({
  annotations, 
  currentImageName, 
  imageNaturalSize, 
  currentRecord, 
  clearAnnotations, 
  getSegmentationMask
})
</script>

<style scoped>
.image-viewer {
  height: 100%;
  display: flex;
  flex-direction: column;
  user-select: none; 
}

.gallery {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.gallery-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.image-name {
  flex: 1;
  font-weight: 500;
  color: rgba(var(--v-theme-primary));
  padding-right: 16px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.annotation-indicators {
  display: flex;
  gap: 4px;
  margin-top: 4px;
}

.navigation-center {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-shrink: 0;
}

.image-counter {
  font-weight: 500;
  min-width: 80px;
  text-align: center;
}

.controls-right {
  flex: 1;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.main-image {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  padding: 20px;
  position: relative;
}

.canvas-container {
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  overflow: hidden;
  margin: 0 auto; 
}


.main-image-content,
.annotation-canvas {
  will-change: transform; 
}

.main-image-content {
  transform: none !important;
}

.annotation-canvas {
  transform: none !important;
}
.main-image-content {
  width: 100%;
  height: 100%;
  object-fit: contain;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  user-select: none;
  -webkit-user-drag: none;
}

.annotation-canvas {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  opacity: 0;
  transition: opacity 0.3s ease;
  pointer-events: none;
}

.annotation-canvas.canvas-visible {
  opacity: 1;
  pointer-events: auto; 
}

.thumbnails {
  display: flex;
  gap: 8px;
  padding: 16px;
  overflow-x: auto;
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.thumbnail {
  position: relative;
  width: 60px;
  height: 60px;
  cursor: pointer;
  border: 2px solid transparent;
  border-radius: 6px;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.checkbox-wrapper {
  position: absolute;
  top: -6px;    
  left: -6px;   
  z-index: 20;  
  border-radius: 50%;
}

.thumbnail-checkbox :deep(.v-checkbox-btn) {
  color: rgb(0, 200, 87); 
  background-color: white;
}

.thumbnail-checkbox :deep(.v-selection-control) {
  min-height: unset; 
}

.thumbnail-checkbox :deep(.v-selection-control__wrapper) {
  width: 14px !important;
  height: 14px !important;
}

.thumbnail-checkbox {
  all: unset;
  margin: 0;
  padding: 0;
}

.thumbnail:hover {
  transform: scale(1.05);
  border-color: rgba(var(--v-theme-primary), 0.5);
}

.thumbnail.active {
  border-color: rgb(var(--v-theme-primary));
  box-shadow: 0 2px 8px rgba(var(--v-theme-primary), 0.2);
}

.thumbnail img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 4px;
  user-select: none;
}

.thumb-indicator {
  position: absolute;
  bottom: 2px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 2px solid white;
}

.thumb-indicator.detection {
  left: 2px;
  background-color: #2746f1;
}

.thumb-indicator.segmentation {
  left: 16px;
  background-color: #00FF00;
}

.loading {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
}

.no-images {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 100%;
  color: rgba(var(--v-theme-on-surface-variant));
}
</style>