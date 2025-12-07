<template>
  <div class="asset-navigation" :class="{ 'collapsed': collapsed }">
 
    <div class="panel-header">
      <h3 class="text-h6">{{ $t('assetnavigation.assets') }}</h3>
      <div class="header-actions">
       
        <v-btn 
          :disabled="!props.is_admin && !props.is_editor"
          icon 
          size="small"
          @click="showUploadNewDialog = true"
          :title="$t('assetnavigation.newasset')"
          variant="text"
        >
          <v-icon>mdi-folder-plus</v-icon>
        </v-btn>
        
        <v-btn 
          icon 
          size="small" 
          @click="$emit('toggle-panel')"
          :title="$t('assetnavigation.collapse')"
          variant="text"
        >
          <v-icon>mdi-chevron-left</v-icon>
        </v-btn>
      </div>
    </div>


    <div class="content-wrapper">
      <div v-if="isUploading" class="upload-progress">
        <div class="progress-header">
          <v-icon small color="primary">mdi-cloud-upload</v-icon>
          <span class="ml-2">{{ $t('assetnavigation.uploading') }}</span>
          <v-spacer></v-spacer>
          <span class="progress-percentage">{{ uploadProgress }}%</span>
        </div>
        
        <v-progress-linear
          :model-value="uploadProgress"
          color="primary"
          height="8"
          rounded
          class="my-2"
        ></v-progress-linear>
        
        <div class="progress-details">
          <span class="text-caption text-grey">
            {{ transferInfo.files_uploaded || 0 }}/{{ transferInfo.total_files_expected || 0 }} {{ $t('assetnavigation.filesuploaded') }}
          </span>
        </div>
      </div>


      <div class="assets-list">
        <div 
          v-for="asset in assets" 
          :key="asset.asset_id"
          class="asset-item"
          :class="{ 
            'selected': selectedAsset?.asset_id === asset.asset_id,
            'annotated': asset.records_count > 0,
            'empty': asset.records_count === 0
          }"
          @click="selectAsset(asset)"
          >
        
          <div class="asset-icon-checkbox">
              <v-icon 
                class="asset-icon"
                :color="getStatusColor(asset)"
              >
                {{ getAssetIcon(asset) }}
              
              </v-icon>
              <v-checkbox
                :model-value="getCheckboxValue(asset)"
                class="asset-checkbox"
                @update:model-value="(value) => handleCheckboxClick(asset, value)"
                hide-details
                @click.stop
              ></v-checkbox>
          </div>
          <div class="asset-info">
            <div class="asset-name">{{ asset.asset_name }}</div>
            <div class="asset-meta">
              <span v-if="asset.records_count > 0">
                {{ asset.records_count }} {{ $t('assetnavigation.annotations') }}
              </span>
              <span v-else class="text-grey">{{ $t('assetnavigation.noannotations') }}</span>
            </div>
          </div>
          
          <div class="asset-actions">
       
            <v-btn 
              :disabled="!props.is_admin && !props.is_editor"
              icon 
              size="x-small"
              @click.stop="addToAsset(asset)"
              :title="$t('assetnavigation.addtoasset')"
              variant="text"
              class="action-btn"
            >
              <v-icon size="16">mdi-plus</v-icon>
            </v-btn>
            
           
            
          </div>
        </div>
      </div>

  
      <div v-if="loading" class="loading-state">
        <v-progress-circular indeterminate></v-progress-circular>
        <p class="mt-2">{{ $t('assetnavigation.loading') }}</p>
      </div>

      
      <div v-if="!loading && assets.length === 0" class="empty-state">
        <v-icon size="48" color="grey-lighten-2">mdi-folder-open</v-icon>
        <p class="text-grey mt-2">{{ $t('assetnavigation.noassets') }}</p>
        <v-btn 
          color="primary"
          variant="outlined"
          size="small"
          @click="showUploadNewDialog = true"
          class="mt-4"
        >
          <v-icon left>mdi-plus</v-icon>
          {{ $t('assetnavigation.createfirst') }}
        </v-btn>
      </div>
    </div>

    
    <v-dialog v-model="showUploadNewDialog" max-width="500">
        <v-card>
          <v-card-title>{{ $t('assetnavigation.createasset') }}</v-card-title>
          <v-card-text>
            <v-text-field
              v-model="newAssetName"
              :label="$t('assetnavigation.assetname')"
              :placeholder="$t('assetnavigation.assetnameplaceholder')"
              variant="outlined"
              :disabled="isUploading"
            />
            <FileUpload 
              ref = "fileUploadRef"
              @files-selected="handleNewAssetUpload" 
              :disabled="isUploading"
            />
            

          
          </v-card-text>
          <v-card-actions>
            <v-spacer></v-spacer>
            <v-btn 
              @click="showUploadNewDialog = false" 
              :disabled="isUploading"
            >
             {{ $t('assetnavigation.cancel') }}
            </v-btn>
            <v-btn 
              color="primary" 
              :disabled="!newAssetName || selectedFiles.length === 0 || isUploading"
              @click="createNewAsset"
              :loading="isUploading"
            >
              {{ isUploading ? $t('assetnavigation.uploading') : $t('assetnavigation.create') }}
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>


   <v-dialog v-model="showAddToAssetDialog" max-width="500" v-if="props.is_admin || props.is_editor">
      <v-card>
        <v-card-title>{{ $t('assetnavigation.addtoasset') }} "{{ selectedAssetForAdd?.asset_name }}"</v-card-title>
        <v-card-text>
          <FileUpload 
            ref = "fileUploadRef"
            @files-selected="handleNewAssetUpload" 
            :disabled="isUploading"
          />

      
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn 
            @click="showAddToAssetDialog = false" 
            :disabled="isUploading"
          >
            {{ $t('assetnavigation.cancel') }}
          </v-btn>
          <v-btn 
            color="primary" 
            :disabled="selectedFiles.length === 0 || isUploading"
            @click="uploadToAsset"
            :loading="isUploading"
          >
            {{ isUploading ? $t('assetnavigation.uploading') : $t('assetnavigation.add') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import FileUpload from './FileUpload.vue'
const { t } = useI18n()
const props = defineProps({
  datasetId: String,
  collapsed: Boolean, 
  annotationMode: String, 
  is_admin: Boolean, 
  is_editor: Boolean
})
const { authGet, authPost, authUpload } = useAuthFetch()
const emit = defineEmits(['select-asset', 'toggle-panel', 'open-asset', 'assets-updated', 'validation-asset'])

const fileUploadRef = ref(null)
const assets = ref([])
const loading = ref(false)
const selectedAsset = ref(null)
const showUploadNewDialog = ref(false)
const showAddToAssetDialog = ref(false)
const newAssetName = ref('')
const selectedAssetForAdd = ref(null)
const selectedFiles = ref([])

const isUploading = ref(false)
const uploadProgress = ref(0)
const currentChunk = ref(0)
const totalChunks = ref(0)
const transferInfo = ref({
  files_uploaded: 0,
  total_files_expected: 0,
  status: ''
})
let progressInterval = null

const fetchAssets = async () => {
  loading.value = true

  try {
    const response = await authGet(`/api/datasets/${props.datasetId}/assets/`)
    assets.value = response
    
  } catch (error) {
    console.error('Error fetching assets:', error)
  } finally {
    loading.value = false
  }
}

const handleCheckboxClick = async (asset, value) => {


  try {
    const response = await authPost(`/api/asset/validation/${asset.asset_id}/`, {
      mode: props.annotationMode.charAt(0).toUpperCase() + props.annotationMode.slice(1), 
      validation_flag: value
    })
    
    await fetchAssets()
    emit('validation-asset')
    
  } catch (error) {
    console.error('Error:', error)
    throw error
  }
}
const getCheckboxValue = (asset) => {
  return props.annotationMode === 'detection' 
    ? asset.validation_bbox_flag 
    : asset.validation_mask_flag
}

const selectAsset = (asset) => {
  selectedAsset.value = asset
  emit('select-asset', asset)
}


const addToAsset = (asset) => {
  selectedAssetForAdd.value = asset
  showAddToAssetDialog.value = true
}

const getAssetIcon = (asset) => {
  const ext = asset.asset_name.split('.').pop().toLowerCase()
  if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext)) return 'mdi-image'
  if (['mp4', 'mov', 'avi', 'webm'].includes(ext)) return 'mdi-video'
  return 'mdi-folder'
}

const getStatusColor = (asset) => {
  if (asset.records_count > 0) return 'rgb(74, 153, 255)'
  return 'grey'
}

const handleNewAssetUpload = (uploadedFiles) => {
  selectedFiles.value = uploadedFiles
  
}

const createTransfer = async (totalFiles, assetName = null, assetId = null) => {
  try {
    const response = await authPost(`/api/dataset/${props.datasetId}/transfers/`, {
      total_files_expected: totalFiles,
      asset_name: assetName,
      asset_id: assetId
    })
    
   
    return response.transfer_id
    
  } catch (error) {
    
    throw error
  }
}

const pollTransferProgress = async (transferId) => {
  try {
    const response = await authGet(`/api/dataset/${props.datasetId}/transfers/${transferId}/`)
    
    
    transferInfo.value = {
      files_uploaded: response.files_uploaded,
      total_files_expected: response.total_files_expected,
      status: response.status
    }
    
    
    uploadProgress.value = response.progress
    
    
    
    return response
    
  } catch (error) {
    
    throw error
  }
}


const uploadFiles = async (files, assetName = null, assetId = null, metadata) => {
  const CHUNK_SIZE = 100
  totalChunks.value = Math.ceil(files.length / CHUNK_SIZE)
  currentChunk.value = 0
  isUploading.value = true
  uploadProgress.value = 0
  transferInfo.value = {
    files_uploaded: 0,
    total_files_expected: files.length,
    status: 'in_progress'
  }
  
  let transferId = null
  
  try {
 
    transferId = await createTransfer(files.length, assetName, assetId)
   
    

    progressInterval = setInterval(async () => {
      if (transferId) {
        await pollTransferProgress(transferId)
      }
    }, 2000) 
    
    let metadata_formdata = {}
    if (metadata){
      
        for (let key in metadata) {
          if (metadata[key] !== '' && metadata[key] !== null && key !== 'ageYears' && key !== 'ageMonths') {
            metadata_formdata[key] = metadata[key]
          }
        }
        metadata_formdata['age'] = metadata['ageYears'] * 12 + metadata['ageMonths']
      

    }
   
 
    for (let i = 0; i < files.length; i += CHUNK_SIZE) {
      currentChunk.value++
      const chunk = files.slice(i, i + CHUNK_SIZE)
      const formData = new FormData()
      
      chunk.forEach(file => {
        formData.append('files', file)
      })
      
      if (assetName) {
        formData.append('asset_name', assetName)
      } else if (assetId) {
        formData.append('asset_id', assetId)
      }
      formData.append('metadata', JSON.stringify(metadata_formdata))
      formData.append('transfer_id', transferId)
      

      
      const response = await authUpload(`/api/dataset/${props.datasetId}/assets/upload/`, formData)
      

      if (response.progress) {
        uploadProgress.value = response.progress
      }
      
      
    }
    
 
    clearInterval(progressInterval)
    progressInterval = null

    const finalProgress = await pollTransferProgress(transferId)
    uploadProgress.value = finalProgress.progress
    
    return true
    
  } catch (error) {

    if (progressInterval) {
      clearInterval(progressInterval)
      progressInterval = null
    }
   
    throw error
  } finally {
    isUploading.value = false

  }
}

const createNewAsset = async () => {
  if (!newAssetName.value || selectedFiles.value.length === 0) return
  showUploadNewDialog.value = false

  try {
    await uploadFiles(selectedFiles.value, newAssetName.value, null, fileUploadRef.value.metadata)

    
    newAssetName.value = ''
    selectedFiles.value = []
    
    await fetchAssets()
    emit('assets-updated')
    
  } catch (error) {

  }
}

const uploadToAsset = async () => {
  if (!selectedAssetForAdd.value || selectedFiles.value.length === 0) return
  showAddToAssetDialog.value = false
  try {
    await uploadFiles(
      selectedFiles.value, 
      null, 
      selectedAssetForAdd.value.asset_id, 
      fileUploadRef.value.metadata
    )
    
    
    selectedFiles.value = []
    
    await fetchAssets()
    emit('assets-updated')
    
  } catch (error) {
 
  }
}

onMounted(fetchAssets)

defineExpose({
  fetchAssets
})
</script>

<style scoped>
.asset-navigation {
  height: 100%;
  display: flex;
  flex-direction: column;
  transition: all 0.3s ease;
}

.asset-navigation.collapsed {
  opacity: 0;
  transform: translateX(-10px);
  pointer-events: none;
}

.asset-navigation:not(.collapsed) {
  opacity: 1;
  transform: translateX(0);
  pointer-events: all;
}

.content-wrapper {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  transition: all 0.3s ease;
}

.search-section {
  padding: 16px;
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  transition: all 0.3s ease;
}

.assets-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
  transition: all 0.3s ease;
  padding-bottom: 100px;
}

.asset-item {
  display: flex;
  align-items: center;
  padding: 12px;
  cursor: pointer;
  border-radius: 8px;
  margin-bottom: 4px;
  transition: all 0.2s ease;
  border: 1px solid transparent;
  background-color: rgba(var(--v-theme-surface));
}

.asset-item:hover {
  background-color: rgba(var(--v-theme-primary), 0.08);
  border-color: rgb(var(--v-theme-primary));
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.asset-item.selected {
  background-color: rgba(var(--v-theme-primary), 0.12);
  border-color: rgb(var(--v-theme-primary));
  border-left: 4px solid rgb(var(--v-theme-primary));
}

.asset-item.annotated {
  border-left: 3px solid rgb(74, 153, 255);
}

.asset-item.empty {
  border-left: 3px solid rgb(var(--v-theme-grey));
}

.asset-icon {
  margin-right: 12px;
  flex-shrink: 0;
  transition: all 0.3s ease;
  font-size: 33px;
}

.asset-info {
  flex: 1;
  min-width: 0;
}

.asset-name {
  font-weight: 500;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: all 0.3s ease;
}

.asset-meta {
  font-size: 12px;
  transition: all 0.3s ease;
}

.loading-state {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 40px;
  color: rgb(var(--v-theme-grey));
  transition: all 0.3s ease;
}

.empty-state {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 40px;
  color: rgb(var(--v-theme-grey));
  transition: all 0.3s ease;
}

.upload-progress {
  background:rgba(var(--v-theme-surface));
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 16px;
  border: 1px solid rgba(var(--v-theme-grey));
}

.progress-header {
  display: flex;
  align-items: center;
  font-size: 14px;
  font-weight: 500;
}

.progress-percentage {
  font-weight: bold;
  color: primary;
}

.progress-details {
  margin-top: 4px;
}

.asset-icon-checkbox{
  padding: 0px;
  display: grid;
  position: relative;
}
.asset-checkbox{
  all: unset;
  margin: 0;
  padding: 0;
  position: absolute;
  top: -3px;
  left: -3px;
 
}
.asset-checkbox:deep(.v-checkbox-btn) {

  color: rgb(0, 200, 87); 
  background-color: white;
}
.asset-checkbox :deep(.v-selection-control) {
  min-height: unset; 
}
.asset-checkbox :deep(.v-selection-control__wrapper) {
  
  width: 14px !important;
  height: 14px !important;
}

</style>