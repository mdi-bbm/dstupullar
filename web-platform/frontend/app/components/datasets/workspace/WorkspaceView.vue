<template>
  <div class="workspace-container">

    <div class="workspace-layout" :class="{ 'assets-collapsed': isAssetsPanelCollapsed, 'tools-collapsed': isToolsPanelCollapsed }">
     
      <div class="assets-panel">
        <AssetNavigation 
          :annotationMode="annotationMode"
          :datasetId="datasetId"
          :is_admin="is_admin"
          :is_editor="is_editor"
          :collapsed="isAssetsPanelCollapsed"
          @select-asset="onSelectAsset"
          @open-asset="onOpenAsset"
          @toggle-panel="toggleAssetsPanel"
          @validation-asset="handleValidation"
          ref="assetNavigationRef"
        />
      </div>

      <div class="main-content">
        <ImageViewer 
          v-if="selectedAsset"
          :annotationMode="annotationMode"
          :is_admin="is_admin"
          :is_editor="is_editor"
          :asset="selectedAsset"
          :records="currentRecords"
          :current-index="currentImageIndex"
          :loading="loadingRecords"
          :active-tool="activeTool"
          :active-class="activeClass"
          :lableProperties="lableProperties"
          :imageSettings="imageSettings"
          :brushSettings="brushSettings"
          :selectedScale="selectedScale"
          @next="nextImage"
          @prev="prevImage"
          @select-image="currentImageIndex = $event"
          @delete-record="handleDeleteUpdate"
          @update-brush-size="handleBrushSizeUpdate"
          @validation-record="handleValidation"
          ref="ImageViewerRef"
        />
        
        <div v-else class="placeholder">
          <v-icon size="64" color="grey-lighten-2">mdi-image-multiple</v-icon>
          <p class="text-grey mt-4">{{  $t('workspaceview.select_asset') }}</p>
        </div>
      </div>

      <div class="tools-panel">
        <AnnotationTools 
          v-show="selectedAsset && !isToolsPanelCollapsed"
          :datasetId="datasetId"
          :is_admin="is_admin"
          :is_editor="is_editor"
          :annotationMode="annotationMode"
          :lableProperties="lableProperties"
          :favoriteClasses="favoriteClasses"
          @close="isToolsPanelCollapsed = true"
          @clear-annotations="clearAnnotations"
          @save-annotations="saveAnnotations"
          ref="annotationToolsRef"
        />
        
        <div v-if="!isToolsPanelCollapsed && !selectedAsset" class="tools-placeholder">
          <v-icon size="48" color="grey-lighten-2">mdi-tools</v-icon>
          <p class="text-grey mt-2">{{  $t('workspaceview.select_asset_to_annotate') }}</p>
        </div>
      </div>

    </div>

    <v-btn 
      v-if="isAssetsPanelCollapsed"
      class="expand-button left"
      icon
      size="small"
      @click="toggleAssetsPanel"
      :title="$t('workspaceview.expand_assets_panel')"
    >
      <v-icon>mdi-chevron-right</v-icon>
    </v-btn>

    <v-btn 
      v-if="isToolsPanelCollapsed"
      class="expand-button right"
      icon
      size="small"
      @click="isToolsPanelCollapsed = false"
      :title="$t('workspaceview.expand_tools_panel')"
    >
      <v-icon>mdi-chevron-left</v-icon>
    </v-btn>
    <v-snackbar v-model="successSnackbar" color="success" timeout="3000">
      {{ $t('workspaceview.success_message') }}
      <template v-slot:actions>
        <v-btn icon @click="successSnackbar = false">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </template>
    </v-snackbar>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import AssetNavigation from './AssetNavigation.vue'
import ImageViewer from './ImageViewer.vue'
import AnnotationTools from './AnnotationTools.vue'
const { t } = useI18n()
const { authGet, authUpload } = useAuthFetch()
const props = defineProps({
  datasetId: {
    type: String,
    required: true
  },
  annotationMode: String, 
  lableProperties: Object, 
  favoriteClasses: Array, 
  is_admin: Boolean, 
  is_editor: Boolean
})
const successSnackbar = ref(false)
const selectedAsset = ref(null)
const isAssetsPanelCollapsed = ref(false)
const isToolsPanelCollapsed = ref(true)
const currentRecords = ref([])
const currentImageIndex = ref(0)
const currentImageUrl = ref('')
const loadingRecords = ref(false)
const annotationToolsRef = ref(null)
const ImageViewerRef = ref(null)
const assetNavigationRef = ref(null)

const activeTool = computed(() => {
  return annotationToolsRef.value?.activeTool || 'rectangle'
})

const activeClass = computed(() => {
  return annotationToolsRef.value?.activeClass || null
})

const brushSettings = computed(() => {
  return annotationToolsRef.value?.brushSettings || {}
})

const selectedScale = computed(() => {
  return annotationToolsRef.value?.selectedScale || []
})

const imageSettings = computed(() => {
  return annotationToolsRef.value?.imageSettings || {}
})

const handleBrushSizeUpdate = (newSize) => {
  annotationToolsRef.value.updateBrushSize(newSize)
}
const toggleAssetsPanel = () => {
  isAssetsPanelCollapsed.value = !isAssetsPanelCollapsed.value
}

const loadAssetRecords = async (assetId, not_was_annotation = true) => {
   if (not_was_annotation) {
      loadingRecords.value = true
      currentImageIndex.value = 0
    }
    
  try {
    const response = await authGet(`/api/assets/${assetId}/records/`)
    currentRecords.value = response.records
    if (currentRecords.value.length > 0) {
      currentImageUrl.value = currentRecords.value[0].record_link
    }
  } catch (error) {
    console.error('Error loading records:', error)
  } finally {
    loadingRecords.value = false
  }
}

const nextImage = () => {
  if (currentImageIndex.value < currentRecords.value.length - 1) {
    currentImageIndex.value++
  }
}

const prevImage = () => {
  if (currentImageIndex.value > 0) {
    currentImageIndex.value--
  }
}

const onSelectAsset = (asset) => {
  selectedAsset.value = asset
  isToolsPanelCollapsed.value = false
}

const onOpenAsset = (asset) => {
  selectedAsset.value = asset
}

const handleDeleteUpdate = async () => {
  await assetNavigationRef.value.fetchAssets()

  if (selectedAsset.value) {
    await loadAssetRecords(selectedAsset.value.asset_id, false)  
  }
}

const clearAnnotations = () => {
  ImageViewerRef.value.clearAnnotations()
}

const handleValidation = async () => {
  await loadAssetRecords(selectedAsset.value.asset_id, false)
}

const convertAnnotationsToServerFormat = () => {
  if (!ImageViewerRef.value.currentRecord || ImageViewerRef.value.annotations.length === 0) {
    return null
  }

  const imageName = ImageViewerRef.value.currentImageName
  const imageWidth = ImageViewerRef.value.imageNaturalSize.width
  const imageHeight = ImageViewerRef.value.imageNaturalSize.height

  const formattedAnnotations = ImageViewerRef.value.annotations.map(annotation => ({
    label_name: annotation.class.name,
    bbox_x: annotation.x,
    bbox_y: annotation.y,
    bbox_width: annotation.width,
    bbox_height: annotation.height,
    image_name: imageName,
    image_width: imageWidth,
    image_height: imageHeight
  }))

  return {
    [imageName.replace(/\.[^/.]+$/, "")]: formattedAnnotations
  }
}

const saveAnnotations = async () => {
  try {
    const formData = new FormData();
    formData.append('processing_type', props.annotationMode.charAt(0).toUpperCase() + props.annotationMode.slice(1));
    
    if (props.annotationMode === 'detection') {
      const annotations = convertAnnotationsToServerFormat();
      const fileName = ImageViewerRef.value.currentImageName;
      
      formData.append('record_metadata_link', 
        new Blob([JSON.stringify(annotations)], { type: 'application/json' }),
        `${fileName.replace(/\.[^/.]+$/, "")}_bbox.json`
      );
    }
    else if (props.annotationMode === 'segmentation') {
      const segmentationBlob = await ImageViewerRef.value.getSegmentationMask()
      const fileName = ImageViewerRef.value.currentImageName;
      
      formData.append('record_metadata_link', 
        segmentationBlob,
        `${fileName.replace(/\.[^/.]+$/, "")}_mask.png`
      );
    }
    
    await authUpload(
      `/api/dataset/assets/records/${ImageViewerRef.value.currentRecord.record_id}/`, 
      formData
    );
    successSnackbar.value = true
    setTimeout(() => {
      successSnackbar.value = false
    }, 1500)
    await assetNavigationRef.value.fetchAssets()
    await loadAssetRecords(selectedAsset.value.asset_id, false)
  } catch (error) {
    console.error('Error saving annotations:', error)
  }
}

watch(selectedAsset, async (newAsset) => {
  if (newAsset) {
    await loadAssetRecords(newAsset.asset_id)
    activeTool.value = props.annotationMode === 'detection' ? 'rectangle' : 'brush'
  } else {
    currentRecords.value = []
    currentImageUrl.value = ''
    currentImageIndex.value = 0
  }
})

watch(currentImageIndex, (newIndex) => {
  if (currentRecords.value.length > 0) {
    currentImageUrl.value = currentRecords.value[newIndex]?.record_link || ''
  }
})


defineExpose({ handleDeleteUpdate})
</script>

<style scoped>
.workspace-container {
  height: calc(100vh - 64px);
  overflow: hidden;
  position: relative;
}

.workspace-layout {
  display: grid;
  grid-template-columns: minmax(250px, 300px) 1fr minmax(250px, 300px);
  height: 100%;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.workspace-layout.assets-collapsed {
  grid-template-columns: 0px 1fr minmax(250px, 300px);
}

.workspace-layout.tools-collapsed {
  grid-template-columns: minmax(250px, 300px) 1fr 0px;
}

.workspace-layout.assets-collapsed.tools-collapsed {
  grid-template-columns: 0px 1fr 0px;
}

.assets-panel {
  border-right: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  overflow: hidden;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.workspace-layout.assets-collapsed .assets-panel {
  border-right: none;
}

.tools-panel {
  border-left: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  overflow: hidden;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.workspace-layout.tools-collapsed .tools-panel {
  border-left: none;
}

.main-content {
  position: relative;
  overflow: hidden;
  background-color: rgba(var(--v-theme-background));
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.placeholder {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 100%;
}

.tools-placeholder {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 100%;
  padding: 20px;
  text-align: center;
}

.expand-button {
  position: absolute;
  top: 16px;
  z-index: 1000;
  background-color: rgb(var(--v-theme-surface)) !important;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  transition: all 0.3s ease;
}

.expand-button:hover {
  transform: scale(1.1);
  box-shadow: 0 4px 12px rgba(0,0,0,0.2);
}

.expand-button.left {
  left: 8px;
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.expand-button.right {
  right: 8px;
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.expand-button {
  opacity: 0;
  animation: fadeIn 0.3s ease forwards;
  animation-delay: 0.1s;
}

@keyframes fadeIn {
  to {
    opacity: 1;
  }
}
</style>